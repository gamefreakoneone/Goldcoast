from types import SimpleNamespace

import pytest
from pydantic import ValidationError
from test_studio_foundation import foundation as foundation
from test_studio_notify import bot as bot
from test_studio_workflow import campaign as campaign

from goldcoast.api.studio_views import job_view
from goldcoast.api.workflow_routes import revisions
from goldcoast.studio.creative import CreativeVerdict, JudgedVerdict
from goldcoast.studio.repository import AccessError
from goldcoast.studio.workflow import WorkflowStart, start_campaign


def test_campaign_origin_is_server_controlled_and_historical_keys_are_recognized(bot):
    with pytest.raises(ValidationError):
        WorkflowStart(mode="live", started_via="telegram")
    job = start_campaign(
        bot.repo,
        bot.assets,
        bot.tenant,
        WorkflowStart(mode="live"),
        "phone-start",
        started_via="telegram",
    )
    assert job.input["started_via"] == job_view(job)["started_via"] == "telegram"
    historical = bot.repo.create_job(bot.tenant, "campaign", "replay", "telegram:legacy", {})
    digest = historical.request_digest
    assert job_view(historical)["started_via"] == "telegram"
    assert historical.input == {} and historical.request_digest == digest
    assert job_view(bot.job)["started_via"] == "studio"


def test_revision_family_is_tenant_scoped_and_preserves_original_decisions(bot):
    original = bot.repo.get(bot.tenant, "creative", bot.creative["id"])
    child = bot.repo.create_job(
        bot.tenant,
        "campaign",
        "replay",
        "child",
        {
            "regenerate_from": bot.job.id,
            "started_via": "telegram",
            "owner_feedback": "Less copy",
        },
    )
    grandchild = bot.repo.create_job(
        bot.tenant,
        "campaign",
        "replay",
        "grandchild",
        {
            "regenerate_from": child.id,
        },
    )
    foreign = bot.repo.create_job(
        bot.other,
        "campaign",
        "replay",
        "foreign",
        {
            "regenerate_from": child.id,
        },
    )
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(repo=bot.repo)))
    identity = SimpleNamespace(tenant_id=bot.tenant)
    family = revisions(child.id, request, identity)
    assert [item["id"] for item in family] == [bot.job.id, child.id, grandchild.id]
    assert family[1]["parent_id"] == bot.job.id and family[1]["started_via"] == "telegram"
    assert bot.repo.get(bot.tenant, "creative", original.id).data == original.data
    with pytest.raises(AccessError):
        revisions(foreign.id, request, identity)


def test_new_judge_requires_reasons_and_version_but_keeps_historical_verdicts(bot):
    old = bot.artifact.verdict.model_dump(exclude={"rubric_version", "score_reasons"})
    assert CreativeVerdict.model_validate(old).score_reasons is None
    with pytest.raises(ValidationError):
        JudgedVerdict.model_validate(old)
    reasons = {
        "factuality": "The latte matches the supplied reference.",
        "brand_fidelity": "The logo is correct.",
        "visual_quality": "The image has no obvious artifacts.",
        "legibility": "The CTA is clipped at the bottom edge.",
    }
    verdict = JudgedVerdict.model_validate(
        {
            **old,
            "rubric_version": "2026-09-v1",
            "score_reasons": reasons,
            "critical_issues": ["Clipped essential CTA"],
        }
    )
    assert not verdict.passing()
    with pytest.raises(ValidationError):
        JudgedVerdict.model_validate({**verdict.model_dump(), "rubric_version": "unknown"})
