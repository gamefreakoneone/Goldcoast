import socket
import sys
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def deny_network(monkeypatch):
    original_connect = socket.socket.connect
    socketpair_code = getattr(socket.socketpair, "__code__", None)

    def denied(*args, **kwargs):
        if socketpair_code is not None and sys._getframe(1).f_code is socketpair_code:
            return original_connect(*args, **kwargs)
        raise AssertionError("Tests must not access the network; use recorded responses")

    monkeypatch.setattr(socket.socket, "connect", denied)
    monkeypatch.setattr(socket, "create_connection", denied)


@pytest.fixture
def seed():
    from goldcoast.data import load_seed

    return load_seed(Path("data"))


@pytest.fixture
def agent_settings(tmp_path):
    from goldcoast.settings import Settings

    return Settings(
        replay=True,
        video_model="recorded-video",
        image_model="recorded-image",
        judge_model="recorded-judge",
        clip_manifest=tmp_path / "manifest.json",
    )


@pytest.fixture
def moment():
    from goldcoast.models.manifest import ClipManifest

    entry = ClipManifest.load(Path("sample_clips/manifest.json")).get("gymnastics_simone.mp4")
    return entry.to_hype_moments("fixture", Path("sample_clips/gymnastics_simone.mp4"))[0]


@pytest.fixture
def creative_inputs():
    from goldcoast.models.pipeline import AdBrief, HypeMoment

    root = Path(__file__).parent / "fixtures/model_calls/ad/creative/inputs"
    brief = AdBrief.model_validate_json((root / "brief.json").read_text())
    moment = HypeMoment.model_validate_json((root / "moment.json").read_text())
    moment.best_frame_path = root / "hero.png"
    return brief, moment
