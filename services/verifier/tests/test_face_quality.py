from __future__ import annotations

import base64

import cv2
import numpy as np

from app.pipeline.quality import HeuristicFaceQualityEvaluator
from app.pipeline.types import FaceBoundingBox, FaceDetectionResult, FrameInput


def _encode_image(image: np.ndarray) -> str:
    ok, encoded = cv2.imencode(".jpg", image)
    assert ok
    return base64.b64encode(encoded.tobytes()).decode("utf-8")


def _frame_from_image(
    image: np.ndarray,
    *,
    yaw: float | None = None,
    pitch: float | None = None,
) -> FrameInput:
    metadata: dict[str, object] = {}
    if yaw is not None:
        metadata["yaw"] = yaw
    if pitch is not None:
        metadata["pitch"] = pitch
    return FrameInput(
        frame_index=0,
        image_base64=_encode_image(image),
        metadata=metadata,
    )


def _detection(width: int, height: int) -> FaceDetectionResult:
    return FaceDetectionResult(
        detected=True,
        confidence=0.99,
        frame_index=0,
        bounding_box=FaceBoundingBox(x=20, y=20, width=width, height=height),
        message="Face detected and centered",
    )


def test_quality_evaluator_passes_clear_well_lit_face_crop() -> None:
    image = np.zeros((180, 180, 3), dtype=np.uint8)
    for row in range(20, 140, 10):
        for col in range(20, 140, 10):
            value = 220 if (row + col) % 20 == 0 else 40
            image[row : row + 10, col : col + 10] = (value, value, value)

    evaluator = HeuristicFaceQualityEvaluator(
        blur_threshold=45.0,
        min_face_size=80,
        max_yaw_degrees=40.0,
        max_pitch_degrees=30.0,
        min_brightness=40.0,
        max_brightness=220.0,
    )

    result = evaluator.evaluate(_frame_from_image(image), _detection(120, 120))

    assert result.passed is True
    assert result.score > 0.9
    assert result.primary_issue is None
    assert result.feedback == []


def test_quality_evaluator_flags_blurry_and_extreme_angle_frames() -> None:
    image = np.full((180, 180, 3), 128, dtype=np.uint8)
    evaluator = HeuristicFaceQualityEvaluator(
        blur_threshold=45.0,
        min_face_size=80,
        max_yaw_degrees=40.0,
        max_pitch_degrees=30.0,
        min_brightness=40.0,
        max_brightness=220.0,
    )

    result = evaluator.evaluate(
        _frame_from_image(image, yaw=52.0, pitch=34.0),
        _detection(70, 70),
    )

    assert result.passed is False
    assert result.primary_issue == "face_too_small"
    assert "Move closer to the camera" in result.feedback
    assert "Face the camera directly" in result.feedback
    assert "Hold still so the camera can focus" in result.feedback
