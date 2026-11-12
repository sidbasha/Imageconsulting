"""Garment and hairstyle try-on by transfer from a reference photo (rows 11, 12).

How it works
- An administrator uploads a photo of a model wearing the garment, or with
  the hairstyle. The garment (clothes class) or the hair (hair class) is cut
  out with the segmentation model, together with anchor points from the pose
  or face landmarks, and kept as a transparent template.
- On the user's photo the same anchors are found, the template is warped onto
  them (affine fit by least squares), and composited: for hair, the user's own
  hair outside the new style is painted over from its surroundings; for
  garments, the user's hair, face and hands stay in front.

What it is not
- Not a generative try-on. The garment keeps the drape, folds and pose of the
  reference photo; it is fitted, not re-simulated, so loose or very different
  poses look pasted on. A generative service would look more natural but means
  sending user photos to a third party, an open privacy decision (row 65).
- The user's own clothes are not removed: a garment smaller than what she
  wears shows the old one around it. Shorter hairstyles rely on inpainting,
  which blurs the background where long hair was.

Reference photos must be ones the client has the rights to use (models,
brand imagery). The template keeps a licence note.
"""

from dataclasses import dataclass

import cv2
import numpy as np

from app.modules.ai_analysis import engine
from app.modules.ai_analysis.colour import LEFT_EYE, RIGHT_EYE
from app.modules.ai_analysis.previews import parse_colour, recolour
from app.modules.ai_analysis.shapes import (
    ELBOW_L,
    ELBOW_R,
    HIP_L,
    HIP_R,
    MIN_VISIBILITY,
    SHOULDER_L,
    SHOULDER_R,
    WRIST_L,
    WRIST_R,
    Unusable,
    single_face,
)

FOREHEAD, CHIN = 10, 152
PAD = 0.15  # template crop margin, as a share of its size


@dataclass
class Template:
    rgba: np.ndarray  # cropped template, RGBA uint8
    anchors: dict[str, list[float]]  # name -> [x, y] in template coordinates


def _crop(rgb: np.ndarray, alpha: np.ndarray, anchors: dict[str, np.ndarray]) -> Template:
    ys, xs = np.nonzero(alpha > 8)
    if xs.size == 0:
        raise Unusable("nothing_to_extract")
    pts = np.array(list(anchors.values()))
    x0, x1 = min(xs.min(), pts[:, 0].min()), max(xs.max(), pts[:, 0].max())
    y0, y1 = min(ys.min(), pts[:, 1].min()), max(ys.max(), pts[:, 1].max())
    pad_x, pad_y = int((x1 - x0) * PAD), int((y1 - y0) * PAD)
    x0, y0 = max(0, int(x0) - pad_x), max(0, int(y0) - pad_y)
    x1, y1 = min(rgb.shape[1], int(x1) + pad_x), min(rgb.shape[0], int(y1) + pad_y)
    rgba = np.dstack([rgb[y0:y1, x0:x1], alpha[y0:y1, x0:x1]]).astype(np.uint8)
    return Template(rgba, {k: [float(v[0] - x0), float(v[1] - y0)] for k, v in anchors.items()})


def _soft(mask: np.ndarray, erode: int = 1, blur: int = 5) -> np.ndarray:
    """0/1 mask to an 8-bit alpha with a slightly feathered edge."""
    m = mask.astype(np.uint8)
    if erode:
        m = cv2.erode(m, np.ones((3, 3), np.uint8), iterations=erode)
    k = blur | 1
    return (cv2.GaussianBlur(m.astype(np.float32), (k, k), 0) * 255).astype(np.uint8)


def _largest_component(mask: np.ndarray, near: np.ndarray | None = None) -> np.ndarray:
    count, labels, stats, _ = cv2.connectedComponentsWithStats(mask.astype(np.uint8), 8)
    if count <= 1:
        return mask.astype(np.uint8) * 0
    sizes = stats[1:, cv2.CC_STAT_AREA]
    keep = 1 + int(np.argmax(sizes))
    out = (labels == keep).astype(np.uint8)
    # Also keep other large pieces (e.g. a top and skirt split by a belt).
    for i, size in enumerate(sizes, start=1):
        if i != keep and size > 0.15 * sizes.max():
            out |= (labels == i).astype(np.uint8)
    return out


def _eye(points: np.ndarray, contour: list[int]) -> np.ndarray:
    return points[contour, :2].mean(axis=0)


def _face_anchors(rgb: np.ndarray) -> dict[str, np.ndarray]:
    p = single_face(rgb).points[:, :2]
    return {"left_eye": _eye(p, LEFT_EYE), "right_eye": _eye(p, RIGHT_EYE), "forehead": p[FOREHEAD], "chin": p[CHIN]}


def _body(rgb: np.ndarray) -> engine.Pose:
    poses = engine.models.poses(rgb)
    if not poses:
        raise Unusable("no_person")
    if len(poses) > 1:
        raise Unusable("multiple_people")
    pose = poses[0]
    if (pose.visibility[[SHOULDER_L, SHOULDER_R, HIP_L, HIP_R]] < MIN_VISIBILITY).any():
        raise Unusable("body_not_fully_visible")
    return pose


def _body_anchors(pose: engine.Pose) -> dict[str, np.ndarray]:
    p = pose.points[:, :2]
    return {"shoulder_l": p[SHOULDER_L], "shoulder_r": p[SHOULDER_R], "hip_l": p[HIP_L], "hip_r": p[HIP_R]}


# ---------------------------------------------------------------- extraction (admin)

def extract_hairstyle(rgb: np.ndarray) -> Template:
    anchors = _face_anchors(rgb)
    hair = engine.models.segment(rgb) == engine.HAIR
    hair = _largest_component(hair)
    if hair.sum() < 2000:
        raise Unusable("hair_not_visible")
    return _crop(rgb, _soft(hair, erode=1, blur=7), anchors)


def extract_garment(rgb: np.ndarray) -> Template:
    pose = _body(rgb)
    clothes = engine.models.segment(rgb) == engine.CLOTHES
    # Clothes on the body only: inside the person silhouette from the pose model.
    clothes &= pose.mask.astype(bool)
    clothes = _largest_component(clothes)
    if clothes.sum() < 0.01 * clothes.size:
        raise Unusable("clothes_not_visible")
    return _crop(rgb, _soft(clothes, erode=1, blur=5), _body_anchors(pose))


# ---------------------------------------------------------------- application (customer)

def _fit(template: Template, target: dict[str, np.ndarray], full_affine: bool) -> np.ndarray:
    names = list(template.anchors)
    src = np.float32([template.anchors[n] for n in names])
    dst = np.float32([target[n] for n in names])
    if full_affine:
        matrix, _ = cv2.estimateAffine2D(src, dst, method=cv2.LMEDS)
    else:
        matrix, _ = cv2.estimateAffinePartial2D(src, dst, method=cv2.LMEDS)  # rotation, scale, shift only
    if matrix is None:
        raise Unusable("cannot_fit")
    return matrix


def _warp(template: Template, matrix: np.ndarray, shape) -> tuple[np.ndarray, np.ndarray]:
    h, w = shape[:2]
    warped = cv2.warpAffine(template.rgba, matrix, (w, h), flags=cv2.INTER_LINEAR, borderValue=(0, 0, 0, 0))
    return warped[..., :3], warped[..., 3].astype(np.float32) / 255.0


def _match_light(rgb: np.ndarray, alpha: np.ndarray, reference: np.ndarray) -> np.ndarray:
    """Nudges the template's brightness toward the user's photo so it does not look pasted on."""
    lab = cv2.cvtColor(rgb.astype(np.float32) / 255.0, cv2.COLOR_RGB2LAB)
    ref = cv2.cvtColor(reference.astype(np.float32) / 255.0, cv2.COLOR_RGB2LAB)
    inside = alpha > 0.5
    if inside.sum() < 50:
        return rgb
    shift = 0.5 * (ref[..., 0].mean() - lab[..., 0][inside].mean()) * 0.5
    lab[..., 0] = np.clip(lab[..., 0] + shift, 0, 100)
    return np.clip(cv2.cvtColor(lab, cv2.COLOR_LAB2RGB) * 255 + 0.5, 0, 255).astype(np.uint8)


def _smooth_fill(image: np.ndarray, known: np.ndarray) -> np.ndarray:
    """Estimate of every pixel from the nearby `known` pixels (normalised
    convolution, coarse to fine; finer scales win where they have data)."""
    img = image.astype(np.float32)
    weight = known.astype(np.float32)
    if weight.sum() == 0:
        return img
    fill = np.broadcast_to(img[known.astype(bool)].mean(axis=0), img.shape).copy()
    for size in (201, 101, 51, 25):
        k = (size, size)
        w = cv2.GaussianBlur(weight, k, 0)
        est = cv2.GaussianBlur(img * weight[..., None], k, 0) / np.maximum(w, 1e-6)[..., None]
        ok = w > 0.02
        fill[ok] = est[ok]
    return fill


FACE_OVAL = [10, 338, 297, 332, 284, 251, 389, 356, 454, 323, 361, 288, 397, 365, 379, 378, 400, 377, 152, 148,
             176, 149, 150, 136, 172, 58, 132, 93, 234, 127, 162, 21, 54, 103, 67, 109]


def _head_area(points: np.ndarray, shape) -> np.ndarray:
    """The face outline, with its upper half raised to where a hairline would be."""
    oval = points[FACE_OVAL, :2].copy()
    eye_line = (points[33, 1] + points[263, 1]) / 2
    height = points[CHIN, 1] - points[FOREHEAD, 1]
    above = oval[:, 1] < eye_line
    oval[above, 1] -= 0.18 * height * (eye_line - oval[above, 1]) / max(eye_line - oval[:, 1].min(), 1)
    mask = np.zeros(shape[:2], np.uint8)
    cv2.fillPoly(mask, [np.round(oval).astype(np.int32)], 1)
    return mask


def _fill_removed_hair(image: np.ndarray, region: np.ndarray, background: np.ndarray, skin: np.ndarray,
                       head: np.ndarray) -> np.ndarray:
    """Paints over hair that the new style no longer covers: with skin tone
    inside the head outline (the forehead under former bangs), otherwise with
    the surrounding background. Smooth, so it reads as out of focus, not smeared."""
    bg_fill, skin_fill = _smooth_fill(image, background), _smooth_fill(image, skin)
    towards_skin = cv2.GaussianBlur(head.astype(np.float32), (21, 21), 0)
    fill = bg_fill * (1 - towards_skin[..., None]) + skin_fill * towards_skin[..., None]
    soft = cv2.GaussianBlur(region.astype(np.float32), (15, 15), 0)[..., None]
    return np.clip(image * (1 - soft) + fill * soft, 0, 255).astype(np.uint8)


def apply_hairstyle(user: np.ndarray, template: Template, colour: str | None = None) -> np.ndarray:
    face_points = single_face(user).points
    target = _face_anchors(user)
    matrix = _fit(template, target, full_affine=False)
    hair_rgb, alpha = _warp(template, matrix, user.shape)
    if colour:
        hair_rgb = recolour(hair_rgb, (alpha > 0.3).astype(np.uint8), parse_colour(colour), lightness_follow=0.6, texture=0.4)

    seg = engine.models.segment(user)
    old_hair = (seg == engine.HAIR).astype(np.uint8)
    # Paint over the user's own hair wherever the new style does not cover it.
    exposed = cv2.dilate(old_hair, np.ones((5, 5), np.uint8), iterations=2) & (alpha < 0.5).astype(np.uint8)
    kernel = np.ones((5, 5), np.uint8)
    background = cv2.erode((seg == engine.BACKGROUND).astype(np.uint8), kernel, iterations=2)
    skin = cv2.erode((seg == engine.FACE_SKIN).astype(np.uint8), kernel, iterations=2)
    head = _head_area(face_points, user.shape)
    base = _fill_removed_hair(user, exposed, background, skin, head) if exposed.any() else user.copy()
    # The face stays in front of hair that falls behind it (the template's own face area).
    face = (seg == engine.FACE_SKIN).astype(np.float32)
    face = cv2.GaussianBlur(cv2.erode(face, np.ones((7, 7), np.uint8)), (9, 9), 0)
    alpha = alpha * (1 - face * 0.85)
    out = base * (1 - alpha[..., None]) + _match_light(hair_rgb, alpha, user) * alpha[..., None]
    return np.clip(out, 0, 255).astype(np.uint8)


def apply_garment(user: np.ndarray, template: Template) -> np.ndarray:
    pose = _body(user)
    matrix = _fit(template, _body_anchors(pose), full_affine=True)
    garment, alpha = _warp(template, matrix, user.shape)
    garment = _match_light(garment, alpha, user)

    # Keep hair, face and hands in front of the garment.
    seg = engine.models.segment(user)
    front = np.isin(seg, (engine.HAIR, engine.FACE_SKIN)).astype(np.uint8)
    p = pose.points[:, :2]
    hands = np.zeros(user.shape[:2], np.uint8)
    width = float(np.linalg.norm(p[SHOULDER_L] - p[SHOULDER_R]))
    for elbow, wrist in ((ELBOW_L, WRIST_L), (ELBOW_R, WRIST_R)):
        if pose.visibility[wrist] >= MIN_VISIBILITY:
            cv2.line(hands, tuple(int(v) for v in p[elbow]), tuple(int(v) for v in p[wrist]), 1, max(2, int(0.22 * width)))
            cv2.circle(hands, tuple(int(v) for v in p[wrist]), max(2, int(0.18 * width)), 1, -1)
    front |= hands & (seg == engine.BODY_SKIN).astype(np.uint8)
    keep = cv2.GaussianBlur(front.astype(np.float32), (5, 5), 0)
    alpha = alpha * (1 - keep)
    out = user * (1 - alpha[..., None]) + garment * alpha[..., None]
    return np.clip(out, 0, 255).astype(np.uint8)


# ---------------------------------------------------------------- storage format

def encode(template: Template) -> bytes:
    ok, buf = cv2.imencode(".png", cv2.cvtColor(template.rgba, cv2.COLOR_RGBA2BGRA))
    if not ok:
        raise RuntimeError("could not encode template")
    return buf.tobytes()


def decode(data: bytes, anchors: dict) -> Template:
    bgra = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_UNCHANGED)
    return Template(cv2.cvtColor(bgra, cv2.COLOR_BGRA2RGBA), anchors)
