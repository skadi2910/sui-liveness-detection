from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any

from .image_utils import decode_frame_image
from .types import FaceDetectionResult
from .types import FrameInput

LEFT_EYE_INDICES = (33, 160, 158, 133, 153, 144)
RIGHT_EYE_INDICES = (362, 385, 387, 263, 373, 380)
MOUTH_INDICES = (78, 308, 13, 14)
FACE_YAW_INDICES = (234, 454, 1)
FACE_PITCH_INDICES = (10, 152, 1)
MOTION_ANCHOR_INDICES = {
    "nose_tip": 1,
    "left_eye_outer": 33,
    "right_eye_outer": 263,
    "mouth_left": 78,
    "mouth_right": 308,
}


@dataclass(slots=True)
class Point2D:
    x: float
    y: float


@dataclass(slots=True)
class LandmarkMetrics:
    ear: float | None = None
    left_ear: float | None = None
    right_ear: float | None = None
    mar: float | None = None
    yaw_degrees: float | None = None
    yaw_ratio: float | None = None
    pitch: float | None = None
    pitch_ratio: float | None = None
    smile_ratio: float | None = None
    point_count: int = 0
    points_available: bool = False


@dataclass(slots=True)
class LandmarkSpotCheckEvaluation:
    enforced: bool
    passed: bool
    message: str
    mismatch_pixels: float | None = None
    threshold_pixels: float | None = None
    anchors_used: int = 0
    landmark_center: dict[str, float] | None = None
    face_center: dict[str, float] | None = None


def extract_landmark_metrics(frame: FrameInput) -> LandmarkMetrics:
    metrics = LandmarkMetrics()
    containers = _metric_containers(frame.landmarks)

    metrics.left_ear = _first_float(containers, "left_ear", "leftEAR")
    metrics.right_ear = _first_float(containers, "right_ear", "rightEAR")
    metrics.ear = _first_float(
        containers,
        "ear",
        "avg_ear",
        "eye_aspect_ratio",
        "eyeAspectRatio",
    )
    if metrics.ear is None:
        ear_samples = [value for value in (metrics.left_ear, metrics.right_ear) if value is not None]
        if ear_samples:
            metrics.ear = sum(ear_samples) / len(ear_samples)

    metrics.mar = _first_float(
        containers,
        "mar",
        "mouth_ratio",
        "mouth_aspect_ratio",
        "mouthAspectRatio",
    )
    metrics.yaw_degrees = _first_float(
        containers,
        "yaw",
        "head_yaw",
        "yaw_degrees",
        "yawDegrees",
    )
    metrics.yaw_ratio = _first_float(
        containers,
        "yaw_ratio",
        "nose_offset_ratio",
        "head_turn_ratio",
    )
    metrics.pitch = _first_float(
        containers,
        "pitch",
        "head_pitch",
        "pitch_degrees",
        "pitchDegrees",
    )
    metrics.pitch_ratio = _first_float(
        containers,
        "pitch_ratio",
        "nose_vertical_ratio",
        "head_pitch_ratio",
    )
    metrics.smile_ratio = _first_float(
        containers,
        "smile_ratio",
        "smileRatio",
        "mouth_smile_ratio",
    )

    points = _extract_points(frame.landmarks)
    if not points:
        return metrics

    metrics.points_available = True
    metrics.point_count = len(points)
    if metrics.left_ear is None:
        metrics.left_ear = _eye_aspect_ratio(points, LEFT_EYE_INDICES)
    if metrics.right_ear is None:
        metrics.right_ear = _eye_aspect_ratio(points, RIGHT_EYE_INDICES)
    if metrics.ear is None:
        ear_samples = [value for value in (metrics.left_ear, metrics.right_ear) if value is not None]
        if ear_samples:
            metrics.ear = sum(ear_samples) / len(ear_samples)
    if metrics.mar is None:
        metrics.mar = _mouth_aspect_ratio(points, MOUTH_INDICES)
    if metrics.yaw_ratio is None:
        metrics.yaw_ratio = _yaw_ratio(points, FACE_YAW_INDICES)
    if metrics.pitch_ratio is None:
        metrics.pitch_ratio = _pitch_ratio(points, FACE_PITCH_INDICES)
    if metrics.smile_ratio is None:
        metrics.smile_ratio = _smile_ratio(points, MOUTH_INDICES, FACE_YAW_INDICES[:2])
    return metrics


def inter_frame_landmark_displacement(first: FrameInput, second: FrameInput) -> float | None:
    first_points = _extract_motion_anchor_points(first.landmarks)
    second_points = _extract_motion_anchor_points(second.landmarks)
    if not first_points or not second_points:
        return None

    shared_labels = sorted(set(first_points).intersection(second_points))
    if not shared_labels:
        return None

    displacements = [
        _distance(first_points[label], second_points[label])
        for label in shared_labels
    ]
    if not displacements:
        return None
    return sum(displacements) / len(displacements)


def evaluate_landmark_spot_check(
    frame: FrameInput,
    face_detection: FaceDetectionResult,
    *,
    max_center_mismatch_px: float,
) -> LandmarkSpotCheckEvaluation:
    if not face_detection.detected or face_detection.bounding_box is None:
        return LandmarkSpotCheckEvaluation(
            enforced=False,
            passed=True,
            message="No face box available for landmark spot-check",
        )

    landmark_points = _extract_motion_anchor_points(frame.landmarks)
    if len(landmark_points) < 3:
        return LandmarkSpotCheckEvaluation(
            enforced=False,
            passed=True,
            message="Not enough landmark anchors for spot-check",
            anchors_used=len(landmark_points),
            threshold_pixels=round(max_center_mismatch_px, 4),
        )

    frame_dimensions = _frame_dimensions(frame)
    if frame_dimensions is None:
        return LandmarkSpotCheckEvaluation(
            enforced=False,
            passed=True,
            message="Frame dimensions unavailable for spot-check",
            anchors_used=len(landmark_points),
            threshold_pixels=round(max_center_mismatch_px, 4),
        )

    frame_width, frame_height = frame_dimensions
    if frame_width <= 0 or frame_height <= 0:
        return LandmarkSpotCheckEvaluation(
            enforced=False,
            passed=True,
            message="Invalid frame dimensions for spot-check",
            anchors_used=len(landmark_points),
            threshold_pixels=round(max_center_mismatch_px, 4),
        )

    normalized_landmark_points = [
        _normalize_point(point, frame_width, frame_height)
        for point in landmark_points.values()
    ]
    landmark_center_x = sum(point.x for point in normalized_landmark_points) / len(normalized_landmark_points)
    landmark_center_y = sum(point.y for point in normalized_landmark_points) / len(normalized_landmark_points)

    bbox = face_detection.bounding_box
    face_center_x = bbox.x + (bbox.width / 2)
    face_center_y = bbox.y + (bbox.height / 2)
    if bbox.width <= 1.0 and bbox.height <= 1.0 and bbox.x <= 1.0 and bbox.y <= 1.0:
        normalized_face_center_x = face_center_x
        normalized_face_center_y = face_center_y
    else:
        normalized_face_center_x = face_center_x / frame_width
        normalized_face_center_y = face_center_y / frame_height

    mismatch_pixels = math.hypot(
        (landmark_center_x - normalized_face_center_x) * frame_width,
        (landmark_center_y - normalized_face_center_y) * frame_height,
    )
    passed = mismatch_pixels <= max_center_mismatch_px
    return LandmarkSpotCheckEvaluation(
        enforced=True,
        passed=passed,
        message=(
            "Landmark spot-check passed"
            if passed
            else "Landmark telemetry does not match the detected face position"
        ),
        mismatch_pixels=round(mismatch_pixels, 4),
        threshold_pixels=round(max_center_mismatch_px, 4),
        anchors_used=len(landmark_points),
        landmark_center={
            "x": round(landmark_center_x, 4),
            "y": round(landmark_center_y, 4),
        },
        face_center={
            "x": round(normalized_face_center_x, 4),
            "y": round(normalized_face_center_y, 4),
        },
    )


def _metric_containers(landmarks: dict[str, Any]) -> list[dict[str, Any]]:
    containers = [landmarks]
    for key in ("metrics", "signals"):
        nested = landmarks.get(key)
        if isinstance(nested, dict):
            containers.append(nested)
    return containers


def _extract_motion_anchor_points(landmarks: dict[str, Any]) -> dict[str, Point2D]:
    points = _extract_points(landmarks)
    if points:
        anchors = {
            label: points[index]
            for label, index in MOTION_ANCHOR_INDICES.items()
            if index in points
        }
        if anchors:
            return anchors

    containers = _metric_containers(landmarks)
    anchors: dict[str, Point2D] = {}
    for label in MOTION_ANCHOR_INDICES:
        x = _first_float(containers, f"{label}_x")
        y = _first_float(containers, f"{label}_y")
        if x is None or y is None:
            continue
        anchors[label] = Point2D(x=x, y=y)
    return anchors


def _frame_dimensions(frame: FrameInput) -> tuple[float, float] | None:
    width = _to_float(frame.metadata.get("frame_width"))
    height = _to_float(frame.metadata.get("frame_height"))
    if width is not None and height is not None:
        return width, height

    image = decode_frame_image(frame)
    if image is None:
        return None
    return float(image.shape[1]), float(image.shape[0])


def _normalize_point(point: Point2D, width: float, height: float) -> Point2D:
    if point.x <= 1.0 and point.y <= 1.0:
        return point
    normalized_x = point.x / width if width > 0 else point.x
    normalized_y = point.y / height if height > 0 else point.y
    return Point2D(x=normalized_x, y=normalized_y)


def _first_float(containers: list[dict[str, Any]], *keys: str) -> float | None:
    for container in containers:
        for key in keys:
            value = _to_float(container.get(key))
            if value is not None:
                return value
    return None


def _extract_points(landmarks: dict[str, Any]) -> dict[int, Point2D]:
    candidates = (
        landmarks.get("points"),
        landmarks.get("face_landmarks"),
        landmarks.get("faceMesh"),
        landmarks.get("mesh"),
    )
    for candidate in candidates:
        points = _coerce_points(candidate)
        if points:
            return points

    if all(str(index).isdigit() for index in landmarks.keys()):
        points = _coerce_points(landmarks)
        if points:
            return points
    return {}


def _coerce_points(candidate: Any) -> dict[int, Point2D]:
    points: dict[int, Point2D] = {}
    if isinstance(candidate, list):
        for index, raw_point in enumerate(candidate):
            point = _coerce_point(raw_point)
            if point is not None:
                points[index] = point
        return points

    if isinstance(candidate, dict):
        for raw_index, raw_point in candidate.items():
            try:
                index = int(raw_index)
            except (TypeError, ValueError):
                continue
            point = _coerce_point(raw_point)
            if point is not None:
                points[index] = point
        return points

    return {}


def _coerce_point(raw_point: Any) -> Point2D | None:
    if not isinstance(raw_point, dict):
        return None
    x = _to_float(raw_point.get("x"))
    y = _to_float(raw_point.get("y"))
    if x is None or y is None:
        return None
    return Point2D(x=x, y=y)


def _eye_aspect_ratio(points: dict[int, Point2D], indices: tuple[int, int, int, int, int, int]) -> float | None:
    selected = [points.get(index) for index in indices]
    if any(point is None for point in selected):
        return None
    p1, p2, p3, p4, p5, p6 = selected
    horizontal = _distance(p1, p4)
    if horizontal <= 0:
        return None
    vertical = _distance(p2, p6) + _distance(p3, p5)
    return vertical / (2 * horizontal)


def _mouth_aspect_ratio(points: dict[int, Point2D], indices: tuple[int, int, int, int]) -> float | None:
    left_point, right_point, top_point, bottom_point = (points.get(index) for index in indices)
    if any(point is None for point in (left_point, right_point, top_point, bottom_point)):
        return None
    horizontal = _distance(left_point, right_point)
    if horizontal <= 0:
        return None
    vertical = _distance(top_point, bottom_point)
    return vertical / horizontal


def _yaw_ratio(points: dict[int, Point2D], indices: tuple[int, int, int]) -> float | None:
    left_anchor, right_anchor, nose_tip = (points.get(index) for index in indices)
    if any(point is None for point in (left_anchor, right_anchor, nose_tip)):
        return None
    face_width = abs(right_anchor.x - left_anchor.x)
    if face_width <= 0:
        return None
    center_x = (left_anchor.x + right_anchor.x) / 2
    return (nose_tip.x - center_x) / face_width


def _pitch_ratio(points: dict[int, Point2D], indices: tuple[int, int, int]) -> float | None:
    top_anchor, chin_anchor, nose_tip = (points.get(index) for index in indices)
    if any(point is None for point in (top_anchor, chin_anchor, nose_tip)):
        return None
    face_height = abs(chin_anchor.y - top_anchor.y)
    if face_height <= 0:
        return None
    center_y = (top_anchor.y + chin_anchor.y) / 2
    return (nose_tip.y - center_y) / face_height


def _smile_ratio(
    points: dict[int, Point2D],
    mouth_indices: tuple[int, int, int, int],
    face_width_indices: tuple[int, int],
) -> float | None:
    left_corner, right_corner, _, _ = (points.get(index) for index in mouth_indices)
    face_left, face_right = (points.get(index) for index in face_width_indices)
    if any(point is None for point in (left_corner, right_corner, face_left, face_right)):
        return None
    face_width = _distance(face_left, face_right)
    if face_width <= 0:
        return None
    mouth_width = _distance(left_corner, right_corner)
    return mouth_width / face_width


def _distance(first: Point2D, second: Point2D) -> float:
    return math.hypot(first.x - second.x, first.y - second.y)


def _to_float(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    return None
