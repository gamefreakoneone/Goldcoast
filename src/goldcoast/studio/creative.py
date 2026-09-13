import hashlib
import io
import json
import re
import zipfile
from datetime import UTC, datetime, time
from typing import Literal
from zoneinfo import ZoneInfo

from google.genai import types
from PIL import Image
from pydantic import AwareDatetime, Field
from sqlalchemy import select

from goldcoast.storage import write_bytes
from goldcoast.studio.brand import StrictModel, resource_view
from goldcoast.studio.compositor import SIZES, render_composite
from goldcoast.studio.database import Resource, Tenant
from goldcoast.studio.repository import AccessError, Conflict
from goldcoast.studio.workflow import Snapshot


class CreativeBrief(StrictModel):
    headline: str = Field(min_length=1, max_length=80)
    subheading: str = Field(min_length=1, max_length=140)
    cta: str = Field(min_length=1, max_length=30)
    product_name: str = Field(min_length=1, max_length=100)
    offer_text: str = Field(default="", max_length=200)
    image_prompt: str = Field(min_length=1, max_length=1500)


class CreativeVerdict(StrictModel):
    factuality: int = Field(ge=0, le=10)
    brand_fidelity: int = Field(ge=0, le=10)
    visual_quality: int = Field(ge=0, le=10)
    legibility: int = Field(ge=0, le=10)
    critical_issues: list[str] = Field(default_factory=list, max_length=10)
    feedback: str = Field(max_length=1500)
    detected_text: str = Field(max_length=1500)

    def passing(self):
        return (
            not self.critical_issues
            and min(self.factuality, self.brand_fidelity, self.visual_quality, self.legibility) >= 7
        )


class CreativeArtifact(StrictModel):
    job_id: str
    business_id: str
    brand_id: str
    format: Literal["landscape", "portrait"]
    attempt: int = Field(ge=1, le=3)
    width: int
    height: int
    sha256: str
    brief: CreativeBrief
    verdict: CreativeVerdict
    expires_at: AwareDatetime
    decision: Literal["pending", "approved", "rejected"] = "pending"
    decision_note: str = Field(default="", max_length=500)
    decided_at: AwareDatetime | None = None
    replay: bool = False


class DecisionRequest(StrictModel):
    version: int = Field(ge=1)
    decision: Literal["approved", "rejected"]
    note: str = Field(default="", max_length=500)


def validate_brief(brief, snapshot, selected):
    if brief.product_name.casefold() != selected.product_name.casefold():
        raise ValueError("Creative brief changed the selected product")
    if brief.product_name.casefold() not in {p.name.casefold() for p in snapshot.profile.products}:
        raise ValueError("Creative product is not owner-confirmed")
    offers = [o.text for o in snapshot.profile.offers if o.valid_until >= snapshot.local_date]
    if brief.offer_text and brief.offer_text not in offers:
        raise ValueError("Creative offer is not an exact current owner-confirmed offer")
    text = " ".join([brief.headline, brief.subheading, brief.cta])
    promotions = re.findall(
        r"\d+(?:\.\d+)?\s*%|\$\s*\d+(?:\.\d+)?|\bfree\b|\bdiscount\b", text, re.I
    )
    if any(value.casefold() not in brief.offer_text.casefold() for value in promotions):
        raise ValueError("Creative copy contains an unsupported promotional claim")
    for term in snapshot.brand.prohibited:
        if term and term.casefold() in (text + " " + brief.offer_text).casefold():
            raise ValueError("Creative copy contains a prohibited brand term")
    return brief


class CreativeService:
    def __init__(self, repo, assets):
        self.repo, self.assets = repo, assets

    def save(self, tenant, artifact, raw):
        with Image.open(io.BytesIO(raw)) as image:
            if image.size != SIZES[artifact.format]:
                raise ValueError("Composite dimensions do not match the required format")
        artifact.sha256 = hashlib.sha256(raw).hexdigest()
        row = self.repo.put(tenant, "creative", artifact.model_dump(mode="json"))
        self.assets.put(tenant, row.id, raw)
        return resource_view(row)

    def stale(self, tenant, artifact):
        job = self.repo.job(tenant, artifact.job_id)
        if job.mode == "replay" and artifact.replay:
            return False
        snapshot = Snapshot.model_validate(job.input["snapshot"])
        business = self.repo.get(tenant, "business", snapshot.business_id)
        brand = self.repo.get(tenant, "brand", snapshot.brand_id)
        return (
            business.version != snapshot.business_version
            or brand.version != snapshot.brand_version
            or artifact.expires_at <= datetime.now(UTC)
        )

    def view(self, tenant, row):
        artifact = CreativeArtifact.model_validate(row.data)
        return {
            **resource_view(row),
            "passed": artifact.verdict.passing(),
            "stale": self.stale(tenant, artifact),
        }

    def list(self, tenant, job_id):
        self.repo.job(tenant, job_id)
        return [
            self.view(tenant, row)
            for row in self.repo.list(tenant, "creative")
            if row.data["job_id"] == job_id
        ]

    def decide(self, tenant, creative_id, body):
        with self.repo.sessions.begin() as session:
            session.execute(
                select(Tenant).where(Tenant.id == tenant).with_for_update()
            ).scalar_one()
            row = session.scalar(
                select(Resource)
                .where(
                    Resource.id == creative_id,
                    Resource.tenant_id == tenant,
                    Resource.kind == "creative",
                )
                .with_for_update()
            )
            if row is None:
                raise AccessError("Not found")
            if row.version != body.version:
                raise Conflict("Creative changed; reload before reviewing")
            artifact = CreativeArtifact.model_validate(row.data)
            if body.decision == "approved":
                job = self.repo.job(tenant, artifact.job_id)
                if (
                    job.state != "completed"
                    or not artifact.verdict.passing()
                    or self.stale(tenant, artifact)
                ):
                    raise Conflict("Only completed, passing, current creatives can be approved")
            artifact.decision, artifact.decision_note = body.decision, body.note
            artifact.decided_at = datetime.now(UTC)
            row.data, row.version = artifact.model_dump(mode="json"), row.version + 1
            return resource_view(row)

    def export(self, tenant, job_id):
        with self.repo.sessions.begin() as session:
            session.execute(
                select(Tenant).where(Tenant.id == tenant).with_for_update()
            ).scalar_one()
            return self._export(tenant, job_id)

    def _export(self, tenant, job_id):
        rows = self.list(tenant, job_id)
        selected = {}
        for row in sorted(rows, key=lambda r: r["data"]["attempt"]):
            if row["passed"] and not row["stale"] and row["data"]["decision"] == "approved":
                selected[row["data"]["format"]] = row
        if set(selected) != set(SIZES):
            raise Conflict("Approve one passing, current creative in each format before export")
        output = io.BytesIO()
        with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
            for format, row in selected.items():
                archive.writestr(format + ".png", self.assets.get(tenant, row["id"]))
            job = self.repo.job(tenant, job_id)
            archive.writestr(
                "manifest.json",
                json.dumps(
                    {
                        "job_id": job_id,
                        "mode": job.mode,
                        "replay": job.mode == "replay",
                        "historical_notice": "Historical demonstration; evidence may be out of date"
                        if job.mode == "replay"
                        else None,
                        "snapshot": job.input["snapshot"],
                        "creatives": list(selected.values()),
                        "campaign": job.checkpoint["campaign"]["output"],
                    },
                    indent=2,
                ),
            )
        return output.getvalue()


async def produce_creatives(
    repo,
    assets,
    job,
    snapshot,
    campaign,
    runtime,
    client,
    settings,
    stages,
    root,
    renderer=render_composite,
):
    brief = CreativeBrief.model_validate(
        await stages.run(
            "creative_brief",
            lambda: runtime.run(
                "creative_director",
                "Write an ad brief for the selected real product in the business voice. "
                "Copy only current owner-confirmed offers exactly, or leave empty. No "
                "invented claims, endorsements, prices or partnerships. Describe food "
                "imagery without text/logos, matching the uploaded references.",
                {
                    "business": snapshot.profile.model_dump(mode="json"),
                    "brand": snapshot.brand.model_dump(mode="json"),
                    "selected": campaign.selected.model_dump(mode="json"),
                    "graph": campaign.graph.model_dump(mode="json"),
                },
                CreativeBrief,
            ),
        )
    )
    validate_brief(brief, snapshot, campaign.selected)
    expires_at = campaign.selected.expires_at
    if brief.offer_text:
        offer = next(o for o in snapshot.profile.offers if o.text == brief.offer_text)
        expires_at = min(
            expires_at,
            datetime.combine(
                offer.valid_until, time.max, tzinfo=ZoneInfo(snapshot.profile.timezone)
            ),
        )
    kit = snapshot.brand
    reference_ids = list(
        dict.fromkeys(
            kit.reference_asset_ids
            + [r["id"] for r in snapshot.assets if r["data"]["role"] == "product"]
        )
    )[:6]
    references = [
        types.Part.from_bytes(data=assets.get(job.tenant_id, asset_id), mime_type="image/png")
        for asset_id in reference_ids
    ]
    logo = assets.get(job.tenant_id, kit.logo_asset_id) if kit.logo_asset_id else None
    font = assets.get(job.tenant_id, kit.font_asset_id) if kit.font_asset_id else None
    service = CreativeService(repo, assets)
    completed = []
    for format, (width, height) in SIZES.items():
        feedback = ""
        for attempt in range(1, 4):

            async def generate(
                format=format, attempt=attempt, width=width, height=height, feedback=feedback
            ):
                prompt = (
                    "Create a photograph without text, logos, people or endorsements. "
                    "Match the uploaded product appearance and brand reference style. "
                    + brief.image_prompt
                    + "\nBrand direction: "
                    + kit.image_direction
                    + "\nPrior judge feedback: "
                    + feedback
                )
                result = client.generate_image(
                    "studio_image_" + format,
                    settings.image_model,
                    [prompt, *references],
                    types.GenerateContentConfig(
                        response_modalities=["TEXT", "IMAGE"],
                        image_config=types.ImageConfig(
                            aspect_ratio="16:9" if format == "landscape" else "9:16"
                        ),
                    ),
                    output_path=root / f"{format}-{attempt}-background.png",
                    input_refs=reference_ids,
                )
                if result.image_path is None:
                    raise ValueError("Image provider returned no usable image")
                raw = await renderer(
                    snapshot.profile, kit, brief, result.image_path.read_bytes(), format, logo, font
                )
                composite_path = root / f"{format}-{attempt}-composite.png"
                write_bytes(composite_path, raw)
                judge = client.generate(
                    "studio_judge_" + format,
                    settings.judge_model,
                    [
                        "Judge this FINAL ad strictly. Read all text. Check facts against "
                        "the profile, evidence, exact brief and brand references. "
                        "Reject invented offers/endorsements, wrong logos, typos, low contrast "
                        "or clipping. Scores 0-10; critical issues prevent approval. Context: "
                        + json.dumps(
                            {
                                "business": snapshot.profile.model_dump(mode="json"),
                                "brief": brief.model_dump(),
                                "brand": kit.model_dump(),
                                "selected": campaign.selected.model_dump(mode="json"),
                                "evidence": campaign.graph.model_dump(mode="json"),
                            }
                        ),
                        types.Part.from_bytes(data=raw, mime_type="image/png"),
                        *references,
                    ],
                    types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_json_schema=CreativeVerdict.model_json_schema(),
                    ),
                    input_refs=reference_ids + [str(composite_path)],
                )
                verdict = CreativeVerdict.model_validate_json(judge.response_text)
                artifact = CreativeArtifact(
                    job_id=job.id,
                    business_id=snapshot.business_id,
                    brand_id=snapshot.brand_id,
                    format=format,
                    attempt=attempt,
                    width=width,
                    height=height,
                    sha256="",
                    brief=brief,
                    verdict=verdict,
                    expires_at=expires_at,
                )
                return service.save(job.tenant_id, artifact, raw)

            saved = await stages.run(f"creative_{format}_{attempt}", generate)
            artifact = CreativeArtifact.model_validate(saved["data"])
            if artifact.verdict.passing():
                completed.append(saved["id"])
                break
            if artifact.verdict.legibility < 7 or artifact.verdict.factuality < 7:
                break
            feedback = artifact.verdict.feedback + " " + "; ".join(artifact.verdict.critical_issues)
    await stages.run("creative_result", lambda: {"passing_creative_ids": completed})
    return completed
