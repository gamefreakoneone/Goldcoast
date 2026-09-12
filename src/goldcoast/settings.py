from __future__ import annotations

import json
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
    judge_min_criterion: int = Field(default=5, ge=0, le=10)
    replay: bool = False
    replay_run: str | None = None
    output_dir: Path = Path("output")
    data_dir: Path = Path("data")
    clip_manifest: Path = Path("sample_clips/manifest.json")
    hype_threshold: int = Field(default=6, ge=0, le=10)
    frame_candidate_window_s: float = Field(default=1.0, gt=0)
    athlete_confidence_threshold: float = Field(default=0.6, ge=0, le=1)
    max_businesses: int = Field(default=2, ge=1)
    api_cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])
    sample_clips_dir: Path = Path("sample_clips")

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
            "judge_min_criterion": os.getenv("GOLDCOAST_JUDGE_MIN_CRITERION", "5"),
            "replay": os.getenv("GOLDCOAST_REPLAY", "0"),
            "replay_run": os.getenv("GOLDCOAST_REPLAY_RUN") or None,
            "output_dir": os.getenv("GOLDCOAST_OUTPUT_DIR", "output"),
            "data_dir": Path("data"),
            "clip_manifest": os.getenv("GOLDCOAST_CLIP_MANIFEST", "sample_clips/manifest.json"),
            "hype_threshold": os.getenv("GOLDCOAST_HYPE_THRESHOLD", "6"),
            "frame_candidate_window_s": os.getenv("GOLDCOAST_FRAME_CANDIDATE_WINDOW_S", "1.0"),
            "athlete_confidence_threshold": os.getenv(
                "GOLDCOAST_ATHLETE_CONFIDENCE_THRESHOLD", ".6"
            ),
            "max_businesses": os.getenv("GOLDCOAST_MAX_BUSINESSES", "2"),
            "sample_clips_dir": os.getenv("GOLDCOAST_SAMPLE_CLIPS_DIR", "sample_clips"),
        }
        try:
            values["api_cors_origins"] = json.loads(
                os.getenv("GOLDCOAST_API_CORS_ORIGINS", '["http://localhost:5173"]')
            )
            return cls.model_validate(values)
        except json.JSONDecodeError as exc:
            raise SettingsError("GOLDCOAST_API_CORS_ORIGINS must be a JSON array") from exc
        except ValidationError as exc:
            messages = "; ".join(
                str(error["msg"]).removeprefix("Value error, ") for error in exc.errors()
            )
            raise SettingsError(messages) from exc


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings.from_env()
