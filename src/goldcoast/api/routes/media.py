from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from goldcoast.api.deps import SettingsDep, StoreDep, require_run
from goldcoast.api.paths import clip_url, safe_path
from goldcoast.api.schemas import ClipInfo
from goldcoast.models.manifest import ClipEntry, ClipManifest

router = APIRouter()


@router.get("/clips", response_model=list[ClipInfo])
def clips(settings: SettingsDep):
    root = settings.sample_clips_dir
    entries = {entry.file: entry for entry in ClipManifest.load(settings.clip_manifest).entries}
    for path in root.glob("*"):
        if path.suffix.lower() == ".mp4" and path.is_file():
            entries.setdefault(path.name, ClipEntry(file=path.name))
    result = []
    for name, entry in sorted(entries.items()):
        if "/" in name or not name.lower().endswith(".mp4"):
            continue
        try:
            path = safe_path(root, name)
        except HTTPException:
            continue
        result.append(
            ClipInfo(
                **entry.model_dump(),
                clip_path=path.as_posix(),
                clip_url=clip_url(name),
                available=path.is_file(),
            )
        )
    return result


@router.get("/clips/{name}")
def clip(name: str, settings: SettingsDep):
    path = safe_path(settings.sample_clips_dir, name)
    if path.suffix.lower() != ".mp4" or not path.is_file():
        raise HTTPException(404, "Clip not found")
    return FileResponse(path, media_type="video/mp4")


@router.get("/media/{run_id}/{path:path}")
def media(run_id: str, path: str, store: StoreDep):
    require_run(store, run_id)
    target = safe_path(store.run_dir(run_id), path)
    if not target.is_file():
        raise HTTPException(404, "Media not found")
    return FileResponse(target)
