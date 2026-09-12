from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from goldcoast.models import (
    AD_FORMAT_SIZES,
    AdBrief,
    AdFormat,
    Athlete,
    AthleteHints,
    HypeMoment,
    PipelineEvent,
    PipelineEventType,
)


def test_ad_format_sizes_are_fixed() -> None:
    assert AD_FORMAT_SIZES == {
        AdFormat.LANDSCAPE: (1920, 1080),
        AdFormat.PORTRAIT: (1080, 1920),
    }


def test_hype_moment_validates_timestamp_window_and_score() -> None:
    with pytest.raises(ValidationError, match="best_frame_s"):
        HypeMoment(
            id="moment-1",
            run_id="run-1",
            clip_path=Path("clip.mp4"),
            start_s=2,
            end_s=4,
            best_frame_s=5,
            best_frame_path=Path("frame.png"),
            hype_score=8,
            description="A decisive shot",
            sport="archery",
            event_context="Final arrow",
        )

    with pytest.raises(ValidationError):
        HypeMoment(
            id="moment-1",
            run_id="run-1",
            clip_path=Path("clip.mp4"),
            start_s=2,
            end_s=4,
            best_frame_s=3,
            best_frame_path=Path("frame.png"),
            hype_score=11,
            description="A decisive shot",
            sport="archery",
            event_context="Final arrow",
        )


def test_seed_identifiers_and_colors_are_validated() -> None:
    payload = {
        "id": "Bad Id",
        "name": "Demo Athlete",
        "aliases": [],
        "country": "Demo",
        "sport": "archery",
        "discipline": "recurve",
        "event": "individual",
        "home_city": "Demo City",
        "favorite_foods": [{"cuisine": "not valid", "dishes": ["dish"]}],
        "interests": ["archery"],
        "identification": {
            "kit_colors": [],
            "bib_number": None,
            "distinguishing_features": [],
        },
    }
    with pytest.raises(ValidationError):
        Athlete.model_validate(payload)


def test_collection_defaults_are_not_shared() -> None:
    first = AthleteHints()
    second = AthleteHints()
    first.kit_colors.append("red")
    assert second.kit_colors == []

    first_event = PipelineEvent(
        id="event-1",
        run_id="run-1",
        type=PipelineEventType.RUN_STARTED,
        timestamp=datetime.now(UTC),
    )
    second_event = PipelineEvent(
        id="event-2",
        run_id="run-1",
        type=PipelineEventType.CLIP_LOADED,
        timestamp=datetime.now(UTC),
    )
    first_event.payload["value"] = 1
    assert second_event.payload == {}


def test_contracts_round_trip_as_json() -> None:
    brief = AdBrief(
        id="brief-1",
        run_id="run-1",
        moment_id="moment-1",
        athlete_id="hana-mori",
        business_id="kintsugi-sushi",
        ad_style_id="precision-pulse",
        match_reason="Shared Japanese cuisine tag",
        match_score=0.9,
        headline_direction="Celebrate precision",
        offer_text="Free tea",
        cta="Visit today",
        formats=[AdFormat.LANDSCAPE, AdFormat.PORTRAIT],
    )
    assert AdBrief.model_validate_json(brief.model_dump_json()) == brief

    with pytest.raises(ValidationError, match="duplicates"):
        AdBrief.model_validate({**brief.model_dump(), "formats": ["landscape", "landscape"]})
