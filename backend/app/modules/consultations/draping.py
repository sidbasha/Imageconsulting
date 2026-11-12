"""Guided draping: the consultant's structured colour analysis (rows 27-28).

The consultant compares two drapes at a time on the client's face photo and
picks the one that flatters more (or "same"). Three test steps each settle one
axis of the colour space in colour_types.py, then a final step compares the
leading types' signature colours:

1. undertone: warm vs cool versions of the same colour, and gold vs silver
2. depth: light vs deep, at the undertone found in step 1
3. clarity: bright vs soft, at the undertone and depth found so far
4. confirm: the three closest types, four signature drapes each; the consultant chooses

Each answer is +1 (the first drape's side of the axis), -1 (the other) or 0.
An axis is the mean of its answers. The consultant's final choice is the
result; the computed ranking is kept beside it. Drape colours come from the
same palette generator as the client's palette, so the drapes are the palette.
"""

from app.modules.ai_analysis import colour_types as ct

STEPS = ("undertone", "depth", "clarity", "confirm")
AXIS = {"undertone": "warmth", "depth": "depth", "clarity": "clarity"}
PICKS = {"a": 1.0, "b": -1.0, "same": 0.0}
GOLD, SILVER = "#c8a046", "#bfc3c7"


def L(en: str, ar: str) -> dict:
    return {"en": en, "ar": ar}


STEP_TITLES = {
    "undertone": (L("Undertone", "درجة الأساس"), L("Which drape makes the skin look clearer and more even: warm or cool?",
                                                     "أيّ القماشين يجعل البشرة أصفى وأكثر تجانساً: الدافئ أم البارد؟")),
    "depth": (L("Depth", "العمق"), L("Does a light or a deep drape balance the face better?",
                                      "هل يوازن القماش الفاتح أم الداكن الوجه بشكل أفضل؟")),
    "clarity": (L("Clarity", "الصفاء"), L("Does a bright, clear drape or a soft, muted one look more natural?",
                                           "هل يبدو القماش الساطع الصافي أم الناعم المخفّف أكثر طبيعية؟")),
    "confirm": (L("Your type", "النوع"), L("Compare the closest types and choose the one that looks best.",
                                            "قارني الأنواع الأقرب واختاري الأنسب.")),
}
SIDE_LABELS = {
    "undertone": (L("Warm", "دافئ"), L("Cool", "بارد")),
    "depth": (L("Deep", "داكن"), L("Light", "فاتح")),
    "clarity": (L("Bright", "ساطع"), L("Soft", "ناعم")),
}


def axes_from(choices: list[dict]) -> dict[str, float]:
    """The axes the answers so far point to; 0 where an axis has no answers yet."""
    out = {}
    for step, axis in AXIS.items():
        picks = [PICKS[c["pick"]] for c in choices if c["step"] == step]
        out[axis] = round(sum(picks) / len(picks), 3) if picks else 0.0
    return out


def _pairs(step: str, axes: dict) -> list[dict]:
    """Two-drape comparisons for one step. 'a' is always the positive side of the axis."""
    def at(**override):
        return {**axes, **override}

    if step == "undertone":
        pairs = [(ct.colour(at(warmth=1, depth=0, clarity=0), f), ct.colour(at(warmth=-1, depth=0, clarity=0), f))
                 for f in ("red", "pink", "green", "blue")]
        pairs.append((GOLD, SILVER))
    elif step == "depth":
        pairs = [(ct.colour(at(depth=1, clarity=0), f, "deep"), ct.colour(at(depth=-1, clarity=0), f, "light"))
                 for f in ("blue", "pink", "brown")]
    else:
        pairs = [(ct.colour(at(clarity=1), f), ct.colour(at(clarity=-1), f)) for f in ("green", "pink", "teal")]
    return [{"index": i, "a": a, "b": b} for i, (a, b) in enumerate(pairs)]


def _localise(d: dict, language: str) -> str:
    return d.get(language) or d["en"]


def next_step(choices: list[dict], language: str = "en") -> dict | None:
    """The next comparison to show, or None when the analysis is complete."""
    axes = axes_from(choices)
    for step in STEPS[:-1]:
        pairs = _pairs(step, axes)
        answered = {c["pair"] for c in choices if c["step"] == step}
        remaining = [p for p in pairs if p["index"] not in answered]
        if remaining:
            title, prompt = STEP_TITLES[step]
            a_label, b_label = SIDE_LABELS[step]
            return {"step": step, "number": STEPS.index(step) + 1, "of": len(STEPS),
                    "title": _localise(title, language), "prompt": _localise(prompt, language),
                    "pair": remaining[0], "labels": {"a": _localise(a_label, language), "b": _localise(b_label, language)},
                    "progress": {"answered": len(answered), "total": len(pairs)}}
    if not any(c["step"] == "confirm" for c in choices):
        title, prompt = STEP_TITLES["confirm"]
        return {"step": "confirm", "number": len(STEPS), "of": len(STEPS), "title": _localise(title, language),
                "prompt": _localise(prompt, language), "options": candidates(axes, language)}
    return None


def candidates(axes: dict, language: str = "en", count: int = 3) -> list[dict]:
    ranked = list(ct.scores(axes).items())[:count]
    return [{"key": k, "title": _localise(ct.BY_KEY[k].title, language), "score": v, "drapes": ct.palette(k)["signature"]}
            for k, v in ranked]


def validate(choices: list[dict], answer: dict) -> None:
    """Raises ValueError unless the answer is for the step and pair being asked."""
    asked = next_step(choices)
    if asked is None:
        raise ValueError("already complete")
    if answer.get("step") != asked["step"]:
        raise ValueError("not the current step")
    if asked["step"] == "confirm":
        if answer.get("pick") not in {o["key"] for o in asked["options"]}:
            raise ValueError("choose one of the offered types")
    elif answer.get("pair") != asked["pair"]["index"] or answer.get("pick") not in PICKS:
        raise ValueError("not the current pair")


def result(choices: list[dict], language: str = "en") -> dict:
    axes = axes_from(choices)
    ranked = list(ct.scores(axes).items())[:3]
    chosen = next((c["pick"] for c in choices if c["step"] == "confirm"), None)
    return {"axes": axes, "scores": ranked, "colour_type": chosen or ranked[0][0]}
