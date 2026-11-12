"""Photo-based face-shape and body-shape analysis.

STATUS: INDICATIVE. The geometry comes from MediaPipe landmarks and masks. The
rules that turn measurements into a shape are DRAFT prototypes written by the
development team from common styling conventions, calibrated by eye on a
handful of public photos. Accuracy has NOT been measured: that needs photos
labelled by the client's consultants (open decision, Feature List row 64).
All constants are in the PROTOTYPES tables below so they can be recalibrated
without touching the measuring code.

Classification is nearest-prototype: each shape has an expected value and a
tolerance per measurement; the score is a Gaussian likelihood, normalised over
shapes. The top score is returned as `confidence`, and results under
LOW_CONFIDENCE are flagged so the app can suggest the questionnaire as well.
"""

from dataclasses import dataclass, field

import cv2
import numpy as np

from app.modules.ai_analysis import engine

LOW_CONFIDENCE = 0.45


class Unusable(Exception):
    """The photo cannot be analysed; `reasons` are codes the app can explain."""

    def __init__(self, *reasons: str, measurements: dict | None = None):
        super().__init__(", ".join(reasons))
        self.reasons = list(reasons)
        self.measurements = measurements or {}


@dataclass
class ShapeResult:
    profile_key: str
    confidence: float
    scores: dict[str, float]
    measurements: dict[str, float]
    notes: list[str] = field(default_factory=list)


def classify(features: dict[str, float], prototypes: dict, tolerance: dict) -> tuple[str, float, dict]:
    log_likelihood = {}
    for shape, expected in prototypes.items():
        z = [(features[k] - v) / tolerance[k] for k, v in expected.items()]
        log_likelihood[shape] = -0.5 * float(np.sum(np.square(z)))
    top = max(log_likelihood.values())
    weights = {k: np.exp(v - top) for k, v in log_likelihood.items()}
    total = sum(weights.values())
    scores = {k: round(float(w / total), 3) for k, w in weights.items()}
    winner = max(scores, key=scores.get)
    return winner, scores[winner], scores


# ---------------------------------------------------------------- face

# MediaPipe face mesh indices.
FOREHEAD_TOP, CHIN = 10, 152
CHEEK_L, CHEEK_R = 234, 454
TEMPLE_L, TEMPLE_R = 54, 284
JAW_L, JAW_R = 172, 397

MAX_YAW, MAX_PITCH = 12.0, 18.0  # degrees; turned faces distort widths

FACE_TOLERANCE = {"length_ratio": 0.06, "jaw_ratio": 0.04, "taper": 0.05, "jaw_angle": 6.0, "chin_angle": 8.0}
FACE_PROTOTYPES = {
    #           face length / cheekbone width, jaw / cheekbones, (forehead - jaw) / cheekbones, angle at jaw corner, angle at chin
    "oval": {"length_ratio": 1.30, "jaw_ratio": 0.78, "taper": 0.07, "jaw_angle": 138, "chin_angle": 105},
    "round": {"length_ratio": 1.16, "jaw_ratio": 0.86, "taper": 0.01, "jaw_angle": 138, "chin_angle": 115},
    "square": {"length_ratio": 1.18, "jaw_ratio": 0.88, "taper": 0.00, "jaw_angle": 126, "chin_angle": 118},
    "heart": {"length_ratio": 1.26, "jaw_ratio": 0.74, "taper": 0.16, "jaw_angle": 140, "chin_angle": 95},
    "oblong": {"length_ratio": 1.42, "jaw_ratio": 0.80, "taper": 0.04, "jaw_angle": 134, "chin_angle": 105},
}


def _angle(a: np.ndarray, b: np.ndarray, c: np.ndarray) -> float:
    v1, v2 = a - b, c - b
    cos = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))
    return float(np.degrees(np.arccos(np.clip(cos, -1, 1))))


def single_face(rgb: np.ndarray) -> engine.Face:
    faces = engine.models.faces(rgb)
    if not faces:
        raise Unusable("no_face")
    if len(faces) > 1:
        raise Unusable("multiple_faces")
    face = faces[0]
    if abs(face.yaw) > MAX_YAW or abs(face.pitch) > MAX_PITCH:
        raise Unusable("face_not_frontal", measurements={"yaw": round(face.yaw, 1), "pitch": round(face.pitch, 1)})
    return face


def face_measurements(face: engine.Face) -> dict[str, float]:
    p = face.points[:, :2]

    def dist(a, b):
        return float(np.linalg.norm(p[a] - p[b]))

    cheeks = dist(CHEEK_L, CHEEK_R)
    jaw = dist(JAW_L, JAW_R)
    return {
        "length_ratio": dist(FOREHEAD_TOP, CHIN) / cheeks,
        "jaw_ratio": jaw / cheeks,
        "taper": (dist(TEMPLE_L, TEMPLE_R) - jaw) / cheeks,
        "jaw_angle": (_angle(p[CHEEK_L], p[JAW_L], p[CHIN]) + _angle(p[CHEEK_R], p[JAW_R], p[CHIN])) / 2,
        "chin_angle": _angle(p[JAW_L], p[CHIN], p[JAW_R]),
    }


def analyse_face_shape(rgb: np.ndarray) -> ShapeResult:
    face = single_face(rgb)
    features = face_measurements(face)
    winner, confidence, scores = classify(features, FACE_PROTOTYPES, FACE_TOLERANCE)
    measurements = {k: round(v, 3) for k, v in features.items()} | {"yaw": round(face.yaw, 1), "pitch": round(face.pitch, 1)}
    notes = ["low_confidence"] if confidence < LOW_CONFIDENCE else []
    return ShapeResult(winner, confidence, scores, measurements, notes)


# ---------------------------------------------------------------- body

# MediaPipe pose indices.
NOSE = 0
SHOULDER_L, SHOULDER_R, ELBOW_L, ELBOW_R, WRIST_L, WRIST_R = 11, 12, 13, 14, 15, 16
HIP_L, HIP_R, KNEE_L, KNEE_R, ANKLE_L, ANKLE_R = 23, 24, 25, 26, 27, 28
REQUIRED = (NOSE, SHOULDER_L, SHOULDER_R, HIP_L, HIP_R, KNEE_L, KNEE_R)
MIN_VISIBILITY = 0.6
MAX_SHOULDER_TILT = 0.12  # height difference / shoulder width; above this the person is turned or leaning
MIN_FRONTAL = 0.55  # shoulder width / torso length; side-on photos fall below this

BODY_TOLERANCE = {"shoulder_hip": 0.08, "waist_hip": 0.07, "waist_shoulder": 0.07}
BODY_PROTOTYPES = {
    # Front-view silhouette widths (not circumferences, which one photo cannot give).
    "hourglass": {"shoulder_hip": 1.00, "waist_hip": 0.62, "waist_shoulder": 0.62},
    "pear": {"shoulder_hip": 0.85, "waist_hip": 0.66, "waist_shoulder": 0.78},
    "inverted_triangle": {"shoulder_hip": 1.18, "waist_hip": 0.78, "waist_shoulder": 0.66},
    "rectangle": {"shoulder_hip": 1.00, "waist_hip": 0.80, "waist_shoulder": 0.80},
    "apple": {"shoulder_hip": 1.00, "waist_hip": 0.92, "waist_shoulder": 0.92},
}


def _arm_x(p: np.ndarray, side: tuple[int, int, int], y: float) -> float | None:
    """x of the arm's centreline (shoulder-elbow-wrist) at height y, if the arm spans it."""
    for a, b in ((side[0], side[1]), (side[1], side[2])):
        (x0, y0), (x1, y1) = p[a], p[b]
        if min(y0, y1) <= y <= max(y0, y1) and y1 != y0:
            return float(x0 + (y - y0) * (x1 - x0) / (y1 - y0))
    return None


def _torso_run(row: np.ndarray, centre: int, max_gap: int) -> tuple[int, int] | None:
    """Span of the body at one row. Starts at the centre (or, below the crotch,
    the two legs either side of it) and stops at the first background gap."""
    width = row.shape[0]
    if not row[centre]:
        left = np.flatnonzero(row[max(0, centre - max_gap):centre])
        right = np.flatnonzero(row[centre:min(width, centre + max_gap)])
        if left.size == 0 or right.size == 0:
            return None
        lo, hi = max(0, centre - max_gap) + int(left[-1]), centre + int(right[0])
    else:
        lo = hi = centre
    while lo > 0 and row[lo - 1]:
        lo -= 1
    while hi < width - 1 and row[hi + 1]:
        hi += 1
    return lo, hi


ARMS = ((SHOULDER_L, ELBOW_L, WRIST_L), (SHOULDER_R, ELBOW_R, WRIST_R))
MIN_CLEAN_ROWS = 5  # of 17 per band


def analyse_body_shape(rgb: np.ndarray) -> ShapeResult:
    poses = engine.models.poses(rgb)
    if not poses:
        raise Unusable("no_person")
    if len(poses) > 1:
        raise Unusable("multiple_people")
    pose = poses[0]
    p = pose.points[:, :2]
    if (pose.visibility[list(REQUIRED)] < MIN_VISIBILITY).any():
        raise Unusable("body_not_fully_visible")

    shoulder_mid, hip_mid = (p[SHOULDER_L] + p[SHOULDER_R]) / 2, (p[HIP_L] + p[HIP_R]) / 2
    torso = float(hip_mid[1] - shoulder_mid[1])
    shoulder_joints = float(np.linalg.norm(p[SHOULDER_L] - p[SHOULDER_R]))
    if torso <= 0:
        raise Unusable("body_not_upright")
    tilt = abs(p[SHOULDER_L][1] - p[SHOULDER_R][1]) / shoulder_joints
    frontal = shoulder_joints / torso
    if tilt > MAX_SHOULDER_TILT or frontal < MIN_FRONTAL:
        raise Unusable("body_not_frontal", measurements={"tilt": round(tilt, 3), "frontal": round(frontal, 3)})

    # Arms must hang down: hands on hips or raised arms change the outline.
    if any((p[w][1] - shoulder_mid[1]) / torso < 0.8 for w in (WRIST_L, WRIST_R)):
        raise Unusable("arms_not_down")
    person = pose.mask
    centre = int(round((shoulder_mid[0] + hip_mid[0]) / 2))
    max_gap = int(0.4 * shoulder_joints)

    def width(t: float, check_arms: bool = True) -> int | None:
        """Body width at a fraction t of the torso below the shoulders, or None
        when it cannot be measured cleanly (an arm or hand touches the body there)."""
        y = shoulder_mid[1] + t * torso
        run = _torso_run(person[int(np.clip(round(y), 0, person.shape[0] - 1))], centre, max_gap)
        if run is None:
            return None
        if check_arms:
            for side in ARMS:
                x = _arm_x(p, side, y)
                if x is not None and run[0] <= x <= run[1]:
                    return None
                wrist = p[side[2]]
                hand = 0.15 * shoulder_joints
                if abs(wrist[1] - y) < hand and run[0] - hand <= wrist[0] <= run[1] + hand:
                    return None  # a hand at the body's edge, e.g. on the hip
        return run[1] - run[0] + 1

    # The shoulder line includes the deltoids, so arms are not excluded there.
    shoulders = max((width(t, check_arms=False) or 0) for t in (0.04, 0.08, 0.12))
    waist_rows = [w for w in (width(t) for t in np.linspace(0.45, 0.85, 17)) if w]
    hip_rows = [w for w in (width(t) for t in np.linspace(0.9, 1.3, 17)) if w]
    counts = {"waist_rows": len(waist_rows), "hip_rows": len(hip_rows)}
    if len(waist_rows) < MIN_CLEAN_ROWS or len(hip_rows) < MIN_CLEAN_ROWS:
        raise Unusable("arms_touching_body", measurements=counts)
    waist, hips = min(waist_rows), max(hip_rows)
    if min(shoulders, waist, hips) < 0.3 * shoulder_joints:
        raise Unusable("silhouette_unclear", measurements={"shoulders": shoulders, "waist": waist, "hips": hips})

    features = {"shoulder_hip": shoulders / hips, "waist_hip": waist / hips, "waist_shoulder": waist / shoulders}
    winner, confidence, scores = classify(features, BODY_PROTOTYPES, BODY_TOLERANCE)
    notes = ["low_confidence"] if confidence < LOW_CONFIDENCE else []
    measurements = {k: round(v, 3) for k, v in features.items()} | {
        "shoulders_px": shoulders, "waist_px": waist, "hips_px": hips, "frontal": round(frontal, 3)
    } | counts
    return ShapeResult(winner, confidence, scores, measurements, notes)
