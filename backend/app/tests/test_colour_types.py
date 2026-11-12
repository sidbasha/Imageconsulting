"""Twelve colour types: classification, palettes and the API."""

import numpy as np
import pytest

from app.modules.ai_analysis import colour_types as ct

API = "/api/v1"


def _lab(hex_colour: str) -> np.ndarray:
    import cv2

    rgb = np.array([[[int(hex_colour[i:i + 2], 16) for i in (1, 3, 5)]]], np.uint8)
    return cv2.cvtColor(rgb.astype(np.float32) / 255, cv2.COLOR_RGB2LAB)[0, 0]


def test_there_are_twelve_types_three_per_season():
    assert len(ct.TYPES) == 12
    for season in ("spring", "summer", "autumn", "winter"):
        assert len([t for t in ct.TYPES if t.season == season]) == 3


@pytest.mark.parametrize("t", ct.TYPES, ids=lambda t: t.key)
def test_each_type_is_nearest_to_itself_and_has_a_full_palette(t):
    assert ct.nearest(t.axes) == t.key
    p = ct.palette(t.key)
    assert len(p["neutrals"]) == 6 and len(p["colours"]) == 30 and len(p["lips"]) == 7
    assert all(c["hex"].startswith("#") and len(c["hex"]) == 7 for c in p["neutrals"] + p["colours"] + p["lips"] + p["avoid"])
    assert p["avoid_type"] != t.key and ct.BY_KEY[p["avoid_type"]].season != t.season
    assert all(set(c["name"]) == {"en", "ar"} for c in p["colours"])


def test_palettes_follow_the_axes():
    """Deep types are darker than light ones, bright types more saturated than soft, warm reds more golden than cool."""
    def mean_l(key):
        return np.mean([_lab(c["hex"])[0] for c in ct.palette(key)["colours"]])

    def mean_c(key):
        return np.mean([np.hypot(*_lab(c["hex"])[1:]) for c in ct.palette(key)["colours"]])

    assert mean_l("deep_winter") < mean_l("light_summer") - 15
    assert mean_c("bright_spring") > mean_c("soft_autumn") + 10
    warm_red, cool_red = (_lab(ct.colour(ct.BY_KEY[k].axes, "red")) for k in ("warm_spring", "cool_summer"))
    assert np.degrees(np.arctan2(warm_red[2], warm_red[1])) > np.degrees(np.arctan2(cool_red[2], cool_red[1]))
    assert "gold" in ct.palette("warm_autumn")["metals"] and "silver" in ct.palette("cool_winter")["metals"]


def test_scores_sum_to_one_and_rank():
    s = ct.scores({"warmth": 0.9, "depth": 0.4, "clarity": -0.4})
    assert abs(sum(s.values()) - 1) < 0.01 and next(iter(s)) == "warm_autumn"


def test_colour_type_api_in_both_languages(client):
    from app.tests.test_users_and_commerce import register

    headers = register(client, "types@example.com")
    listed = client.get(f"{API}/colour-types", headers=headers).json()
    assert len(listed) == 12 and {"key", "title", "signature"} <= set(listed[0])
    detail = client.get(f"{API}/colour-types/deep_autumn", headers={**headers, "Accept-Language": "ar"}).json()
    assert detail["title"] == "خريف عميق" and len(detail["colours"]) == 30
    assert client.get(f"{API}/colour-types/nope", headers=headers).status_code == 404
    assert client.get(f"{API}/colour-types").status_code == 401
