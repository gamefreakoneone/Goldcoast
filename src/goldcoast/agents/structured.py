from typing import Any

from pydantic import BaseModel, ValidationError


class AgentParseError(RuntimeError):
    pass


class ModelSafetyError(RuntimeError):
    pass


def response_schema(schema: type[BaseModel]) -> dict[str, Any]:
    root = schema.model_json_schema()

    def convert(value: Any) -> Any:
        if isinstance(value, list):
            return [convert(item) for item in value]
        if not isinstance(value, dict):
            return value
        if "$ref" in value:
            return convert(root["$defs"][value["$ref"].split("/")[-1]])
        if "anyOf" in value and {"type": "null"} in value["anyOf"]:
            choices = [item for item in value["anyOf"] if item != {"type": "null"}]
            if len(choices) == 1:
                return {**convert(choices[0]), "nullable": True}
        return {
            key: convert(item)
            for key, item in value.items()
            if key not in {"$defs", "additionalProperties", "default", "title"}
        }

    return convert(root)


def structured_call[T: BaseModel](
    client: Any,
    stage: str,
    model: str,
    contents: Any,
    schema: type[T],
    *,
    input_refs: list[str] | None = None,
) -> T:
    config = {
        "response_mime_type": "application/json",
        "response_schema": response_schema(schema),
        "automatic_function_calling": {"disable": True},
    }
    for attempt in range(2):
        call = client.generate(stage, model, contents, config, input_refs=input_refs)
        raw = getattr(call, "response_raw", {}).get("response", {})
        feedback = raw.get("prompt_feedback") or {}
        blocked = feedback.get("block_reason")
        for candidate in raw.get("candidates", []) or []:
            if candidate.get("finish_reason") in {
                "SAFETY",
                "BLOCKLIST",
                "PROHIBITED_CONTENT",
                "IMAGE_SAFETY",
            }:
                blocked = candidate.get("finish_message") or candidate["finish_reason"]
        if blocked:
            raise ModelSafetyError(f"{stage} blocked: {blocked}")
        try:
            return schema.model_validate_json(call.response_text)
        except ValidationError as exc:
            if attempt:
                raise AgentParseError(f"Invalid {stage} response after repair: {exc}") from exc
            contents = (
                f"Repair this JSON to satisfy the response schema. Do not analyze the "
                f"video again. Validation errors: {exc}\nResponse: {call.response_text}"
            )
            input_refs = []
    raise AssertionError("unreachable")
