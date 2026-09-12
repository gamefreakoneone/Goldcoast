from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

MODEL_PLACEHOLDERS = {
    "replace-with-video-model-id",
    "replace-with-image-model-id",
    "replace-with-judge-model-id",
}
MODEL_VARIABLES = {
    "video_model": "GOLDCOAST_VIDEO_MODEL",
    "image_model": "GOLDCOAST_IMAGE_MODEL",
    "judge_model": "GOLDCOAST_JUDGE_MODEL",
}


class SettingsError(RuntimeError):
    pass


class Settings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    gemini_api_key: str | None = Field(default=None, repr=False)
    video_model: str = "replace-with-video-model-id"
    image_model: str = "replace-with-image-model-id"
    judge_model: str = "replace-with-judge-model-id"
    judge_max_retries: int = Field(default=2, ge=0)
    judge_pass_threshold: int = Field(default=7, ge=0, le=10)
    replay: bool = False
    replay_run: str | None = None
    output_dir: Path = Path("output")
    data_dir: Path = Path("data")
    clip_manifest: Path = Path("sample_clips/manifest.json")

    @model_validator(mode="after")
    def validate_configuration(self) -> Settings:
        issues: list[str] = []
        missing_models = [
            name
            for name in ("video_model", "image_model", "judge_model")
            if getattr(self, name) in MODEL_PLACEHOLDERS or not getattr(self, name).strip()
        ]
        if missing_models:
            variables = ", ".join(MODEL_VARIABLES[name] for name in missing_models)
            issues.append(f"configure {variables} with Gemini model ids")
        if not self.replay and not self.gemini_api_key:
            issues.append(
                "GEMINI_API_KEY is required when GOLDCOAST_REPLAY is off "
                "(GOOGLE_API_KEY is also accepted)"
            )
        if issues:
            raise ValueError("; ".join(issues) + "; see .env.example")
        return self

    @classmethod
    def from_env(cls, env_file: str | Path = ".env") -> Settings:
        load_dotenv(dotenv_path=env_file, override=False)
        values = {
            "gemini_api_key": os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY"),
            "video_model": os.getenv("GOLDCOAST_VIDEO_MODEL", "replace-with-video-model-id"),
            "image_model": os.getenv("GOLDCOAST_IMAGE_MODEL", "replace-with-image-model-id"),
            "judge_model": os.getenv("GOLDCOAST_JUDGE_MODEL", "replace-with-judge-model-id"),
            "judge_max_retries": os.getenv("GOLDCOAST_JUDGE_MAX_RETRIES", "2"),
            "judge_pass_threshold": os.getenv("GOLDCOAST_JUDGE_PASS_THRESHOLD", "7"),
            "replay": os.getenv("GOLDCOAST_REPLAY", "0"),
            "replay_run": os.getenv("GOLDCOAST_REPLAY_RUN") or None,
            "output_dir": os.getenv("GOLDCOAST_OUTPUT_DIR", "output"),
            "data_dir": Path("data"),
            "clip_manifest": os.getenv("GOLDCOAST_CLIP_MANIFEST", "sample_clips/manifest.json"),
        }
        try:
            return cls.model_validate(values)
        except ValidationError as exc:
            messages = "; ".join(
                str(error["msg"]).removeprefix("Value error, ") for error in exc.errors()
            )
            raise SettingsError(messages) from exc


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings.from_env()
