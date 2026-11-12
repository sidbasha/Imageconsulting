import cv2
import numpy as np
import pytest
from skimage import data as sample_images
from sqlalchemy import func, select

from app.integrations.storage import LocalStorage, get_storage
from app.modules.assessments import content
from app.modules.assessments.models import Assessment, AssessmentImage, Questionnaire
from app.modules.image_processing import quality
from app.tests.conftest import ELIGIBLE, login

API = "/api/v1"
STYLE_ROMANTIC = {"line": "curved", "shape": "fitted", "colour": "pastels", "texture": "delicate", "pattern": "floral"}
FACE_ROUND = {"length": "equal", "widest": "cheekbones", "jaw": "soft"}


def answer(client, headers, key, answers):
    return client.post(f"{API}/assessments/{key}/responses", json={"answers": answers}, headers=headers)


def english(client):
    client.post(f"{API}/auth/register", json={"email": "en@example.com", "password": "a-long-enough-password", "full_name": "En", **ELIGIBLE})
    return login_as(client, "en@example.com", "a-long-enough-password")


def login_as(client, email, password):
    token = client.post(f"{API}/auth/login", json={"email": email, "password": password}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# ---------- questionnaires ----------

def test_seeded_content_is_complete_in_both_languages(db):
    questionnaires = db.scalars(select(Questionnaire)).all()
    assert {q.key for q in questionnaires} == {"onboarding_quiz", "style", "body_shape", "face_shape", "seasonal_color"}

    def bilingual(value):
        return isinstance(value, dict) and all(value.get(lang) for lang in ("en", "ar"))

    for q in questionnaires:
        assert q.content_status == "draft"  # must be reviewed by the client before release
        assert bilingual(q.title) and bilingual(q.intro)
        profile_keys = {p.key for p in q.profiles}
        for question in q.questions:
            assert bilingual(question.prompt) and len(question.options) >= 2
            for option in question.options:
                assert bilingual(option.label)
                assert set(option.scores) <= profile_keys, f"{q.key}.{question.key}.{option.key} scores an unknown profile"
        for profile in q.profiles:
            assert bilingual(profile.title) and bilingual(profile.summary)
            for items in profile.advice.values():
                assert items["en"] and len(items["en"]) == len(items["ar"])


def test_every_profile_can_be_reached(db):
    """No result may be impossible to get: try every combination of answers."""
    from itertools import product

    from app.modules.assessments.service import score

    for q in db.scalars(select(Questionnaire)):
        if not q.profiles:
            continue
        reached = set()
        for combo in product(*[[o.key for o in question.options] for question in q.questions]):
            reached.add(score(q, dict(zip([question.key for question in q.questions], combo)))[1])
        assert reached == {p.key for p in q.profiles}, q.key


def test_questionnaire_is_served_in_the_users_language(client, customer):
    arabic = client.get(f"{API}/assessments/style", headers=customer).json()  # this customer's language is Arabic
    assert arabic["title"] == "تقييم الأسلوب الشخصي"
    assert [q["key"] for q in arabic["questions"]] == ["line", "shape", "colour", "texture", "pattern"]
    assert "scores" not in arabic["questions"][0]["options"][0]  # scoring is never sent to the client
    assert client.get(f"{API}/assessments/style", headers=english(client)).json()["title"] == "Personal style assessment"


def test_submit_scores_and_returns_the_profile(client):
    headers = english(client)
    response = answer(client, headers, "style", STYLE_ROMANTIC)
    assert response.status_code == 201
    body = response.json()
    assert body["profile"]["key"] == "romantic" and body["basis"] == "self_assessment"
    assert len(body["profile"]["advice"]["outfits"]) == 3
    assert body["answers"][0] == {"question": "Which lines do you prefer in clothes?", "answer": "Soft, curved lines"}
    assert client.get(f"{API}/assessments/style/result", headers=headers).json()["profile"]["key"] == "romantic"


def test_majority_wins_and_ties_go_to_the_first_listed_profile(client):
    headers = english(client)
    mixed = {**STYLE_ROMANTIC, "line": "sharp", "shape": "oversized"}  # 3 romantic, 2 dramatic
    assert answer(client, headers, "style", mixed).json()["profile"]["key"] == "romantic"
    # Colour: gold + green veins (warm), light, bright -> spring
    spring = {"jewellery": "gold", "veins": "green", "depth": "light", "clarity": "bright"}
    result = answer(client, headers, "seasonal_color", spring).json()
    assert result["profile"]["key"] == "spring" and len(result["profile"]["palette"]) == 6
    winter = {"jewellery": "silver", "veins": "blue", "depth": "deep", "clarity": "bright"}
    assert answer(client, headers, "seasonal_color", winter).json()["profile"]["key"] == "winter"


def test_incomplete_or_invalid_answers_are_rejected_and_nothing_is_saved(client, db):
    headers = english(client)
    response = answer(client, headers, "style", {"line": "curved", "shape": "nonsense", "bogus": "x"})
    assert response.status_code == 422
    detail = response.json()["error"]["detail"]
    assert detail == {"missing": ["colour", "pattern", "texture"], "unknown": ["bogus"], "invalid_option": ["shape"]}
    assert db.scalar(select(func.count()).select_from(Assessment)) == 0
    assert client.get(f"{API}/assessments/style/result", headers=headers).json() is None


def test_retaking_keeps_history_and_shows_the_latest(client, db):
    headers = english(client)
    answer(client, headers, "style", STYLE_ROMANTIC)
    answer(client, headers, "style", {k: v for k, v in zip(STYLE_ROMANTIC, ["straight", "tailored", "neutrals", "smooth", "subtle"])})
    assert client.get(f"{API}/assessments/style/result", headers=headers).json()["profile"]["key"] == "classic"
    assert db.scalar(select(func.count()).select_from(Assessment)) == 2


def test_onboarding_quiz_saves_answers_without_a_profile(client):
    headers = english(client)
    quiz = {"personality": "calm", "preference": "tailored", "challenge": "colour", "occasion": "work"}
    body = answer(client, headers, "onboarding_quiz", quiz).json()
    assert body["profile"] is None and len(body["answers"]) == 4


def test_results_are_private_to_each_user(client, customer):
    answer(client, english(client), "style", STYLE_ROMANTIC)
    assert client.get(f"{API}/assessments/style/result", headers=customer).json() is None
    assert client.get(f"{API}/assessments/style").status_code == 401


def test_list_shows_completion(client):
    headers = english(client)
    answer(client, headers, "face_shape", FACE_ROUND)
    listing = {item["key"]: item for item in client.get(f"{API}/assessments", headers=headers).json()}
    assert len(listing) == 5
    assert listing["face_shape"]["result"] == "Round" and listing["style"]["completed_at"] is None


# ---------- release control applies to real endpoints now ----------

def test_switching_a_feature_off_blocks_its_questionnaire_and_keeps_the_data(client, release, db):
    headers = english(client)
    answer(client, headers, "face_shape", FACE_ROUND)
    # Eyewear and hair depend on face shape, so all three go off together.
    off = {"phase1.face_shape": False, "phase1.eyewear": False, "phase1.hair_preview": False}
    assert release(features=off).status_code == 201

    assert client.get(f"{API}/assessments/face_shape", headers=headers).status_code == 404
    assert answer(client, headers, "face_shape", FACE_ROUND).status_code == 404
    assert client.get(f"{API}/recommendations/eyewear", headers=headers).status_code == 404
    assert "face_shape" not in [i["key"] for i in client.get(f"{API}/assessments", headers=headers).json()]
    assert client.get(f"{API}/assessments/style", headers=headers).status_code == 200  # others unaffected

    # Mandatory case 10: the result is still there when the feature comes back.
    assert db.scalar(select(func.count()).select_from(Assessment)) == 1
    assert release(features={k: True for k in off}).status_code == 201
    assert client.get(f"{API}/assessments/face_shape/result", headers=headers).json()["profile"]["key"] == "round"


def test_disabling_phase1_blocks_everything(client, release):
    headers = english(client)
    assert release(phases={"phase1": False}).status_code == 201
    assert client.get(f"{API}/assessments", headers=headers).json() == []
    assert client.get(f"{API}/assessments/style", headers=headers).status_code == 404
    assert client.get(f"{API}/recommendations/outfits", headers=headers).status_code == 404
    assert client.get(f"{API}/assessment-images", headers=headers).status_code == 404


# ---------- recommendations ----------

def test_recommendations_come_from_the_users_results(client):
    headers = english(client)
    empty = client.get(f"{API}/recommendations/outfits", headers=headers).json()
    assert empty["sections"] == [] and [m["key"] for m in empty["missing"]] == ["style", "body_shape", "seasonal_color"]

    answer(client, headers, "style", STYLE_ROMANTIC)
    answer(client, headers, "face_shape", FACE_ROUND)
    outfits = client.get(f"{API}/recommendations/outfits", headers=headers).json()
    assert [(s["source"], s["result"]) for s in outfits["sections"]] == [("style", "Romantic")]
    assert [m["key"] for m in outfits["missing"]] == ["body_shape", "seasonal_color"]

    eyewear = client.get(f"{API}/recommendations/eyewear", headers=headers).json()
    assert eyewear["sections"][0]["items"][0].startswith("Choose rectangular or square frames")
    assert client.get(f"{API}/recommendations/hair", headers=headers).json()["sections"][0]["result"] == "Round"
    assert client.get(f"{API}/recommendations/shoes", headers=headers).status_code == 404


def test_recommendation_categories_point_at_real_features_and_questionnaires(db):
    from app.modules.phase_management.catalog import FEATURES

    known = {f[1] for f in FEATURES}
    keys = set(db.scalars(select(Questionnaire.key)))
    for feature, sources in content.RECOMMENDATION_CATEGORIES.values():
        assert feature in known and set(sources) <= keys
    assert {q["feature"] for q in content.QUESTIONNAIRES} <= known


# ---------- photos ----------

def jpeg(image) -> bytes:
    ok, encoded = cv2.imencode(".jpg", cv2.cvtColor(image, cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 92])
    assert ok
    return encoded.tobytes()


@pytest.fixture(scope="module")
def portrait():
    """A real head-and-shoulders photo with one face (NASA portrait bundled with scikit-image)."""
    return cv2.resize(sample_images.astronaut()[0:400, 60:460], (600, 600), interpolation=cv2.INTER_CUBIC)


@pytest.fixture
def uploads(client, tmp_path):
    storage = LocalStorage(str(tmp_path))
    client.app.dependency_overrides[get_storage] = lambda: storage
    return tmp_path


def upload(client, headers, data, kind="face", consent="true", content_type="image/jpeg"):
    return client.post(
        f"{API}/assessment-images",
        files={"file": ("photo.jpg", data, content_type)},
        data={"kind": kind, "consent": consent},
        headers=headers,
    )


def test_quality_gate_measurements(portrait):
    good = quality.check(jpeg(portrait), "face")
    assert good.ok and good.faces == 1 and good.face_fraction > quality.MIN_FACE_FRACTION

    assert quality.check(jpeg(cv2.GaussianBlur(portrait, (0, 0), 9)), "face").reasons == ["too_blurry"]
    assert "too_dark" in quality.check(jpeg((portrait * 0.12).astype(np.uint8)), "face").reasons
    washed = np.clip(portrait.astype(np.int16) + 190, 0, 255).astype(np.uint8)
    assert "too_bright" in quality.check(jpeg(washed), "face").reasons
    assert "too_small" in quality.check(jpeg(cv2.resize(portrait, (200, 200))), "face").reasons
    assert quality.check(b"this is not an image", "face").reasons == ["not_an_image"]

    scenery = cv2.resize(sample_images.coffee(), (900, 600))  # a sharp, well-lit photo with no person in it
    assert quality.check(jpeg(scenery), "face").reasons == ["no_face"]
    assert quality.check(jpeg(scenery), "full_body").ok  # face rules apply to face photos only

    # The uncropped original: sharp and well lit, but the face fills too little of the frame.
    distant = cv2.resize(sample_images.astronaut(), (768, 768), interpolation=cv2.INTER_CUBIC)
    assert quality.check(jpeg(distant), "face").reasons == ["face_too_small"]


def test_upload_stores_the_photo_privately_with_consent(client, db, uploads, portrait):
    headers = english(client)
    data = jpeg(portrait)
    response = upload(client, headers, data)
    assert response.status_code == 201, response.text
    body = response.json()
    assert (body["width"], body["height"], body["size_bytes"]) == (600, 600, len(data))
    assert "storage_key" not in body and body["consent_at"]

    image = db.scalar(select(AssessmentImage))
    stored = uploads / image.storage_key
    assert stored.read_bytes() == data
    assert "photo.jpg" not in image.storage_key  # the client's file name is never used
    assert [i["id"] for i in client.get(f"{API}/assessment-images", headers=headers).json()] == [body["id"]]


def test_upload_is_refused_without_consent_or_with_a_bad_file(client, db, uploads, portrait):
    headers = english(client)
    data = jpeg(portrait)
    assert upload(client, headers, data, consent="false").json()["error"]["code"] == "consent_required"
    assert upload(client, headers, data, kind="passport").json()["error"]["code"] == "invalid_image_kind"
    assert upload(client, headers, data, content_type="image/gif").status_code == 415
    assert upload(client, headers, b"<svg/>").json()["error"]["detail"]["reasons"] == ["not_an_image"]
    blurry = upload(client, headers, jpeg(cv2.GaussianBlur(portrait, (0, 0), 9)))
    assert blurry.status_code == 422 and blurry.json()["error"]["detail"]["reasons"] == ["too_blurry"]
    assert upload(client, {}, data).status_code == 401

    assert db.scalar(select(func.count()).select_from(AssessmentImage)) == 0
    assert not any(p.is_file() for p in uploads.rglob("*"))  # nothing rejected is ever written


def test_oversized_upload_is_rejected(client, uploads, monkeypatch):
    from app.modules.assessments import service

    monkeypatch.setattr(service, "MAX_UPLOAD_BYTES", 1000)
    assert upload(client, english(client), b"x" * 5000).status_code == 413


def test_user_can_delete_her_photo_and_only_hers(client, customer, db, uploads, portrait):
    headers = english(client)
    image_id = upload(client, headers, jpeg(portrait)).json()["id"]
    assert client.delete(f"{API}/assessment-images/{image_id}", headers=customer).status_code == 404
    assert client.get(f"{API}/assessment-images", headers=customer).json() == []

    assert client.delete(f"{API}/assessment-images/{image_id}", headers=headers).status_code == 204
    assert client.get(f"{API}/assessment-images", headers=headers).json() == []
    assert not any(p.is_file() for p in uploads.rglob("*"))  # the file itself is gone
    assert db.scalar(select(AssessmentImage)).deleted_at is not None
    assert client.delete(f"{API}/assessment-images/{image_id}", headers=headers).status_code == 404


def test_storage_keys_cannot_escape_the_storage_root(tmp_path):
    with pytest.raises(ValueError):
        LocalStorage(str(tmp_path)).put("../outside.txt", b"x")


def test_user_sees_her_own_photo_only(client, customer, uploads, portrait):
    headers = english(client)
    data = jpeg(portrait)
    image_id = upload(client, headers, data).json()["id"]
    own = client.get(f"{API}/assessment-images/{image_id}/file", headers=headers)
    assert own.status_code == 200 and own.content == data
    assert own.headers["content-type"] == "image/jpeg" and "no-store" in own.headers["cache-control"]
    assert client.get(f"{API}/assessment-images/{image_id}/file", headers=customer).status_code == 404
    assert client.delete(f"{API}/assessment-images/{image_id}", headers=headers).status_code == 204
    assert client.get(f"{API}/assessment-images/{image_id}/file", headers=headers).status_code == 404
