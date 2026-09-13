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
