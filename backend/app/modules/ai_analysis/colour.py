"""Preliminary seasonal colour analysis from a face photo (Feature List row 9).

STATUS: INDICATIVE and DRAFT. Distinguished from the consultant's expert
colour analysis (row 24) everywhere it is shown. Photo colour depends heavily
on lighting and camera processing; the app asks for daylight without filters,
and a tinted-light warning is raised when the eye whites look coloured. Thresholds were set by the development team on a few
public photos, not validated against consultant draping. Row 64 (assessment
accuracy) is an open client decision.

Method
1. Sample skin from both cheeks and the forehead (landmark polygons, limited
   to the segmenter's face-skin class, highlights and shadows trimmed).
   Hair from the hair class (optional: covered hair is common and allowed).
   Eyes from the iris discs, without pupil and reflections.
2. If the eye whites are visible and bright, measure their tint as a check on
   the lighting and flag a strong colour cast. (Correcting the photo from the
   eye whites was tried and made results worse, so it is not done.)
3. Convert to CIELAB and derive three axes, each in [-1, 1]:
   warmth (skin hue angle), depth (skin and hair lightness), clarity
   (contrast between skin, hair and eyes, plus skin chroma).
4. Each season is a corner of that cube: spring warm/light/clear, summer
   cool/light/soft, autumn warm/deep/soft, winter cool/deep/clear.
"""

from dataclasses import dataclass, field

import cv2
import numpy as np

from app.modules.ai_analysis import engine
from app.modules.ai_analysis.shapes import Unusable, single_face

# Landmark polygons (MediaPipe face mesh).
LEFT_CHEEK = [117, 118, 101, 36, 205, 187, 123, 116]
RIGHT_CHEEK = [346, 347, 330, 266, 425, 411, 352, 345]
FOREHEAD = [109, 10, 338, 337, 9, 108]
LEFT_EYE = [33, 7, 163, 144, 145, 153, 154, 155, 133, 173, 157, 158, 159, 160, 161, 246]
RIGHT_EYE = [263, 249, 390, 373, 374, 380, 381, 382, 362, 398, 384, 385, 386, 387, 388, 466]
LEFT_IRIS, RIGHT_IRIS = (468, (469, 470, 471, 472)), (473, (474, 475, 476, 477))

MIN_SKIN_PIXELS = 400
# Even the deepest skin tones read above L*30 in good light; below that the face is underexposed.
MIN_SKIN_L, MAX_SKIN_L = 30.0, 90.0
MIN_HAIR_PIXELS = 800
MAX_CAST = 12.0  # chroma of the eye whites; above this the light is visibly tinted
MIN_PHOTO_CHROMA = 8.0  # 90th percentile chroma; below this the photo is black and white
MAX_HUE_CONCENTRATION = 0.97  # nearly every pixel the same hue: sepia or a tint filter

# Draft calibration (see module docstring).
WARMTH_CENTRE, WARMTH_SPAN = 50.0, 5.0  # skin hue angle in degrees; above the centre reads warm
DEPTH_CENTRE, DEPTH_SPAN = 52.0, 18.0  # weighted lightness L*; below the centre reads deep
CLARITY_CENTRE, CLARITY_SPAN = 65.0, 12.0  # contrast in L* plus chroma; above reads clear

SEASONS = {
    "spring": {"warmth": 1, "depth": -1, "clarity": 1},
    "summer": {"warmth": -1, "depth": -1, "clarity": -1},
    "autumn": {"warmth": 1, "depth": 1, "clarity": -1},
    "winter": {"warmth": -1, "depth": 1, "clarity": 1},
}
# Undertone matters most in seasonal theory, so it is weighted above the other two axes.
AXIS_WEIGHTS = {"warmth": 1.5, "depth": 1.0, "clarity": 1.0}


@dataclass
class ColourResult:
    profile_key: str
    confidence: float
    scores: dict[str, float]
    axes: dict[str, float]
    measurements: dict
    swatches: dict[str, str]  # sampled colours as hex, for display
    notes: list[str] = field(default_factory=list)


def _poly_mask(shape, pts: np.ndarray) -> np.ndarray:
    mask = np.zeros(shape[:2], np.uint8)
    cv2.fillPoly(mask, [np.round(pts).astype(np.int32)], 1)
    return mask


def _trimmed(pixels: np.ndarray, lightness: np.ndarray, low: float, high: float) -> np.ndarray:
    lo, hi = np.percentile(lightness, [low, high])
    return pixels[(lightness >= lo) & (lightness <= hi)]


def _lab(rgb_pixels: np.ndarray) -> np.ndarray:
    """sRGB uint8 (N, 3) -> CIELAB float (N, 3), L in 0-100."""
    lab = cv2.cvtColor(rgb_pixels.reshape(-1, 1, 3).astype(np.float32) / 255.0, cv2.COLOR_RGB2LAB)
    return lab.reshape(-1, 3)


def _hex(rgb: np.ndarray) -> str:
    r, g, b = (int(np.clip(round(float(v)), 0, 255)) for v in rgb)
    return f"#{r:02x}{g:02x}{b:02x}"


def _squash(value: float, centre: float, span: float) -> float:
    return float(np.tanh((value - centre) / span))


def _median_lab(pixels: np.ndarray, low: float, high: float) -> np.ndarray:
    lab = _lab(pixels)
    lo, hi = np.percentile(lab[:, 0], [low, high])
    return np.median(lab[(lab[:, 0] >= lo) & (lab[:, 0] <= hi)], axis=0)


def lab_to_hex(lab) -> str:
    rgb = cv2.cvtColor(np.array(lab, np.float32).reshape(1, 1, 3), cv2.COLOR_LAB2RGB).reshape(3) * 255
    return _hex(rgb)


def is_monochrome(rgb: np.ndarray) -> bool:
    lab = cv2.cvtColor(rgb.astype(np.float32) / 255.0, cv2.COLOR_RGB2LAB)
    chroma = np.hypot(lab[..., 1], lab[..., 2])
    if float(np.percentile(chroma, 90)) < MIN_PHOTO_CHROMA:
        return True
    coloured = chroma > 4
    hue = np.arctan2(lab[..., 2][coloured], lab[..., 1][coloured])
    concentration = float(abs(np.exp(1j * hue).mean()))
    return coloured.mean() > 0.9 and concentration > MAX_HUE_CONCENTRATION


def analyse_colour(rgb: np.ndarray) -> ColourResult:
    if is_monochrome(rgb):
        raise Unusable("not_a_colour_photo")
    face = single_face(rgb)
    pts = face.points[:, :2]
    seg = engine.models.segment(rgb)
    notes: list[str] = []

    # --- eyes: iris discs, and the whites around them
    eye_any = np.zeros(rgb.shape[:2], np.uint8)
    iris_any = np.zeros(rgb.shape[:2], np.uint8)
    for contour, (centre_idx, ring) in ((LEFT_EYE, LEFT_IRIS), (RIGHT_EYE, RIGHT_IRIS)):
        eye = _poly_mask(rgb.shape, pts[contour])
        radius = float(np.mean([np.linalg.norm(pts[i] - pts[centre_idx]) for i in ring]))
        iris = np.zeros_like(eye)
        cv2.circle(iris, tuple(int(v) for v in np.round(pts[centre_idx])), max(1, int(radius)), 1, -1)
        eye_any |= eye
        iris_any |= iris & eye
    sclera = rgb[(eye_any == 1) & (iris_any == 0)]

    # --- lighting check from the sclera (measured, not corrected: correcting from eye whites proved unreliable)
    cast = None
    if len(sclera) >= 30:
        brightness = sclera.astype(np.int32).sum(axis=1)
        bright = sclera[brightness >= np.percentile(brightness, 70)]
        if bright.mean() > 110:  # dark or shadowed eye whites are not a reliable reference
            cast = _median_lab(bright, 0, 100)
            if np.hypot(cast[1], cast[2]) > MAX_CAST:
                notes.append("lighting_colour_cast")
    if cast is None:
        notes.append("no_lighting_reference")

    # --- skin
    region = np.zeros(rgb.shape[:2], np.uint8)
    for polygon in (LEFT_CHEEK, RIGHT_CHEEK, FOREHEAD):
        region |= _poly_mask(rgb.shape, pts[polygon])
    skin_px = rgb[(region == 1) & (seg == engine.FACE_SKIN)]
    if len(skin_px) < MIN_SKIN_PIXELS:
        skin_px = rgb[region == 1]  # segmenter missed; fall back to the polygons alone
        notes.append("skin_from_landmarks_only")
    if len(skin_px) < MIN_SKIN_PIXELS:
        raise Unusable("face_too_small")
    skin = _median_lab(skin_px, 15, 92)  # drop shadows and shine
    if not MIN_SKIN_L <= skin[0] <= MAX_SKIN_L:
        raise Unusable("face_badly_lit", measurements={"skin_lightness": round(float(skin[0]), 1)})

    # --- hair (optional)
    hair_px = rgb[seg == engine.HAIR]
    hair = _median_lab(hair_px, 10, 90) if len(hair_px) >= MIN_HAIR_PIXELS else None
    if hair is None:
        notes.append("hair_not_visible")

    # --- eyes: iris without pupil (darkest) and reflections (brightest)
    iris_px = rgb[iris_any == 1]
    eye = _median_lab(iris_px, 25, 85) if len(iris_px) >= 20 else None
    if eye is None:
        notes.append("eyes_not_visible")

    # --- axes
    hue = float(np.degrees(np.arctan2(skin[2], skin[1])))
    chroma = float(np.hypot(skin[1], skin[2]))
    lightness = float(skin[0] if hair is None else 0.6 * skin[0] + 0.4 * hair[0])
    contrasts = [abs(float(skin[0] - other[0])) for other in (hair, eye) if other is not None]
    contrast = max(contrasts) if contrasts else 0.0
    axes = {
        "warmth": _squash(hue, WARMTH_CENTRE, WARMTH_SPAN),
        "depth": _squash(DEPTH_CENTRE, lightness, DEPTH_SPAN),
        "clarity": _squash(contrast + 0.8 * chroma, CLARITY_CENTRE, CLARITY_SPAN),
    }
    raw = {
        season: sum(AXIS_WEIGHTS[a] * sign * axes[a] for a, sign in corner.items())
        for season, corner in SEASONS.items()
    }
    weights = {k: float(np.exp(2.0 * v)) for k, v in raw.items()}
    total = sum(weights.values())
    scores = {k: round(v / total, 3) for k, v in weights.items()}
    winner = max(scores, key=scores.get)
    if scores[winner] < 0.45:
        notes.append("low_confidence")
    if abs(axes["warmth"]) < 0.2:
        notes.append("neutral_undertone")

    swatches = {"skin": lab_to_hex(skin)}
    if hair is not None:
        swatches["hair"] = lab_to_hex(hair)
    if eye is not None:
        swatches["eyes"] = lab_to_hex(eye)
    measurements = {
        "skin_lab": [round(float(v), 1) for v in skin],
        "skin_hue_deg": round(hue, 1),
        "skin_chroma": round(chroma, 1),
        "hair_lab": None if hair is None else [round(float(v), 1) for v in hair],
        "eye_lab": None if eye is None else [round(float(v), 1) for v in eye],
        "contrast": round(contrast, 1),
        "eye_white_lab": None if cast is None else [round(float(v), 1) for v in cast],
    }
    return ColourResult(
        profile_key=winner,
        confidence=scores[winner],
        scores=scores,
        axes={k: round(v, 3) for k, v in axes.items()},
        measurements=measurements,
        swatches=swatches,
        notes=notes,
    )
