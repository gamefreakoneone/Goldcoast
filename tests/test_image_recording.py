from io import BytesIO
from types import SimpleNamespace

from google.genai import types
from PIL import Image

from goldcoast.llm.client import GeminiClient
from goldcoast.llm.recordings import RecordedResponseClient


def test_original_image_record_survives_output_edits(agent_settings, tmp_path):
    buffer = BytesIO()
    Image.new("RGB", (16, 9), "red").save(buffer, format="PNG")
    original = buffer.getvalue()
    response = types.GenerateContentResponse(
        candidates=[
            types.Candidate(
                content=types.Content(
                    parts=[types.Part.from_bytes(data=original, mime_type="image/png")]
                )
            )
        ]
    )
    client = GeminiClient(
        agent_settings,
        tmp_path / "source",
        client=SimpleNamespace(models=SimpleNamespace(generate_content=lambda **kw: response)),
    )
    call = client.generate_image(
        "ad_generate", "image", ["prompt"], {}, output_path=tmp_path / "ad.png"
    )
    assert call.image_path.read_bytes() == original
    call.image_path.write_bytes(b"changed output")
    replay = RecordedResponseClient(tmp_path / "source", tmp_path / "replay")
    copied = replay.generate_image(
        "ad_generate", "image", [], {}, output_path=tmp_path / "copied.png"
    )
    assert copied.image_path.read_bytes() == original
    assert (tmp_path / "replay/images/ad_generate_1_0.png").read_bytes() == original
