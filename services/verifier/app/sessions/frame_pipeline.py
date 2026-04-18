from __future__ import annotations

from typing import Any

from app.pipeline.face import FaceDetector
from app.pipeline.landmark_metrics import (
    LandmarkSpotCheckEvaluation,
    evaluate_landmark_spot_check,
)
from app.pipeline.quality import FaceQualityEvaluation, FaceQualityEvaluator
from app.pipeline.types import FaceBoundingBox, FaceDetectionResult, FrameInput

_SERVER_FACE_DETECTION_KEY = "_server_face_detection"
_SERVER_QUALITY_KEY = "_server_quality"
_SERVER_LANDMARK_SPOTCHECK_KEY = "_server_landmark_spotcheck"


def clear_cached_frame_analysis(metadata: dict[str, Any]) -> dict[str, Any]:
    metadata.pop(_SERVER_FACE_DETECTION_KEY, None)
    metadata.pop(_SERVER_QUALITY_KEY, None)
    metadata.pop(_SERVER_LANDMARK_SPOTCHECK_KEY, None)
    return metadata


class SessionFrameEvaluator:
    def __init__(
        self,
        *,
        face_detector: FaceDetector,
        face_quality_evaluator: FaceQualityEvaluator,
        max_landmark_center_mismatch_px: float,
    ) -> None:
        self.face_detector = face_detector
        self.face_quality_evaluator = face_quality_evaluator
        self.max_landmark_center_mismatch_px = max_landmark_center_mismatch_px

    def frame_input_from_payload(self, payload: dict[str, object]) -> FrameInput:
        return FrameInput(
            frame_index=int(payload.get("frame_index", 0)),
            timestamp=str(payload.get("timestamp")) if payload.get("timestamp") else None,
            image_base64=payload.get("image_base64")
            if isinstance(payload.get("image_base64"), str)
            else None,
            landmarks=payload.get("landmarks")
            if isinstance(payload.get("landmarks"), dict)
            else {},
            metadata=payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {},
        )

    def build_frame_bundle(
        self,
        payloads: list[dict[str, object]],
    ) -> list[
        tuple[
            FrameInput,
            FaceDetectionResult,
            FaceQualityEvaluation,
            LandmarkSpotCheckEvaluation,
        ]
    ]:
        frame_bundle: list[
            tuple[
                FrameInput,
                FaceDetectionResult,
                FaceQualityEvaluation,
                LandmarkSpotCheckEvaluation,
            ]
        ] = []
        for payload in payloads:
            frame = self.frame_input_from_payload(payload)
            face_detection = self.face_detection_from_payload(payload, frame)
            face_quality = self.face_quality_from_payload(payload, frame, face_detection)
            landmark_spotcheck = self.landmark_spotcheck_from_payload(
                payload,
                frame,
                face_detection,
            )
            frame_bundle.append((frame, face_detection, face_quality, landmark_spotcheck))
        return frame_bundle

    def face_detection_from_payload(
        self,
        payload: dict[str, object],
        frame: FrameInput,
    ) -> FaceDetectionResult:
        metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}
        stored = metadata.get(_SERVER_FACE_DETECTION_KEY) if isinstance(metadata, dict) else None
        if isinstance(stored, dict):
            raw_bbox = stored.get("bounding_box")
            bounding_box = None
            if isinstance(raw_bbox, dict):
                bounding_box = FaceBoundingBox(
                    x=float(raw_bbox.get("x", 0.0)),
                    y=float(raw_bbox.get("y", 0.0)),
                    width=float(raw_bbox.get("width", 0.0)),
                    height=float(raw_bbox.get("height", 0.0)),
                )
            return FaceDetectionResult(
                detected=bool(stored.get("detected")),
                confidence=round(float(stored.get("confidence", 0.0)), 4),
                frame_index=frame.frame_index,
                bounding_box=bounding_box,
                landmarks_source=str(stored.get("landmarks_source", "server")),
                face_hash=str(stored.get("face_hash")) if stored.get("face_hash") else None,
                message=str(stored.get("message", "No face detected in frame")),
            )

        should_detect = bool(
            frame.image_base64 or frame.landmarks or ("force_face_detected" in frame.metadata)
        )
        face_detection = (
            self.face_detector.detect(frame)
            if should_detect
            else FaceDetectionResult(
                detected=False,
                confidence=0.0,
                frame_index=frame.frame_index,
                message="No face detected in frame",
            )
        )
        self._store_face_detection(payload, face_detection)
        return face_detection

    def face_quality_from_payload(
        self,
        payload: dict[str, object],
        frame: FrameInput,
        face_detection: FaceDetectionResult,
    ) -> FaceQualityEvaluation:
        metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}
        stored = metadata.get(_SERVER_QUALITY_KEY) if isinstance(metadata, dict) else None
        if isinstance(stored, dict):
            return FaceQualityEvaluation(
                frame_index=frame.frame_index,
                passed=bool(stored.get("passed")),
                score=round(float(stored.get("score", 0.0)), 4),
                message=str(stored.get("message", "Improve frame quality")),
                primary_issue=str(stored.get("primary_issue"))
                if stored.get("primary_issue")
                else None,
                feedback=[
                    str(item) for item in stored.get("feedback", [])
                ]
                if isinstance(stored.get("feedback"), list)
                else [],
                checks=dict(stored.get("checks", {}))
                if isinstance(stored.get("checks"), dict)
                else {},
                metrics=dict(stored.get("metrics", {}))
                if isinstance(stored.get("metrics"), dict)
                else {},
            )

        face_quality = self.face_quality_evaluator.evaluate(frame, face_detection)
        self._store_face_quality(payload, face_quality)
        return face_quality

    def landmark_spotcheck_from_payload(
        self,
        payload: dict[str, object],
        frame: FrameInput,
        face_detection: FaceDetectionResult,
    ) -> LandmarkSpotCheckEvaluation:
        metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}
        stored = (
            metadata.get(_SERVER_LANDMARK_SPOTCHECK_KEY)
            if isinstance(metadata, dict)
            else None
        )
        if isinstance(stored, dict):
            return LandmarkSpotCheckEvaluation(
                enforced=bool(stored.get("enforced")),
                passed=bool(stored.get("passed")),
                message=str(stored.get("message", "Landmark spot-check unavailable")),
                mismatch_pixels=(
                    round(float(stored["mismatch_pixels"]), 4)
                    if stored.get("mismatch_pixels") is not None
                    else None
                ),
                threshold_pixels=(
                    round(float(stored["threshold_pixels"]), 4)
                    if stored.get("threshold_pixels") is not None
                    else None
                ),
                anchors_used=int(stored.get("anchors_used", 0) or 0),
                landmark_center=(
                    dict(stored.get("landmark_center", {}))
                    if isinstance(stored.get("landmark_center"), dict)
                    else None
                ),
                face_center=(
                    dict(stored.get("face_center", {}))
                    if isinstance(stored.get("face_center"), dict)
                    else None
                ),
            )

        landmark_spotcheck = evaluate_landmark_spot_check(
            frame,
            face_detection,
            max_center_mismatch_px=self.max_landmark_center_mismatch_px,
        )
        self._store_landmark_spotcheck(payload, landmark_spotcheck)
        return landmark_spotcheck

    def _store_face_detection(
        self,
        payload: dict[str, object],
        face_detection: FaceDetectionResult,
    ) -> None:
        metadata = (
            dict(payload.get("metadata", {}))
            if isinstance(payload.get("metadata"), dict)
            else {}
        )
        bounding_box = None
        if face_detection.bounding_box is not None:
            bounding_box = {
                "x": face_detection.bounding_box.x,
                "y": face_detection.bounding_box.y,
                "width": face_detection.bounding_box.width,
                "height": face_detection.bounding_box.height,
            }
        metadata[_SERVER_FACE_DETECTION_KEY] = {
            "detected": face_detection.detected,
            "confidence": face_detection.confidence,
            "bounding_box": bounding_box,
            "landmarks_source": face_detection.landmarks_source,
            "face_hash": face_detection.face_hash,
            "message": face_detection.message,
        }
        payload["metadata"] = metadata

    def _store_face_quality(
        self,
        payload: dict[str, object],
        face_quality: FaceQualityEvaluation,
    ) -> None:
        metadata = (
            dict(payload.get("metadata", {}))
            if isinstance(payload.get("metadata"), dict)
            else {}
        )
        metadata[_SERVER_QUALITY_KEY] = {
            "passed": face_quality.passed,
            "score": face_quality.score,
            "message": face_quality.message,
            "primary_issue": face_quality.primary_issue,
            "feedback": face_quality.feedback,
            "checks": face_quality.checks,
            "metrics": face_quality.metrics,
        }
        payload["metadata"] = metadata

    def _store_landmark_spotcheck(
        self,
        payload: dict[str, object],
        landmark_spotcheck: LandmarkSpotCheckEvaluation,
    ) -> None:
        metadata = (
            dict(payload.get("metadata", {}))
            if isinstance(payload.get("metadata"), dict)
            else {}
        )
        metadata[_SERVER_LANDMARK_SPOTCHECK_KEY] = {
            "enforced": landmark_spotcheck.enforced,
            "passed": landmark_spotcheck.passed,
            "message": landmark_spotcheck.message,
            "mismatch_pixels": landmark_spotcheck.mismatch_pixels,
            "threshold_pixels": landmark_spotcheck.threshold_pixels,
            "anchors_used": landmark_spotcheck.anchors_used,
            "landmark_center": landmark_spotcheck.landmark_center,
            "face_center": landmark_spotcheck.face_center,
        }
        payload["metadata"] = metadata
