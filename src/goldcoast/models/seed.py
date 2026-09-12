from __future__ import annotations

import re
from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, model_validator

from goldcoast.models.pipeline import AdFormat

KebabId = Annotated[str, Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")]
Tag = Annotated[str, Field(pattern=r"^[a-z0-9]+(?:_[a-z0-9]+)*$")]
HexColor = Annotated[str, Field(pattern=r"^#[0-9A-Fa-f]{6}$")]


class SeedModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class FoodPreference(SeedModel):
    cuisine: Tag
    dishes: list[str] = Field(min_length=1)


class AthleteIdentification(SeedModel):
    kit_colors: list[str] = Field(default_factory=list)
    bib_number: str | None = None
    distinguishing_features: list[str] = Field(default_factory=list)


class Athlete(SeedModel):
    id: KebabId
    name: str
    aliases: list[str] = Field(default_factory=list)
    country: str
    sport: str
    discipline: str
    event: str
    home_city: str
    favorite_foods: list[FoodPreference] = Field(min_length=1)
    interests: list[Tag] = Field(min_length=1)
    identification: AthleteIdentification
    headshot: str | None = None
    social_handles: dict[str, str] = Field(default_factory=dict)
    fun_facts: list[str] = Field(default_factory=list)


class BusinessCategory(StrEnum):
    RESTAURANT = "restaurant"
    CAFE = "cafe"
    BAR = "bar"
    SPORTS_VENUE = "sports_venue"
    RETAIL = "retail"
    EXPERIENCE = "experience"


class Business(SeedModel):
    id: KebabId
    name: str
    category: BusinessCategory
    tags: list[Tag] = Field(min_length=1)
    address: str
    neighborhood: str
    nearest_venue: KebabId
    short_description: str
    offerings: list[str] = Field(min_length=1)
    logo: str
    brand_colors: list[HexColor] = Field(min_length=1)
    tagline: str
    offer_text: str | None = None
    cta: str
    website: str
    instagram: str
    hours: str | None = None
    price_range: str | None = None
    reference_photos: list[str] = Field(default_factory=list)


class AdStyle(SeedModel):
    id: KebabId
    name: str
    description: str
    mood_keywords: list[str] = Field(min_length=1)
    palette: list[HexColor] = Field(min_length=1)
    typography_guidance: str
    layout_notes: dict[AdFormat, str]
    required_elements: list[str] = Field(min_length=1)
    use_when: list[str] = Field(min_length=1)
    reference_images: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_layout_notes(self) -> AdStyle:
        if set(self.layout_notes) != set(AdFormat):
            raise ValueError("layout_notes must define exactly landscape and portrait")
        return self


class Venue(SeedModel):
    id: KebabId
    name: str
    sport: str
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)
    neighborhood: str


def is_safe_asset_path(value: str) -> bool:
    return (
        bool(value)
        and "\\" not in value
        and not value.startswith("/")
        and not re.match(r"^[A-Za-z]:", value)
        and ".." not in value.split("/")
    )
