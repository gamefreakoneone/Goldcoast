from __future__ import annotations

import re
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel

from goldcoast.models.pipeline import (
    AdBrief,
    ApprovalDecision,
    GeneratedAd,
    HypeMoment,
    QualityVerdict,
    Run,
    RunStatus,
)
from goldcoast.pipeline.ids import run_id
from goldcoast.storage import write_json


class RunStore:
    def __init__(self, output_dir: Path):
        self.root = Path(output_dir) / "runs"

    def run_dir(self, identifier: str) -> Path:
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,127}", identifier):
            raise ValueError("Invalid run ID")
        path = self.root / identifier
        if not path.resolve().is_relative_to(self.root.resolve()):
            raise ValueError("Run path outside store")
        return path

    def create_run(self, clip_path: Path, replay: bool = False) -> Run:
        run = Run(
            id=run_id(),
            clip_path=clip_path,
            replay=replay,
            status=RunStatus.RUNNING,
            started_at=datetime.now(UTC),
        )
        self.run_dir(run.id).mkdir(parents=True, exist_ok=False)
        self.save_run(run)
        return run

    def save_run(self, run: Run) -> None:
        write_json(self.run_dir(run.id) / "run.json", run)

    def get_run(self, identifier: str) -> Run:
        return Run.model_validate_json(
            (self.run_dir(identifier) / "run.json").read_text(encoding="utf-8")
        )

    def list_runs(self) -> list[Run]:
        runs = [
            Run.model_validate_json(p.read_text(encoding="utf-8"))
            for p in self.root.glob("*/run.json")
        ]
        return sorted(runs, key=lambda run: run.started_at, reverse=True)

    def _read[T: BaseModel](self, identifier: str, pattern: str, model: type[T]) -> list[T]:
        return [
            model.model_validate_json(p.read_text(encoding="utf-8"))
            for p in sorted(self.run_dir(identifier).glob(pattern))
        ]

    def moments(self, identifier: str) -> list[HypeMoment]:
        moments = self._read(identifier, "moments/*.json", HypeMoment)
        for moment in moments:
            if moment.best_frame_path:
                moment.best_frame_path = self.run_dir(identifier) / "frames" / f"{moment.id}.png"
        return moments

    def briefs(self, identifier: str) -> list[AdBrief]:
        return self._read(identifier, "briefs/*.json", AdBrief)

    def ads(self, identifier: str) -> list[GeneratedAd]:
        ads = []
        for path in sorted(self.run_dir(identifier).glob("ads/**/attempt_*.json")):
            ad = GeneratedAd.model_validate_json(path.read_text(encoding="utf-8"))
            ad.image_path = path.with_suffix(".png")
            ads.append(ad)
        return ads

    def verdicts(self, identifier: str) -> list[QualityVerdict]:
        return self._read(identifier, "verdicts/*.json", QualityVerdict)

    def decisions(self, identifier: str) -> list[ApprovalDecision]:
        return self._read(identifier, "decisions/*.json", ApprovalDecision)
