import argparse
import hashlib
import io
import json
from pathlib import Path

from google.genai import types
from PIL import Image, ImageDraw, ImageFont, ImageOps

from goldcoast.llm.client import GeminiClient
from goldcoast.settings import Settings
from goldcoast.studio.assets import LocalAssetStore
from goldcoast.studio.config import StudioSettings
from goldcoast.studio.creative import CreativeArtifact, JudgedVerdict, judge_prompt
from goldcoast.studio.database import session_factory
from goldcoast.studio.repository import Repository
from goldcoast.studio.social import reference_assets
from goldcoast.studio.workflow import CampaignResult, Snapshot


def prepare(repo, assets, tenant, creative_ids, directory):
    manifest = directory / "cases.json"
    if manifest.exists():
        saved = json.loads(manifest.read_text())
        if saved["tenant"] != tenant or saved["creative_ids"] != creative_ids:
            raise ValueError("Calibration directory belongs to different inputs")
        return saved
    directory.mkdir(parents=True, exist_ok=False)
    cases = []
    for index, creative_id in enumerate(creative_ids):
        artifact = CreativeArtifact.model_validate(repo.get(tenant, "creative", creative_id).data)
        job = repo.job(tenant, artifact.job_id)
        snapshot = Snapshot.model_validate(job.input["snapshot"])
        campaign = CampaignResult.model_validate(job.checkpoint["campaign"]["output"])
        prompt = judge_prompt(snapshot, artifact.brief, campaign, job.input.get("testimonial"))
        products, styles = reference_assets(snapshot, campaign.selected.product_id)
        references = []
        for label, rows in [("PRODUCT APPEARANCE", products), ("VISUAL STYLE ONLY", styles)]:
            for row in rows:
                target = directory / (row["id"] + ".reference")
                target.write_bytes(assets.get(tenant, row["id"]))
                references.append(
                    {"label": label, "path": str(target), "mime": row["data"]["mime"]}
                )
        image = Image.open(io.BytesIO(assets.get(tenant, creative_id))).convert("RGB")
        variants = [(f"saved_{index + 1}", image, None)]
        if index == 0:
            if image.size != (1080, 1440):
                raise ValueError("Calibration perturbations require a 1080x1440 saved post")
            offer = image.copy()
            draw = ImageDraw.Draw(offer)
            draw.rectangle((52, 1050, 1028, 1160), fill="white")
            font = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 46)
            draw.text((75, 1070), "FREE COFFEE FOR EVERYONE", font=font, fill="black")
            wrong = image.copy()
            alternative = next(
                row
                for row in snapshot.assets
                if row["data"].get("role") == "product"
                and row["data"].get("product_id") != campaign.selected.product_id
            )
            replacement = Image.open(io.BytesIO(assets.get(tenant, alternative["id"]))).convert(
                "RGB"
            )
            wrong.paste(ImageOps.fit(replacement, (976, 605)), (52, 144))
            clipped = image.copy()
            ImageDraw.Draw(clipped).rectangle((45, 808, 1035, 925), fill=(245, 239, 227))
            contrast = image.copy()
            text_region = image.crop((0, 780, 1080, 1440))
            faded = Image.blend(
                Image.new("RGB", text_region.size, (245, 239, 227)), text_region, 0.02
            )
            contrast.paste(faded, (0, 780))
            variants += [
                ("unsupported_offer", offer, "factuality"),
                ("wrong_product", wrong, "factuality"),
                ("clipped_text", clipped, "legibility"),
                ("poor_contrast", contrast, "legibility"),
            ]
        for name, final, criterion in variants:
            path = directory / (name + ".png")
            final.save(path)
            cases.append(
                {
                    "name": name,
                    "image": str(path),
                    "prompt": prompt,
                    "references": references,
                    "criterion": criterion,
                    "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                }
            )
    saved = {"tenant": tenant, "creative_ids": creative_ids, "cases": cases}
    manifest.write_text(json.dumps(saved, indent=2), encoding="utf-8")
    return saved


def evaluate(saved, directory):
    settings = Settings.from_env()
    cases = saved["cases"]
    if len(cases) != 6:
        raise ValueError("Exactly six bounded cases are required")
    client = GeminiClient(settings, directory / "recordings")
    results = []
    for case in cases:
        name = case["name"]
        result_path = directory / (name + ".result.json")
        if result_path.exists():
            results.append(json.loads(result_path.read_text()))
            continue
        path = Path(case["image"])
        if hashlib.sha256(path.read_bytes()).hexdigest() != case["sha256"]:
            raise ValueError("Calibration image changed after preparation")
        parts = [
            case["prompt"],
            types.Part.from_bytes(data=path.read_bytes(), mime_type="image/png"),
        ]
        for reference in case["references"]:
            parts.extend(
                [
                    reference["label"],
                    types.Part.from_bytes(
                        data=Path(reference["path"]).read_bytes(), mime_type=reference["mime"]
                    ),
                ]
            )
        try:
            with (directory / (name + ".attempted")).open("x") as marker:
                marker.write(settings.judge_model)
        except FileExistsError:
            results.append({"name": name, "error": "Interrupted attempt; no automatic retry"})
            continue
        try:
            record = client.generate(
                "calibration_" + name,
                settings.judge_model,
                parts,
                types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_json_schema=JudgedVerdict.model_json_schema(),
                ),
                input_refs=[str(path), *[r["path"] for r in case["references"]]],
            )
            verdict = JudgedVerdict.model_validate_json(record.response_text)
            criterion = case["criterion"]
            matched = (
                not verdict.passing()
                and bool(verdict.critical_issues)
                and getattr(verdict, criterion) < 7
                if criterion
                else verdict.passing()
            )
            result = {
                "name": name,
                "expected_rejection": bool(criterion),
                "matched": matched,
                "verdict": verdict.model_dump(mode="json"),
                "model": record.model_id,
                "latency_ms": record.latency_ms,
                "usage": record.response_raw.get("response", {}).get("usage_metadata", {}),
            }
        except Exception as exc:
            result = {"name": name, "matched": False, "error": type(exc).__name__}
        result_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
        results.append(result)
        print(
            json.dumps({k: v for k, v in result.items() if k not in {"verdict", "usage"}}),
            flush=True,
        )
    report = {
        "attempts": len(list(directory.glob("*.attempted"))),
        "passed": all(item.get("matched", False) for item in results),
        "results": results,
    }
    (directory / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"attempts": report["attempts"], "passed": report["passed"]}), flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tenant", required=True)
    parser.add_argument("--creatives", nargs=2, required=True)
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--live", action="store_true")
    args = parser.parse_args()
    config = StudioSettings.from_env()
    engine, sessions = session_factory(config.database_url)
    try:
        saved = prepare(
            Repository(sessions),
            LocalAssetStore(config.asset_root),
            args.tenant,
            args.creatives,
            args.directory.resolve(),
        )
        if args.live:
            evaluate(saved, args.directory.resolve())
        else:
            print(json.dumps({"prepared_cases": len(saved["cases"]), "provider_calls": 0}))
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
