import json
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest
from PIL import Image

from goldcoast.agents.prompts.video_detect import DetectedMoment
from goldcoast.agents.video_agent import VideoAgent, merge_moments
from goldcoast.llm.client import GeminiClient, LLMCallError, RecordedCall
from goldcoast.llm.recordings import RecordedResponseClient, ReplayMissError
from goldcoast.media.frames import FrameExtractionError, extract_candidates
from goldcoast.models.manifest import ClipEntry, ClipManifest, ManifestError, ManifestMoment
from goldcoast.settings import Settings
from goldcoast.sources.clip_source import ClipError, LocalClipSource

FIXTURES = Path(__file__).parent / "fixtures" / "model_calls" / "video"


@pytest.fixture(scope="module")
def clip(tmp_path_factory):
    root = tmp_path_factory.mktemp("video")
    path = root / "gymnastics_simone.mp4"
    subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-f",
            "lavfi",
            "-i",
            "testsrc2=size=64x64:rate=2:duration=300",
            "-c:v",
            "mpeg4",
            str(path),
        ],
        check=True,
        capture_output=True,
        timeout=60,
    )
    return path


@pytest.fixture
def settings(tmp_path):
    return Settings(
        replay=True,
        video_model="recorded-video",
        image_model="recorded-image",
        judge_model="recorded-judge",
        clip_manifest=tmp_path / "manifest.json",
    )


def cached(settings, clip, **changes):
    moment = ManifestMoment(
        start_s=0,
        end_s=5,
        best_frame_s=1,
        hype_score=8,
        description="Great landing",
        event_context="final",
    )
    entry = ClipEntry(
        file=clip.name,
        sport="gymnastics",
        athlete_id="simone-biles",
        analyzed=True,
        analyzed_by="manual",
        moments=[moment],
        **changes,
    )
    ClipManifest(entries=[entry]).save(settings.clip_manifest)
    return entry


def test_manifest_hit_and_edit_extract_fresh_frames_without_calls(settings, clip, tmp_path):
    cached(settings, clip)
    client = RecordedResponseClient(tmp_path / "absent", tmp_path / "calls")
    first = VideoAgent(client, settings, tmp_path / "first").detect(clip)[0]
    assert first.athlete_id == "simone-biles"
    assert first.source == "manual"
    manifest = ClipManifest.load(settings.clip_manifest)
    manifest.entries[0].moments[0].best_frame_s = 4
    manifest.save(settings.clip_manifest)
    second = VideoAgent(client, settings, tmp_path / "second").detect(clip)[0]
    assert second.best_frame_s == 4
    assert first.best_frame_path.read_bytes() != second.best_frame_path.read_bytes()
    assert not client.sequences


def test_real_recording_replays_and_persists_manifest(settings, clip, tmp_path):
    client = RecordedResponseClient(FIXTURES, tmp_path / "calls")
    moments = VideoAgent(client, settings, tmp_path / "run").detect(clip)
    assert moments
    assert client.sequences["video_detect"] == 1
    entry = ClipManifest.load(settings.clip_manifest).get(clip.name)
    assert entry.analyzed and entry.analyzed_by == "gemini"
    for moment in moments:
        assert moment.hype_score >= 6
        with Image.open(moment.best_frame_path) as image:
            assert image.format == "PNG"
        assert (tmp_path / "run" / "moments" / f"{moment.id}.json").is_file()


def test_empty_recording_is_cached(settings, clip, tmp_path):
    client = RecordedResponseClient(FIXTURES / "empty", tmp_path / "calls")
    agent = VideoAgent(client, settings, tmp_path / "run")
    assert agent.detect(clip) == []
    assert agent.detect(clip) == []
    assert client.sequences["video_detect"] == 1
    assert ClipManifest.load(settings.clip_manifest).get(clip.name).analyzed


def test_invalid_manifest_and_timestamp_never_reanalyze(settings, clip, tmp_path):
    settings.clip_manifest.write_text("not JSON")
    client = RecordedResponseClient(tmp_path / "absent", tmp_path / "calls")
    agent = VideoAgent(client, settings, tmp_path / "run")
    with pytest.raises(ManifestError):
        agent.detect(clip)
    cached(settings, clip)
    manifest = ClipManifest.load(settings.clip_manifest)
    manifest.entries[0].moments[0].end_s = 1000
    manifest.entries[0].moments[0].best_frame_s = 999
    manifest.save(settings.clip_manifest)
    with pytest.raises(FrameExtractionError, match="duration"):
        agent.detect(clip)
    assert not client.sequences


def test_overlap_merge_and_threshold():
    def moment(start, end, score):
        return DetectedMoment(
            start_s=start,
            end_s=end,
            best_frame_s=start,
            hype_score=score,
            description="landing",
            event_context="final",
        )

    results = merge_moments([moment(1, 3, 7), moment(2, 5, 9), moment(7, 8, 4)], 6)
    assert len(results) == 1
    assert (results[0].start_s, results[0].end_s, results[0].hype_score) == (1, 5, 9)


def test_source_and_candidates(clip, tmp_path):
    source = LocalClipSource(clip.parent)
    assert source.open(clip.name) == clip
    assert source.list_clips() == [clip]
    with pytest.raises(ClipError):
        source.open("../elsewhere.mp4")
    choices = extract_candidates(clip, 1, 1, out_dir=tmp_path / "candidates")
    assert [t for t, _ in choices] == [0, 1, 2]
    assert all(p.is_file() for _, p in choices)


def test_missing_replay_is_explicit(settings, clip, tmp_path):
    with pytest.raises(ReplayMissError, match="video_detect"):
        VideoAgent(
            RecordedResponseClient(tmp_path, tmp_path / "calls"), settings, tmp_path / "run"
        ).detect(clip)


def test_files_api_polls_active_and_never_inlines_large_video(settings, tmp_path):
    from google.genai import types

    class Files:
        def __init__(self):
            self.uploaded = 0
            self.polled = 0

        def upload(self, **kwargs):
            self.uploaded += 1
            return types.File(name="files/clip", state="PROCESSING")

        def get(self, **kwargs):
            self.polled += 1
            return types.File(name="files/clip", state="ACTIVE", uri="https://example.test/clip")

    files = Files()
    path = tmp_path / "large.mp4"
    with path.open("wb") as handle:
        handle.seek(21 * 1024 * 1024)
        handle.write(b"x")
    client = GeminiClient(settings, tmp_path / "calls", client=SimpleNamespace(files=files))
    part = client.video_part(path)
    assert part.inline_data is None
    assert part.file_data.file_uri == "https://example.test/clip"
    assert files.uploaded == files.polled == 1
    reused = client.video_part(path)
    assert reused.file_data.file_uri == part.file_data.file_uri
    assert files.uploaded == 1
    assert files.polled == 2


def test_files_processing_failure(settings, tmp_path):
    from google.genai import types

    path = tmp_path / "large.mp4"
    with path.open("wb") as handle:
        handle.seek(21 * 1024 * 1024)
        handle.write(b"x")
    files = SimpleNamespace(upload=lambda **kwargs: types.File(name="files/bad", state="FAILED"))
    client = GeminiClient(settings, tmp_path / "calls", client=SimpleNamespace(files=files))
    with pytest.raises(LLMCallError, match="processing failed"):
        client.video_part(path)


def test_force_preserves_curated_athlete_and_notes(settings, clip, tmp_path):
    cached(settings, clip, notes="owner annotation")
    client = RecordedResponseClient(FIXTURES, tmp_path / "calls")
    moments = VideoAgent(client, settings, tmp_path / "run").detect(clip, force=True)
    assert all(m.athlete_id == "simone-biles" for m in moments)
    assert ClipManifest.load(settings.clip_manifest).get(clip.name).notes == "owner annotation"


def test_recordings_remain_valid_json():
    for path in FIXTURES.glob("*.json"):
        record = RecordedCall.model_validate(json.loads(path.read_text()))
        assert record.stage.startswith("video_")


def test_wire_schema_omits_unsupported_keys_but_local_validation_is_strict():
    from pydantic import ValidationError

    from goldcoast.agents.prompts.video_detect import VideoAnalysis
    from goldcoast.agents.structured import response_schema

    wire = json.dumps(response_schema(VideoAnalysis))
    assert "additionalProperties" not in wire
    assert "$ref" not in wire
    assert "nullable" in wire
    with pytest.raises(ValidationError):
        VideoAnalysis.model_validate({"sport": "gymnastics", "invented": "field"})
