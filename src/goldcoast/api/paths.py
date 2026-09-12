import re
from pathlib import Path, PureWindowsPath
from urllib.parse import quote

from fastapi import HTTPException


def safe_path(root: Path, value: str, status: int = 404) -> Path:
    if (
        not value
        or "\\" in value
        or ":" in value
        or "\x00" in value
        or PureWindowsPath(value).is_absolute()
        or Path(value).is_absolute()
        or any(part in {"", ".", ".."} for part in value.split("/"))
    ):
        raise HTTPException(status, "Invalid path")
    path = root / value
    try:
        if not path.resolve().is_relative_to(root.resolve()):
            raise HTTPException(status, "Path outside allowed directory")
    except (OSError, ValueError) as exc:
        raise HTTPException(status, "Invalid path") from exc
    return path


def clip_path(root: Path, value: str) -> Path:
    normalized = value.replace("\\", "/")
    if "\x00" in value or ".." in normalized.split("/"):
        raise HTTPException(400, "Invalid clip path")
    path = Path(normalized)
    if "/" not in normalized:
        path = root / path
    try:
        relative = path.resolve().relative_to(root.resolve())
    except (OSError, ValueError) as exc:
        raise HTTPException(400, "Clip outside sample_clips directory") from exc
    if len(relative.parts) != 1 or path.suffix.lower() != ".mp4":
        raise HTTPException(400, "Clip must be an MP4 in the sample_clips directory")
    safe_path(root, relative.as_posix(), 400)
    return path


def valid_ad_id(identifier: str) -> None:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,255}", identifier):
        raise HTTPException(404, "Ad not found")


def media_url(run_id: str, relative: str) -> str:
    return f"/media/{quote(run_id, safe='')}/{quote(relative, safe='/')}"


def clip_url(name: str) -> str:
    return f"/clips/{quote(name, safe='')}"
