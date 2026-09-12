import asyncio
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException

from goldcoast.agents.ad_agent import brief_key
from goldcoast.api.deps import RegistryDep, SeedDep, SettingsDep, StoreDep, require_run
from goldcoast.api.paths import clip_path, media_url, safe_path
from goldcoast.api.schemas import AdWithVerdict, ExportAd, ExportManifest, MomentView, RunCreate
from goldcoast.api.views import final_ads, moment_view
from goldcoast.models.pipeline import AdBrief, Run
from goldcoast.pipeline.events import EventBus
from goldcoast.pipeline.orchestrator import Pipeline
from goldcoast.storage import write_bytes, write_json

router = APIRouter()


@router.post("/runs", response_model=Run, status_code=201)
async def create_run(
    body: RunCreate,
    settings: SettingsDep,
    seed: SeedDep,
    store: StoreDep,
    registry: RegistryDep,
) -> Run:
    def prepare():
        clip = clip_path(settings.sample_clips_dir, body.clip_path)
        replay = bool(body.replay_from) or (settings.replay if body.replay is None else body.replay)
        source = (body.replay_from or settings.replay_run) if replay else None
        if replay:
            if not source:
                raise HTTPException(400, "Replay requires replay_from or GOLDCOAST_REPLAY_RUN")
            original = require_run(store, source)
            if original.clip_path.resolve() != clip.resolve():
                raise HTTPException(400, "Replay clip must match the source run's clip_path")
        elif not clip.is_file():
            raise HTTPException(400, "Clip not found")
        configuration = settings.model_copy(update={"replay": replay, "replay_run": source})
        if not replay and not configuration.gemini_api_key:
            raise HTTPException(400, "Live runs require a configured API key")
        run = store.create_run(clip, replay)
        run.replay_from = source
        store.save_run(run)
        return run, Pipeline(configuration, seed, store)

    run, pipeline = await asyncio.to_thread(prepare)
    response = run.model_copy(deep=True)
    registry.start(run, EventBus(store.run_dir(run.id)), pipeline)
    return response


@router.get("/runs", response_model=list[Run])
def list_runs(store: StoreDep):
    return store.list_runs()


@router.get("/runs/{run_id}", response_model=Run)
def get_run(run_id: str, store: StoreDep):
    return require_run(store, run_id)


@router.get("/runs/{run_id}/moments", response_model=list[MomentView])
def moments(run_id: str, store: StoreDep):
    require_run(store, run_id)
    return [moment_view(moment) for moment in store.moments(run_id)]


@router.get("/runs/{run_id}/briefs", response_model=list[AdBrief])
def briefs(run_id: str, store: StoreDep):
    require_run(store, run_id)
    return store.briefs(run_id)


@router.get("/runs/{run_id}/ads", response_model=list[AdWithVerdict])
def ads(run_id: str, store: StoreDep):
    return final_ads(store, require_run(store, run_id))


@router.get("/runs/{run_id}/export", response_model=ExportManifest)
def export(run_id: str, store: StoreDep, registry: RegistryDep):
    require_run(store, run_id)
    root = store.run_dir(run_id)
    bus = registry.get_bus(run_id) or EventBus(root)
    with bus.lock:
        selected = [
            ad
            for ad in final_ads(store, require_run(store, run_id))
            if ad.decision and ad.decision.decision == "approved"
        ]
        entries = []
        for ad in selected:
            relative = f"approved/{ad.business_id}_brief_{brief_key(ad.brief_id)}_{ad.format}.png"
            target = safe_path(root, relative)
            source = safe_path(root, ad.image_path.relative_to(root).as_posix())
            if not source.is_file():
                raise HTTPException(409, "Approved ad image is missing")
            write_bytes(target, source.read_bytes())
            entries.append(
                ExportAd(
                    ad_id=ad.id,
                    brief_id=ad.brief_id,
                    business_id=ad.business_id,
                    format=ad.format,
                    path=relative,
                    image_url=media_url(run_id, relative),
                    decision=ad.decision,
                )
            )
        manifest = ExportManifest(run_id=run_id, exported_at=datetime.now(UTC), ads=entries)
        write_json(safe_path(root, "approved/manifest.json"), manifest)
        keep = {entry.path for entry in entries}
        for path in safe_path(root, "approved").glob("*.png"):
            relative = path.relative_to(root).as_posix()
            if relative not in keep:
                safe_path(root, relative).unlink()
        return manifest
