import asyncio

import pytest

from goldcoast.models.pipeline import PipelineEventType as E
from goldcoast.pipeline.events import EventBus, EventPersistenceError
from goldcoast.pipeline.run_store import RunStore


@pytest.mark.asyncio
async def test_backlog_threaded_delivery_resume_and_cleanup(tmp_path):
    store = RunStore(tmp_path)
    run = store.create_run(tmp_path / "clip.mp4")
    assert store.get_run(run.id) == run
    assert store.list_runs() == [run]
    bus = EventBus(store.run_dir(run.id))
    bus.emit(E.RUN_STARTED, {})
    bus.emit(E.CLIP_LOADED, {})
    received = []

    async def consume():
        stream = bus.subscribe(after=0)
        try:
            async for event in stream:
                received.append(event)
                assert event in bus.backlog()
                if event.type == E.RUN_COMPLETED:
                    break
        finally:
            await stream.aclose()

    consumer = asyncio.create_task(consume())
    await asyncio.sleep(0)
    await asyncio.to_thread(bus.emit, E.RUN_COMPLETED, {})
    await asyncio.wait_for(consumer, timeout=2)
    assert [event.id for event in received] == ["1", "2"]
    assert not bus.listeners


def test_event_persistence_error_is_explicit(tmp_path):
    path = tmp_path / "not-directory"
    path.write_text("occupied")
    with pytest.raises(EventPersistenceError):
        EventBus(path).emit(E.RUN_STARTED, {})


@pytest.mark.parametrize("identifier", ["../outside", "..", "C:/outside", "a\\b"])
def test_run_store_confines_identifiers(tmp_path, identifier):
    with pytest.raises(ValueError):
        RunStore(tmp_path).run_dir(identifier)
