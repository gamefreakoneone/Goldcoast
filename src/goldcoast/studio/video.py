import json
import subprocess
import tempfile
from pathlib import Path

from google.genai import types

from goldcoast.media.frames import extract_frame
from goldcoast.studio.brand import AssetMetadata, Product
from goldcoast.studio.workflow import VideoAnalysis, VideoEvidence


def duration_seconds(path):
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "json",
            str(path),
        ],
        capture_output=True,
        timeout=15,
        check=True,
    )
    return float(json.loads(result.stdout)["format"]["duration"])


def frame_bytes(raw, timestamp_s):
    with tempfile.TemporaryDirectory() as directory:
        clip = Path(directory) / "campaign.mp4"
        frame = Path(directory) / "best-frame.png"
        clip.write_bytes(raw)
        duration = duration_seconds(clip)
        if timestamp_s >= duration:
            raise ValueError("Video agent selected a frame outside the uploaded clip")
        extract_frame(clip, timestamp_s, frame)
        return frame.read_bytes()


def analyze_campaign_video(repo, assets, job, client, settings, reserve):
    asset_id = job.input["video_asset_id"]
    row = repo.get(job.tenant_id, "asset", asset_id)
    metadata = AssetMetadata.model_validate(row.data)
    if metadata.role != "video":
        raise ValueError("Campaign video is no longer available")
    reserve("video")
    record = client.generate(
        "studio_video",
        settings.video_model,
        [
            "Analyze this owner-uploaded campaign video. Describe only visible activity, "
            "products, setting and readable text. Select the single strongest frame for an ad "
            "and return its timestamp in seconds with a specific visual reason. Propose at most "
            "three searches that could connect this subject to current local or cultural topics. "
            "Do not infer identity, nationality, preferences, endorsements, prices or offers. "
            "The owner label is context, not verified evidence: "
            + json.dumps(
                {
                    "title": metadata.title,
                    "description": metadata.description,
                    "product_id": metadata.product_id,
                }
            ),
            types.Part.from_bytes(data=assets.get(job.tenant_id, asset_id), mime_type="video/mp4"),
        ],
        types.GenerateContentConfig(
            response_mime_type="application/json",
            response_json_schema=VideoAnalysis.model_json_schema(),
            temperature=0.2,
        ),
        input_refs=[asset_id],
    )
    analysis = VideoAnalysis.model_validate_json(record.response_text)
    raw = frame_bytes(assets.get(job.tenant_id, asset_id), analysis.best_frame_s)
    frame = repo.put(
        job.tenant_id,
        "campaign_frame",
        {
            "job_id": job.id,
            "source_asset_id": asset_id,
            "timestamp_s": analysis.best_frame_s,
            "mime": "image/png",
        },
    )
    assets.put(job.tenant_id, frame.id, raw)
    return VideoEvidence(
        **analysis.model_dump(),
        asset_id=asset_id,
        title=metadata.title or metadata.filename,
        description=metadata.description or "Historical campaign video",
        product_id=metadata.product_id,
        frame_asset_id=frame.id,
    )


def video_snapshot(snapshot, evidence, requested_product_id=None):
    video = VideoEvidence.model_validate(evidence)
    selected = snapshot.model_copy(deep=True)
    product_id = requested_product_id or video.product_id
    if product_id:
        products = [p for p in selected.profile.products if p.id == product_id]
        if not products:
            raise ValueError("The campaign video's linked product is no longer available")
        selected.profile.products = products
    else:
        selected.profile.products = [
            Product(id="video-" + video.asset_id, name=video.title, description=video.description)
        ]
        selected.profile.offers = []
    return selected
