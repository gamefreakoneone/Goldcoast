import asyncio
from pathlib import Path

from PIL import Image

from goldcoast.studio.brand import BrandKit, BusinessProfile
from goldcoast.studio.compositor import SIZES, render_composite
from goldcoast.studio.creative import CreativeBrief


async def main():
    root = Path("output/compositor-probe")
    root.mkdir(parents=True, exist_ok=True)
    profile = BusinessProfile(name="Prime Pizza", city="Los Angeles", neighborhood="Little Tokyo")
    kit = BrandKit(palette=["#223E35", "#FFF9ED"], typography="serif")
    brief = CreativeBrief(
        headline="Make room for a good slice.",
        subheading="Pepperoni pizza. A neighborhood favorite worth slowing down for.",
        cta="Come by today",
        product_name="Pepperoni pizza",
        image_prompt="Probe fixture",
    )
    background = Path("data/assets/prime-pizza-little-tokyo/pepperoni-pizza.jpg").read_bytes()
    logo = Path("data/assets/prime-pizza-little-tokyo/logo.png").read_bytes()
    for format, size in SIZES.items():
        raw = await render_composite(profile, kit, brief, background, format, logo)
        path = root / (format + ".png")
        path.write_bytes(raw)
        with Image.open(path) as image:
            assert image.size == size
        print(f"{format}: {size[0]}x{size[1]}, no overflow; {path}")


if __name__ == "__main__":
    asyncio.run(main())
