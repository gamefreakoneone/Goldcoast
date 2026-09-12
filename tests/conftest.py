import socket
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def deny_network(monkeypatch):
    def denied(*args, **kwargs):
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
