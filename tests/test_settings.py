from pathlib import Path

import pytest

from goldcoast.settings import Settings, SettingsError, get_settings

MODEL_ENV = {
    "GOLDCOAST_VIDEO_MODEL": "gemini-video-test",
    "GOLDCOAST_IMAGE_MODEL": "gemini-image-test",
    "GOLDCOAST_JUDGE_MODEL": "gemini-judge-test",
}


def _clear_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in (
        "GEMINI_API_KEY",
        "GOOGLE_API_KEY",
        "GOLDCOAST_VIDEO_MODEL",
        "GOLDCOAST_IMAGE_MODEL",
        "GOLDCOAST_JUDGE_MODEL",
        "GOLDCOAST_JUDGE_MAX_RETRIES",
        "GOLDCOAST_JUDGE_PASS_THRESHOLD",
        "GOLDCOAST_REPLAY",
        "GOLDCOAST_REPLAY_RUN",
        "GOLDCOAST_OUTPUT_DIR",
        "GOLDCOAST_CLIP_MANIFEST",
    ):
        monkeypatch.delenv(name, raising=False)


def test_live_settings_require_an_api_key(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _clear_environment(monkeypatch)
    for name, value in MODEL_ENV.items():
        monkeypatch.setenv(name, value)
    with pytest.raises(SettingsError, match="GEMINI_API_KEY"):
        Settings.from_env(tmp_path / "missing.env")


def test_replay_settings_allow_missing_key_and_parse_types(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _clear_environment(monkeypatch)
    for name, value in MODEL_ENV.items():
        monkeypatch.setenv(name, value)
    monkeypatch.setenv("GOLDCOAST_REPLAY", "1")
    monkeypatch.setenv("GOLDCOAST_JUDGE_MAX_RETRIES", "4")
    settings = Settings.from_env(tmp_path / "missing.env")
    assert settings.replay is True
    assert settings.gemini_api_key is None
    assert settings.judge_max_retries == 4


def test_google_api_key_takes_precedence(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _clear_environment(monkeypatch)
    for name, value in MODEL_ENV.items():
        monkeypatch.setenv(name, value)
    monkeypatch.setenv("GEMINI_API_KEY", "gemini-key")
    monkeypatch.setenv("GOOGLE_API_KEY", "google-key")
    assert Settings.from_env(tmp_path / "missing.env").gemini_api_key == "google-key"


def test_placeholder_models_are_rejected(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _clear_environment(monkeypatch)
    monkeypatch.setenv("GOLDCOAST_REPLAY", "1")
    with pytest.raises(SettingsError, match="VIDEO_MODEL"):
        Settings.from_env(tmp_path / "missing.env")


def test_dotenv_loading_and_settings_cache(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _clear_environment(monkeypatch)
    env_path = tmp_path / ".env"
    env_path.write_text(
        "\n".join(
            [
                "GEMINI_API_KEY=file-key",
                "GOLDCOAST_VIDEO_MODEL=video-from-file",
                "GOLDCOAST_IMAGE_MODEL=image-from-file",
                "GOLDCOAST_JUDGE_MODEL=judge-from-file",
            ]
        ),
        encoding="utf-8",
    )
    assert Settings.from_env(env_path).video_model == "video-from-file"

    for name, value in MODEL_ENV.items():
        monkeypatch.setenv(name, value)
    monkeypatch.setenv("GEMINI_API_KEY", "cached-key")
    get_settings.cache_clear()
    try:
        first = get_settings()
        monkeypatch.setenv("GEMINI_API_KEY", "changed-key")
        assert get_settings() is first
        assert get_settings().gemini_api_key == "cached-key"
    finally:
        get_settings.cache_clear()
