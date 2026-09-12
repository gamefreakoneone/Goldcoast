import json
import shutil
from pathlib import Path

import pytest
from PIL import Image

from goldcoast.data import SeedValidationError, load_seed

PROJECT_DATA = Path(__file__).parents[1] / "data"


def test_project_seed_loads_and_logos_are_valid() -> None:
    seed = load_seed(PROJECT_DATA)
    assert len(seed.athletes) == 3
    assert len(seed.businesses) == 6
    assert len(seed.ad_styles) == 3
    assert len(seed.venues) == 3
    for business in seed.businesses.values():
        with Image.open(PROJECT_DATA / "assets" / business.logo) as image:
            assert image.format == "PNG"
            assert image.size[0] >= 512
            assert image.size[1] >= 512


def test_venues_file_is_optional(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    shutil.copytree(PROJECT_DATA, data_dir)
    (data_dir / "venues.json").unlink()
    assert load_seed(data_dir).venues == {}


def test_loader_aggregates_duplicate_tag_asset_and_venue_errors(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    shutil.copytree(PROJECT_DATA, data_dir)

    athletes_path = data_dir / "athletes.json"
    athletes = json.loads(athletes_path.read_text(encoding="utf-8"))
    athletes[0]["interests"].append("unmatched_interest")
    athletes.append(athletes[0])
    athletes_path.write_text(json.dumps(athletes), encoding="utf-8")

    businesses_path = data_dir / "businesses.json"
    businesses = json.loads(businesses_path.read_text(encoding="utf-8"))
    businesses[0]["logo"] = "../outside.png"
    businesses[1]["nearest_venue"] = "missing-venue"
    businesses_path.write_text(json.dumps(businesses), encoding="utf-8")

    with pytest.raises(SeedValidationError) as raised:
        load_seed(data_dir)

    message = str(raised.value)
    assert "duplicate id" in message
    assert "unmatched_interest" in message
    assert "safe path" in message
    assert "unknown venue id" in message
    assert len(raised.value.errors) >= 4


def test_invalid_records_report_file_index_and_id(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    shutil.copytree(PROJECT_DATA, data_dir)
    businesses_path = data_dir / "businesses.json"
    businesses = json.loads(businesses_path.read_text(encoding="utf-8"))
    businesses[0]["brand_colors"] = ["red"]
    businesses_path.write_text(json.dumps(businesses), encoding="utf-8")

    with pytest.raises(SeedValidationError, match=r"businesses.json\[0\] id=kintsugi-sushi"):
        load_seed(data_dir)
