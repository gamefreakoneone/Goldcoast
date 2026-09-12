from __future__ import annotations

from io import BytesIO
from pathlib import Path

from google.genai import types
from PIL import Image

from goldcoast.models.pipeline import AD_FORMAT_SIZES, AdFormat, ContractModel
from goldcoast.storage import write_bytes


class AssetMissingError(ValueError):
    pass


class DimensionResult(ContractModel):
    size: tuple[int, int]
    exact: bool
    correct_ratio: bool


def check_dimensions(path: Path, fmt: AdFormat) -> DimensionResult:
    with Image.open(path) as image:
        size = image.size
    width, height = AD_FORMAT_SIZES[fmt]
    return DimensionResult(
        size=size,
        exact=size == (width, height),
        correct_ratio=abs((size[0] / size[1]) / (width / height) - 1) <= 0.01,
    )


def save_png(image: Image.Image, path: Path) -> None:
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    write_bytes(path, buffer.getvalue())


def resize_to_format(path: Path, fmt: AdFormat) -> None:
    with Image.open(path) as image:
        save_png(image.convert("RGB").resize(AD_FORMAT_SIZES[fmt], Image.Resampling.LANCZOS), path)


def load_image_part(path: Path) -> types.Part:
    if not path.is_file():
        raise AssetMissingError(f"Image file not found: {path}")
    with Image.open(path) as image:
        mime = Image.MIME.get(image.format, "image/png")
    return types.Part.from_bytes(data=path.read_bytes(), mime_type=mime)
