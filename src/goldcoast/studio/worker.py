import argparse
import asyncio
import os
import threading
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

from google.genai import types

from goldcoast.agents.runtime import AgentRuntime, ExecutionBudget
from goldcoast.llm.client import GeminiClient
from goldcoast.settings import Settings
from goldcoast.studio.assets import LocalAssetStore
from goldcoast.studio.brand import BrandService
from goldcoast.studio.config import StudioSettings
from goldcoast.studio.creative import produce_creatives
from goldcoast.studio.database import session_factory
from goldcoast.studio.discovery import Discovery, ProviderCassette
from goldcoast.studio.repository import Conflict, Repository
from goldcoast.studio.workflow import CampaignResult, Snapshot, Stages, VideoEvidence, plan_campaign


class MeteredClient:
    def __init__(self, client, reserve):
        self.client, self.reserve = client, reserve

    def generate(self, *args, **kwargs):
        self.reserve("model")
        return self.client.generate(*args, **kwargs)

    def generate_image(self, *args, **kwargs):
        self.reserve("image")
        self.reserve("model")
        return self.client.generate_image(*args, **kwargs)


def live_providers(repo, assets, job, worker):
    settings = Settings.from_env()
    if not settings.gemini_api_key:
        raise ValueError("GEMINI_API_KEY is required for live workflows")
    root = (
        Path(os.getenv("GOLDCOAST_STUDIO_RUN_ROOT", "output/studio/runs")) / job.tenant_id / job.id
    )

    def reserve(kind):
        repo.reserve_call(job.tenant_id, job.id, kind, worker)

    def emit(kind, payload):
        repo.emit(
            job.tenant_id,
            job.id,
            kind,
            {
                "agent": payload.get("agent") or payload.get("name", ""),
                "tool": payload.get("payload", {}).get("name", ""),
            },
        )

    runtime = AgentRuntime.gemini(
        root / "agents",
        settings.judge_model,
        settings.gemini_api_key,
        budget=ExecutionBudget(reserve=reserve),
        emit=emit,
    )
    discovery = Discovery(
        ProviderCassette(root / "providers", reserve),
        os.getenv("TAVILY_API_KEY"),
        os.getenv("TICKETMASTER_API_KEY"),
    )
    client = MeteredClient(GeminiClient(settings, root / "models"), reserve)
    return runtime, discovery, client, settings, reserve, root


async def execute_job(
    repo, assets, job, worker, provider_factory=live_providers, creative_producer=produce_creatives
):
    stages = Stages(repo, job, worker)
    if job.mode == "replay":
        from goldcoast.studio.replay import replay_job

        replay_job(repo, assets, job, worker)
        return
    snapshot = Snapshot.model_validate(job.input["snapshot"])
    runtime, discovery, client, settings, reserve, root = provider_factory(
        repo, assets, job, worker
    )
    if job.kind == "brand":
        await stages.run(
            "brand_analysis",
            lambda: BrandService(repo, assets).analyze(
                job.tenant_id,
                client,
                settings.judge_model,
                [r["id"] for r in snapshot.assets],
            ),
        )
        return
    video = None
    if job.input.get("video_asset_id"):

        def analyze_video():
            asset_id = job.input["video_asset_id"]
            repo.get(job.tenant_id, "asset", asset_id)
            reserve("video")
            record = client.generate(
                "studio_video",
                settings.video_model,
                [
                    "Describe visible activity, products, readable text and local cultural cues. "
                    "Propose search queries to verify context. Do not infer identity, nationality, "
                    "personal preferences or endorsements from appearance.",
                    types.Part.from_bytes(
                        data=assets.get(job.tenant_id, asset_id), mime_type="video/mp4"
                    ),
                ],
                types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_json_schema=VideoEvidence.model_json_schema(),
                ),
                input_refs=[asset_id],
            )
            return VideoEvidence.model_validate_json(record.response_text)

        video = await stages.run("video_evidence", analyze_video)
    if discovery.ticketmaster_key:
        now = datetime.now(UTC)
        events = await stages.run(
            "local_events",
            lambda: discovery.local_events(
                snapshot.profile.city,
                now.strftime("%Y-%m-%dT%H:%M:%SZ"),
                (now + timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            ),
        )
        from goldcoast.studio.graph import EvidenceSource

        for source in events["sources"]:
            parsed = EvidenceSource.model_validate(source)
            discovery.sources[parsed.id] = parsed
    prior = stages.data.get("campaign", {})
    if prior.get("state") == "completed":
        result = CampaignResult.model_validate(prior["output"])
    else:
        result = await plan_campaign(snapshot, job.input["goal"], runtime, discovery, stages, video)
        await stages.run("campaign", lambda: result)

    if creative_producer is not None:
        await creative_producer(
            repo, assets, job, snapshot, result, runtime, client, settings, stages, root
        )


def process_job(
    repo, assets, job, worker, provider_factory=live_providers, creative_producer=produce_creatives
):
    stop = threading.Event()

    def heartbeat():
        while not stop.wait(20):
            try:
                repo.renew(job.tenant_id, job.id, worker)
            except Exception:
                return

    thread = threading.Thread(target=heartbeat, daemon=True)
    thread.start()
    try:
        asyncio.run(execute_job(repo, assets, job, worker, provider_factory, creative_producer))
        repo.finish(job.tenant_id, job.id, "completed", worker)
    except Exception as exc:
        try:
            repo.emit(
                job.tenant_id,
                job.id,
                "workflow_error",
                {
                    "error": type(exc).__name__,
                    "message": str(exc)[:250]
                    if isinstance(exc, (Conflict, ValueError))
                    else "Workflow failed; inspect private recordings",
                },
            )
            repo.finish(job.tenant_id, job.id, "failed", worker)
        except Conflict:
            pass
    finally:
        stop.set()
        thread.join(timeout=2)


def main():
    parser = argparse.ArgumentParser(description="Run the Goldcoast marketing workflow worker")
    parser.add_argument(
        "--once", action="store_true", help="Process at most one queued job and exit"
    )
    args = parser.parse_args()
    settings = StudioSettings.from_env()
    engine, sessions = session_factory(settings.database_url)
    repo, assets = Repository(sessions), LocalAssetStore(settings.asset_root)
    worker = uuid4().hex
    from goldcoast.studio.schedule import ScheduleService

    next_schedule_check = 0
    try:
        while True:
            if time.monotonic() >= next_schedule_check:
                ScheduleService(repo, assets).tick()
                next_schedule_check = time.monotonic() + 60
            job = repo.claim(worker)
            if job:
                process_job(repo, assets, job, worker)
            if args.once:
                break
            if not job:
                time.sleep(2)
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
