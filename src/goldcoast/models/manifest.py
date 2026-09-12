from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator

from goldcoast.models.pipeline import AthleteHints, ContractModel


class ManifestMoment(ContractModel):
    start_s: float = Field(ge=0)
    end_s: float = Field(ge=0)
    best_frame_s: float = Field(ge=0)
    hype_score: float = Field(ge=0, le=10)
    description: str
    event_context: str
    athlete_hints: AthleteHints | None = None

    @model_validator(mode="after")
    def validate_timestamps(self) -> ManifestMoment:
        if self.end_s < self.start_s:
            raise ValueError("end_s must be greater than or equal to start_s")
        if not self.start_s <= self.best_frame_s <= self.end_s:
            raise ValueError("best_frame_s must fall between start_s and end_s")
        return self


class ClipEntry(ContractModel):
    file: str
    sport: str | None = None
    athlete_id: str | None = None
    analyzed: bool = False
    analyzed_by: Literal["gemini", "manual"] | None = None
    analyzed_at: datetime | None = None
    notes: str = ""
    moments: list[ManifestMoment] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_analysis_state(self) -> ClipEntry:
        if self.analyzed and self.analyzed_by is None:
            raise ValueError("analyzed_by is required when analyzed is true")
        return self


class ClipManifest(ContractModel):
    entries: list[ClipEntry] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_unique_files(self) -> ClipManifest:
        files = [entry.file for entry in self.entries]
        if len(files) != len(set(files)):
            raise ValueError("clip manifest contains duplicate file names")
        return self

    @classmethod
    def load(cls, path: Path) -> ClipManifest:
        if not path.exists():
            return cls()
        with path.open(encoding="utf-8") as handle:
            data = json.load(handle)
        if not isinstance(data, list):
            raise ValueError("clip manifest must contain a JSON array")
        return cls(entries=[ClipEntry.model_validate(item) for item in data])

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=path.parent,
                prefix=f".{path.name}.",
                suffix=".tmp",
                delete=False,
            ) as handle:
                temporary_path = Path(handle.name)
                json.dump(
                    [entry.model_dump(mode="json") for entry in self.entries],
                    handle,
                    indent=2,
                    ensure_ascii=False,
                )
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary_path, path)
        finally:
            if temporary_path is not None and temporary_path.exists():
                temporary_path.unlink()

    def get(self, file_name: str) -> ClipEntry | None:
        return next((entry for entry in self.entries if entry.file == file_name), None)

    def upsert(self, entry: ClipEntry) -> None:
        for index, current in enumerate(self.entries):
            if current.file == entry.file:
                self.entries[index] = entry
                return
        self.entries.append(entry)
