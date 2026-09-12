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
from uuid import uuid4

import httpx
from google import genai
from google.genai import types
from pydantic import BaseModel, ConfigDict, Field

from goldcoast.settings import Settings
from goldcoast.storage import write_json


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
    if isinstance(value, type) and issubclass(value, BaseModel):
        return value.model_json_schema()
    if isinstance(value, BaseModel):
        return _json_safe(value.model_dump(mode="python"))
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
    replay = False

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
        self._client = client or genai.Client(
            api_key=settings.gemini_api_key,
            http_options=types.HttpOptions(
                timeout=180_000,
                retry_options=types.HttpRetryOptions(attempts=1),
                client_args={
                    "event_hooks": {
                        "request": [self._record_http_request],
                        "response": [self._record_http_response],
                    }
                },
            ),
        )

    def _record_http_request(self, request: httpx.Request) -> None:
        request_id = uuid4().hex
        request.extensions["goldcoast_trace"] = {
            "id": request_id,
            "method": request.method,
            "path": request.url.path,
            "timestamp": datetime.now(UTC).isoformat(),
            "status_code": None,
        }
        request.extensions["goldcoast_started"] = time.perf_counter()
        write_json(
            self.record_dir / "http_requests" / f"{request_id}.json",
            request.extensions["goldcoast_trace"],
        )

    def _record_http_response(self, response: httpx.Response) -> None:
        trace = response.request.extensions["goldcoast_trace"]
        trace["status_code"] = response.status_code
        trace["latency_ms"] = round(
            (time.perf_counter() - response.request.extensions["goldcoast_started"]) * 1000
        )
        write_json(self.record_dir / "http_requests" / f"{trace['id']}.json", trace)

    def _uploaded_file_name(self, path: Path, identity: dict[str, Any]) -> str | None:
        cache = self.record_dir / "video_upload.json"
        if cache.is_file():
            saved = json.loads(cache.read_text(encoding="utf-8"))
            if saved.get("source") == identity:
                return saved["file"]["name"]
        records = sorted(
            self.record_dir.glob("video_detect_*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        for record_path in records:
            record = RecordedCall.model_validate_json(record_path.read_text(encoding="utf-8"))
            if path.stat().st_mtime > record.timestamp.timestamp():
                continue
            if not any(Path(ref).resolve() == path.resolve() for ref in record.input_refs):
                continue
            for part in record.response_raw.get("request", {}).get("contents", []):
                if isinstance(part, dict) and part.get("file_data"):
                    uri = part["file_data"].get("file_uri", "")
                    if "/files/" in uri:
                        return "files/" + uri.rsplit("/files/", 1)[1]
        return None

    def video_part(self, path: Path) -> types.Part:
        if path.stat().st_size < 20 * 1024 * 1024:
            return types.Part.from_bytes(data=path.read_bytes(), mime_type="video/mp4")
        started = time.monotonic()
        try:
            identity = {
                "path": str(path.resolve()),
                "size": path.stat().st_size,
                "mtime_ns": path.stat().st_mtime_ns,
            }
            name = self._uploaded_file_name(path, identity)
            uploaded = None
            if name:
                try:
                    uploaded = self._client.files.get(name=name)
                except genai.errors.ClientError as exc:
                    if exc.code != 404:
                        raise
            if uploaded is None:
                uploaded = self._client.files.upload(
                    file=path, config=types.UploadFileConfig(mime_type="video/mp4")
                )
            while uploaded.state != types.FileState.ACTIVE:
                if uploaded.state == types.FileState.FAILED:
                    raise LLMCallError(f"Files API processing failed: {uploaded.error}")
                if time.monotonic() - started >= 180:
                    raise LLMCallError("Files API activation timed out after 180 seconds")
                time.sleep(2)
                uploaded = self._client.files.get(name=uploaded.name)
            write_json(
                self.record_dir / "video_upload.json",
                {"source": identity, "file": _json_safe(uploaded)},
            )
            return types.Part.from_uri(file_uri=uploaded.uri, mime_type="video/mp4")
        except LLMCallError:
            raise
        except Exception as exc:
            raise LLMCallError(f"Files API upload failed for {path}: {exc}") from exc

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
        *,
        input_refs: list[str] | None = None,
    ) -> RecordedCall:
        if not re.fullmatch(r"[a-z0-9]+(?:[_-][a-z0-9]+)*", stage):
            raise ValueError(
                "stage must contain only lowercase letters, digits, hyphens, or underscores"
            )
        sequence = self._next_sequence(stage)
        timestamp = datetime.now(UTC)
        started = time.perf_counter()
        prompt = _prompt_text(contents)
        input_refs = input_refs if input_refs is not None else _input_refs(contents)
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
