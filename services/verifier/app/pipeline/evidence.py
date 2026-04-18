from __future__ import annotations

from .types import (
    AntiSpoofEvaluation,
    ChallengeType,
    EvidenceBlob,
    FaceDetectionResult,
    FrameInput,
    LivenessEvaluation,
)


class EvidenceAssembler:
    def __init__(
        self,
        face_model_hash: str = "sha256:mock-face-detector-v1",
        antispoof_model_hash: str = "sha256:mock-antispoof-v1",
    ) -> None:
        self.face_model_hash = face_model_hash
        self.antispoof_model_hash = antispoof_model_hash

    def assemble(
        self,
        *,
        session_id: str,
        wallet_address: str,
        challenge_type: ChallengeType,
        frames: list[FrameInput],
        liveness: LivenessEvaluation,
        antispoof: AntiSpoofEvaluation,
        face_detections: list[FaceDetectionResult],
    ) -> EvidenceBlob:
        landmark_frame = next((frame for frame in reversed(frames) if frame.landmarks), None)
        last_timestamp = frames[-1].timestamp.isoformat() if frames else ""
        face_confidences = [result.confidence for result in face_detections if result.detected]

        landmark_snapshot = {
            "source": "mediapipe" if landmark_frame else "none",
            "frame_index": landmark_frame.frame_index if landmark_frame else -1,
            "landmark_keys": sorted(landmark_frame.landmarks.keys()) if landmark_frame else [],
            "faces_detected": sum(1 for result in face_detections if result.detected),
        }

        challenge_summary = {
            "passed": liveness.passed,
            "progress": liveness.progress,
            "matched_signals": liveness.matched_signals,
            "required_signals": liveness.required_signals,
            "message": liveness.message,
            "face_confidence_avg": round(
                sum(face_confidences) / len(face_confidences), 4
            )
            if face_confidences
            else 0.0,
        }

        return EvidenceBlob(
            session_id=session_id,
            wallet_address=wallet_address,
            challenge_type=challenge_type,
            frame_hashes=[f"sha256:{frame.fingerprint('evidence-frame')}" for frame in frames],
            landmark_snapshot=landmark_snapshot,
            spoof_score_summary={
                "max": antispoof.max_spoof_score,
                "final": antispoof.spoof_score,
            },
            model_hashes={
                "antispoof": antispoof.model_hash,
                "face_detector": self.face_model_hash,
            },
            captured_at=last_timestamp,
            challenge_summary=challenge_summary,
        )
