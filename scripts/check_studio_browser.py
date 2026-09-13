import argparse
import asyncio
import re
import sys
from pathlib import Path

from dotenv import dotenv_values
from playwright.async_api import async_playwright


async def main():
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--phase",
        choices=[
            "inspect",
            "onboard",
            "brand",
            "campaign",
            "pause",
            "confirm",
            "review",
            "capture",
            "sample",
        ],
        default="inspect",
    )
    args = parser.parse_args()
    username = "demo" if args.phase == "sample" else "owner"
    root = Path("output/studio-browser")
    root.mkdir(parents=True, exist_ok=True)
    credentials = dotenv_values(".env")
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="chrome", headless=True)
        page = await browser.new_page(viewport={"width": 1536, "height": 1024})
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        await page.goto("http://localhost:5173", wait_until="networkidle")
        await page.screenshot(path=str(root / "login.png"), full_page=True)
        await page.get_by_role("button", name="Sign in to your workspace").click()
        await page.wait_for_url("**/realms/goldcoast/**")
        await page.get_by_role("textbox", name="Username", exact=True).fill(username)
        await page.get_by_label("Password", exact=True).fill(
            credentials[f"GOLDCOAST_LOCAL_{username.upper()}_PASSWORD"]
        )
        await page.get_by_role("button", name="Sign In", exact=True).click()
        await page.wait_for_load_state("networkidle")
        if "/required-action" in page.url:
            await page.get_by_role("textbox", name="Email", exact=False).fill(
                username + "@goldcoast.example"
            )
            await page.get_by_role("button", name="Submit", exact=True).click()
        try:
            await page.wait_for_url("http://localhost:5173/**", timeout=15_000)
        except Exception:
            await page.screenshot(path=str(root / "login-blocker.png"), full_page=True)
            print("Login destination:", page.url.split("?")[0])
            print(await page.locator("body").inner_text())
            raise
        await page.get_by_role("heading", name="Your daily marketing desk.").wait_for(
            timeout=30_000
        )
        await page.screenshot(path=str(root / "today-empty.png"), full_page=True)
        print("OIDC authorization-code login succeeded. Authenticated workspace loaded.")
        if args.phase == "onboard":
            await page.get_by_role("button", name="Business", exact=True).click()
            existing = await page.get_by_label("Business name", exact=True).input_value()
            if existing not in {"", "Morrow Coffee"}:
                raise RuntimeError(
                    "The validation account contains another business; not overwriting it"
                )
            await page.get_by_label("Business name", exact=True).fill("Morrow Coffee")
            await page.get_by_label("City", exact=True).fill("Los Angeles")
            await page.get_by_label("Neighborhood", exact=True).fill("Silver Lake")
            await page.get_by_label("What makes your place special?").fill(
                "Fictional cafe for this hackathon demonstration. "
                "Warm ceramic cups, thoughtful coffee and an unhurried neighborhood atmosphere."
            )
            await page.get_by_label("Who would you like to reach?").fill(
                "Neighbors and visitors looking for an afternoon coffee stop"
            )
            await page.get_by_label("Product 1 name").fill("Latte")
            await page.get_by_label("Description", exact=True).fill(
                "Espresso and steamed milk in a ceramic cup"
            )
            await page.get_by_label(
                "I confirm these business details, products, and offers."
            ).check()
            async with page.expect_response(
                lambda r: "/api/v2/business" in r.url and r.request.method == "PUT"
            ) as saved:
                await page.get_by_role("button", name="Save business details").click()
            assert (await saved.value).ok
            await page.get_by_role("button", name="Brand library", exact=True).click()
            await page.get_by_label("I have permission to use this material.").check()
            if await page.get_by_role("heading", name="latte.png", exact=True).count() == 0:
                await page.get_by_label("Use these files as").select_option("product")
                async with page.expect_response(
                    lambda r: "/api/v2/assets" in r.url and r.request.method == "POST"
                ) as uploaded:
                    await page.locator("input[type=file]").set_input_files(
                        "data/studio_demo/assets/latte.png"
                    )
                assert (await uploaded.value).status == 201
                await page.get_by_role("heading", name="latte.png", exact=True).wait_for()
            if (
                await page.get_by_role("heading", name="cafe-reference.png", exact=True).count()
                == 0
            ):
                await page.get_by_label("Use these files as").select_option("reference")
                async with page.expect_response(
                    lambda r: "/api/v2/assets" in r.url and r.request.method == "POST"
                ) as uploaded:
                    await page.locator("input[type=file]").set_input_files(
                        "data/studio_demo/assets/cafe-reference.png"
                    )
                assert (await uploaded.value).status == 201
                await page.get_by_role("heading", name="cafe-reference.png", exact=True).wait_for()
            await page.screenshot(path=str(root / "brand-uploaded.png"), full_page=True)
            print(
                "Business profile saved through UI; "
                "both real PNG uploads succeeded with private previews."
            )
        if args.phase == "brand":
            await page.get_by_role("button", name="Settings", exact=True).click()
            async with page.expect_response(
                lambda r: "/admin/grants/" in r.url and r.request.method == "POST"
            ) as grant:
                await page.get_by_role("button", name="Grant allowance", exact=True).click()
            assert (await grant.value).ok
            async with page.expect_response(
                lambda r: "/admin/controls" in r.url and r.request.method == "POST"
            ) as enabled:
                await page.get_by_role("button", name="Enable live generation", exact=True).click()
            assert (await enabled.value).ok
            await page.get_by_role("button", name="Brand library", exact=True).click()
            await page.get_by_role("button", name="Analyze my brand", exact=True).click()
        if args.phase in {"brand", "confirm"}:
            await page.get_by_role("button", name="Brand library", exact=True).click()
            await page.get_by_role("button", name="Review the new draft").wait_for(timeout=240_000)
            await page.get_by_role("button", name="Review the new draft").click()
            print("Live brand analysis completed; actual image-derived draft loaded.", flush=True)
            await page.get_by_label("Brand color 1", exact=True).fill("#183d35")
            await page.get_by_label("Brand color 2", exact=True).fill("#fff9ed")
            await page.get_by_label("reviewed this brand direction.", exact=False).check()
            async with page.expect_response(
                lambda r: "/api/v2/brand" in r.url and r.request.method == "PUT"
            ) as saved:
                await page.get_by_role("button", name="Save brand kit", exact=True).click()
            assert (await saved.value).ok
            await page.get_by_role("button", name="Save brand kit", exact=True).wait_for()
            await page.evaluate("window.scrollTo(0, 0)")
            await page.screenshot(path=str(root / "brand-confirmed.png"), full_page=True)
            print("Analyzed brand kit confirmed and saved through UI.", flush=True)
        if args.phase == "campaign":
            await page.get_by_role("button", name="Live", exact=True).click()
            await page.get_by_label("Today's campaign brief", exact=True).fill(
                "Find a timely neighborhood or cultural reason for Los Angeles visitors "
                "to stop for our latte today. Use only our confirmed product; "
                "do not invent prices, offers, partnerships, or opening hours."
            )
            await page.screenshot(path=str(root / "today-ready.png"), full_page=True)
            async with page.expect_response(
                lambda r: "/api/v2/workflows" in r.url and r.request.method == "POST"
            ) as started:
                await page.get_by_role("button", name=re.compile("Start today.*workflow")).click()
            response = await started.value
            assert response.ok, await response.text()
            job = await response.json()
            (root / "live-job.txt").write_text(job["id"], encoding="utf-8")
            print("Live campaign started:", job["id"], flush=True)
            await page.screenshot(path=str(root / "review-running.png"), full_page=True)
        if args.phase in {"review", "capture"}:
            await page.get_by_role("button", name="Brand library", exact=True).click()
            await page.evaluate("window.scrollTo(0, 0)")
            await page.screenshot(path=str(root / "brand-final.png"), full_page=True)
            await page.get_by_role("button", name="Campaigns", exact=True).click()
            await page.screenshot(path=str(root / "campaign-history.png"), full_page=True)
            job_id = (root / "live-job.txt").read_text(encoding="utf-8")
            await (
                page.get_by_role("row")
                .filter(has_text=job_id[:8])
                .get_by_role("button", name="Open")
                .click()
            )
            await page.get_by_role("heading", name="Made for your neighborhood.").wait_for(
                timeout=180_000
            )
            await page.get_by_role("button", name="Creatives", exact=True).click()
            await page.wait_for_function(
                "document.querySelectorAll('img.creative-preview').length === 2 && "
                "[...document.querySelectorAll('img.creative-preview')]"
                ".every(i => i.complete && i.naturalWidth > 0)"
            )
            await page.evaluate("window.scrollTo(0, 0)")
            await page.screenshot(path=str(root / "review-final.png"), full_page=True)
            await page.get_by_role("button", name="The thinking", exact=True).click()
            await page.screenshot(path=str(root / "evidence.png"), full_page=True)
            await page.get_by_role("button", name="Activity", exact=True).click()
            await page.screenshot(path=str(root / "activity.png"), full_page=True)
            await page.get_by_role("button", name="Creatives", exact=True).click()
            if args.phase == "capture":
                await page.wait_for_function(
                    "document.querySelectorAll('img.creative-preview').length === 2 && "
                    "[...document.querySelectorAll('img.creative-preview')]"
                    ".every(i => i.complete && i.naturalWidth > 0)"
                )
                await page.set_viewport_size({"width": 390, "height": 844})
                await page.evaluate("window.scrollTo(0, 0)")
                await page.screenshot(path=str(root / "review-mobile.png"), full_page=True)
                assert await page.evaluate("document.documentElement.scrollWidth <= innerWidth")
                print("Completed campaign images and responsive review captured.")
                await browser.close()
                return
            await page.get_by_role("button", name="Reject", exact=True).first.click()
            await page.get_by_role("button", name="Rejected", exact=True).wait_for()
            for _ in range(2):
                button = page.get_by_role("button", name="Approve ad", exact=True).first
                await button.click()
                await page.get_by_role("button", name="Approved", exact=True).first.wait_for()
            async with page.expect_download() as download:
                await page.get_by_role("button", name="Download campaign", exact=True).click()
            await (await download.value).save_as(root / "approved-campaign.zip")
            print(
                "Reviewed evidence/activity, rejected then approved ads, "
                "and downloaded the real ZIP.",
                flush=True,
            )
        if args.phase == "sample":
            async with page.expect_response(
                lambda r: "/replays/sample" in r.url and r.request.method == "POST"
            ) as started:
                await page.get_by_role("button", name="Try recorded example", exact=True).click()
            response = await started.value
            assert response.status == 202
            job = await response.json()
            (root / "sample-job.txt").write_text(job["id"], encoding="utf-8")
            await page.get_by_role("heading", name="Made for your neighborhood.").wait_for(
                timeout=30_000
            )
            await page.get_by_text("Historical demonstration", exact=False).wait_for()
            await page.get_by_role("button", name="Creatives", exact=True).click()
            await page.wait_for_function(
                "document.querySelectorAll('img.creative-preview').length === 2 && "
                "[...document.querySelectorAll('img.creative-preview')]"
                ".every(i => i.complete && i.naturalWidth > 0)"
            )
            await page.screenshot(path=str(root / "sample-replay.png"), full_page=True)
            for _ in range(2):
                await page.get_by_role("button", name="Approve ad", exact=True).first.click()
                await page.get_by_role("button", name="Approved", exact=True).first.wait_for()
            async with page.expect_download() as download:
                await page.get_by_role("button", name="Download campaign", exact=True).click()
            await (await download.value).save_as(root / "sample-campaign.zip")
            await page.get_by_role("button", name="Settings", exact=True).click()
            await page.get_by_label("Automatically start my daily workflow").check()
            await page.get_by_role("button", name="Save daily schedule", exact=True).click()
            await page.get_by_text("Daily schedule enabled.", exact=True).wait_for()
            await page.get_by_label("Automatically start my daily workflow").uncheck()
            await page.get_by_role("button", name="Save daily schedule", exact=True).click()
            await page.get_by_text("Daily schedule disabled.", exact=True).wait_for()
            print(
                "Zero-grant demo account replayed, approved, exported and toggled its schedule.",
                flush=True,
            )
        if args.phase == "pause":
            await page.get_by_role("button", name="Settings", exact=True).click()
            async with page.expect_response(
                lambda r: "/admin/controls" in r.url and r.request.method == "POST"
            ) as paused:
                await page.get_by_role(
                    "button", name="Pause all live generation", exact=True
                ).click()
            assert (await paused.value).ok
            print("Global live generation paused.", flush=True)
        await page.set_viewport_size({"width": 390, "height": 844})
        await page.get_by_role("button", name="Today", exact=True).click()
        await page.screenshot(path=str(root / "today-mobile.png"), full_page=True)
        assert await page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
        print("390px mobile layout has no horizontal overflow.")
        print("Page errors:", errors)
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
