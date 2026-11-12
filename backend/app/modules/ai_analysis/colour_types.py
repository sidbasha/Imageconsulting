"""Twelve colour types and their palettes (professional colour analysis).

STATUS: DRAFT content, developer-calibrated. The twelve types are the common
"dominant characteristic" split of the four seasons: each season divides into
three types by whichever of its qualities leads (light/deep, warm/cool,
bright/soft). Every type is a point in the same three-axis space the photo
analysis measures (ai_analysis/colour.py), each axis in [-1, 1]:

- warmth: +1 warm (golden) ... -1 cool (blue-pink)
- depth: +1 deep (dark) ... -1 light
- clarity: +1 bright (clear, saturated) ... -1 soft (muted)

Palettes are generated, not copied: for each type, ten hue families are placed
in CIELAB at the type's lightness range (depth), chroma (clarity) and hue lean
(warmth), then kept inside the sRGB gamut. The same function produces the drape
colours of the guided draping studio, so what a consultant compares is the
palette the client receives. A consultant can replace any of it with a custom
palette per client.
"""

from dataclasses import dataclass
from functools import lru_cache

import numpy as np


def L(en: str, ar: str) -> dict[str, str]:
    return {"en": en, "ar": ar}


@dataclass(frozen=True)
class ColourType:
    key: str
    season: str
    dominant: str  # light | deep | warm | cool | bright | soft
    title: dict
    summary: dict
    axes: dict  # warmth, depth, clarity


TYPES: tuple[ColourType, ...] = (
    ColourType("light_spring", "spring", "light", L("Light Spring", "ربيع فاتح"),
               L("Light and warm, with a fresh, delicate clarity.", "فاتح ودافئ، بصفاء رقيق ومنعش."),
               {"warmth": 0.45, "depth": -1.0, "clarity": 0.3}),
    ColourType("warm_spring", "spring", "warm", L("Warm Spring", "ربيع دافئ"),
               L("Golden warmth leads; colours are clear and lively.", "يغلب الدفء الذهبي، وألوانه صافية ونابضة."),
               {"warmth": 1.0, "depth": -0.35, "clarity": 0.45}),
    ColourType("bright_spring", "spring", "bright", L("Bright Spring", "ربيع ساطع"),
               L("High clarity and contrast, leaning warm.", "صفاء وتباين عاليان مع ميل إلى الدفء."),
               {"warmth": 0.35, "depth": -0.15, "clarity": 1.0}),
    ColourType("light_summer", "summer", "light", L("Light Summer", "صيف فاتح"),
               L("Light and cool, soft rather than bright.", "فاتح وبارد، ناعم أكثر منه ساطعاً."),
               {"warmth": -0.45, "depth": -1.0, "clarity": -0.3}),
    ColourType("cool_summer", "summer", "cool", L("Cool Summer", "صيف بارد"),
               L("Cool, rosy undertone leads; colours are gentle.", "يغلب الأساس البارد الوردي، وألوانه هادئة."),
               {"warmth": -1.0, "depth": -0.3, "clarity": -0.35}),
    ColourType("soft_summer", "summer", "soft", L("Soft Summer", "صيف ناعم"),
               L("Muted and blended, leaning cool.", "ألوان مخففة ومتداخلة مع ميل إلى البرودة."),
               {"warmth": -0.35, "depth": -0.1, "clarity": -1.0}),
    ColourType("soft_autumn", "autumn", "soft", L("Soft Autumn", "خريف ناعم"),
               L("Muted and blended, leaning warm.", "ألوان مخففة ومتداخلة مع ميل إلى الدفء."),
               {"warmth": 0.35, "depth": 0.1, "clarity": -1.0}),
    ColourType("warm_autumn", "autumn", "warm", L("Warm Autumn", "خريف دافئ"),
               L("Rich golden warmth leads; colours are earthy.", "يغلب الدفء الذهبي الغني، وألوانه ترابية."),
               {"warmth": 1.0, "depth": 0.35, "clarity": -0.45}),
    ColourType("deep_autumn", "autumn", "deep", L("Deep Autumn", "خريف عميق"),
               L("Deep and warm, with rich, strong colours.", "عميق ودافئ، بألوان غنية وقوية."),
               {"warmth": 0.45, "depth": 1.0, "clarity": -0.2}),
    ColourType("deep_winter", "winter", "deep", L("Deep Winter", "شتاء عميق"),
               L("Deep and cool, with dramatic contrast.", "عميق وبارد، بتباين لافت."),
               {"warmth": -0.45, "depth": 1.0, "clarity": 0.3}),
    ColourType("cool_winter", "winter", "cool", L("Cool Winter", "شتاء بارد"),
               L("Icy, blue-based coolness leads; colours are clear.", "تغلب البرودة الزرقاء، وألوانه صافية."),
               {"warmth": -1.0, "depth": 0.35, "clarity": 0.45}),
    ColourType("bright_winter", "winter", "bright", L("Bright Winter", "شتاء ساطع"),
               L("High clarity and contrast, leaning cool.", "صفاء وتباين عاليان مع ميل إلى البرودة."),
               {"warmth": -0.35, "depth": 0.15, "clarity": 1.0}),
)
BY_KEY = {t.key: t for t in TYPES}
AXES = ("warmth", "depth", "clarity")
# Undertone carries the most weight in seasonal theory (as in colour.py).
WEIGHTS = {"warmth": 1.5, "depth": 1.0, "clarity": 1.0}

# Hue families: (key, title, hue angle when cool, hue angle when warm), LCh degrees.
FAMILIES = (
    ("red", L("Red", "أحمر"), 18.0, 40.0),
    ("pink", L("Pink", "وردي"), 355.0, 28.0),
    ("coral", L("Coral", "مرجاني"), 20.0, 50.0),
    ("yellow", L("Yellow", "أصفر"), 100.0, 82.0),
    ("green", L("Green", "أخضر"), 160.0, 118.0),
    ("teal", L("Teal", "تركوازي"), 215.0, 190.0),
    ("blue", L("Blue", "أزرق"), 268.0, 238.0),
    ("navy", L("Navy", "كحلي"), 275.0, 255.0),
    ("purple", L("Purple", "بنفسجي"), 300.0, 325.0),
    ("brown", L("Brown", "بنّي"), 40.0, 62.0),
)
TONES = (("light", L("Light", "فاتح")), ("mid", L("", "")), ("deep", L("Deep", "داكن")))


# ---------------------------------------------------------------- colour maths (CIELAB D65 <-> sRGB)

_M = np.array([[3.2404542, -1.5371385, -0.4985314], [-0.9692660, 1.8760108, 0.0415560], [0.0556434, -0.2040259, 1.0572252]])
_WHITE = np.array([0.95047, 1.0, 1.08883])


def _lab_to_linear_rgb(lab: np.ndarray) -> np.ndarray:
    lightness, a, b = lab
    fy = (lightness + 16) / 116
    f = np.array([fy + a / 500, fy, fy - b / 200])
    xyz = np.where(f ** 3 > 0.008856, f ** 3, (f - 16 / 116) / 7.787) * _WHITE
    return _M @ xyz


def _gamma(c: np.ndarray) -> np.ndarray:
    c = np.clip(c, 0, 1)
    return np.where(c <= 0.0031308, 12.92 * c, 1.055 * np.power(c, 1 / 2.4) - 0.055)


def lch_to_hex(lightness: float, chroma: float, hue: float) -> str:
    """The colour at (L, C, h), with chroma reduced until it fits in sRGB."""
    for _ in range(40):
        rad = np.radians(hue)
        rgb = _lab_to_linear_rgb(np.array([lightness, chroma * np.cos(rad), chroma * np.sin(rad)]))
        if np.all(rgb >= -1e-4) and np.all(rgb <= 1 + 1e-4):
            break
        chroma *= 0.92
    r, g, b = (int(round(float(v) * 255)) for v in _gamma(rgb))
    return f"#{r:02x}{g:02x}{b:02x}"


# ---------------------------------------------------------------- palettes

def _lean(axes: dict) -> tuple[float, float, float]:
    warmth, depth, clarity = (float(np.clip(axes[a], -1, 1)) for a in AXES)
    return warmth, depth, clarity


def _hue(family: tuple, warmth: float) -> float:
    _, _, cool, warm = family
    t = (warmth + 1) / 2  # 0 cool .. 1 warm
    delta = (warm - cool + 180) % 360 - 180  # shortest way round the hue circle
    return (cool + t * delta) % 360


def _tone(depth: float, clarity: float, tone: str) -> tuple[float, float]:
    centre = 60 - 17 * depth  # deep types sit lower in lightness
    lightness = {"light": centre + 15, "mid": centre, "deep": centre - 17}[tone]
    chroma = 38 + 22 * clarity  # bright types more saturated, soft types more muted
    if tone == "light":
        chroma *= 0.7  # pastels carry less colour
    return float(np.clip(lightness, 18, 92)), float(max(chroma, 8))


def colour(axes: dict, family_key: str, tone: str = "mid") -> str:
    """One palette colour for a point in the three-axis space."""
    warmth, depth, clarity = _lean(axes)
    family = next(f for f in FAMILIES if f[0] == family_key)
    lightness, chroma = _tone(depth, clarity, tone)
    if family_key == "brown":
        chroma *= 0.55
    if family_key == "navy":
        lightness, chroma = min(lightness, 30 + 8 * (1 - depth)), chroma * 0.8
    return lch_to_hex(lightness, chroma, _hue(family, warmth))


def _name(family: tuple, tone: tuple) -> dict:
    return {lang: f"{tone[1][lang]} {family[1][lang]}".strip() if lang == "en" else f"{family[1][lang]} {tone[1][lang]}".strip()
            for lang in ("en", "ar")}


def _neutrals(axes: dict) -> list[dict]:
    warmth, depth, clarity = _lean(axes)
    hue = 75.0 if warmth > 0 else 255.0
    tint = 6 + 4 * abs(warmth)
    top = 96 if clarity > 0.5 else 92 if clarity > -0.5 else 88  # crisp white only for clear types
    # Near-black only for deep or bright cool types; deep warm types get a dark brown instead.
    clear_dark = clarity > -0.3 and (depth > 0.6 or (clarity > 0.8 and warmth < 0))
    bottom = 14 if clear_dark else 22 if depth > 0 else 32
    steps = np.linspace(top, bottom, 6)
    names = (L("Light neutral", "محايد فاتح"), L("Soft neutral", "محايد ناعم"), L("Mid neutral", "محايد متوسّط"),
             L("Rich neutral", "محايد غني"), L("Dark neutral", "محايد داكن"), L("Deepest neutral", "أعمق محايد"))
    return [{"hex": lch_to_hex(float(v), tint * (0.6 if i in (0, 5) else 1.0), hue), "name": names[i]} for i, v in enumerate(steps)]


@lru_cache
def palette(key: str) -> dict:
    """The full palette for one type: neutrals, 30 colours, lips, hair, metals, and colours to avoid."""
    t = BY_KEY[key]
    axes = t.axes
    colours = [{"hex": colour(axes, f[0], tone[0]), "name": _name(f, tone), "family": f[0], "tone": tone[0]}
               for f in FAMILIES for tone in TONES]
    warmth, depth, clarity = _lean(axes)
    lips = [{"hex": colour(axes, fam, tone), "name": _name(next(f for f in FAMILIES if f[0] == fam), next(x for x in TONES if x[0] == tone))}
            for fam, tone in (("pink", "light"), ("coral", "mid"), ("pink", "mid"), ("red", "mid"), ("red", "deep"), ("purple", "deep"))]
    nude_l, nude_c = 62 - 12 * depth, 22 + 6 * clarity
    lips.insert(0, {"hex": lch_to_hex(nude_l, nude_c, 50 if warmth > 0 else 20), "name": L("Nude", "نود")})
    if warmth > 0:
        hair = [L("Golden blonde", "أشقر ذهبي"), L("Copper", "نحاسي"), L("Warm chestnut", "كستنائي دافئ"), L("Golden brown", "بنّي ذهبي")]
        hair_hex = [lch_to_hex(72, 30, 75), lch_to_hex(48, 45, 50), lch_to_hex(35, 25, 50), lch_to_hex(40, 22, 65)]
        metals = ["gold", "bronze", "copper"]
    else:
        hair = [L("Ash blonde", "أشقر رمادي"), L("Ash brown", "بنّي رمادي"), L("Cool espresso", "قهوة باردة"), L("Soft black", "أسود ناعم")]
        hair_hex = [lch_to_hex(72, 10, 85), lch_to_hex(42, 8, 60), lch_to_hex(25, 6, 40), lch_to_hex(15, 2, 270)]
        metals = ["silver", "platinum", "white_gold"]
    if abs(warmth) < 0.5:
        metals.append("rose_gold")
    if depth < -0.5:  # light types: lighter hair suggestions first, darkest dropped
        hair, hair_hex = hair[:3], hair_hex[:3]
    elif depth > 0.5:
        hair, hair_hex = hair[1:], hair_hex[1:]
    opposite = nearest({a: -v for a, v in axes.items()})
    avoid = [{"hex": colour(BY_KEY[opposite].axes, fam, "mid"), "name": next(f for f in FAMILIES if f[0] == fam)[1]}
             for fam in ("red", "pink", "green", "blue", "yellow", "brown")]
    return {
        "key": t.key, "season": t.season, "dominant": t.dominant, "title": t.title, "summary": t.summary, "axes": axes,
        "neutrals": _neutrals(axes), "colours": colours, "lips": lips,
        "hair": [{"hex": h, "name": n} for h, n in zip(hair_hex, hair)],
        "metals": metals, "avoid": avoid, "avoid_type": opposite,
        "signature": [c["hex"] for c in colours if c["tone"] == "mid" and c["family"] in ("red", "teal", "pink", "green")],
    }


# ---------------------------------------------------------------- classification

def scores(axes: dict, sharpness: float = 2.5) -> dict[str, float]:
    """How close a point in the three-axis space is to each type, as shares summing to 1."""
    distance = {t.key: sum(WEIGHTS[a] * (float(axes.get(a, 0.0)) - t.axes[a]) ** 2 for a in AXES) for t in TYPES}
    weights = {k: float(np.exp(-sharpness * d)) for k, d in distance.items()}
    total = sum(weights.values())
    return {k: round(v / total, 3) for k, v in sorted(weights.items(), key=lambda kv: -kv[1])}


def nearest(axes: dict) -> str:
    return next(iter(scores(axes)))


def summary(key: str, language: str) -> dict:
    """The type in one language, for API answers."""
    p = palette(key)
    pick = lambda d: d.get(language) or d["en"]  # noqa: E731
    named = lambda items: [{**i, "name": pick(i["name"])} for i in items]  # noqa: E731
    return {
        "key": p["key"], "season": p["season"], "dominant": p["dominant"], "title": pick(p["title"]),
        "summary": pick(p["summary"]), "axes": p["axes"], "neutrals": named(p["neutrals"]), "colours": named(p["colours"]),
        "lips": named(p["lips"]), "hair": named(p["hair"]), "metals": p["metals"], "avoid": named(p["avoid"]),
        "avoid_type": p["avoid_type"], "signature": p["signature"],
    }
