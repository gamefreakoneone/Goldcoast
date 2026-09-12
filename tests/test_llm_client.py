import json
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest

from goldcoast.llm import GeminiClient, LLMCallError
from goldcoast.settings import Settings


class FakeResponse:
    text = "generated response"

    def model_dump(self, mode: str = "python") -> dict[str, object]:
        return {"text": self.text, "mode": mode}


class FakeModels:
    def __init__(self, error: Exception | None = None) -> None:
        self.error = error

    def generate_content(self, **kwargs: object) -> FakeResponse:
        if self.error:
            raise self.error
        return FakeResponse()


def _settings() -> Settings:
    return Settings(
        gemini_api_key="test-key",
        video_model="video-model",
        image_model="image-model",
        judge_model="judge-model",
    )


def test_successful_call_is_recorded_atomically(tmp_path: Path) -> None:
    fake_client = SimpleNamespace(models=FakeModels())
    client = GeminiClient(_settings(), tmp_path, client=fake_client)
    record = client.generate(
        "video",
        "video-model",
        {"prompt": "Find the moment", "file_uri": "gs://bucket/clip.mp4"},
        {"temperature": 0},
    )

    assert record.sequence == 1
    assert record.response_text == "generated response"
    assert record.input_refs == ["gs://bucket/clip.mp4"]
    saved = json.loads((tmp_path / "video_1.json").read_text(encoding="utf-8"))
    assert saved["model_id"] == "video-model"
    assert saved["response_raw"]["response"]["text"] == "generated response"
    assert not list(tmp_path.glob("*.tmp"))

    assert client.generate("video", "video-model", "Again").sequence == 2


def test_failed_call_is_recorded_before_wrapped_error(tmp_path: Path) -> None:
    fake_client = SimpleNamespace(models=FakeModels(RuntimeError("service unavailable")))
    client = GeminiClient(_settings(), tmp_path, client=fake_client)

    with pytest.raises(LLMCallError, match="service unavailable"):
        client.generate("judge", "judge-model", "Judge this")

    saved = json.loads((tmp_path / "judge_1.json").read_text(encoding="utf-8"))
    assert saved["response_raw"]["error"]["type"] == "RuntimeError"
    assert saved["response_raw"]["error"]["message"] == "service unavailable"


def test_one_sdk_attempt_and_http_audit_on_unavailable(tmp_path, monkeypatch):
    from google import genai

    original = genai.Client
    requests = []

    def respond(request):
        requests.append(request)
        return httpx.Response(
            503,
            json={
                "error": {
                    "code": 503,
                    "message": "high demand",
                    "status": "UNAVAILABLE",
                }
            },
        )

    def create_client(**kwargs):
        options = kwargs["http_options"]
        assert options.retry_options.attempts == 1
        options.client_args["transport"] = httpx.MockTransport(respond)
        return original(**kwargs)

    monkeypatch.setattr(genai, "Client", create_client)
    client = GeminiClient(_settings(), tmp_path)
    try:
        with pytest.raises(LLMCallError, match="503"):
            client.generate(
                "video_detect",
                "gemini-3.8-flash",
                "test",
                {
                    "automatic_function_calling": {"disable": True},
                },
            )
        assert len(requests) == 1
        traces = list((tmp_path / "http_requests").glob("*.json"))
        assert len(traces) == 1
        trace = json.loads(traces[0].read_text())
        assert trace["status_code"] == 503
        assert trace["path"].endswith("models/gemini-3.8-flash:generateContent")
        assert "test-key" not in traces[0].read_text()
    finally:
        client._client.close()
