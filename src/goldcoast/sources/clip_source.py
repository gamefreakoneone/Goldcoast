from pathlib import Path
from typing import Protocol


class ClipError(ValueError):
    pass


class ClipSource(Protocol):
    def list_clips(self) -> list[Path]: ...

    def open(self, name: str) -> Path: ...


def validate_clip(path: Path) -> Path:
    if path.suffix.lower() != ".mp4" or not path.is_file():
        raise ClipError(f"Unreadable MP4 clip: {path}")
    try:
        with path.open("rb") as handle:
            if not handle.read(1):
                raise ClipError(f"Empty MP4 clip: {path}")
    except OSError as exc:
        raise ClipError(f"Unreadable MP4 clip: {path}: {exc}") from exc
    return path


class LocalClipSource:
    def __init__(self, root: Path = Path("sample_clips")) -> None:
        self.root = root.resolve()

    def list_clips(self) -> list[Path]:
        return sorted(p for p in self.root.glob("*") if p.is_file() and p.suffix.lower() == ".mp4")

    def open(self, name: str) -> Path:
        path = (self.root / name).resolve()
        if path.parent != self.root:
            raise ClipError(f"Clip must be directly under {self.root}: {name}")
        return validate_clip(path)
