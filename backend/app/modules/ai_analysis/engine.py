"""Loads the on-device vision models (Google MediaPipe Tasks, Apache 2.0) once per process.

Models are files, not code, and are not kept in git. Fetch them with

    python -m app.cli fetch-models

which downloads them into settings.model_dir and checks their SHA-256.

MediaPipe task objects are not safe to share between threads, so each call
holds a per-model lock. Inference is CPU-only and takes tens of milliseconds
per photo at the sizes used here.
"""

import atexit
import hashlib
import threading
import urllib.request
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

from app.config.settings import get_settings

_BASE = "https://storage.googleapis.com/mediapipe-models"
MODELS = {
    "face_landmarker": (
        f"{_BASE}/face_landmarker/face_landmarker/float16/1/face_landmarker.task",
        "64184e229b263107bc2b804c6625db1341ff2bb731874b0bcc2fe6544e0bc9ff",
    ),
    "pose_landmarker": (
        f"{_BASE}/pose_landmarker/pose_landmarker_full/float16/1/pose_landmarker_full.task",
        "5134a3aad27a58b93da0088d431f366da362b44e3ccfbe3462b3827a839011b1",
    ),
    "segmenter": (
        f"{_BASE}/image_segmenter/selfie_multiclass_256x256/float32/latest/selfie_multiclass_256x256.tflite",
        "c6748b1253a99067ef71f7e26ca71096cd449baefa8f101900ea23016507e0e0",
    ),
}
FILENAMES = {
    "face_landmarker": "face_landmarker.task",
    "pose_landmarker": "pose_landmarker_full.task",
    "segmenter": "selfie_multiclass_256x256.tflite",
}
# Recorded with every result so an analysis can be traced to the models that made it.
MODEL_VERSION = "mediapipe:face_landmarker-f16-v1+pose_full-f16-v1+selfie_multiclass_256"

# Classes of the multiclass selfie segmenter.
BACKGROUND, HAIR, BODY_SKIN, FACE_SKIN, CLOTHES, OTHER = range(6)

MAX_SIDE = 1280  # photos are downscaled to this before analysis


class ModelsMissing(RuntimeError):
    pass


def model_path(name: str) -> Path:
    return Path(get_settings().model_dir) / FILENAMES[name]


def models_available() -> bool:
    return all(model_path(name).is_file() for name in MODELS)


def fetch_models() -> list[str]:
    """Downloads missing models and verifies every file's checksum."""
    done = []
    for name, (url, sha) in MODELS.items():
        path = model_path(name)
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.is_file():
            urllib.request.urlretrieve(url, path)  # noqa: S310 (fixed https URL)
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != sha:
            path.unlink()
            raise RuntimeError(f"{name}: checksum mismatch, file removed")
        done.append(str(path))
    return done


@dataclass
class Face:
    points: np.ndarray  # (478, 3) pixel x, pixel y, relative depth
    yaw: float  # degrees, from the facial transformation matrix
    pitch: float
    roll: float


@dataclass
class Pose:
    points: np.ndarray  # (33, 3) pixel x, pixel y, relative depth
    visibility: np.ndarray  # (33,)
    mask: np.ndarray  # person silhouette, uint8 0/1, at the photo's size


class _Models:
    def __init__(self):
        self._lock = threading.Lock()
        self._face = self._pose = self._seg = None
        self._locks = {"face": threading.Lock(), "pose": threading.Lock(), "seg": threading.Lock()}

    def _load(self):
        if self._seg is not None:
            return
        with self._lock:
            if self._seg is not None:
                return
            if not models_available():
                raise ModelsMissing("vision models not installed; run `python -m app.cli fetch-models`")
            from mediapipe.tasks.python import BaseOptions, vision

            self._face = vision.FaceLandmarker.create_from_options(
                vision.FaceLandmarkerOptions(
                    base_options=BaseOptions(model_asset_path=str(model_path("face_landmarker"))),
                    num_faces=2,
                    output_facial_transformation_matrixes=True,
                )
            )
            self._pose = vision.PoseLandmarker.create_from_options(
                vision.PoseLandmarkerOptions(
                    base_options=BaseOptions(model_asset_path=str(model_path("pose_landmarker"))),
                    num_poses=2,
                    output_segmentation_masks=True,
                )
            )
            self._seg = vision.ImageSegmenter.create_from_options(
                vision.ImageSegmenterOptions(
                    base_options=BaseOptions(model_asset_path=str(model_path("segmenter"))),
                    output_category_mask=True,
                )
            )

    @staticmethod
    def _mp(rgb: np.ndarray):
        import mediapipe as mp

        return mp.Image(image_format=mp.ImageFormat.SRGB, data=np.ascontiguousarray(rgb))

    def faces(self, rgb: np.ndarray) -> list[Face]:
        self._load()
        h, w = rgb.shape[:2]
        with self._locks["face"]:
            result = self._face.detect(self._mp(rgb))
        faces = []
        for marks, matrix in zip(result.face_landmarks, result.facial_transformation_matrixes, strict=False):
            pts = np.array([(m.x * w, m.y * h, m.z * w) for m in marks], dtype=np.float64)
            yaw, pitch, roll = _euler(np.asarray(matrix))
            faces.append(Face(points=pts, yaw=yaw, pitch=pitch, roll=roll))
        return faces

    def poses(self, rgb: np.ndarray) -> list[Pose]:
        self._load()
        h, w = rgb.shape[:2]
        with self._locks["pose"]:
            result = self._pose.detect(self._mp(rgb))
        masks = result.segmentation_masks or [None] * len(result.pose_landmarks)
        return [
            Pose(
                points=np.array([(m.x * w, m.y * h, m.z * w) for m in marks], dtype=np.float64),
                visibility=np.array([m.visibility or 0.0 for m in marks]),
                mask=(np.zeros((h, w), np.uint8) if mask is None else (mask.numpy_view().reshape(h, w) > 0.5).astype(np.uint8)),
            )
            for marks, mask in zip(result.pose_landmarks, masks, strict=False)
        ]

    def segment(self, rgb: np.ndarray) -> np.ndarray:
        """Per-pixel class (see the constants above), at the photo's own size."""
        self._load()
        with self._locks["seg"]:
            result = self._seg.segment(self._mp(rgb))
        mask = result.category_mask.numpy_view().copy()
        mask = mask.reshape(mask.shape[:2])
        if mask.shape != rgb.shape[:2]:
            mask = cv2.resize(mask, (rgb.shape[1], rgb.shape[0]), interpolation=cv2.INTER_NEAREST)
        return mask

    def close(self) -> None:
        for task in (self._face, self._pose, self._seg):
            if task is not None:
                task.close()
        self._face = self._pose = self._seg = None


def _euler(matrix: np.ndarray) -> tuple[float, float, float]:
    r = matrix[:3, :3]
    pitch = np.degrees(np.arctan2(r[2, 1], r[2, 2]))
    yaw = np.degrees(np.arcsin(-np.clip(r[2, 0], -1, 1)))
    roll = np.degrees(np.arctan2(r[1, 0], r[0, 0]))
    return float(yaw), float(pitch), float(roll)


models = _Models()
# Close explicitly while the interpreter is still intact; MediaPipe's own
# finalisers otherwise print errors at shutdown.
atexit.register(models.close)


def decode(data: bytes) -> np.ndarray:
    """JPEG/PNG bytes to an RGB array, honouring EXIF orientation, downscaled to MAX_SIDE."""
    bgr = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
    if bgr is None:
        raise ValueError("not an image")
    scale = MAX_SIDE / max(bgr.shape[:2])
    if scale < 1:
        bgr = cv2.resize(bgr, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    return cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)


def encode_jpeg(rgb: np.ndarray, quality: int = 88) -> bytes:
    ok, buf = cv2.imencode(".jpg", cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, quality])
    if not ok:
        raise RuntimeError("could not encode preview")
    return buf.tobytes()
