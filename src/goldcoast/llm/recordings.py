from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any

from goldcoast.llm.client import RecordedCall
from goldcoast.storage import write_json


class ReplayMissError(RuntimeError):
    pass


class RecordedResponseClient:
    replay = True

    def __init__(self, source_dir: Path, record_dir: Path) -> None:
        self.source_dir = source_dir
        self.record_dir = record_dir
        self.sequences: dict[str, int] = defaultdict(int)

    def generate(
        self,
        stage: str,
        model_id: str,
        contents: Any,
        config: Any = None,
        *,
        input_refs: list[str] | None = None,
    ) -> RecordedCall:
        self.sequences[stage] += 1
        name = f"{stage}_{self.sequences[stage]}.json"
        path = self.source_dir / name
        if not path.is_file():
            raise ReplayMissError(
                f"Missing replay call: stage={stage}, sequence={self.sequences[stage]}, path={path}"
            )
        record = RecordedCall.model_validate_json(path.read_text(encoding="utf-8"))
        write_json(self.record_dir / name, record)
        if "error" in record.response_raw:
            from goldcoast.llm.client import LLMCallError

            raise LLMCallError(str(record.response_raw["error"]))
        return record
