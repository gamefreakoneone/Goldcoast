from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException

from goldcoast.api.deps import RegistryDep, StoreDep
from goldcoast.api.paths import safe_path, valid_ad_id
from goldcoast.api.schemas import DecisionCreate
from goldcoast.api.views import matching_verdict
from goldcoast.models.pipeline import ApprovalDecision
from goldcoast.models.pipeline import PipelineEventType as E
from goldcoast.pipeline.events import EventBus
from goldcoast.storage import write_json

router = APIRouter()


@router.post("/ads/{ad_id}/decision", response_model=ApprovalDecision)
def decide(ad_id: str, body: DecisionCreate, store: StoreDep, registry: RegistryDep):
    valid_ad_id(ad_id)
    if body.ad_id is not None and body.ad_id != ad_id:
        raise HTTPException(400, "Body ad_id must match the URL")
    for run in store.list_runs():
        ad = next((ad for ad in store.ads(run.id) if ad.id == ad_id), None)
        if ad is None:
            continue
        if ad.run_id != run.id:
            raise HTTPException(409, "Ad does not belong to its run")
        root = store.run_dir(run.id)
        bus = registry.get_bus(run.id) or EventBus(root)
        with bus.lock:
            if matching_verdict(ad, store.verdicts(run.id)) is None:
                raise HTTPException(409, "Ad has no matching verdict")
            decision = ApprovalDecision(
                **body.model_dump(exclude={"ad_id"}), ad_id=ad_id, decided_at=datetime.now(UTC)
            )
            write_json(safe_path(root, f"decisions/{ad_id}.json"), decision)
            bus.emit(E.AD_DECIDED, decision.model_dump(mode="json"))
        return decision
    raise HTTPException(404, "Ad not found")
