from __future__ import annotations

from app.pipeline.landmark_metrics import evaluate_landmark_spot_check
from app.pipeline.types import FaceBoundingBox, FaceDetectionResult, FrameInput


def _frame_with_landmarks(
    *,
    frame_width: int = 640,
    frame_height: int = 480,
    center_x: float,
    center_y: float,
) -> FrameInput:
    return FrameInput(
        frame_index=0,
        metadata={
            "frame_width": frame_width,
            "frame_height": frame_height,
        },
        landmarks={
            "nose_tip_x": center_x,
            "nose_tip_y": center_y - 0.02,
            "left_eye_outer_x": center_x - 0.08,
            "left_eye_outer_y": center_y - 0.06,
            "right_eye_outer_x": center_x + 0.08,
            "right_eye_outer_y": center_y - 0.06,
            "mouth_left_x": center_x - 0.05,
            "mouth_left_y": center_y + 0.08,
            "mouth_right_x": center_x + 0.05,
            "mouth_right_y": center_y + 0.08,
        },
    )


def _face_detection() -> FaceDetectionResult:
    return FaceDetectionResult(
        detected=True,
        confidence=0.99,
        frame_index=0,
        bounding_box=FaceBoundingBox(x=160, y=120, width=320, height=240),
        message="Face detected and centered",
    )


def test_landmark_spotcheck_passes_for_aligned_landmarks() -> None:
    frame = _frame_with_landmarks(center_x=0.5, center_y=0.5)

    result = evaluate_landmark_spot_check(
        frame,
        _face_detection(),
        max_center_mismatch_px=96.0,
    )

    assert result.enforced is True
    assert result.passed is True
    assert result.mismatch_pixels is not None
    assert result.mismatch_pixels < 30


def test_landmark_spotcheck_fails_for_far_away_landmarks() -> None:
    frame = _frame_with_landmarks(center_x=0.88, center_y=0.18)

    result = evaluate_landmark_spot_check(
        frame,
        _face_detection(),
        max_center_mismatch_px=96.0,
    )

    assert result.enforced is True
    assert result.passed is False
    assert result.mismatch_pixels is not None
    assert result.mismatch_pixels > 200
    assert result.message == "Landmark telemetry does not match the detected face position"


def test_landmark_spotcheck_skips_when_not_enough_anchors_are_available() -> None:
    frame = FrameInput(
        frame_index=0,
        metadata={"frame_width": 640, "frame_height": 480},
        landmarks={"nose_tip_x": 0.5, "nose_tip_y": 0.5},
    )

    result = evaluate_landmark_spot_check(
        frame,
        _face_detection(),
        max_center_mismatch_px=96.0,
    )

    assert result.enforced is False
    assert result.passed is True
    assert result.anchors_used == 1
