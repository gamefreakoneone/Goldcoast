from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel, ValidationError

from goldcoast.models.seed import AdStyle, Athlete, Business, Venue, is_safe_asset_path


class SeedValidationError(ValueError):
    def __init__(self, errors: list[str]) -> None:
        self.errors = tuple(errors)
        super().__init__("Seed validation failed:\n" + "\n".join(f"- {error}" for error in errors))


@dataclass(frozen=True, slots=True)
class SeedData:
    athletes: dict[str, Athlete]
    businesses: dict[str, Business]
    ad_styles: dict[str, AdStyle]
    venues: dict[str, Venue]
    warnings: tuple[str, ...] = ()


def _load_records[SeedModelT: BaseModel](
    path: Path,
    model_type: type[SeedModelT],
    errors: list[str],
    *,
    required: bool,
) -> tuple[dict[str, SeedModelT], bool]:
    if not path.exists():
        if required:
            errors.append(f"{path.name}: file is required")
        return {}, False
    try:
        with path.open(encoding="utf-8") as handle:
            raw_records = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"{path.name}: {exc}")
        return {}, True
    if not isinstance(raw_records, list):
        errors.append(f"{path.name}: root must be a JSON array")
        return {}, True

    records: dict[str, SeedModelT] = {}
    seen_ids: dict[str, int] = {}
    for index, raw_record in enumerate(raw_records):
        raw_id = raw_record.get("id") if isinstance(raw_record, dict) else None
        location = f"{path.name}[{index}]"
        if raw_id:
            location += f" id={raw_id}"
            if raw_id in seen_ids:
                errors.append(f"{location}: duplicate id; first seen at index {seen_ids[raw_id]}")
                continue
            seen_ids[raw_id] = index
        try:
            record = model_type.model_validate(raw_record)
        except ValidationError as exc:
            for detail in exc.errors(include_url=False):
                field = ".".join(str(part) for part in detail["loc"]) or "record"
                errors.append(f"{location} {field}: {detail['msg']}")
            continue
        records[record.id] = record
    return records, True


def _validate_asset_path(
    value: str,
    location: str,
    errors: list[str],
) -> bool:
    if not is_safe_asset_path(value):
        errors.append(f"{location}: must be a safe path relative to data/assets")
        return False
    return True


def load_seed(data_dir: Path) -> SeedData:
    data_dir = Path(data_dir)
    errors: list[str] = []
    warnings: list[str] = []
    athletes, _ = _load_records(data_dir / "athletes.json", Athlete, errors, required=True)
    businesses, _ = _load_records(data_dir / "businesses.json", Business, errors, required=True)
    ad_styles, _ = _load_records(data_dir / "ad_styles.json", AdStyle, errors, required=True)
    venues, venues_present = _load_records(data_dir / "venues.json", Venue, errors, required=False)

    business_tags = {tag for business in businesses.values() for tag in business.tags}
    for athlete in athletes.values():
        athlete_tags = {food.cuisine for food in athlete.favorite_foods} | set(athlete.interests)
        unmatched_tags = sorted(athlete_tags - business_tags)
        if businesses and not (athlete_tags & business_tags):
            errors.append(
                f"athletes.json id={athlete.id}: no business shares any of the athlete's tags "
                f"({', '.join(sorted(athlete_tags))}); the athlete can never be matched"
            )
        elif unmatched_tags:
            warnings.append(
                f"athletes.json id={athlete.id}: tags not used by any business, "
                f"so they will never match: {', '.join(unmatched_tags)}"
            )
        if athlete.headshot:
            _validate_asset_path(
                athlete.headshot,
                f"athletes.json id={athlete.id} headshot",
                errors,
            )

    for business in businesses.values():
        location = f"businesses.json id={business.id}"
        if _validate_asset_path(business.logo, f"{location} logo", errors):
            logo_path = data_dir / "assets" / Path(business.logo)
            if not logo_path.is_file():
                errors.append(f"{location} logo: file not found at {logo_path}")
        for index, photo in enumerate(business.reference_photos):
            _validate_asset_path(photo, f"{location} reference_photos[{index}]", errors)
        if venues_present and business.nearest_venue not in venues:
            errors.append(f"{location} nearest_venue: unknown venue id '{business.nearest_venue}'")

    for style in ad_styles.values():
        for index, image in enumerate(style.reference_images):
            _validate_asset_path(
                image,
                f"ad_styles.json id={style.id} reference_images[{index}]",
                errors,
            )

    if errors:
        raise SeedValidationError(errors)
    return SeedData(
        athletes=athletes,
        businesses=businesses,
        ad_styles=ad_styles,
        venues=venues,
        warnings=tuple(warnings),
    )
