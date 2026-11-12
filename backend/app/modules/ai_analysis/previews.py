"""Appearance previews drawn on the user's own photo.

What these are, and are not:
- Hair colour (row 12): recolours the hair the segmenter finds. It previews
  COLOUR only. A new haircut or hairstyle on the photo needs a generative
  model and is not built; hairstyle advice stays text (recommendations).
- Outfit colour try-on (row 11): recolours the clothes the user is wearing in
  a recommended palette colour. It is NOT a garment try-on (putting a
  different item of clothing on the photo); that needs a generative try-on
  model or a vendor service and is an open client question ("what virtual
  try-on means", STATUS.md). The interface below takes a colour so a
  garment provider can be added beside it later.
- Permanent-makeup preview (row 14): tints lips and brows.
- Digital draping (row 28, consultant workspace): covers the clothing area
  with a flat fabric colour so the consultant can compare colours against the
  face.

Previews are generated on request and returned as JPEG; they are never stored.
All recolouring happens in CIELAB, replacing the hue and shifting lightness
while keeping the photo's own shading, through a feathered mask.
"""

import re

import cv2
import numpy as np

from app.modules.ai_analysis import engine
from app.modules.ai_analysis.shapes import Unusable, single_face

HEX = re.compile(r"^#[0-9a-fA-F]{6}$")

# Face mesh outlines.
LIPS_OUTER = [61, 146, 91, 181, 84, 17, 314, 405, 321, 375, 291, 409, 270, 269, 267, 0, 37, 39, 40, 185]
LIPS_INNER = [78, 95, 88, 178, 87, 14, 317, 402, 318, 324, 308, 415, 310, 311, 312, 13, 82, 81, 80, 191]
LEFT_BROW = [70, 63, 105, 66, 107, 55, 65, 52, 53, 46]
RIGHT_BROW = [300, 293, 334, 296, 336, 285, 295, 282, 283, 276]


def parse_colour(value: str) -> np.ndarray:
    if not HEX.match(value or ""):
        raise ValueError("colour must be #rrggbb")
    rgb = np.array([int(value[i : i + 2], 16) for i in (1, 3, 5)], np.uint8).reshape(1, 1, 3)
    return cv2.cvtColor(rgb.astype(np.float32) / 255.0, cv2.COLOR_RGB2LAB).reshape(3)


def recolour(rgb: np.ndarray, mask: np.ndarray, target_lab: np.ndarray, *, strength: float = 1.0,
             lightness_follow: float = 0.7, texture: float = 0.35, feather: int = 7) -> np.ndarray:
    """Moves the masked pixels to the target colour, keeping relative shading.

    lightness_follow: how far the region's mean lightness moves to the target's.
    texture: how much of the original a/b variation is kept (0 = flat colour).
    """
    if mask.sum() == 0:
        return rgb.copy()
    lab = cv2.cvtColor(rgb.astype(np.float32) / 255.0, cv2.COLOR_RGB2LAB)
    region = mask.astype(bool)
    mean = lab[region].mean(axis=0)
    out = lab.copy()
    out[..., 0] = lab[..., 0] + lightness_follow * (target_lab[0] - mean[0])
    out[..., 1] = target_lab[1] + texture * (lab[..., 1] - mean[1])
    out[..., 2] = target_lab[2] + texture * (lab[..., 2] - mean[2])
    out[..., 0] = np.clip(out[..., 0], 0, 100)
    k = feather | 1
    alpha = cv2.GaussianBlur(mask.astype(np.float32), (k, k), 0)[..., None] * strength
    blended = lab * (1 - alpha) + out * alpha
    result = cv2.cvtColor(blended.astype(np.float32), cv2.COLOR_LAB2RGB)
    return np.clip(result * 255.0 + 0.5, 0, 255).astype(np.uint8)


def _poly(shape, pts) -> np.ndarray:
    mask = np.zeros(shape[:2], np.uint8)
    cv2.fillPoly(mask, [np.round(pts).astype(np.int32)], 1)
    return mask


def hair_colour(rgb: np.ndarray, colour: str) -> np.ndarray:
    target = parse_colour(colour)
    hair = (engine.models.segment(rgb) == engine.HAIR).astype(np.uint8)
    if hair.sum() < 800:
        raise Unusable("hair_not_visible")
    return recolour(rgb, hair, target, lightness_follow=0.6, texture=0.4, feather=9)


def outfit_colour(rgb: np.ndarray, colour: str) -> np.ndarray:
    target = parse_colour(colour)
    clothes = (engine.models.segment(rgb) == engine.CLOTHES).astype(np.uint8)
    if clothes.sum() < 0.02 * clothes.size:
        raise Unusable("clothes_not_visible")
    return recolour(rgb, clothes, target, lightness_follow=0.8, texture=0.2, feather=5)


def makeup(rgb: np.ndarray, lip_colour: str | None, brow_colour: str | None, intensity: float = 0.7) -> np.ndarray:
    if not lip_colour and not brow_colour:
        raise ValueError("choose a lip or brow colour")
    face = single_face(rgb)
    pts = face.points[:, :2]
    out = rgb
    if lip_colour:
        lips = _poly(rgb.shape, pts[LIPS_OUTER]) & (1 - _poly(rgb.shape, pts[LIPS_INNER]))
        out = recolour(out, lips, parse_colour(lip_colour), strength=intensity, lightness_follow=0.5, texture=0.5, feather=5)
    if brow_colour:
        brows = _poly(rgb.shape, pts[LEFT_BROW]) | _poly(rgb.shape, pts[RIGHT_BROW])
        # Tint only the darker (hair) pixels inside the brow outline, not the skin between them.
        gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
        inside = gray[brows == 1]
        if inside.size:
            brows = brows & (gray <= np.percentile(inside, 60)).astype(np.uint8)
        out = recolour(out, brows, parse_colour(brow_colour), strength=intensity, lightness_follow=0.6, texture=0.4, feather=3)
    return out


def cape_mask(rgb: np.ndarray) -> np.ndarray:
    """Everything below the chin that is not face, hair or background: where a draping cape goes."""
    face = single_face(rgb)
    chin_y = int(face.points[152, 1])
    seg = engine.models.segment(rgb)
    cape = np.isin(seg, (engine.CLOTHES, engine.BODY_SKIN, engine.OTHER)).astype(np.uint8)
    cape[: chin_y + 2] = 0
    if cape.sum() < 0.03 * cape.size:
        # Close crops: fall back to a band across the bottom of the photo.
        cape[:] = 0
        cape[max(chin_y + 2, int(rgb.shape[0] * 0.8)) :] = 1
    return cape


def drape(rgb: np.ndarray, colour: str, cape: np.ndarray | None = None) -> np.ndarray:
    """Covers the area below the chin with a flat fabric colour, like a draping cape.
    Pass a cape from cape_mask() to drape several colours on one photo without re-running the models."""
    if cape is None:
        cape = cape_mask(rgb)
    return recolour(rgb, cape, parse_colour(colour), lightness_follow=1.0, texture=0.0, feather=5)


def drapes(rgb: np.ndarray, colours: list[str]) -> list[np.ndarray]:
    cape = cape_mask(rgb)
    return [drape(rgb, c, cape) for c in colours]


def lips(rgb: np.ndarray, colours: list[str], intensity: float = 0.75) -> list[np.ndarray]:
    """The same face with each lip colour, for side-by-side comparison."""
    pts = single_face(rgb).points[:, :2]
    mask = _poly(rgb.shape, pts[LIPS_OUTER]) & (1 - _poly(rgb.shape, pts[LIPS_INNER]))
    return [recolour(rgb, mask, parse_colour(c), strength=intensity, lightness_follow=0.5, texture=0.5, feather=5) for c in colours]


def side_by_side(tiles: list[np.ndarray], height: int = 520, per_row: int = 4, gap: int = 8) -> np.ndarray:
    """Tiles scaled to one height, laid out in rows on a white ground."""
    tiles = [cv2.resize(t, (int(t.shape[1] * height / t.shape[0]), height), interpolation=cv2.INTER_AREA) for t in tiles]
    rows = []
    for i in range(0, len(tiles), per_row):
        row = tiles[i:i + per_row]
        spacer = np.full((height, gap, 3), 255, np.uint8)
        parts = [p for t in row for p in (t, spacer)][:-1]
        rows.append(np.hstack(parts))
    width = max(r.shape[1] for r in rows)
    padded = [np.pad(r, ((0, gap), (0, width - r.shape[1]), (0, 0)), constant_values=255) for r in rows]
    return np.vstack(padded)[:-gap]
