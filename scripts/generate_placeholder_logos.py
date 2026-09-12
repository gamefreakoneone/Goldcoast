from pathlib import Path

from PIL import Image, ImageDraw

LOGOS = [
    ("kintsugi-sushi", "#C93C3C", "#F5E9D5"),
    ("bullseye-social-club", "#12263A", "#F4C95D"),
    ("sol-y-sombra-tacos", "#F15A29", "#FFD166"),
    ("kickturn-supply", "#592E83", "#00C2A8"),
    ("golden-lap-kitchen", "#D98E04", "#542A0E"),
    ("island-stride-cafe", "#007F5F", "#F9C74F"),
]


for index, (slug, background, foreground) in enumerate(LOGOS):
    directory = Path("data/assets") / slug
    directory.mkdir(parents=True, exist_ok=True)
    image = Image.new("RGBA", (512, 512), background)
    draw = ImageDraw.Draw(image)
    inset = 52 + index * 5
    draw.ellipse(
        (inset, inset, 512 - inset, 512 - inset),
        outline=foreground,
        width=28,
    )
    draw.polygon([(256, 104), (408, 360), (104, 360)], fill=foreground)
    draw.ellipse((206, 206, 306, 306), fill=background)
    image.save(directory / "logo.png", format="PNG", optimize=True)
