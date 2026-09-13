import copy
import hashlib
import io
import json
import os
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from PIL import Image
from pydantic import Field
from sqlalchemy import select

from goldcoast.studio.brand import StrictModel
from goldcoast.studio.compositor import SIZES
from goldcoast.studio.creative import CreativeArtifact
from goldcoast.studio.database import Resource, Tenant
from goldcoast.studio.repository import Conflict
from goldcoast.studio.workflow import CampaignResult, Snapshot


class PackagedCreative(StrictModel):
    file: str
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    artifact: CreativeArtifact


class ReplayPackage(StrictModel):
    version: int = Field(ge=1, le=1)
    label: str
    source_job: str
    recorded_at: float
    goal: str
    snapshot: Snapshot
    checkpoint: dict
    creatives: list[PackagedCreative] = Field(min_length=2, max_length=6)
    usage: dict
    events: list[dict]


def package_root():
    return Path(os.getenv("GOLDCOAST_REPLAY_PACKAGE", "data/studio_demo")).resolve()


def confined_file(root, name):
    path = (root / name).resolve()
    if not path.is_relative_to(root) or not path.is_file():
        raise ValueError("Invalid replay package path")
    return path


def load_package(root=None):
    root = (root or package_root()).resolve()
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    for name, digest in manifest.items():
        if hashlib.sha256(confined_file(root, name).read_bytes()).hexdigest() != digest:
            raise ValueError("Replay package hash mismatch")
    if "campaign.json" not in manifest:
        raise ValueError("Replay package manifest is incomplete")
    package = ReplayPackage.model_validate_json(
        (root / "campaign.json").read_text(encoding="utf-8")
    )
    CampaignResult.model_validate(package.checkpoint["campaign"]["output"])
    for creative in package.creatives:
        raw = confined_file(root, creative.file).read_bytes()
        if creative.file not in manifest or hashlib.sha256(raw).hexdigest() != creative.sha256:
            raise ValueError("Replay creative hash mismatch")
        with Image.open(io.BytesIO(raw)) as image:
            if image.format != "PNG" or image.size != SIZES[creative.artifact.format]:
                raise ValueError("Replay creative dimensions or format are invalid")
    return package


def start_sample(repo, tenant, key):
    package = load_package()
    return repo.create_job(
        tenant,
        "campaign",
        "replay",
        key,
        {
            "sample": True,
            "package_hash": hashlib.sha256(
                (package_root() / "campaign.json").read_bytes()
            ).hexdigest(),
            "snapshot": package.snapshot.model_dump(mode="json"),
            "goal": package.goal,
            "recorded_at": package.recorded_at,
        },
    )


def replay_job(repo, assets, job, worker):
    if job.input.get("sample"):
        package = load_package()
        if (
            hashlib.sha256((package_root() / "campaign.json").read_bytes()).hexdigest()
            != job.input["package_hash"]
        ):
            raise Conflict("Replay package changed after workflow start")
        checkpoint = copy.deepcopy(package.checkpoint)
        source_id = package.source_job
        creatives = [
            (item.file, item.artifact, confined_file(package_root(), item.file).read_bytes())
            for item in package.creatives
        ]
    else:
        source = repo.job(job.tenant_id, job.input["source"])
        if source.state != "completed" or source.kind != job.kind:
            raise Conflict("Replay source is not a completed matching workflow")
        checkpoint = copy.deepcopy(source.checkpoint)
        source_id = source.id
        creatives = [
            (row.id, CreativeArtifact.model_validate(row.data), assets.get(job.tenant_id, row.id))
            for row in repo.list(job.tenant_id, "creative")
            if row.data["job_id"] == source.id
        ]
    if job.kind == "campaign":
        CampaignResult.model_validate(checkpoint["campaign"]["output"])
    ids = []
    for identity, original, raw in creatives:
        artifact = original.model_copy(
            update={
                "job_id": job.id,
                "decision": "pending",
                "decision_note": "",
                "decided_at": None,
                "replay": True,
            }
        )
        identifier = uuid5(NAMESPACE_URL, f"goldcoast:{job.tenant_id}:{job.id}:{identity}").hex
        with repo.sessions.begin() as session:
            session.execute(
                select(Tenant).where(Tenant.id == job.tenant_id).with_for_update()
            ).scalar_one()
            existing = session.get(Resource, identifier)
            if existing is None:
                assets.put(job.tenant_id, identifier, raw)
                session.add(
                    Resource(
                        id=identifier,
                        tenant_id=job.tenant_id,
                        kind="creative",
                        data=artifact.model_dump(mode="json"),
                    )
                )
            elif existing.tenant_id != job.tenant_id:
                raise Conflict("Replay resource ownership mismatch")
        ids.append(identifier)
    checkpoint = {
        key: value for key, value in checkpoint.items() if not key.startswith("creative_")
    }
    checkpoint["creative_result"] = {"state": "completed", "output": {"creative_ids": ids}}
    checkpoint["replay"] = {
        "state": "completed",
        "output": {"source": source_id, "provider_calls": 0, "historical": True},
    }
    repo.checkpoint(job.tenant_id, job.id, worker, checkpoint)
    for stage in checkpoint:
        if stage not in {"replay", "creative_result"}:
            repo.emit(job.tenant_id, job.id, "recorded_stage", {"stage": stage, "historical": True})
    repo.emit(job.tenant_id, job.id, "workflow_replayed", {"source": source_id, "historical": True})
