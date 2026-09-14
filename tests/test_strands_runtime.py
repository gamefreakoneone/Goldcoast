import json

import pytest
from pydantic import BaseModel
from strands import tool
from strands.models import Model

from goldcoast.agents.runtime import AgentRuntime, ExecutionBudget, ExecutionStopped
from goldcoast.llm.recordings import ReplayMissError


class Answer(BaseModel):
    total: int


class ScriptedModel(Model):
    def __init__(self):
        self.calls = 0

    def get_config(self):
        return {"model_id": "offline-strands-test"}

    def update_config(self, **kwargs):
        pass

    async def stream(self, messages, tool_specs=None, system_prompt=None, **kwargs):
        self.calls += 1
        yield {"messageStart": {"role": "assistant"}}
        if self.calls == 1:
            yield {
                "contentBlockStart": {"start": {"toolUse": {"toolUseId": "sum-1", "name": "add"}}}
            }
            yield {
                "contentBlockDelta": {"delta": {"toolUse": {"input": '{"left": 2, "right": 3}'}}}
            }
            yield {"contentBlockStop": {}}
            yield {"messageStop": {"stopReason": "tool_use"}}
        else:
            assert any("toolResult" in block for m in messages for block in m["content"])
            yield {"contentBlockDelta": {"delta": {"text": "The total is 5."}}}
            yield {"contentBlockStop": {}}
            yield {"messageStop": {"stopReason": "end_turn"}}
        yield {
            "metadata": {
                "usage": {"inputTokens": 10, "outputTokens": 5, "totalTokens": 15},
                "metrics": {"latencyMs": 1},
            }
        }

    async def structured_output(self, output_model, *args, **kwargs):
        self.calls += 1
        yield {"output": output_model(total=5)}


def make_tool(calls):
    @tool(description="Add two integers.")
    def add(left: int, right: int) -> int:
        calls.append((left, right))
        return left + right

    return add


@pytest.mark.asyncio
async def test_real_strands_tool_loop_and_replay(tmp_path):
    calls = []
    tools = [make_tool(calls)]
    model = ScriptedModel()
    runtime = AgentRuntime(tmp_path / "live", model=model)
    answer = await runtime.run(
        "math", "Use add to calculate the answer.", {"task": "2+3"}, Answer, tools
    )
    assert answer.total == 5
    assert calls == [(2, 3)]
    assert model.calls == 3
    assert runtime.budget.used == {"model": 3, "tool": 1}
    recorded = json.loads((tmp_path / "live/math_0001.json").read_text())
    assert recorded["status"] == "completed"
    assert any(e["type"] == "tool_finished" for e in recorded["events"])
    replay = AgentRuntime(tmp_path / "replay", replay_dir=tmp_path / "live")
    result = await replay.run(
        "math", "Use add to calculate the answer.", {"task": "2+3"}, Answer, tools
    )
    assert result == answer
    assert calls == [(2, 3)]
    assert replay.budget.used == {"model": 0, "tool": 0}
    mismatch = AgentRuntime(tmp_path / "mismatch", replay_dir=tmp_path / "live")
    with pytest.raises(ReplayMissError):
        await mismatch.run("math", "Different instructions", {"task": "2+3"}, Answer, tools)


@pytest.mark.asyncio
async def test_budget_includes_structured_output(tmp_path):
    model = ScriptedModel()
    runtime = AgentRuntime(tmp_path, model=model, budget=ExecutionBudget(model_calls=2))
    with pytest.raises(ExecutionStopped, match="budget"):
        await runtime.run("math", "Calculate", {}, Answer, [make_tool([])])
    assert model.calls == 2
    assert json.loads((tmp_path / "math_0001.json").read_text())["status"] == "failed"


@pytest.mark.asyncio
async def test_cancelled_run_never_invokes_model(tmp_path):
    model = ScriptedModel()
    budget = ExecutionBudget()
    budget.cancelled.set()
    runtime = AgentRuntime(tmp_path, model=model, budget=budget)
    with pytest.raises(ExecutionStopped):
        await runtime.run("math", "Calculate", {}, Answer)
    assert model.calls == 0


@pytest.mark.asyncio
async def test_tool_budget_prevents_side_effect(tmp_path):
    calls = []
    runtime = AgentRuntime(tmp_path, model=ScriptedModel(), budget=ExecutionBudget(tool_calls=0))
    with pytest.raises(ExecutionStopped):
        await runtime.run("math", "Calculate", {}, Answer, [make_tool(calls)])
    assert calls == []


@pytest.mark.asyncio
async def test_missing_replay_and_invalid_name(tmp_path):
    runtime = AgentRuntime(tmp_path / "out", replay_dir=tmp_path / "missing")
    with pytest.raises(ReplayMissError):
        await runtime.run("math", "Calculate", {}, Answer)
    with pytest.raises(ValueError):
        await runtime.run("../escape", "Calculate", {}, Answer)


def test_durable_reservation_failure_does_not_consume_local_budget():
    def reject(kind):
        raise ExecutionStopped("Global allowance exhausted")

    budget = ExecutionBudget(reserve=reject)
    with pytest.raises(ExecutionStopped):
        budget.consume("model")
    assert budget.used["model"] == 0


@pytest.mark.asyncio
async def test_invalid_structured_output_is_recorded(tmp_path):
    class InvalidModel(ScriptedModel):
        async def structured_output(self, *args, **kwargs):
            yield {"output": {"total": "not-an-integer"}}

    runtime = AgentRuntime(tmp_path, model=InvalidModel())
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        await runtime.run("math", "Calculate", {}, Answer, [make_tool([])])
    recorded = json.loads((tmp_path / "math_0001.json").read_text())
    assert recorded["status"] == "failed"
    replay = AgentRuntime(tmp_path / "replay", replay_dir=tmp_path)
    with pytest.raises(ReplayMissError):
        await replay.run("math", "Calculate", {}, Answer, [make_tool([])])


def test_reservations_are_atomic_across_threads():
    from concurrent.futures import ThreadPoolExecutor

    budget = ExecutionBudget(model_calls=3)

    def attempt(_):
        try:
            budget.consume("model")
            return 1
        except ExecutionStopped:
            return 0

    with ThreadPoolExecutor(max_workers=8) as pool:
        assert sum(pool.map(attempt, range(20))) == 3
    assert budget.used["model"] == 3


@pytest.mark.asyncio
async def test_gemini_strict_schema_uses_json_schema_and_validates_text(monkeypatch):
    from types import SimpleNamespace

    from google.genai import types

    from goldcoast.agents.runtime import UsageGeminiModel
    from goldcoast.studio.brand import BrandKit

    captured = {}

    async def generate_content(**request):
        captured.update(request)
        return types.GenerateContentResponse(
            candidates=[
                types.Candidate(
                    content=types.Content(
                        parts=[
                            types.Part(
                                text='{"palette":["#183D35","#FFF9ED"],"prohibited":[],"reference_asset_ids":[],"uncertainty":[]}'
                            )
                        ]
                    )
                )
            ]
        )

    client = SimpleNamespace(
        aio=SimpleNamespace(models=SimpleNamespace(generate_content=generate_content))
    )
    model = UsageGeminiModel(model_id="test", client_args={"api_key": "offline"})
    monkeypatch.setattr(model, "_get_client", lambda: client)
    events = [
        event
        async for event in model.structured_output(
            BrandKit, [{"role": "user", "content": [{"text": "Analyze"}]}]
        )
    ]
    config = types.GenerateContentConfig.model_validate(captured["config"])
    assert captured["contents"][-1]["role"] == "user"
    assert config.response_schema is None
    assert config.response_json_schema["additionalProperties"] is False
    assert events[-1]["output"].palette == ["#183D35", "#FFF9ED"]


def test_generation_schema_preserves_property_names_and_local_constraints():
    from goldcoast.agents.runtime import generation_schema
    from goldcoast.studio.workflow import ScoutReport

    schema = generation_schema(ScoutReport)
    candidate = schema["properties"]["candidates"]["items"]
    assert set(candidate["required"]) <= set(candidate["properties"])
    assert "title" in candidate["properties"]
    assert "pattern" not in candidate["properties"]["id"]
    assert "pattern" in ScoutReport.model_json_schema()["$defs"]["Candidate"]["properties"]["id"]


@pytest.mark.asyncio
async def test_runtime_restart_does_not_overwrite_recording(tmp_path):
    (tmp_path / "sum_0001.json").write_text('{"prior": true}')
    runtime = AgentRuntime(tmp_path, model=ScriptedModel())

    @tool(description="Add two numbers")
    def add(left: int, right: int) -> int:
        return left + right

    await runtime.run("sum", "Add numbers", {"left": 2, "right": 3}, Answer, tools=[add])
    assert json.loads((tmp_path / "sum_0001.json").read_text()) == {"prior": True}
    assert (tmp_path / "sum_0002.json").is_file()


@pytest.mark.asyncio
@pytest.mark.parametrize("limit,succeeds", [(4, True), (3, False)])
async def test_truncated_formatting_retries_once_without_repeating_tools(tmp_path, limit, succeeds):
    from goldcoast.agents.runtime import StructuredOutputTruncated

    class TruncatedModel(ScriptedModel):
        formatting_calls = 0

        async def structured_output(self, output_model, *args, **kwargs):
            self.calls += 1
            self.formatting_calls += 1
            if self.formatting_calls == 1:
                raise StructuredOutputTruncated("MAX_TOKENS")
            yield {"output": output_model(total=5)}

    calls = []
    model = TruncatedModel()
    runtime = AgentRuntime(tmp_path, model=model, budget=ExecutionBudget(model_calls=limit))
    if succeeds:
        answer = await runtime.run("math", "Calculate", {}, Answer, [make_tool(calls)])
        assert answer.total == 5
        assert model.formatting_calls == 2
    else:
        with pytest.raises(ExecutionStopped, match="budget"):
            await runtime.run("math", "Calculate", {}, Answer, [make_tool(calls)])
        assert model.formatting_calls == 1
    assert calls == [(2, 3)]
    assert runtime.budget.used == {"model": limit, "tool": 1}
    record = json.loads((tmp_path / "math_0001.json").read_text())
    assert sum(e["type"] == "structured_output_retry" for e in record["events"]) == 1


@pytest.mark.asyncio
async def test_gemini_max_tokens_is_recorded_before_json_parsing(monkeypatch):
    from types import SimpleNamespace

    from google.genai import types

    from goldcoast.agents.runtime import StructuredOutputTruncated, UsageGeminiModel

    async def generate_content(**request):
        return types.GenerateContentResponse(
            candidates=[
                types.Candidate(
                    finish_reason="MAX_TOKENS",
                    content=types.Content(parts=[types.Part(text='{"summary":"' + "x" * 32400)]),
                )
            ]
        )

    model = UsageGeminiModel(model_id="offline", client_args={"api_key": "offline"})
    monkeypatch.setattr(
        model,
        "_get_client",
        lambda: SimpleNamespace(
            aio=SimpleNamespace(models=SimpleNamespace(generate_content=generate_content))
        ),
    )
    events = []
    with pytest.raises(StructuredOutputTruncated):
        async for event in model.structured_output(Answer, []):
            events.append(event)
    assert len(events) == 1
    assert events[0]["provider_response"]["candidates"][0]["finish_reason"] == "MAX_TOKENS"


def test_compact_scout_schema_preserves_bounds_and_string_guidance():
    from goldcoast.agents.runtime import generation_schema
    from goldcoast.studio.workflow import CompactScoutReport

    schema = generation_schema(CompactScoutReport)
    assert schema["properties"]["claims"]["maxItems"] == 6
    assert schema["properties"]["candidates"]["maxItems"] == 3
    assert "600 characters" in schema["properties"]["summary"]["description"]
    quote = schema["properties"]["claims"]["items"]["properties"]["quote"]
    assert "240 characters" in quote["description"]
