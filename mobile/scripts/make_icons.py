"""Generates the launcher icons and splash logo for Android and iOS.

    python scripts/make_icons.py            (needs Pillow)

PLACEHOLDER ARTWORK: a plain monogram in the app's accent colour, so builds
have a real icon. Replace MONOGRAM/colours, or swap `draw_mark` for the
client's logo, and run again; every size is regenerated.
"""

import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
BRAND = (140, 74, 94)  # theme.colors.primary
PAPER = (250, 247, 244)  # theme.colors.background
MONOGRAM = "IC"
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"


def draw_mark(size: int, background, ink) -> Image.Image:
    image = Image.new("RGBA", (size, size), background)
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype(FONT, int(size * 0.42))
    left, top, right, bottom = draw.textbbox((0, 0), MONOGRAM, font=font)
    draw.text(((size - (right - left)) / 2 - left, (size - (bottom - top)) / 2 - top), MONOGRAM, font=font, fill=ink)
    ring = max(2, size // 48)
    inset = size * 0.14
    draw.ellipse([inset, inset, size - inset, size - inset], outline=ink, width=ring)
    return image


def save(image: Image.Image, path: Path, size: int, opaque: bool = True) -> None:
    out = image.resize((size, size), Image.LANCZOS)
    if opaque:
        out = out.convert("RGB")  # iOS rejects icons with an alpha channel
    path.parent.mkdir(parents=True, exist_ok=True)
    out.save(path)


def main() -> None:
    master = draw_mark(1024, BRAND + (255,), PAPER + (255,))
    mask = Image.new("L", (1024, 1024), 0)
    ImageDraw.Draw(mask).ellipse([0, 0, 1023, 1023], fill=255)
    round_master = Image.new("RGBA", (1024, 1024), (0, 0, 0, 0))
    round_master.paste(master, (0, 0), mask)

    res = ROOT / "android/app/src/main/res"
    for density, px in {"mdpi": 48, "hdpi": 72, "xhdpi": 96, "xxhdpi": 144, "xxxhdpi": 192}.items():
        save(master, res / f"mipmap-{density}/ic_launcher.png", px)
        save(round_master, res / f"mipmap-{density}/ic_launcher_round.png", px, opaque=False)

    # Splash logo: the mark in brand colour on a transparent ground, shown on the paper colour.
    logo = draw_mark(1024, (0, 0, 0, 0), BRAND + (255,))
    for density, px in {"mdpi": 144, "hdpi": 216, "xhdpi": 288, "xxhdpi": 432, "xxxhdpi": 576}.items():
        save(logo, res / f"drawable-{density}/splash_logo.png", px, opaque=False)

    iconset = ROOT / "ios/ImageConsulting/Images.xcassets/AppIcon.appiconset"
    contents = json.loads((iconset / "Contents.json").read_text())
    for entry in contents["images"]:
        points = float(entry["size"].split("x")[0])
        scale = int(entry["scale"].rstrip("x"))
        px = round(points * scale)
        entry["filename"] = f"icon-{px}.png"
        save(master, iconset / entry["filename"], px)
    (iconset / "Contents.json").write_text(json.dumps(contents, indent=2) + "\n")
    print("icons written")


if __name__ == "__main__":
    main()
