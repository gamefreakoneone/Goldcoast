import shutil
from pathlib import Path

import pytest

from goldcoast.agents.video_agent import VideoAgent
from goldcoast.llm.client import GeminiClient
from goldcoast.models.pipeline import RunStatus
from goldcoast.pipeline.events import EventBus
from goldcoast.pipeline.orchestrator import Pipeline
from goldcoast.pipeline.run_store import RunStore

SOURCE_ID = "20260912-230559-0d2470"
FIXTURE = Path(__file__).parent / "fixtures/runs" / SOURCE_ID


@pytest.fixture
def installed_run(tmp_path):
    store = RunStore(tmp_path)
    shutil.copytree(FIXTURE, store.run_dir(SOURCE_ID))
    return store


def test_full_replay_and_replay_of_replay_are_independent(
    installed_run, seed, agent_settings, monkeypatch
):
    def forbidden(*args, **kwargs):
        raise AssertionError("Replay must not create a live client or detect/decode the clip")

    monkeypatch.setattr(GeminiClient, "__init__", forbidden)
    monkeypatch.setattr(VideoAgent, "detect", forbidden)
    store = installed_run
    original = store.get_run(SOURCE_ID)
    original_events = EventBus(store.run_dir(SOURCE_ID)).backlog()
    expected = {
        ad.id.removeprefix(SOURCE_ID): ad.image_path.read_bytes() for ad in store.ads(SOURCE_ID)
    }
    pipeline = Pipeline(agent_settings, seed, store)
    replay = pipeline.run(original.clip_path, SOURCE_ID)
    assert replay.status == RunStatus.COMPLETED
    assert not replay.failures
    assert (len(replay.moment_ids), len(replay.brief_ids), len(replay.ad_ids)) == (3, 6, 12)
    assert [e.type for e in EventBus(store.run_dir(replay.id)).backlog()] == [
        e.type for e in original_events
    ]
    for ad in store.ads(replay.id):
        assert ad.image_path.read_bytes() == expected[ad.id.removeprefix(replay.id)]
    assert not (store.run_dir(replay.id) / "model_calls/http_requests").exists()
    assert len(store.verdicts(replay.id)) == len(store.ads(replay.id))
    shutil.rmtree(store.run_dir(SOURCE_ID))
    again = pipeline.run(original.clip_path, replay.id)
    assert again.status == RunStatus.COMPLETED
    assert len(again.ad_ids) == 12
    assert all(ad.image_path.is_file() for ad in store.ads(again.id))
    assert not agent_settings.clip_manifest.exists()


def test_missing_record_fails_without_network_fallback(installed_run, seed, agent_settings):
    store = installed_run
    (store.run_dir(SOURCE_ID) / "model_calls/match_rerank_1.json").unlink()
    run = Pipeline(agent_settings, seed, store).run(store.get_run(SOURCE_ID).clip_path, SOURCE_ID)
    assert run.status == RunStatus.FAILED
    assert "stage=match_rerank, sequence=1" in run.failures[-1].message
    assert EventBus(store.run_dir(run.id)).backlog()[-1].type == "run_failed"


def test_replay_rejects_different_clip(installed_run, seed, agent_settings):
    run = Pipeline(agent_settings, seed, installed_run).run(
        Path("sample_clips/other.mp4"), SOURCE_ID
    )
    assert run.status == RunStatus.FAILED
    assert "must match" in run.failures[-1].message


def test_one_format_failure_does_not_stop_other_briefs(
    installed_run, seed, agent_settings, monkeypatch
):
    import goldcoast.pipeline.orchestrator as orchestration

    original_loop = orchestration.judge_loop
    calls = 0

    def fail_after_first_result(*args, **kwargs):
        nonlocal calls
        result = original_loop(*args, **kwargs)
        calls += 1
        if calls == 1:
            raise ValueError("Injected finalization failure")
        return result

    monkeypatch.setattr(orchestration, "judge_loop", fail_after_first_result)
    store = installed_run
    run = Pipeline(agent_settings, seed, store).run(store.get_run(SOURCE_ID).clip_path, SOURCE_ID)
    assert run.status == RunStatus.COMPLETED
    assert calls == 12 and len(run.ad_ids) == 11
    assert run.failures[0].message == "Injected finalization failure"
