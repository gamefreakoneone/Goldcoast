from datetime import UTC, datetime

import pytest
from test_studio_foundation import foundation as foundation
from test_studio_workflow import campaign as campaign

from goldcoast.studio.repository import Conflict
from goldcoast.studio.schedule import ScheduleInput, ScheduleSave, ScheduleService


def test_schedule_is_opt_in_due_once_and_uses_live_allowance(campaign):
    repo, assets, tenant, _, _ = campaign
    service = ScheduleService(repo, assets)
    assert service.tick(datetime(2026, 9, 13, 20, tzinfo=UTC)) == []
    saved = service.save(
        tenant, ScheduleSave(version=0, schedule=ScheduleInput(enabled=True, hour=9))
    )
    assert service.tick(datetime(2026, 9, 13, 15, tzinfo=UTC)) == []
    jobs = service.tick(datetime(2026, 9, 13, 17, tzinfo=UTC))
    assert len(jobs) == 1 and repo.tenant(tenant).campaign_grants == 2
    assert service.tick(datetime(2026, 9, 13, 18, tzinfo=UTC)) == []
    assert repo.jobs(tenant)[0].request_key == "scheduled:2026-09-13"
    with pytest.raises(Conflict):
        service.save(tenant, ScheduleSave(version=saved["version"], schedule=ScheduleInput()))
    current = service.current(tenant)
    service.save(
        tenant, ScheduleSave(version=current.version, schedule=ScheduleInput(enabled=False))
    )
    assert service.tick(datetime(2026, 9, 14, 17, tzinfo=UTC)) == []


def test_schedule_reports_paused_without_consuming_grant(campaign):
    repo, assets, tenant, _, _ = campaign
    repo.controls(enabled=False)
    service = ScheduleService(repo, assets)
    service.save(tenant, ScheduleSave(version=0, schedule=ScheduleInput(enabled=True, hour=0)))
    assert service.tick(datetime(2026, 9, 13, 17, tzinfo=UTC)) == []
    assert service.current(tenant).data["last_error"].startswith("Not started")
    assert repo.tenant(tenant).campaign_grants == 3
    repo.controls(enabled=True)
    assert len(service.tick(datetime(2026, 9, 13, 17, tzinfo=UTC))) == 1
