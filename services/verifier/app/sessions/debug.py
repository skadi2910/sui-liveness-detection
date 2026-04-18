from __future__ import annotations

from app.pipeline.landmark_metrics import (
    LandmarkSpotCheckEvaluation,
    extract_landmark_metrics,
)
from app.pipeline.quality import FaceQualityEvaluation
from app.pipeline.types import (
    AntiSpoofEvaluation,
    DeepfakeEvaluation,
    FaceDetectionResult,
    FrameInput,
    HumanFaceEvaluation,
)
from app.sessions.models import ChallengeType


def build_session_debug_payload(
    *,
    latest_frame: FrameInput | None,
    face_detection: FaceDetectionResult | None,
    face_quality: FaceQualityEvaluation | None,
    landmark_spotcheck: LandmarkSpotCheckEvaluation | None,
    human_face: HumanFaceEvaluation | None,
    antispoof: AntiSpoofEvaluation | None,
    deepfake: DeepfakeEvaluation | None = None,
    antispoof_preview: bool = True,
    current_step: ChallengeType,
    step_progress: float,
    message: str,
) -> dict[str, object]:
    metrics = extract_landmark_metrics(latest_frame) if latest_frame is not None else None
    bounding_box = None
    if face_detection is not None and face_detection.bounding_box is not None:
        bounding_box = {
            "x": face_detection.bounding_box.x,
            "y": face_detection.bounding_box.y,
            "width": face_detection.bounding_box.width,
            "height": face_detection.bounding_box.height,
        }

    point_count = 0
    if metrics is not None:
        point_count = metrics.point_count
    if point_count == 0 and latest_frame is not None:
        point_count = int(latest_frame.landmarks.get("point_count", 0) or 0)

    return {
        "face_detection": {
            "detected": bool(face_detection.detected) if face_detection is not None else False,
            "confidence": face_detection.confidence if face_detection is not None else 0.0,
            "bounding_box": bounding_box,
        },
        "quality": {
            "passed": face_quality.passed if face_quality is not None else False,
            "score": face_quality.score if face_quality is not None else 0.0,
            "primary_issue": face_quality.primary_issue if face_quality is not None else None,
            "feedback": face_quality.feedback if face_quality is not None else [],
            "checks": face_quality.checks if face_quality is not None else {},
            "metrics": face_quality.metrics if face_quality is not None else {},
        },
        "landmark_spotcheck": {
            "enforced": landmark_spotcheck.enforced if landmark_spotcheck is not None else False,
            "passed": landmark_spotcheck.passed if landmark_spotcheck is not None else True,
            "message": (
                landmark_spotcheck.message
                if landmark_spotcheck is not None
                else "Landmark spot-check unavailable"
            ),
            "mismatch_pixels": (
                landmark_spotcheck.mismatch_pixels
                if landmark_spotcheck is not None
                else None
            ),
            "threshold_pixels": (
                landmark_spotcheck.threshold_pixels
                if landmark_spotcheck is not None
                else None
            ),
            "anchors_used": landmark_spotcheck.anchors_used if landmark_spotcheck is not None else 0,
            "landmark_center": (
                landmark_spotcheck.landmark_center
                if landmark_spotcheck is not None
                else None
            ),
            "face_center": landmark_spotcheck.face_center if landmark_spotcheck is not None else None,
        },
        "human_face": {
            "enabled": human_face.enabled if human_face is not None else False,
            "enforced": human_face.enforced if human_face is not None else False,
            "passed": human_face.passed if human_face is not None else False,
            "score": human_face.human_face_score if human_face is not None else None,
            "top_label": human_face.top_label if human_face is not None else None,
            "frames_processed": human_face.frames_processed if human_face is not None else 0,
            "message": (
                human_face.message if human_face is not None else "Human-face scoring disabled"
            ),
        },
        "landmarks": {
            "face_detected": bool(latest_frame and latest_frame.landmarks),
            "point_count": point_count,
            "yaw": metrics.yaw_degrees if metrics is not None else None,
            "pitch": metrics.pitch if metrics is not None else None,
            "smile_ratio": metrics.smile_ratio if metrics is not None else None,
            "average_ear": metrics.ear if metrics is not None else None,
        },
        "liveness": {
            "current_step": current_step.value,
            "step_progress": round(step_progress, 4),
            "message": message,
        },
        "antispoof": {
            "passed": antispoof.passed if antispoof is not None else None,
            "spoof_score": antispoof.spoof_score if antispoof is not None else None,
            "max_spoof_score": antispoof.max_spoof_score if antispoof is not None else None,
            "frames_processed": antispoof.frames_processed if antispoof is not None else 0,
            "message": antispoof.message if antispoof is not None else "Preview pending",
            "preview": antispoof_preview,
        },
        "deepfake": {
            "enabled": deepfake.enabled if deepfake is not None else False,
            "enforced": deepfake.enforced if deepfake is not None else False,
            "score": deepfake.deepfake_score if deepfake is not None else None,
            "max_score": deepfake.max_deepfake_score if deepfake is not None else None,
            "frames_processed": deepfake.frames_processed if deepfake is not None else 0,
            "message": (
                deepfake.message if deepfake is not None else "Deepfake scoring disabled"
            ),
            "preview": False,
        },
    }
