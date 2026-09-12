from pathlib import Path
from types import SimpleNamespace

import pytest

from goldcoast.agents.ad_agent import AdAgent
from goldcoast.agents.judge_agent import JudgeAgent, score_verdict
from goldcoast.agents.prompts.judge_rubric import CriterionScores
from goldcoast.llm.recordings import RecordedResponseClient

FIXTURES = Path(__file__).parent / "fixtures/model_calls"


def test_real_pass_fail_and_images_unchanged(seed, agent_settings, creative_inputs, tmp_path):
    brief, moment = creative_inputs
    ads = AdAgent(
        RecordedResponseClient(FIXTURES / "ad/creative", tmp_path / "ad-calls"),
        seed,
        agent_settings,
        tmp_path,
    ).generate(brief, moment)
    judge = JudgeAgent(
        RecordedResponseClient(FIXTURES / "judge/direct", tmp_path / "judge-calls"),
        seed,
        agent_settings,
        tmp_path,
    )
    results = []
    for ad in ads:
        before = ad.image_path.read_bytes()
        verdict = judge.judge(ad, brief, moment)
        assert ad.image_path.read_bytes() == before
        assert (tmp_path / "verdicts" / f"{ad.id}_attempt_1.json").is_file()
        results.append(verdict)
    assert results[0].passed and results[0].scores.overall == 7
    assert not results[1].passed and results[1].scores.overall == 4
    assert any("Billes" in issue for issue in results[1].issues)
    assert results[1].regeneration_hints


@pytest.mark.parametrize("blocked", [False, True])
def test_invalid_output_or_block_is_failing_verdict(
    seed, agent_settings, creative_inputs, tmp_path, blocked
):
    brief, moment = creative_inputs
    ad = AdAgent(
        RecordedResponseClient(FIXTURES / "ad/creative", tmp_path / "ad-calls"),
        seed,
        agent_settings,
        tmp_path,
    ).generate_one(brief, moment, brief.formats[0])

    class InvalidClient:
        calls = 0

        def generate(self, *args, **kwargs):
            self.calls += 1
            return SimpleNamespace(
                response_text="invalid",
                response_raw={"response": {"prompt_feedback": {"block_reason": "SAFETY"}}}
                if blocked
                else {},
            )

    client = InvalidClient()
    verdict = JudgeAgent(client, seed, agent_settings, tmp_path).judge(ad, brief, moment)
    assert not verdict.passed and verdict.scores.overall == 0
    assert client.calls == (1 if blocked else 2)
    assert "Judge failed" in verdict.issues[0]


@pytest.mark.parametrize(
    "values,overall,passed",
    [
        ([7, 7, 7, 7, 7], 7, True),
        ([10, 10, 4, 10, 10], 4, False),
        ([4, 10, 10, 10, 10], 9, False),
        ([5, 8, 8, 8, 8], 7, True),
        ([6, 6, 7, 6, 6], 6, False),
    ],
)
def test_thresholds_are_computed_in_code(agent_settings, values, overall, passed):
    scores, result = score_verdict(
        CriterionScores(**dict(zip(CriterionScores.model_fields, values, strict=True))),
        agent_settings,
    )
    assert scores.overall == overall
    assert result is passed
