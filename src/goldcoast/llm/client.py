from __future__ import annotations

import json
import os
import re
import tempfile
import time
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any

from google import genai
from pydantic import BaseModel, ConfigDict, Field

from goldcoast.settings import Settings


class LLMCallError(RuntimeError):
    pass


class RecordedCall(BaseModel):
    model_config = ConfigDict(extra="forbid")

    stage: str
    sequence: int = Field(ge=1)
    model_id: str
    prompt: str
    input_refs: list[str]
    response_text: str
    response_raw: Any
    latency_ms: int = Field(ge=0)
    timestamp: datetime


def _json_safe(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, bytes):
        return {"type": "bytes", "length": len(value)}
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if value is None or isinstance(value, str | int | float | bool):
        return value
    if hasattr(value, "model_dump"):
        return _json_safe(value.model_dump(mode="json"))
    return repr(value)


def _walk(value: Any) -> list[Any]:
    safe = _json_safe(value)
    if isinstance(safe, dict):
        values: list[Any] = []
        for item in safe.values():
            values.extend(_walk(item))
        return values
    if isinstance(safe, list):
        values = []
        for item in safe:
            values.extend(_walk(item))
        return values
    return [safe]


def _prompt_text(contents: Any) -> str:
    return "\n".join(item for item in _walk(contents) if isinstance(item, str))


def _input_refs(contents: Any) -> list[str]:
    references: list[str] = []

    def visit(value: Any, key: str | None = None) -> None:
        safe = _json_safe(value)
        if isinstance(safe, dict):
            for child_key, child in safe.items():
                visit(child, child_key)
        elif isinstance(safe, list):
            for child in safe:
                visit(child, key)
        elif isinstance(safe, str) and key in {"file", "file_uri", "path", "uri"}:
            references.append(safe)

    visit(contents)
    return list(dict.fromkeys(references))


class GeminiClient:
    def __init__(
        self,
        settings: Settings,
        record_dir: Path,
        *,
        client: Any | None = None,
    ) -> None:
        self.settings = settings
        self.record_dir = Path(record_dir)
        self.record_dir.mkdir(parents=True, exist_ok=True)
        self._client = client or genai.Client(api_key=settings.gemini_api_key)

    def _next_sequence(self, stage: str) -> int:
        pattern = re.compile(rf"^{re.escape(stage)}_(\d+)\.json$")
        sequences = [
            int(match.group(1))
            for path in self.record_dir.glob(f"{stage}_*.json")
            if (match := pattern.match(path.name))
        ]
        return max(sequences, default=0) + 1

    def _write_record(self, record: RecordedCall) -> None:
        target = self.record_dir / f"{record.stage}_{record.sequence}.json"
        temporary_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=self.record_dir,
                prefix=f".{target.name}.",
                suffix=".tmp",
                delete=False,
            ) as handle:
                temporary_path = Path(handle.name)
                json.dump(record.model_dump(mode="json"), handle, indent=2, ensure_ascii=False)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary_path, target)
        finally:
            if temporary_path is not None and temporary_path.exists():
                temporary_path.unlink()

    def generate(
        self,
        stage: str,
        model_id: str,
        contents: Any,
        config: Any | None = None,
    ) -> RecordedCall:
        if not re.fullmatch(r"[a-z0-9]+(?:[_-][a-z0-9]+)*", stage):
            raise ValueError(
                "stage must contain only lowercase letters, digits, hyphens, or underscores"
            )
        sequence = self._next_sequence(stage)
        timestamp = datetime.now(UTC)
        started = time.perf_counter()
        prompt = _prompt_text(contents)
        input_refs = _input_refs(contents)
        try:
            response = self._client.models.generate_content(
                model=model_id,
                contents=contents,
                config=config,
            )
            latency_ms = max(0, round((time.perf_counter() - started) * 1000))
            response_text = response.text or ""
            record = RecordedCall(
                stage=stage,
                sequence=sequence,
                model_id=model_id,
                prompt=prompt,
                input_refs=input_refs,
                response_text=response_text,
                response_raw={
                    "request": {
                        "contents": _json_safe(contents),
                        "config": _json_safe(config),
                    },
                    "response": _json_safe(response),
                },
                latency_ms=latency_ms,
                timestamp=timestamp,
            )
            self._write_record(record)
            return record
        except Exception as exc:
            latency_ms = max(0, round((time.perf_counter() - started) * 1000))
            record = RecordedCall(
                stage=stage,
                sequence=sequence,
                model_id=model_id,
                prompt=prompt,
                input_refs=input_refs,
                response_text="",
                response_raw={
                    "request": {
                        "contents": _json_safe(contents),
                        "config": _json_safe(config),
                    },
                    "error": {"type": type(exc).__name__, "message": str(exc)},
                },
                latency_ms=latency_ms,
                timestamp=timestamp,
            )
            self._write_record(record)
            raise LLMCallError(f"Gemini call failed during stage '{stage}': {exc}") from exc
