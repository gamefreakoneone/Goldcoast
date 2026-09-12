import asyncio
import json
import shutil
from datetime import UTC, datetime
from pathlib import Path
from threading import Event

import httpx
import pytest
from fastapi.testclient import TestClient

from goldcoast.agents.video_agent import VideoAgent
from goldcoast.api.app import create_app
from goldcoast.llm.client import GeminiClient
from goldcoast.models.pipeline import PipelineEventType as E
from goldcoast.models.pipeline import RunStatus
from goldcoast.pipeline.events import EventBus
from goldcoast.pipeline.orchestrator import Pipeline
from goldcoast.pipeline.run_store import RunStore

SOURCE_ID = "20260912-230559-0d2470"
FIXTURE = Path(__file__).parent / "fixtures/runs" / SOURCE_ID


@pytest.fixture
def api_case(tmp_path, agent_settings):
    store = RunStore(tmp_path / "output")
    shutil.copytree(FIXTURE, store.run_dir(SOURCE_ID))
    clips = tmp_path / "clips"
    clips.mkdir()
    clip = clips / "gymnastics_simone.mp4"
    clip.write_bytes(b"recorded-clip-byte-range-test")
    manifest = clips / "manifest.json"
    shutil.copyfile("sample_clips/manifest.json", manifest)
    source = store.get_run(SOURCE_ID)
    source.clip_path = clip
    store.save_run(source)
    settings = agent_settings.model_copy(
        update={
            "output_dir": tmp_path / "output",
            "sample_clips_dir": clips,
            "clip_manifest": manifest,
            "replay_run": SOURCE_ID,
        }
    )
    return create_app(settings), store, settings, clip


def parse_sse(text):
    messages = []
    for block in text.replace("\r\n", "\n").split("\n\n"):
        fields = dict(line.split(": ", 1) for line in block.splitlines() if ": " in line)
        if "data" in fields:
            payload = json.loads(fields["data"])
            assert fields["id"] == payload["id"]
            assert fields["event"] == payload["type"]
            messages.append(payload)
    return messages


def test_fixture_views_media_and_cors(api_case):
    app, store, settings, clip = api_case
    with TestClient(app) as client:
        assert client.get("/runs").json()[0]["id"] == SOURCE_ID
        assert client.get(f"/runs/{SOURCE_ID}").json()["status"] == "completed"
        assert len(client.get(f"/runs/{SOURCE_ID}/briefs").json()) == 6
        moments = client.get(f"/runs/{SOURCE_ID}/moments").json()
        assert [m["best_frame_s"] for m in moments] == [122.5, 41.0, 91.5]
        assert (
            client.get(moments[0]["best_frame_url"]).content
            == (store.run_dir(SOURCE_ID) / "frames" / f"{moments[0]['id']}.png").read_bytes()
        )
        ads = client.get(f"/runs/{SOURCE_ID}/ads").json()
        assert [ad["id"] for ad in ads] == store.get_run(SOURCE_ID).ad_ids
        assert len(ads) == 12
        assert sum(len(ad["attempts"]) for ad in ads) == 17
        for ad in ads:
            assert ad["verdict"]["ad_id"] == ad["id"]
            assert ad["verdict"]["scores"]["overall"] == 7
            assert len(ad["verdict"]["scores"]) == 6
            assert ad["decision"] is None
            assert sum(attempt["is_final"] for attempt in ad["attempts"]) == 1
            assert client.get(ad["image_url"]).content == Path(ad["image_path"]).read_bytes()
        listing = client.get("/clips").json()
        assert listing[0]["analyzed"] and listing[0]["available"]
        assert listing[0]["athlete_id"] == "simone-biles"
        response = client.get(listing[0]["clip_url"], headers={"Range": "bytes=2-8"})
        assert response.status_code == 206
        assert response.content == clip.read_bytes()[2:9]
        assert response.headers["content-range"].startswith("bytes 2-8/")
        assert client.get("/seed/athletes").json()[0]["id"] == "simone-biles"
        businesses = client.get("/seed/businesses").json()
        assert len(businesses) == 3
        assert (
            sum(
                b["offer_text"] == "Demo offer: bring your Olympics ticket for 15% off"
                for b in businesses
            )
            == 2
        )
        assert client.get("/seed/ad-styles").json()
        response = client.options(
            "/runs",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type,Last-Event-ID",
            },
        )
        assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
        assert (
            "access-control-allow-origin"
            not in client.get("/clips", headers={"Origin": "http://unlisted.example"}).headers
        )
        clip.unlink()
        assert not client.get("/clips").json()[0]["available"]
        assert client.get(listing[0]["clip_url"]).status_code == 404


def test_replay_post_and_sse(api_case, monkeypatch):
    app, store, settings, clip = api_case

    def forbidden(*args, **kwargs):
        raise AssertionError("API replay must not call Gemini or detect/decode the video")

    monkeypatch.setattr(GeminiClient, "__init__", forbidden)
    monkeypatch.setattr(VideoAgent, "detect", forbidden)
    clip.unlink()
    with TestClient(app) as client:
        response = client.post("/runs", json={"clip_path": str(clip), "replay_from": SOURCE_ID})
        assert response.status_code == 201
        run = response.json()
        assert run["status"] == "running" and run["replay_from"] == SOURCE_ID
        assert run["id"] != SOURCE_ID
        response = client.get(f"/runs/{run['id']}/events")
        assert response.headers["content-type"].startswith("text/event-stream")
        events = parse_sse(response.text)
        assert [e["id"] for e in events] == [str(i) for i in range(len(events))]
        assert events[-1]["type"] == "run_completed"
        assert [e["type"] for e in events] == [
            e.type for e in EventBus(store.run_dir(SOURCE_ID)).backlog()
        ]
        for event in events:
            if event["type"] == "frame_extracted":
                assert client.get(event["payload"]["best_frame_url"]).status_code == 200
            if event["type"] == "ad_final":
                payload = event["payload"]
                assert client.get(payload["final_ad"]["image_url"]).status_code == 200
                assert len(payload["attempts"][0]) == 2
                assert "image_url" in payload["attempts"][0][0]
        finished = client.get(f"/runs/{run['id']}").json()
        assert not finished["failures"]
        assert [len(finished[key]) for key in ("moment_ids", "brief_ids", "ad_ids")] == [3, 6, 12]
        assert len(client.get("/runs").json()) == 2
        source_bytes = {
            ad.id.removeprefix(SOURCE_ID): ad.image_path.read_bytes() for ad in store.ads(SOURCE_ID)
        }
        for ad in store.ads(run["id"]):
            assert ad.image_path.read_bytes() == source_bytes[ad.id.removeprefix(run["id"])]
        assert not (store.run_dir(run["id"]) / "model_calls/http_requests").exists()
        resumed = client.get(f"/runs/{run['id']}/events", headers={"Last-Event-ID": "2"})
        assert parse_sse(resumed.text) == events[3:]
        for cursor in (events[-1]["id"], "999999"):
            assert (
                client.get(
                    f"/runs/{run['id']}/events", headers={"Last-Event-ID": cursor}
                ).status_code
                == 204
            )
        assert not app.state.registry.tasks


def test_decisions_export_and_restart(api_case):
    app, store, settings, clip = api_case
    with TestClient(app) as client:
        ads = client.get(f"/runs/{SOURCE_ID}/ads").json()
        assert client.get(f"/runs/{SOURCE_ID}/export").json()["ads"] == []
        for ad in ads:
            decision = client.post(
                f"/ads/{ad['id']}/decision",
                json={"ad_id": ad["id"], "decision": "approved", "reviewer": "demo", "note": ""},
            )
            assert decision.status_code == 200
            assert decision.json()["decided_at"]
        manifest = client.get(f"/runs/{SOURCE_ID}/export").json()
        assert len(manifest["ads"]) == 12
        assert len({entry["path"] for entry in manifest["ads"]}) == 12
        for entry in manifest["ads"]:
            ad = next(ad for ad in ads if ad["id"] == entry["ad_id"])
            assert client.get(entry["image_url"]).content == Path(ad["image_path"]).read_bytes()
        rejected = client.post(
            f"/ads/{ads[0]['id']}/decision",
            json={"decision": "rejected", "reviewer": "demo", "note": "Use the other moment"},
        )
        assert rejected.status_code == 200
        refreshed = client.get(f"/runs/{SOURCE_ID}/ads").json()
        assert refreshed[0]["decision"]["decision"] == "rejected"
        exported = client.get(f"/runs/{SOURCE_ID}/export").json()
        assert len(exported["ads"]) == 11
        assert not (store.run_dir(SOURCE_ID) / manifest["ads"][0]["path"]).exists()
        assert len(list((store.run_dir(SOURCE_ID) / "approved").glob("*.png"))) == 11
        assert Path(ads[0]["image_path"]).is_file()
        assert (
            json.loads((store.run_dir(SOURCE_ID) / "approved/manifest.json").read_text())
            == exported
        )
        events = EventBus(store.run_dir(SOURCE_ID)).backlog()
        assert sum(event.type == "ad_decided" for event in events) == 13
        assert [e.id for e in events] == [str(i) for i in range(len(events))]
        assert (
            parse_sse(client.get(f"/runs/{SOURCE_ID}/events").text)[-1]["type"] == "run_completed"
        )
    with TestClient(create_app(settings)) as client:
        assert client.get(f"/runs/{SOURCE_ID}/ads").json()[0]["decision"] == rejected.json()


def test_verdict_precondition_and_final_selection(api_case):
    app, store, settings, clip = api_case
    run = store.get_run(SOURCE_ID)
    candidates = [ad for ad in store.ads(SOURCE_ID) if ad.id not in run.ad_ids]
    selected = candidates[0]
    run.ad_ids = [selected.id]
    store.save_run(run)
    with TestClient(app) as client:
        ads = client.get(f"/runs/{SOURCE_ID}/ads").json()
        assert ads[0]["id"] == selected.id
        assert not ads[0]["verdict"]["passed"]
        assert len(ads[0]["attempts"]) > 1
        assert (
            client.post(
                f"/ads/{selected.id}/decision", json={"decision": "approved", "reviewer": "demo"}
            ).status_code
            == 200
        )
        for path in (store.run_dir(SOURCE_ID) / "verdicts").glob("*.json"):
            if json.loads(path.read_text())["ad_id"] == selected.id:
                path.unlink()
        assert client.get(f"/runs/{SOURCE_ID}/ads").status_code == 409
        assert (
            client.post(
                f"/ads/{selected.id}/decision", json={"decision": "rejected", "reviewer": "demo"}
            ).status_code
            == 409
        )


def test_errors_and_confinement(api_case, tmp_path):
    app, store, settings, clip = api_case
    with TestClient(app) as client:
        for suffix in ("", "/events", "/moments", "/briefs", "/ads", "/export"):
            assert client.get(f"/runs/unknown{suffix}").status_code == 404
        for cursor in ("-1", "abc", "1.0", "", "9999999999999"):
            assert (
                client.get(
                    f"/runs/{SOURCE_ID}/events", headers={"Last-Event-ID": cursor}
                ).status_code
                == 400
            )
        for path in (
            "../run.json",
            "%2e%2e/run.json",
            "..%5crun.json",
            "C%3a/Windows/win.ini",
            "%2fetc/passwd",
            "frames/../../run.json",
            "frames/%00.png",
        ):
            assert client.get(f"/media/{SOURCE_ID}/{path}").status_code == 404
        for path in ("..%5c.env", "manifest.json", "missing.mp4", "C%3a.env"):
            assert client.get(f"/clips/{path}").status_code == 404
        assert client.get(f"/media/{SOURCE_ID}/missing.png").status_code == 404
        assert client.get("/media/..%5coutside/run.json").status_code == 404
        for path in ("../outside.mp4", str(tmp_path / "outside.mp4"), "..\\clip.mp4"):
            assert client.post("/runs", json={"clip_path": path}).status_code == 400
        assert (
            client.post(
                "/runs", json={"clip_path": str(clip), "replay_from": "unknown"}
            ).status_code
            == 404
        )
        assert (
            client.post(
                "/runs",
                json={"clip_path": str(clip.with_name("other.mp4")), "replay_from": SOURCE_ID},
            ).status_code
            == 400
        )
        assert (
            client.post(
                "/runs", json={"clip_path": str(clip), "replay_from": "..\\outside"}
            ).status_code
            == 404
        )
        ad_id = store.get_run(SOURCE_ID).ad_ids[0]
        assert (
            client.post(
                f"/ads/{ad_id}/decision",
                json={"ad_id": "wrong", "decision": "approved", "reviewer": "demo"},
            ).status_code
            == 400
        )
        for identifier in ("unknown", "..%5coutside"):
            assert (
                client.post(
                    f"/ads/{identifier}/decision", json={"decision": "approved", "reviewer": "demo"}
                ).status_code
                == 404
            )
        assert (
            client.post(
                f"/ads/{ad_id}/decision", json={"decision": "approved", "reviewer": " "}
            ).status_code
            == 422
        )
        assert len(store.list_runs()) == 1


def test_symlink_escape(api_case, tmp_path):
    app, store, settings, clip = api_case
    outside = tmp_path / "private"
    outside.mkdir()
    (outside / "private.png").write_bytes(b"outside")

    def link_directory(target):
        try:
            target.symlink_to(outside, target_is_directory=True)
        except OSError as exc:
            if getattr(exc, "winerror", None) != 1314:
                raise
            import _winapi

            _winapi.CreateJunction(str(outside), str(target))

    link_directory(store.run_dir(SOURCE_ID) / "escape")
    link_directory(store.run_dir(SOURCE_ID) / "approved")
    link_directory(settings.sample_clips_dir / "escape.mp4")
    with TestClient(app) as client:
        assert client.get(f"/media/{SOURCE_ID}/escape/private.png").status_code == 404
        assert client.get(f"/runs/{SOURCE_ID}/export").status_code == 404
        assert client.get("/clips/escape.mp4").status_code == 404
        assert "escape.mp4" not in [entry["file"] for entry in client.get("/clips").json()]
        assert not (outside / "manifest.json").exists()


def test_missing_record_ends_sse(api_case):
    app, store, settings, clip = api_case
    (store.run_dir(SOURCE_ID) / "model_calls/match_rerank_1.json").unlink()
    with TestClient(app) as client:
        response = client.post("/runs", json={"clip_path": str(clip)})
        assert response.status_code == 201
        assert response.json()["replay"]
        identifier = response.json()["id"]
        events = parse_sse(client.get(f"/runs/{identifier}/events").text)
        assert events[-1]["type"] == "run_failed"
        assert "stage=match_rerank, sequence=1" in events[-1]["payload"]["reason"]
        assert client.get(f"/runs/{identifier}").json()["status"] == "failed"


def test_replay_defaults_and_live_override(api_case, monkeypatch):
    app, store, settings, clip = api_case
    settings.replay_run = None
    with TestClient(app) as client:
        assert client.post("/runs", json={"clip_path": str(clip)}).status_code == 400
        assert (
            client.post("/runs", json={"clip_path": str(clip), "replay": False}).status_code == 400
        )
    settings.gemini_api_key = "unused-test-key"
    settings.replay_run = SOURCE_ID
    observed = []

    def finish(self, clip_path, replay_from=None, *, run=None, bus=None):
        observed.append((self.settings.replay, replay_from, run.id))
        run.status = RunStatus.COMPLETED
        run.finished_at = datetime.now(UTC)
        self.store.save_run(run)
        bus.emit(E.RUN_COMPLETED, run.model_dump(mode="json"))
        return run

    monkeypatch.setattr(Pipeline, "run", finish)
    with TestClient(create_app(settings)) as client:
        response = client.post("/runs", json={"clip_path": str(clip), "replay": False})
        assert response.status_code == 201
        assert not response.json()["replay"]
        identifier = response.json()["id"]
        client.get(f"/runs/{identifier}/events")
        assert observed == [(False, None, identifier)]
        clip.unlink()
        assert (
            client.post("/runs", json={"clip_path": str(clip), "replay": False}).status_code == 400
        )


async def open_stream(app, path, cursor=None):
    incoming = asyncio.Queue()
    await incoming.put({"type": "http.request", "body": b"", "more_body": False})
    outgoing = asyncio.Queue()
    scope = {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.4"},
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": path,
        "raw_path": path.encode(),
        "query_string": b"",
        "root_path": "",
        "headers": [(b"last-event-id", cursor.encode())] if cursor is not None else [],
        "client": ("127.0.0.1", 1234),
        "server": ("test", 80),
    }
    task = asyncio.create_task(app(scope, incoming.get, outgoing.put))
    return task, incoming, outgoing


async def next_sse(outgoing):
    while True:
        message = await asyncio.wait_for(outgoing.get(), timeout=5)
        if message["type"] == "http.response.body" and b"data: " in message.get("body", b""):
            return parse_sse(message["body"].decode())


@pytest.mark.asyncio
async def test_live_resume_disconnect_and_concurrency(api_case, monkeypatch):
    app, store, settings, clip = api_case
    release = Event()
    started = Event()

    def controlled(self, clip_path, replay_from=None, *, run=None, bus=None):
        bus.emit(E.RUN_STARTED, run.model_dump(mode="json"))
        started.set()
        if not release.wait(15):
            raise RuntimeError("Test did not release background worker")
        run.status = RunStatus.COMPLETED
        run.finished_at = datetime.now(UTC)
        self.store.save_run(run)
        bus.emit(E.RUN_COMPLETED, run.model_dump(mode="json"))
        return run

    monkeypatch.setattr(Pipeline, "run", controlled)
    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client,
    ):
        try:
            response = await asyncio.wait_for(
                client.post("/runs", json={"clip_path": str(clip)}), timeout=5
            )
            identifier = response.json()["id"]
            assert response.json()["status"] == "running" and not release.is_set()
            assert await asyncio.to_thread(started.wait, 5)
            assert (await asyncio.wait_for(client.get("/clips"), 5)).status_code == 200
            bus = app.state.registry.get_bus(identifier)
            task, incoming, outgoing = await open_stream(app, f"/runs/{identifier}/events")
            assert (await next_sse(outgoing))[0]["id"] == "0"
            assert len(bus.listeners) == 1
            await incoming.put({"type": "http.disconnect"})
            await asyncio.wait_for(task, timeout=5)
            assert not bus.listeners
            task, incoming, outgoing = await open_stream(app, f"/runs/{identifier}/events", "0")
            await asyncio.to_thread(bus.emit, E.CLIP_LOADED, {"clip_path": str(clip)})
            assert (await next_sse(outgoing))[0]["id"] == "1"
            second = await client.post("/runs", json={"clip_path": str(clip)})
            assert second.json()["id"] != identifier
            assert len(app.state.registry.tasks) == 2
            release.set()
            assert (await next_sse(outgoing))[0]["type"] == "run_completed"
            await asyncio.wait_for(task, timeout=5)
            assert not bus.listeners
        finally:
            release.set()


def test_unexpected_worker_failure(api_case, monkeypatch):
    app, store, settings, clip = api_case

    def fail(*args, **kwargs):
        raise RuntimeError("Injected worker failure")

    monkeypatch.setattr(Pipeline, "run", fail)
    with TestClient(app) as client:
        run = client.post("/runs", json={"clip_path": str(clip)}).json()
        events = parse_sse(client.get(f"/runs/{run['id']}/events").text)
        assert events[-1]["type"] == "run_failed"
        assert events[-1]["payload"]["reason"] == "Injected worker failure"
        assert client.get(f"/runs/{run['id']}").json()["status"] == "failed"


def test_inactive_interrupted_stream(api_case):
    app, store, settings, clip = api_case
    run = store.create_run(clip, True)
    bus = EventBus(store.run_dir(run.id))
    bus.emit(E.RUN_STARTED, run.model_dump(mode="json"))
    with TestClient(app) as client:
        assert len(parse_sse(client.get(f"/runs/{run.id}/events").text)) == 1
        assert (
            client.get(f"/runs/{run.id}/events", headers={"Last-Event-ID": "1"}).status_code == 400
        )
        assert not parse_sse(
            client.get(f"/runs/{run.id}/events", headers={"Last-Event-ID": "0"}).text
        )
