"""Photo analysis and previews, run against the real MediaPipe models.

These tests need the models (`python -m app.cli fetch-models`). They check that
the pipeline measures, classifies, refuses unsuitable photos and stays behind
its switches. They do NOT show the classifications are correct: accuracy needs
consultant-labelled photos (Feature List row 64).
"""

from pathlib import Path

import cv2
import numpy as np
import pytest
from sqlalchemy import func, select

from app.modules.ai_analysis import engine, previews
from app.modules.ai_analysis.colour import analyse_colour
from app.modules.ai_analysis.models import PhotoAnalysis
from app.modules.ai_analysis.shapes import (
    BODY_PROTOTYPES,
    FACE_PROTOTYPES,
    Unusable,
    analyse_body_shape,
    analyse_face_shape,
)
from app.tests.test_assessments import FACE_ROUND, answer, english, upload, uploads  # noqa: F401

pytestmark = pytest.mark.skipif(not engine.models_available(), reason="run `python -m app.cli fetch-models` first")

API = "/api/v1"
FIXTURES = Path(__file__).parent / "fixtures"
FACE_JPEG = (FIXTURES / "face_colour.jpg").read_bytes()
BODY_JPEG = (FIXTURES / "body_frontal.jpg").read_bytes()


def rgb(data: bytes) -> np.ndarray:
    return engine.decode(data)


def jpeg(image: np.ndarray) -> bytes:
    return engine.encode_jpeg(image, 92)


# ---------- analysers ----------

def test_face_shape_returns_a_known_shape_with_measurements():
    result = analyse_face_shape(rgb(FACE_JPEG))
    assert result.profile_key in FACE_PROTOTYPES
    assert abs(sum(result.scores.values()) - 1) < 0.01
    assert 1.0 < result.measurements["length_ratio"] < 1.6
    assert abs(result.measurements["yaw"]) < 12


def test_body_shape_measures_the_silhouette():
    result = analyse_body_shape(rgb(BODY_JPEG))
    assert result.profile_key in BODY_PROTOTYPES
    m = result.measurements
    assert m["waist_px"] < m["hips_px"] and m["waist_px"] < m["shoulders_px"]
    assert m["waist_rows"] >= 5 and m["hip_rows"] >= 5


def test_colour_analysis_samples_skin_hair_and_eyes():
    result = analyse_colour(rgb(FACE_JPEG))
    assert result.profile_key in ("spring", "summer", "autumn", "winter")
    assert set(result.swatches) == {"skin", "hair", "eyes"}
    assert set(result.axes) == {"warmth", "depth", "clarity"}
    assert all(-1 <= v <= 1 for v in result.axes.values())
    skin_l = result.measurements["skin_lab"][0]
    assert result.measurements["hair_lab"][0] < skin_l  # dark hair, lighter skin, in this photo


def test_unsuitable_photos_are_refused_with_a_reason(monkeypatch):
    face = rgb(FACE_JPEG)
    with pytest.raises(Unusable) as no_face:
        analyse_face_shape(np.full((600, 600, 3), 128, np.uint8))
    assert no_face.value.reasons == ["no_face"]

    from app.modules.ai_analysis import shapes

    monkeypatch.setattr(shapes, "MAX_YAW", 0.0)  # every real head is turned a little
    with pytest.raises(Unusable) as turned:
        analyse_face_shape(face)
    assert turned.value.reasons == ["face_not_frontal"] and "yaw" in turned.value.measurements
    monkeypatch.undo()

    grey = cv2.cvtColor(cv2.cvtColor(face, cv2.COLOR_RGB2GRAY), cv2.COLOR_GRAY2RGB)
    with pytest.raises(Unusable) as mono:
        analyse_colour(grey)
    assert mono.value.reasons == ["not_a_colour_photo"]

    with pytest.raises(Unusable) as dark:
        analyse_colour((face * 0.3).astype(np.uint8))
    assert dark.value.reasons == ["face_badly_lit"]

    with pytest.raises(Unusable) as head_only:
        analyse_body_shape(face)  # a head-and-shoulders photo has no hips or knees
    assert head_only.value.reasons[0] in ("body_not_fully_visible", "no_person")


def test_two_faces_are_refused():
    face = rgb(FACE_JPEG)
    pair = np.hstack([face, face])
    with pytest.raises(Unusable) as many:
        analyse_face_shape(pair)
    assert many.value.reasons == ["multiple_faces"]


# ---------- previews ----------

def changed(before: np.ndarray, after: np.ndarray, mask: np.ndarray) -> tuple[float, float]:
    diff = np.abs(before.astype(int) - after.astype(int)).sum(axis=2)
    return float(diff[mask].mean()), float(diff[~mask].mean())


def test_hair_colour_changes_the_hair_only():
    face = rgb(FACE_JPEG)
    out = previews.hair_colour(face, "#b03020")
    hair = engine.models.segment(face) == engine.HAIR
    inside, outside = changed(face, out, hair)
    assert inside > 40 and outside < 3


def test_outfit_colour_changes_the_clothes_only():
    body = rgb(BODY_JPEG)
    out = previews.outfit_colour(body, "#2060c0")
    clothes = engine.models.segment(body) == engine.CLOTHES
    inside, outside = changed(body, out, clothes)
    assert inside > 30 and outside < 3


def test_makeup_tints_lips():
    face = rgb(FACE_JPEG)
    out = previews.makeup(face, "#d01040", None, 1.0)
    lips = np.zeros(face.shape[:2], np.uint8)
    marks = engine.models.faces(face)[0].points[:, :2]
    cv2.fillPoly(lips, [np.round(marks[previews.LIPS_OUTER]).astype(np.int32)], 1)
    inside, outside = changed(face, out, lips.astype(bool))
    assert inside > 15 and outside < 2
    with pytest.raises(ValueError):
        previews.makeup(face, None, None)


def test_drape_covers_below_the_chin():
    face = rgb(FACE_JPEG)
    out = previews.drape(face, "#3050a0")
    chin = int(engine.models.faces(face)[0].points[152, 1])
    above = np.abs(face[: chin - 20].astype(int) - out[: chin - 20].astype(int)).mean()
    below = np.abs(face[-50:].astype(int) - out[-50:].astype(int)).mean()
    assert above < 2 and below > 20


# ---------- API ----------

def photo_id(client, headers, data, kind):
    response = upload(client, headers, data, kind=kind)
    assert response.status_code == 201, response.text
    return response.json()["id"]


def test_analysis_api_stores_and_returns_an_indicative_result(client, db, uploads):  # noqa: F811
    headers = english(client)
    face = photo_id(client, headers, FACE_JPEG, "face")
    response = client.post(f"{API}/analysis/seasonal_color", json={"image_id": face}, headers=headers)
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["basis"] == "photo_analysis" and body["indicative"] is True
    assert body["profile"]["key"] in ("spring", "summer", "autumn", "winter")
    assert len(body["profile"]["palette"]) == 6 and body["profile"]["title"]
    assert body["scores"][0]["score"] >= body["scores"][-1]["score"]
    assert set(body["swatches"]) == {"skin", "hair", "eyes"}
    assert body["model_version"].startswith("mediapipe:")
    assert client.get(f"{API}/analysis/seasonal_color", headers=headers).json()["id"] == body["id"]

    assert client.post(f"{API}/analysis/face_shape", json={"image_id": face}, headers=headers).status_code == 201
    body_photo = photo_id(client, headers, BODY_JPEG, "full_body")
    shape = client.post(f"{API}/analysis/body_shape", json={"image_id": body_photo}, headers=headers)
    assert shape.status_code == 201 and shape.json()["profile"]["key"] in BODY_PROTOTYPES
    assert db.scalar(select(func.count()).select_from(PhotoAnalysis)) == 3


def test_analysis_needs_the_right_photo_and_owner(client, customer, uploads):  # noqa: F811
    headers = english(client)
    face = photo_id(client, headers, FACE_JPEG, "face")
    wrong = client.post(f"{API}/analysis/body_shape", json={"image_id": face}, headers=headers)
    assert wrong.status_code == 422 and wrong.json()["error"]["code"] == "wrong_photo_kind"
    # Another user cannot analyse this photo.
    assert client.post(f"{API}/analysis/face_shape", json={"image_id": face}, headers=customer).status_code == 404
    assert client.post(f"{API}/analysis/nonsense", json={"image_id": face}, headers=headers).status_code == 404


def test_unanalysable_photo_gets_reasons_in_the_users_language(client, customer, uploads):  # noqa: F811
    grey = cv2.cvtColor(cv2.cvtColor(rgb(FACE_JPEG), cv2.COLOR_RGB2GRAY), cv2.COLOR_GRAY2RGB)
    image = photo_id(client, customer, jpeg(grey), "face")
    response = client.post(f"{API}/analysis/seasonal_color", json={"image_id": image}, headers=customer)
    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "photo_not_analysable" and error["detail"]["reasons"] == ["not_a_colour_photo"]
    assert error["message"].startswith("تعذّر")  # this customer uses Arabic


def test_photo_result_replaces_an_older_self_assessment_in_recommendations(client, uploads):  # noqa: F811
    headers = english(client)
    answer(client, headers, "face_shape", FACE_ROUND)
    before = client.get(f"{API}/recommendations/eyewear", headers=headers).json()["sections"][0]
    assert before["basis"] == "self_assessment" and before["result"] == "Round"

    face = photo_id(client, headers, FACE_JPEG, "face")
    analysed = client.post(f"{API}/analysis/face_shape", json={"image_id": face}, headers=headers).json()
    after = client.get(f"{API}/recommendations/eyewear", headers=headers).json()["sections"][0]
    assert after["basis"] == "photo_analysis" and after["result"] == analysed["profile"]["title"]

    # Retaking the questionnaire afterwards puts the self-assessment back in front.
    answer(client, headers, "face_shape", FACE_ROUND)
    again = client.get(f"{API}/recommendations/eyewear", headers=headers).json()["sections"][0]
    assert again["basis"] == "self_assessment"


def test_deleting_the_photo_keeps_the_result(client, db, uploads):  # noqa: F811
    headers = english(client)
    face = photo_id(client, headers, FACE_JPEG, "face")
    client.post(f"{API}/analysis/face_shape", json={"image_id": face}, headers=headers)
    assert client.delete(f"{API}/assessment-images/{face}", headers=headers).status_code == 204
    assert client.get(f"{API}/analysis/face_shape", headers=headers).json()["profile"]
    assert client.post(f"{API}/analysis/face_shape", json={"image_id": face}, headers=headers).status_code == 404


def test_preview_endpoints_return_jpeg_and_follow_their_switches(client, release, uploads):  # noqa: F811
    headers = english(client)
    face = photo_id(client, headers, FACE_JPEG, "face")
    body_photo = photo_id(client, headers, BODY_JPEG, "full_body")

    hair = client.post(f"{API}/previews/hair-colour", json={"image_id": face, "colour": "#8b2e1a"}, headers=headers)
    assert hair.status_code == 200 and hair.headers["content-type"] == "image/jpeg"
    assert hair.headers["cache-control"] == "no-store" and hair.content[:2] == b"\xff\xd8"
    outfit = client.post(f"{API}/previews/outfit-colour", json={"image_id": body_photo, "colour": "#2060c0"}, headers=headers)
    assert outfit.status_code == 200
    bad = client.post(f"{API}/previews/hair-colour", json={"image_id": face, "colour": "red"}, headers=headers)
    assert bad.status_code == 422

    # Makeup preview is Phase 3: off in the initial release.
    makeup = {"image_id": face, "lip_colour": "#c02040"}
    assert client.post(f"{API}/previews/makeup", json=makeup, headers=headers).status_code == 404
    assert release(phases={"phase2": True, "phase3": True}).status_code == 201
    assert client.post(f"{API}/previews/makeup", json=makeup, headers=headers).status_code == 200

    # Switching hair preview off closes its endpoint.
    assert release(features={"phase1.hair_preview": False}).status_code == 201
    hair = client.post(f"{API}/previews/hair-colour", json={"image_id": face, "colour": "#8b2e1a"}, headers=headers)
    assert hair.status_code == 404


def test_analysis_follows_its_switch_and_keeps_data(client, release, db, uploads):  # noqa: F811
    headers = english(client)
    face = photo_id(client, headers, FACE_JPEG, "face")
    client.post(f"{API}/analysis/face_shape", json={"image_id": face}, headers=headers)
    # Turning off face shape also needs its dependants (eyewear, hair preview) off.
    off = {"phase1.face_shape": False, "phase1.eyewear": False, "phase1.hair_preview": False}
    response = release(features=off)
    assert response.status_code == 201, response.text
    assert client.post(f"{API}/analysis/face_shape", json={"image_id": face}, headers=headers).status_code == 404
    assert client.get(f"{API}/analysis/face_shape", headers=headers).status_code == 404
    assert db.scalar(select(func.count()).select_from(PhotoAnalysis)) == 1


# ---------- garment and hairstyle try-on (rows 11, 12) ----------

GARMENT_JPEG = (FIXTURES / "garment_reference.jpg").read_bytes()


def test_hairstyle_transfer_puts_the_new_hair_on_the_head():
    from app.modules.ai_analysis import tryon

    template = tryon.extract_hairstyle(rgb(FACE_JPEG))
    assert set(template.anchors) == {"left_eye", "right_eye", "forehead", "chin"}
    assert template.rgba.shape[2] == 4 and (template.rgba[..., 3] > 200).sum() > 2000
    template = tryon.decode(tryon.encode(template), template.anchors)  # survives storage
    user = sample_portrait()
    out = tryon.apply_hairstyle(user, template)
    face = engine.models.faces(user)[0].points[:, :2]
    # Above the forehead the picture changed (new hair), the mouth area did not.
    top = int(face[10, 1]) - 10
    x0, x1 = int(face[234, 0]), int(face[454, 0])
    assert np.abs(out[max(0, top - 40):top, x0:x1].astype(int) - user[max(0, top - 40):top, x0:x1].astype(int)).mean() > 10
    mouth = (slice(int(face[13, 1]) - 5, int(face[14, 1]) + 5), slice(int(face[61, 0]), int(face[291, 0])))
    assert np.abs(out[mouth].astype(int) - user[mouth].astype(int)).mean() < 4
    recoloured = tryon.apply_hairstyle(user, template, colour="#b03020")
    assert np.abs(recoloured.astype(int) - out.astype(int)).mean() > 0.5


def test_garment_transfer_fits_the_reference_garment_to_the_body():
    from app.modules.ai_analysis import tryon

    template = tryon.extract_garment(rgb(GARMENT_JPEG))
    assert set(template.anchors) == {"shoulder_l", "shoulder_r", "hip_l", "hip_r"}
    body = rgb(BODY_JPEG)
    out = tryon.apply_garment(body, template)
    pose = engine.models.poses(body)[0].points[:, :2]
    torso_y = int((pose[11, 1] + pose[23, 1]) / 2)
    cx = int((pose[11, 0] + pose[12, 0]) / 2)
    torso = (slice(torso_y - 20, torso_y + 20), slice(cx - 15, cx + 15))
    assert np.abs(out[torso].astype(int) - body[torso].astype(int)).mean() > 25  # the garment is there
    head = (slice(0, int(pose[0, 1])), slice(None))
    assert np.abs(out[head].astype(int) - body[head].astype(int)).mean() < 2  # the head is untouched


def test_extraction_refuses_photos_without_the_thing_to_cut_out():
    from app.modules.ai_analysis import tryon

    with pytest.raises(Unusable):
        tryon.extract_garment(rgb(FACE_JPEG))  # a head-and-shoulders photo has no hips
    with pytest.raises(Unusable):
        tryon.extract_hairstyle(np.full((600, 600, 3), 128, np.uint8))


def sample_portrait():
    from skimage import data as sample_images

    return sample_images.astronaut()


def test_tryon_library_flow_admin_creates_approves_customer_tries(client, owner, uploads, db):  # noqa: F811
    headers = english(client)
    created = client.post(f"{API}/admin/tryon-items", data={"kind": "hairstyle", "title_en": "Natural curls", "title_ar": "تجعيدات طبيعية",
                          "licence": "Test fixture, CC BY 4.0"}, files={"file": ("ref.jpg", FACE_JPEG, "image/jpeg")}, headers=owner)
    assert created.status_code == 201, created.text
    item = created.json()
    assert item["content_status"] == "draft"
    cutout = client.get(f"{API}/admin/tryon-items/{item['id']}/image", headers=owner)
    assert cutout.headers["content-type"] == "image/png" and cutout.content[:4] == b"\x89PNG"
    # Drafts are invisible to customers.
    assert client.get(f"{API}/tryon/items", params={"kind": "hairstyle"}, headers=headers).json() == []
    approve = {"content_status": "approved", "tags": {"face_shape": ["oval", "round"]}}
    assert client.patch(f"{API}/admin/tryon-items/{item['id']}", json=approve, headers=owner).status_code == 200
    listed = client.get(f"{API}/tryon/items", params={"kind": "hairstyle"}, headers=headers).json()
    assert [i["title"] for i in listed] == ["Natural curls"]

    face = photo_id(client, headers, FACE_JPEG, "face")
    preview = client.post(f"{API}/previews/hairstyle", json={"image_id": face, "item_id": item["id"], "colour": "#5a3825"}, headers=headers)
    assert preview.status_code == 200 and preview.content[:2] == b"\xff\xd8"
    # A hairstyle cannot be used as a garment.
    body = photo_id(client, headers, BODY_JPEG, "full_body")
    assert client.post(f"{API}/previews/garment", json={"image_id": body, "item_id": item["id"]}, headers=headers).status_code == 404

    garment = client.post(f"{API}/admin/tryon-items", data={"kind": "garment", "title_en": "Denim swimsuit", "title_ar": "ثوب سباحة",
                          "licence": "Test fixture", "category": "swimwear"}, files={"file": ("g.jpg", GARMENT_JPEG, "image/jpeg")}, headers=owner).json()
    client.patch(f"{API}/admin/tryon-items/{garment['id']}", json={"content_status": "approved"}, headers=owner)
    fitted = client.post(f"{API}/previews/garment", json={"image_id": body, "item_id": garment["id"]}, headers=headers)
    assert fitted.status_code == 200 and fitted.headers["cache-control"] == "no-store"
    # Customers cannot manage the library.
    assert client.get(f"{API}/admin/tryon-items", headers=headers).status_code == 403
    bad = client.post(f"{API}/admin/tryon-items", data={"kind": "garment", "title_en": "x", "title_ar": "x", "licence": "xxx"},
                      files={"file": ("f.jpg", FACE_JPEG, "image/jpeg")}, headers=owner)
    assert bad.status_code == 422 and bad.json()["error"]["code"] == "photo_not_analysable"
