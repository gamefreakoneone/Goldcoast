from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends, HTTPException, Request

from goldcoast.data import SeedData
from goldcoast.models.pipeline import PipelineEventType as E
from goldcoast.models.pipeline import Run, RunFailure, RunStatus
from goldcoast.pipeline.events import EventBus
from goldcoast.pipeline.orchestrator import Pipeline
from goldcoast.pipeline.run_store import RunStore
from goldcoast.settings import Settings

logger = logging.getLogger(__name__)


class RunRegistry:
    def __init__(self, store: RunStore):
        self.store = store
        self.buses: dict[str, EventBus] = {}
        self.tasks: dict[str, asyncio.Task] = {}

    def get_bus(self, run_id: str) -> EventBus | None:
        return self.buses.get(run_id)

    def start(self, run: Run, bus: EventBus, pipeline: Pipeline) -> None:
        self.buses[run.id] = bus
        self.tasks[run.id] = asyncio.create_task(self._execute(run, bus, pipeline))

    async def _execute(self, run: Run, bus: EventBus, pipeline: Pipeline) -> None:
        try:
            await asyncio.to_thread(pipeline.run, run.clip_path, run.replay_from, run=run, bus=bus)
        except Exception as exc:
            logger.exception("Background pipeline failed: %s", run.id)
            try:
                run.status = RunStatus.FAILED
                run.finished_at = datetime.now(UTC)
                run.failures.append(RunFailure(stage="api", message=str(exc)))
                await asyncio.to_thread(self.store.save_run, run)
                await asyncio.to_thread(
                    bus.emit, E.RUN_FAILED, {**run.model_dump(mode="json"), "reason": str(exc)}
                )
            except Exception:
                logger.exception("Could not persist background failure: %s", run.id)
        finally:
            self.buses.pop(run.id, None)
            self.tasks.pop(run.id, None)

    async def close(self) -> None:
        if self.tasks:
            await asyncio.gather(*list(self.tasks.values()))


def settings(request: Request) -> Settings:
    return request.app.state.settings


def seed(request: Request) -> SeedData:
    return request.app.state.seed


def store(request: Request) -> RunStore:
    return request.app.state.store


def registry(request: Request) -> RunRegistry:
    return request.app.state.registry


SettingsDep = Annotated[Settings, Depends(settings)]
SeedDep = Annotated[SeedData, Depends(seed)]
StoreDep = Annotated[RunStore, Depends(store)]
RegistryDep = Annotated[RunRegistry, Depends(registry)]


def require_run(store: RunStore, identifier: str) -> Run:
    try:
        return store.get_run(identifier)
    except (ValueError, OSError) as exc:
        raise HTTPException(404, "Run not found") from exc
