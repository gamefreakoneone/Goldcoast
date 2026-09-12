import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from PIL import Image

from goldcoast.agents.ad_agent import AdAgent, AdGenerationError, brief_key
from goldcoast.llm.recordings import RecordedResponseClient
from goldcoast.media.images import AssetMissingError, save_png
from goldcoast.models.pipeline import AD_FORMAT_SIZES, AdBrief, AdFormat, HypeMoment

FIXTURES = Path(__file__).parent / "fixtures/model_calls/ad"


@pytest.fixture
def ad_inputs():
    brief = AdBrief.model_validate_json((FIXTURES / "inputs/brief.json").read_text())
    moment = HypeMoment.model_validate_json((FIXTURES / "inputs/moment.json").read_text())
    moment.best_frame_path = FIXTURES / "inputs/hero.png"
    return brief, moment


def test_real_images_both_formats_resize_and_metadata(seed, agent_settings, ad_inputs, tmp_path):
    client = RecordedResponseClient(FIXTURES, tmp_path / "model_calls")
    brief, moment = ad_inputs
    ads = AdAgent(client, seed, agent_settings, tmp_path).generate(brief, moment)
    assert len(ads) == 2
    for ad in ads:
        assert Image.open(ad.image_path).size == AD_FORMAT_SIZES[ad.format]
        assert ad.metadata.resized_from
        assert not ad.metadata.format_mismatch
        assert f"brief_{brief_key(brief.id)}" in ad.image_path.parts
        sidecar = json.loads(ad.image_path.with_suffix(".json").read_text())
        assert sidecar["id"] == ad.id
        assert "never redraw" in ad.prompt_used
        assert "No offer language" in ad.prompt_used
    assert client.sequences["ad_generate"] == 2


def test_wrong_ratio_retries_once_then_flags(seed, agent_settings, ad_inputs, tmp_path):
    class WrongRatio(RecordedResponseClient):
        def generate_image(self, *args, **kwargs):
            call = super().generate_image(*args, **kwargs)
            with Image.open(call.image_path) as image:
                save_png(image.resize((512, 512)), call.image_path)
            return call

    client = WrongRatio(FIXTURES, tmp_path / "model_calls")
    brief, moment = ad_inputs
    ad = AdAgent(client, seed, agent_settings, tmp_path).generate_one(
        brief, moment, AdFormat.LANDSCAPE
    )
    assert ad.metadata.format_mismatch
    assert Image.open(ad.image_path).size == (512, 512)
    assert client.sequences["ad_generate"] == 2


def test_refusal_retry_omits_portrait_and_is_bounded(seed, agent_settings, ad_inputs, tmp_path):
    refs = []

    class RefusalThenReal(RecordedResponseClient):
        def generate_image(self, *args, **kwargs):
            refs.append(kwargs["input_refs"])
            if len(refs) == 1:
                return SimpleNamespace(image_path=None, refusal="Recognizable real person refused")
            return super().generate_image(*args, **kwargs)

    brief, moment = ad_inputs
    agent = AdAgent(
        RefusalThenReal(FIXTURES, tmp_path / "model_calls"), seed, agent_settings, tmp_path
    )
    ad = agent.generate_one(brief, moment, AdFormat.LANDSCAPE, hints=["Keep logo readable"])
    assert ad.metadata.portrait_omitted
    assert len(refs[1]) == len(refs[0]) - 1
    assert "Keep logo readable" in ad.prompt_used

    class AlwaysRefuses:
        count = 0

        def generate_image(self, *args, **kwargs):
            self.count += 1
            return SimpleNamespace(image_path=None, refusal="Real person refused")

    refused = AlwaysRefuses()
    with pytest.raises(AdGenerationError, match="Real person"):
        AdAgent(refused, seed, agent_settings, tmp_path).generate_one(
            brief, moment, AdFormat.LANDSCAPE
        )
    assert refused.count == 2


def test_missing_asset_fails_before_model(seed, agent_settings, ad_inputs, tmp_path):
    brief, moment = ad_inputs
    moment.best_frame_path = None
    with pytest.raises(AssetMissingError, match="simone-biles"):
        AdAgent(None, seed, agent_settings, tmp_path).generate(brief, moment)


def test_brief_namespace_prevents_cross_moment_overwrite(seed, agent_settings, ad_inputs, tmp_path):
    brief, moment = ad_inputs
    client = RecordedResponseClient(FIXTURES, tmp_path / "model_calls")
    agent = AdAgent(client, seed, agent_settings, tmp_path)
    first = agent.generate_one(brief, moment, AdFormat.LANDSCAPE)
    original = first.image_path.read_bytes()
    brief.id += "-other"
    second = agent.generate_one(brief, moment, AdFormat.PORTRAIT)
    assert first.image_path.parents[1] != second.image_path.parents[1]
    assert first.image_path.read_bytes() == original
