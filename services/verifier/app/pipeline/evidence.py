from __future__ import annotations

import hashlib

from app.pipeline.quality import FaceQualityEvaluation

from .types import (
    AntiSpoofEvaluation,
    ChallengeType,
    DeepfakeEvaluation,
    EvidenceBlob,
    FaceDetectionResult,
    FrameInput,
    HumanFaceEvaluation,
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
        evidence_schema_version: int,
        session_id: str,
        wallet_address: str,
        challenge_type: ChallengeType,
        challenge_sequence: list[str],
        session_started_at: str,
        session_completed_at: str,
        frames: list[FrameInput],
        liveness: LivenessEvaluation,
        antispoof: AntiSpoofEvaluation,
        deepfake: DeepfakeEvaluation,
        human_face: HumanFaceEvaluation,
        quality_evaluations: list[FaceQualityEvaluation],
        face_detections: list[FaceDetectionResult],
        attack_analysis: dict[str, object] | None,
        evaluation_mode: str,
        human: bool,
        confidence: float,
    ) -> EvidenceBlob:
        landmark_frame = next((frame for frame in reversed(frames) if frame.landmarks), None)
        last_timestamp = frames[-1].timestamp.isoformat() if frames else ""
        face_confidences = [result.confidence for result in face_detections if result.detected]
        quality_scores = [result.score for result in quality_evaluations]
        quality_passes = [result for result in quality_evaluations if result.passed]

        landmark_snapshot = {
            "source": "mediapipe" if landmark_frame else "none",
            "frame_index": landmark_frame.frame_index if landmark_frame else -1,
            "landmark_keys": sorted(landmark_frame.landmarks.keys()) if landmark_frame else [],
            "faces_detected": sum(1 for result in face_detections if result.detected),
        }
        landmark_trace_summary = {
            "frames_with_landmarks": sum(1 for frame in frames if frame.landmarks),
            "last_landmark_frame_index": landmark_frame.frame_index if landmark_frame else None,
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

        human_face_summary = {
            "enabled": human_face.enabled,
            "passed": human_face.passed,
            "score": human_face.human_face_score,
            "top_label": human_face.top_label,
            "message": human_face.message,
            "model_hash": human_face.model_hash,
        }

        quality_summary = {
            "frames_evaluated": len(quality_evaluations),
            "frames_passed": len(quality_passes),
            "average_score": round(sum(quality_scores) / len(quality_scores), 4) if quality_scores else 0.0,
            "latest_message": quality_evaluations[-1].message if quality_evaluations else "",
            "latest_primary_issue": quality_evaluations[-1].primary_issue if quality_evaluations else None,
        }

        antispoof_summary = {
            "passed": antispoof.passed,
            "final_score": antispoof.spoof_score,
            "max_score": antispoof.max_spoof_score,
            "flagged_frames": antispoof.flagged_frames,
            "frames_processed": antispoof.frames_processed,
            "message": antispoof.message,
        }

        deepfake_summary = {
            "enabled": deepfake.enabled,
            "passed": deepfake.passed,
            "score": deepfake.deepfake_score,
            "max_score": deepfake.max_deepfake_score,
            "flagged_frames": deepfake.flagged_frames,
            "frames_processed": deepfake.frames_processed,
            "message": deepfake.message,
            "model_hash": deepfake.model_hash,
        }

        model_hashes = {
            "antispoof": antispoof.model_hash,
            "face_detector": self.face_model_hash,
        }
        if human_face.model_hash:
            model_hashes["human_face"] = human_face.model_hash
        if deepfake.model_hash:
            model_hashes["deepfake"] = deepfake.model_hash
        model_hashes["verifier_bundle"] = self._bundle_model_hash(model_hashes)

        return EvidenceBlob(
            evidence_schema_version=evidence_schema_version,
            session_id=session_id,
            wallet_address=wallet_address,
            challenge_type=challenge_type,
            challenge_sequence=list(challenge_sequence),
            session_started_at=session_started_at,
            session_completed_at=session_completed_at,
            frame_hashes=[f"sha256:{frame.fingerprint('evidence-frame')}" for frame in frames],
            landmark_snapshot=landmark_snapshot,
            landmark_trace_summary=landmark_trace_summary,
            spoof_score_summary={
                "max": antispoof.max_spoof_score,
                "final": antispoof.spoof_score,
            },
            antispoof_summary=antispoof_summary,
            human_face_summary=human_face_summary,
            quality_summary=quality_summary,
            deepfake_summary=deepfake_summary,
            model_hashes=model_hashes,
            verification_context={
                "evaluation_mode": evaluation_mode,
                "wallet_address": wallet_address,
            },
            captured_at=last_timestamp,
            challenge_summary=challenge_summary,
            attack_analysis=dict(attack_analysis or {}),
            verdict_context={
                "human": human,
                "confidence": confidence,
                "status": "verified" if human else "failed",
            },
        )

    def _bundle_model_hash(self, model_hashes: dict[str, str]) -> str:
        serialized = "|".join(f"{key}:{value}" for key, value in sorted(model_hashes.items()))
        return f"sha256:{hashlib.sha256(serialized.encode('utf-8')).hexdigest()}"
