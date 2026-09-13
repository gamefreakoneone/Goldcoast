import hashlib
import io
import json
import shutil
import zipfile

import pytest
from test_studio_foundation import foundation as foundation

from goldcoast.studio.assets import LocalAssetStore
from goldcoast.studio.creative import CreativeService, DecisionRequest
from goldcoast.studio.replay import confined_file, load_package, start_sample
from goldcoast.studio.repository import AccessError
from goldcoast.studio.worker import process_job
from goldcoast.studio.workflow import WorkflowStart, start_campaign


def test_real_sample_replay_is_private_provider_free_and_exportable(foundation):
    settings, _, repo, first, second = foundation
    assets = LocalAssetStore(settings.asset_root)
    before = repo.put(first.id, "business", {"name": "Keep my business"})
    job = start_sample(repo, first.id, "sample")
    assert start_sample(repo, first.id, "sample").id == job.id

    def forbidden(*args):
        pytest.fail("Replay constructed live providers")

    process_job(repo, assets, repo.claim("replay"), "replay", forbidden)
    finished = repo.job(first.id, job.id)
    assert finished.state == "completed" and finished.counters == {}
    assert repo.tenant(first.id).campaign_grants == 0
    assert repo.get(first.id, "business", before.id).data == before.data
    assert repo.list(first.id, "brand") == []
    service = CreativeService(repo, assets)
    rows = service.list(first.id, job.id)
    assert len(rows) == 2 and all(row["passed"] and not row["stale"] for row in rows)
    for row in rows:
        assert row["data"]["replay"] and row["data"]["decision"] == "pending"
        with pytest.raises(AccessError):
            service.decide(second.id, row["id"], DecisionRequest(version=1, decision="approved"))
        service.decide(first.id, row["id"], DecisionRequest(version=1, decision="approved"))
    with zipfile.ZipFile(io.BytesIO(service.export(first.id, job.id))) as archive:
        manifest = json.loads(archive.read("manifest.json"))
        assert manifest["replay"] and "Historical" in manifest["historical_notice"]
        for row in rows:
            raw = archive.read(row["data"]["format"] + ".png")
            assert hashlib.sha256(raw).hexdigest() == row["data"]["sha256"]
    replay = start_campaign(repo, assets, first.id, WorkflowStart(replay_source=job.id), "owned")
    process_job(repo, assets, repo.claim("owned"), "owned", forbidden)
    copies = service.list(first.id, replay.id)
    assert len(copies) == 2 and all(row["data"]["decision"] == "pending" for row in copies)
    assert {row["id"] for row in copies}.isdisjoint({row["id"] for row in rows})
    assert all(row["data"]["decision"] == "approved" for row in service.list(first.id, job.id))


def test_package_tampering_and_path_escape_fail_closed(tmp_path):
    root = tmp_path / "package"
    shutil.copytree("data/studio_demo", root)
    assert load_package(root).source_job
    (root / "creatives/landscape-1.png").write_bytes(b"tampered")
    with pytest.raises(ValueError, match="hash mismatch"):
        load_package(root)
    outside = tmp_path / "outside.txt"
    outside.write_text("private")
    with pytest.raises(ValueError, match="path"):
        confined_file(root.resolve(), "../outside.txt")
