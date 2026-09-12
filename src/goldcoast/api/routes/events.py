import asyncio
import re
from typing import Annotated

from fastapi import APIRouter, Header, HTTPException, Response
from sse_starlette.sse import EventSourceResponse

from goldcoast.api.deps import RegistryDep, StoreDep, require_run
from goldcoast.api.views import event_view
from goldcoast.pipeline.events import EventBus

router = APIRouter()
TERMINAL = {"run_completed", "run_failed"}


@router.get("/runs/{run_id}/events", response_class=EventSourceResponse)
async def events(
    run_id: str,
    store: StoreDep,
    registry: RegistryDep,
    last_event_id: Annotated[str | None, Header()] = None,
):
    await asyncio.to_thread(require_run, store, run_id)
    if last_event_id is not None and not re.fullmatch(r"[0-9]{1,12}", last_event_id):
        raise HTTPException(400, "Last-Event-ID must be a nonnegative event index")
    after = int(last_event_id) if last_event_id is not None else -1
    active_bus = registry.get_bus(run_id)
    bus = active_bus or EventBus(store.run_dir(run_id))
    backlog = await asyncio.to_thread(bus.backlog)
    terminal = next((event for event in backlog if event.type in TERMINAL), None)
    if terminal is not None and after >= int(terminal.id):
        return Response(status_code=204)
    if after > (int(backlog[-1].id) if backlog else -1):
        raise HTTPException(400, "Last-Event-ID is ahead of this run")

    def message(event):
        return {
            "id": event.id,
            "event": event.type.value,
            "data": event_view(event).model_dump_json(),
        }

    async def stream():
        if active_bus is None:
            for event in backlog:
                if int(event.id) > after:
                    yield message(event)
                if event.type in TERMINAL:
                    break
            return
        subscription = bus.subscribe(after)
        try:
            async for event in subscription:
                yield message(event)
                if event.type in TERMINAL:
                    break
        finally:
            await subscription.aclose()

    return EventSourceResponse(stream(), ping=15, send_timeout=30)
