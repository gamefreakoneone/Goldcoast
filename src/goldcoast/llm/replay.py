from pathlib import Path

from goldcoast.llm.client import GeminiClient
from goldcoast.llm.recordings import RecordedResponseClient, ReplayMissError
from goldcoast.settings import Settings


class ReplayClient(RecordedResponseClient):
    def __init__(self, source_run_dir: Path, record_dir: Path):
        if not (source_run_dir / "run.json").is_file():
            raise ReplayMissError(f"Missing replay run: {source_run_dir}")
        super().__init__(source_run_dir / "model_calls", record_dir)


def create_client(settings: Settings, record_dir: Path, source_run_dir: Path | None = None):
    if source_run_dir is not None:
        return ReplayClient(source_run_dir, record_dir)
    if settings.replay:
        raise ReplayMissError("Replay requires a source run; network fallback is disabled")
    return GeminiClient(settings, record_dir)
