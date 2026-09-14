import asyncio
import io
import os
import tempfile
import zipfile
from pathlib import Path

from playwright.async_api import async_playwright

from goldcoast.studio.assets import LocalAssetStore
from goldcoast.studio.creative import CreativeService, DecisionRequest
from goldcoast.studio.database import Base, Controls, session_factory
from goldcoast.studio.replay import start_sample
from goldcoast.studio.repository import Repository
from goldcoast.studio.worker import process_job


async def renderer():
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        try:
            page = await browser.new_page(viewport={"width": 1080, "height": 1440})
            await page.set_content("<html><body>Goldcoast renderer check</body></html>")
            assert (await page.screenshot()).startswith(b"\x89PNG\r\n\x1a\n")
        finally:
            await browser.close()


def forbidden(*args, **kwargs):
    raise AssertionError("Replay must not construct providers")


def main():
    assert os.getuid() != 0, "Application must run nonroot"
    assert not Path("/app/.env").exists()
    assert not Path("/app/.git").exists()
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        os.environ["GOLDCOAST_STUDIO_RUN_ROOT"] = str(root / "runs")
        engine, sessions = session_factory(f"sqlite:///{root / 'smoke.db'}")
        Base.metadata.create_all(engine)
        with sessions.begin() as session:
            session.add(Controls(id=1))
        repo = Repository(sessions)
        tenant = repo.ensure_tenant("smoke", "https://smoke.invalid", "Smoke", "demo")
        assets = LocalAssetStore(root / "assets")
        job = start_sample(repo, tenant.id, "smoke")
        process_job(repo, assets, repo.claim("smoke"), "smoke", forbidden)
        assert repo.job(tenant.id, job.id).state == "completed"
        service = CreativeService(repo, assets)
        rows = service.list(tenant.id, job.id)
        assert len(rows) == 2 and all(row["passed"] for row in rows)
        for row in rows:
            service.decide(tenant.id, row["id"], DecisionRequest(version=1, decision="approved"))
        with zipfile.ZipFile(io.BytesIO(service.export(tenant.id, job.id))) as archive:
            assert "manifest.json" in archive.namelist()
        assert repo.tenant(tenant.id).campaign_grants == 0
        engine.dispose()
    asyncio.run(renderer())
    print("PASS: nonroot, no bundled secrets, offline replay, two approvals/export, Chromium PNG")


if __name__ == "__main__":
    main()
