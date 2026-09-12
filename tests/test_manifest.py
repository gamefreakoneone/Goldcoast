import json
from pathlib import Path

from goldcoast.models import ClipEntry, ClipManifest, ManifestMoment


def test_missing_manifest_loads_empty(tmp_path: Path) -> None:
    assert ClipManifest.load(tmp_path / "missing.json").entries == []


def test_manifest_upsert_save_and_reload(tmp_path: Path) -> None:
    path = tmp_path / "nested" / "manifest.json"
    manifest = ClipManifest()
    manifest.upsert(ClipEntry(file="clip.mp4", notes="first"))
    manifest.upsert(
        ClipEntry(
            file="clip.mp4",
            sport="archery",
            analyzed=True,
            analyzed_by="manual",
            moments=[
                ManifestMoment(
                    start_s=1,
                    end_s=3,
                    best_frame_s=2,
                    hype_score=9,
                    description="Bullseye",
                    event_context="Final arrow",
                )
            ],
        )
    )
    manifest.save(path)

    raw = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(raw, list)
    assert raw[0]["file"] == "clip.mp4"
    assert len(raw) == 1
    assert ClipManifest.load(path) == manifest
    assert not list(path.parent.glob("*.tmp"))


def test_manifest_get_returns_none_for_unknown_file() -> None:
    manifest = ClipManifest(entries=[ClipEntry(file="known.mp4")])
    assert manifest.get("known.mp4") is not None
    assert manifest.get("unknown.mp4") is None
