from pathlib import Path

import pytest

from goldcoast.agents.ad_agent import AdAgent, AdGenerationError
from goldcoast.agents.judge_agent import JudgeAgent
from goldcoast.llm.recordings import RecordedResponseClient
from goldcoast.models.pipeline import AdFormat
from goldcoast.pipeline.judge_loop import judge_loop

FIXTURES = Path(__file__).parent / "fixtures/model_calls/judge/loop"


@pytest.mark.parametrize(
    "start,retries,expected_attempts,final_attempt,passed",
    [
        (2, 2, 1, 1, True),
        (0, 2, 3, 3, True),
        (0, 1, 2, 1, False),
    ],
)
def test_recorded_loop_paths(
    seed,
    agent_settings,
    creative_inputs,
    tmp_path,
    start,
    retries,
    expected_attempts,
    final_attempt,
    passed,
):
    client = RecordedResponseClient(FIXTURES, tmp_path / "model_calls")
    client.sequences.update(ad_generate=start, judge_score=start)
    agent_settings.judge_max_retries = retries
    brief, moment = creative_inputs
    events = []
    result = judge_loop(
        AdAgent(client, seed, agent_settings, tmp_path),
        JudgeAgent(client, seed, agent_settings, tmp_path),
        brief,
        moment,
        AdFormat.PORTRAIT,
        lambda event, payload: events.append((event, payload)),
    )
    assert len(result.attempts) == expected_attempts
    assert result.final_ad.attempt == final_attempt
    assert result.final_verdict.passed is passed
    assert [event for event, _ in events].count("ad_final") == 1
    assert events[-1][0] == "ad_final"
    assert [event for event, _ in events].count("ad_regenerating") == expected_attempts - 1
    if expected_attempts > 1:
        assert "Prior failures" in result.attempts[1][0].prompt_used


def test_generation_failure_keeps_best_judged_attempt(
    seed, agent_settings, creative_inputs, tmp_path
):
    client = RecordedResponseClient(FIXTURES, tmp_path / "model_calls")

    class FailsOnRetry(AdAgent):
        def generate_one(self, brief, moment, fmt, attempt=1, hints=None):
            if attempt > 1:
                raise AdGenerationError("recorded test retry failure")
            return super().generate_one(brief, moment, fmt, attempt, hints)

    brief, moment = creative_inputs
    result = judge_loop(
        FailsOnRetry(client, seed, agent_settings, tmp_path),
        JudgeAgent(client, seed, agent_settings, tmp_path),
        brief,
        moment,
        AdFormat.PORTRAIT,
    )
    assert len(result.attempts) == 1
    assert not result.final_verdict.passed
    assert result.errors == ["recorded test retry failure"]
