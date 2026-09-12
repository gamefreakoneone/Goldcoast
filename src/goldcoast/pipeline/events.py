from __future__ import annotations

import asyncio
import os
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from pathlib import Path
from threading import RLock

from goldcoast.models.pipeline import PipelineEvent, PipelineEventType

_locks: dict[Path, RLock] = {}
_guard = RLock()


class EventPersistenceError(RuntimeError):
    pass


class EventBus:
    def __init__(self, run_dir: Path):
        self.run_dir = run_dir
        self.path = run_dir / "events.jsonl"
        with _guard:
            self.lock = _locks.setdefault(self.path.resolve(), RLock())
        self.listeners: list[tuple[asyncio.AbstractEventLoop, asyncio.Queue]] = []

    def backlog(self) -> list[PipelineEvent]:
        with self.lock:
            if not self.path.exists():
                return []
            return [
                PipelineEvent.model_validate_json(line)
                for line in self.path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]

    def emit(self, type: PipelineEventType, payload: dict) -> PipelineEvent:
        with self.lock:
            event = PipelineEvent(
                id=str(len(self.backlog())),
                run_id=self.run_dir.name,
                type=type,
                timestamp=datetime.now(UTC),
                payload=payload,
            )
            try:
                self.run_dir.mkdir(parents=True, exist_ok=True)
                with self.path.open("ab") as handle:
                    handle.write((event.model_dump_json() + "\n").encode())
                    handle.flush()
                    os.fsync(handle.fileno())
            except OSError as exc:
                raise EventPersistenceError(f"Cannot append event log: {exc}") from exc
            for loop, queue in self.listeners:
                loop.call_soon_threadsafe(queue.put_nowait, event)
            return event

    async def subscribe(self, after: int = -1) -> AsyncIterator[PipelineEvent]:
        queue: asyncio.Queue[PipelineEvent] = asyncio.Queue()
        listener = (asyncio.get_running_loop(), queue)
        with self.lock:
            backlog = [event for event in self.backlog() if int(event.id) > after]
            self.listeners.append(listener)
        try:
            for event in backlog:
                yield event
            while True:
                event = await queue.get()
                if int(event.id) > after:
                    yield event
        finally:
            with self.lock:
                self.listeners.remove(listener)
