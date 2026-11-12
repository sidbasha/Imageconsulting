"""Photo quality gate (OpenCV only, runs on CPU).

A photo is rejected with reason codes so the app can tell the user what to
fix. The thresholds below are starting values chosen on a handful of test
images; they MUST be tuned on real user photos before release.
"""

from dataclasses import dataclass, field

import cv2
import numpy as np

MIN_SIDE_PX = 480
MIN_SHARPNESS = 60.0  # variance of the Laplacian; lower means blurrier
MIN_BRIGHTNESS, MAX_BRIGHTNESS = 50.0, 215.0  # mean luma, 0-255
MIN_FACE_FRACTION = 0.04  # face box area / image area

_face_detector = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")


@dataclass
class QualityReport:
    width: int = 0
    height: int = 0
    sharpness: float = 0.0
    brightness: float = 0.0
    faces: int | None = None
    face_fraction: float | None = None
    reasons: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.reasons

    def measurements(self) -> dict:
        return {
            "sharpness": round(self.sharpness, 1),
            "brightness": round(self.brightness, 1),
            "faces": self.faces,
            "face_fraction": None if self.face_fraction is None else round(self.face_fraction, 3),
        }


def check(data: bytes, kind: str) -> QualityReport:
    report = QualityReport()
    image = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        report.reasons.append("not_an_image")
        return report
    report.height, report.width = image.shape[:2]
    if min(report.width, report.height) < MIN_SIDE_PX:
        report.reasons.append("too_small")

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    # Measure sharpness at a fixed scale so large photos are not favoured.
    scale = 640 / max(gray.shape)
    probe = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA) if scale < 1 else gray
    report.sharpness = float(cv2.Laplacian(probe, cv2.CV_64F).var())
    report.brightness = float(gray.mean())
    if report.sharpness < MIN_SHARPNESS:
        report.reasons.append("too_blurry")
    if report.brightness < MIN_BRIGHTNESS:
        report.reasons.append("too_dark")
    elif report.brightness > MAX_BRIGHTNESS:
        report.reasons.append("too_bright")

    if kind == "face":
        faces = _face_detector.detectMultiScale(probe, scaleFactor=1.1, minNeighbors=6, minSize=(60, 60))
        report.faces = len(faces)
        if len(faces) == 0:
            report.reasons.append("no_face")
        else:
            _, _, w, h = max(faces, key=lambda f: f[2] * f[3])
            report.face_fraction = float(w * h) / float(probe.shape[0] * probe.shape[1])
            if report.face_fraction < MIN_FACE_FRACTION:
                report.reasons.append("face_too_small")
    return report
