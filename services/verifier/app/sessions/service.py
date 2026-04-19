from __future__ import annotations

from dataclasses import asdict
import asyncio
from datetime import UTC, datetime, timedelta
import json
import random
from typing import Any
from uuid import uuid4

from fastapi import HTTPException, status

from app.adapters.evidence_encryptor import EvidenceEncryptor
from app.adapters.evidence_store import EvidenceStore
from app.adapters.proof_minter import ProofMinter
from app.adapters.command_runner import CommandExecutionError
from app.core.config import Settings, resolve_data_path
from app.core.logging import get_logger
from app.pipeline.antispoof import AntiSpoofEvaluator
from app.pipeline.deepfake import DeepfakeEvaluator
from app.pipeline.evidence import EvidenceAssembler
from app.pipeline.face import FaceDetector
from app.pipeline.human_face import HumanFaceEvaluator
from app.pipeline.landmark_metrics import LandmarkSpotCheckEvaluation
from app.pipeline.liveness import LivenessEvaluator
from app.pipeline.quality import FaceQualityEvaluation, FaceQualityEvaluator
from app.pipeline.types import (
    AntiSpoofEvaluation,
    ChallengeType as PipelineChallengeType,
    DeepfakeEvaluation,
    FaceDetectionResult,
    FrameInput,
    HumanFaceEvaluation,
    LivenessEvaluation,
    SessionStatus as PipelineSessionStatus,
)
from app.sessions.debug import build_session_debug_payload
from app.sessions.finalize import (
    build_attack_analysis,
    calculate_terminal_confidence,
    determine_finalization_decision,
)
from app.sessions.frame_pipeline import (
    SessionFrameEvaluator,
    clear_cached_frame_analysis,
)
from app.sessions.models import (
    CalibrationAppendResponse,
    AdminEvaluateFrameRequest,
    AdminEvaluateFrameResponse,
    AdminEvaluateSessionRequest,
    AdminEvaluateSessionResponse,
    ChallengeType,
    CompleteProofClaimRequest,
    ClientEventType,
    HealthResponse,
    PreparedProofClaim,
    ProofClaimOperation,
    ServerEventType,
    SessionCreateRequest,
    SessionCreateResponse,
    SessionRecord,
    SessionResponse,
    SessionStatus,
    StepStatus,
    VerificationMode,
    VerificationResult,
    WalletCooldown,
    WebSocketClientEvent,
)
from app.sessions.store import SessionStore

_HEAD_MOTION_CHALLENGES = {
    ChallengeType.TURN_LEFT,
    ChallengeType.TURN_RIGHT,
    ChallengeType.NOD_HEAD,
}
_FRIENDLY_EXPRESSION_CHALLENGES = {
    ChallengeType.SMILE,
    ChallengeType.OPEN_MOUTH,
}
_FRIENDLY_CHALLENGE_POOL = [
    ChallengeType.TURN_LEFT,
    ChallengeType.TURN_RIGHT,
    ChallengeType.NOD_HEAD,
    ChallengeType.SMILE,
    ChallengeType.OPEN_MOUTH,
]
_ANTI_SPOOF_PREVIEW_FRAME_LIMIT = 8
_EVIDENCE_SCHEMA_VERSION = 1


class VerificationSessionService:
    def __init__(
        self,
        store: SessionStore,
        settings: Settings,
        face_detector: FaceDetector,
        face_quality_evaluator: FaceQualityEvaluator,
        liveness_evaluator: LivenessEvaluator,
        antispoof_evaluator: AntiSpoofEvaluator,
        deepfake_evaluator: DeepfakeEvaluator,
        human_face_evaluator: HumanFaceEvaluator,
        evidence_assembler: EvidenceAssembler,
        proof_minter: ProofMinter,
        evidence_store: EvidenceStore,
        evidence_encryptor: EvidenceEncryptor,
    ) -> None:
        self.store = store
        self.settings = settings
        self.minimum_step_frames = max(settings.verifier_liveness_minimum_step_frames, 1)
        self.calibration_output_path = resolve_data_path(settings.verifier_calibration_output_path)
        self.attack_matrix_output_path = resolve_data_path(settings.verifier_attack_matrix_output_path)
        self.logger = get_logger(__name__)
        self.face_detector = face_detector
        self.liveness_evaluator = liveness_evaluator
        self.antispoof_evaluator = antispoof_evaluator
        self.deepfake_evaluator = deepfake_evaluator
        self.human_face_evaluator = human_face_evaluator
        self.evidence_assembler = evidence_assembler
        self.proof_minter = proof_minter
        self.evidence_store = evidence_store
        self.evidence_encryptor = evidence_encryptor
        self.deepfake_sample_frames = max(settings.verifier_deepfake_sample_frames, 1)
        self.frame_evaluator = SessionFrameEvaluator(
            face_detector=face_detector,
            face_quality_evaluator=face_quality_evaluator,
            max_landmark_center_mismatch_px=(
                settings.verifier_landmark_spotcheck_max_center_mismatch_px
            ),
        )

    async def append_calibration_record(
        self,
        record: dict[str, Any],
    ) -> CalibrationAppendResponse:
        return await self._append_ndjson_record(
            record=record,
            output_path=self.calibration_output_path,
            log_label="calibration row appended",
        )

    async def append_attack_matrix_record(
        self,
        record: dict[str, Any],
    ) -> CalibrationAppendResponse:
        return await self._append_ndjson_record(
            record=record,
            output_path=self.attack_matrix_output_path,
            log_label="attack matrix row appended",
        )

    async def evaluate_frame(
        self,
        payload: AdminEvaluateFrameRequest,
    ) -> AdminEvaluateFrameResponse:
        self._ensure_verifier_ready(action="frame evaluation")
        frame_payload = self._admin_frame_payload(payload.frame)
        frame_bundle = self.frame_evaluator.build_frame_bundle([frame_payload])
        frame, face_detection, face_quality, landmark_spotcheck = frame_bundle[0]
        accepted = face_detection.detected and face_quality.passed and landmark_spotcheck.passed
        human_face = self._evaluate_human_face(frame, face_detection)
        liveness = self.liveness_evaluator.evaluate(
            self._to_pipeline_challenge(payload.challenge_type),
            [frame] if accepted else [],
        )
        antispoof = self.antispoof_evaluator.evaluate(
            [frame] if accepted else [],
            [face_detection] if accepted else [],
        )
        deepfake = self.deepfake_evaluator.evaluate(
            [frame] if accepted else [],
            [face_detection] if accepted else [],
            max_samples=1,
        )
        return AdminEvaluateFrameResponse(
            challenge_type=payload.challenge_type,
            evaluation_mode=payload.mode,
            accepted_for_liveness=accepted,
            accepted_for_spoof=accepted,
            face_detection=self._face_detection_payload(face_detection),
            quality=self._quality_payload(face_quality),
            landmark_spotcheck=self._spotcheck_payload(landmark_spotcheck),
            human_face=self._human_face_payload(human_face),
            liveness=self._liveness_payload(liveness),
            antispoof=self._antispoof_payload(antispoof, preview=True),
            deepfake=self._deepfake_payload(deepfake),
        )

    async def evaluate_session(
        self,
        payload: AdminEvaluateSessionRequest,
    ) -> AdminEvaluateSessionResponse:
        self._ensure_verifier_ready(action="session evaluation")
        frame_bundle = self._admin_frame_bundle(payload.frames)
        (
            frames,
            face_detections,
            quality_evaluations,
            landmark_spotchecks,
            usable_frames,
            usable_face_detections,
            accepted_indices,
        ) = self._split_frame_bundle(frame_bundle)
        face_detected = any(result.detected for result in face_detections)
        quality_frames_available = bool(usable_frames)
        liveness = self.liveness_evaluator.evaluate(
            self._to_pipeline_challenge(payload.challenge_type),
            usable_frames,
        )
        antispoof = self.antispoof_evaluator.evaluate(usable_frames, usable_face_detections)
        deepfake = self.deepfake_evaluator.evaluate(
            usable_frames,
            usable_face_detections,
            max_samples=self.deepfake_sample_frames,
        )
        human_face = self._evaluate_human_face_session(usable_frames, usable_face_detections)
        decision = determine_finalization_decision(
            mode=payload.mode,
            face_detected=face_detected,
            quality_frames_available=quality_frames_available,
            human_face_enabled=human_face.enabled,
            human_face_passed=human_face.passed,
            human_face_enforced=(
                human_face.enabled
                and self.settings.verifier_human_face_enforce_decision
                and payload.mode != VerificationMode.LIVENESS_ONLY
            ),
            liveness_passed=liveness.passed,
            antispoof_passed=antispoof.passed,
            deepfake_enabled=deepfake.enabled,
            deepfake_passed=deepfake.passed,
            deepfake_enforced=(
                payload.mode == VerificationMode.DEEPFAKE_ONLY
                or (deepfake.enabled and deepfake.enforced and payload.mode != VerificationMode.LIVENESS_ONLY)
            ),
        )
        attack_analysis = build_attack_analysis(
            human=decision.human,
            failure_reason=decision.failure_reason,
            spoof_score=antispoof.spoof_score,
            max_spoof_score=antispoof.max_spoof_score,
            antispoof_passed=antispoof.passed,
            deepfake_enabled=deepfake.enabled,
            deepfake_score=deepfake.deepfake_score,
            max_deepfake_score=deepfake.max_deepfake_score,
            deepfake_passed=deepfake.passed,
        )
        return AdminEvaluateSessionResponse(
            challenge_type=payload.challenge_type,
            evaluation_mode=payload.mode,
            frames_processed=len(frames),
            accepted_frame_indices=accepted_indices,
            face_detected=face_detected,
            quality_frames_available=quality_frames_available,
            face_detection=self._face_detection_payload(face_detections[-1] if face_detections else None),
            quality=self._quality_payload(quality_evaluations[-1] if quality_evaluations else None),
            landmark_spotcheck=self._spotcheck_payload(landmark_spotchecks[-1] if landmark_spotchecks else None),
            human_face=self._human_face_payload(human_face),
            liveness=self._liveness_payload(liveness),
            antispoof=self._antispoof_payload(antispoof, preview=False),
            deepfake=self._deepfake_payload(deepfake),
            verdict_preview={
                "human": decision.human,
                "failure_reason": decision.failure_reason,
                "mode": payload.mode.value,
                "attack_analysis": attack_analysis,
            },
        )

    async def _append_ndjson_record(
        self,
        *,
        record: dict[str, Any],
        output_path,
        log_label: str,
    ) -> CalibrationAppendResponse:
        if not isinstance(record, dict) or not record:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Calibration record must be a non-empty object.",
            )

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=True) + "\n")

        sample_id = str(record.get("sample_id")) if record.get("sample_id") else None
        self.logger.info(
            log_label,
            context={
                "sample_id": sample_id or "unknown",
                "output_path": str(output_path),
            },
        )
        return CalibrationAppendResponse(
            saved=True,
            sample_id=sample_id,
            output_path=str(output_path),
        )

    async def create_session(self, payload: SessionCreateRequest) -> SessionCreateResponse:
        self._ensure_verifier_ready(action="session creation")
        existing = await self.store.find_active_session_by_wallet(payload.wallet_address)
        if existing is not None:
            existing.status = SessionStatus.EXPIRED
            existing.step_status = StepStatus.COMPLETED
            existing.progress = 1.0
            existing.step_progress = 1.0 if existing.all_challenges_completed else existing.step_progress
            existing.updated_at = datetime.now(tz=UTC)
            existing.last_message = "Superseded by a newer session."
            await self.store.save_session(existing)
            self.logger.info(
                "session superseded",
                context={
                    "superseded_session_id": existing.session_id,
                    "wallet_address": existing.wallet_address,
                    "status": existing.status.value,
                },
            )

        now = datetime.now(tz=UTC)
        session_id = f"sess_{uuid4().hex[:12]}"
        challenge_sequence = self._resolve_challenge_sequence(payload, session_id)
        session = SessionRecord(
            session_id=session_id,
            wallet_address=payload.wallet_address,
            status=SessionStatus.CREATED,
            challenge_sequence=challenge_sequence,
            current_challenge_index=0,
            completed_challenges=[],
            total_challenges=len(challenge_sequence),
            step_started_frame_index=0,
            step_status=StepStatus.PENDING,
            step_progress=0.0,
            debug=None,
            client=payload.client,
            created_at=now,
            expires_at=now + timedelta(seconds=self.settings.verifier_session_ttl_seconds),
            updated_at=now,
            finalize_ready=False,
            last_message=f"Session created. Start with {self._step_label(challenge_sequence[0])}.",
        )
        await self.store.create_session(session)
        self.logger.info(
            "session created",
            context={
                "session_id": session.session_id,
                "wallet_address": session.wallet_address,
                "challenge_sequence": [step.value for step in session.challenge_sequence],
                "total_challenges": session.total_challenges,
            },
        )

        return SessionCreateResponse(
            session_id=session.session_id,
            status=session.status,
            challenge_type=session.challenge_type,
            challenge_sequence=session.challenge_sequence,
            current_challenge_index=session.current_challenge_index,
            total_challenges=session.total_challenges,
            completed_challenges=session.completed_challenges,
            expires_at=session.expires_at,
            ws_url=f"/ws/sessions/{session.session_id}/stream",
        )

    async def get_session(self, session_id: str) -> SessionResponse:
        session = await self.store.get_session(session_id)
        if session is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found",
            )
        return session.to_response()

    async def mark_ready(self, session_id: str) -> SessionRecord:
        self._ensure_verifier_ready(action="verification stream")
        session = await self._get_session_record(session_id)
        if session.status == SessionStatus.CREATED:
            session.status = SessionStatus.READY
            session.step_status = StepStatus.ACTIVE
            session.finalize_ready = False
            session.last_message = f"Start with {self._step_label(session.challenge_type)}."
            session.updated_at = datetime.now(tz=UTC)
            await self.store.save_session(session)
        return session

    async def record_frame(self, session_id: str, event: WebSocketClientEvent) -> SessionRecord:
        self._ensure_verifier_ready(action="frame processing")
        session = await self._get_session_record(session_id)
        if session.status in {SessionStatus.VERIFIED, SessionStatus.FAILED, SessionStatus.EXPIRED}:
            return session

        frame_index = len(session.frame_payloads)
        session.frame_payloads.append(
            {
                "type": ClientEventType.FRAME.value,
                "frame_index": frame_index,
                "timestamp": event.timestamp.isoformat(),
                "image_base64": event.image_base64,
                "landmarks": event.landmarks or {},
                "metadata": event.metadata or {},
            }
        )
        frame_bundle = self.frame_evaluator.build_frame_bundle(session.frame_payloads)
        latest_frame, face_detection, face_quality, landmark_spotcheck = frame_bundle[-1]
        session.frames_processed += 1
        self._apply_stream_progress(
            session,
            latest_frame=latest_frame,
            face_detection=face_detection,
            face_quality=face_quality,
            landmark_spotcheck=landmark_spotcheck,
            frame_bundle=frame_bundle,
        )
        await self.store.save_session(session)
        return session

    async def record_landmarks(self, session_id: str, event: WebSocketClientEvent) -> SessionRecord:
        self._ensure_verifier_ready(action="landmark processing")
        session = await self._get_session_record(session_id)
        if session.status in {SessionStatus.VERIFIED, SessionStatus.FAILED, SessionStatus.EXPIRED}:
            return session

        if session.frame_payloads:
            session.frame_payloads[-1]["landmarks"] = event.landmarks or {}
            metadata = dict(session.frame_payloads[-1].get("metadata", {}))
            metadata.update(event.metadata or {})
            session.frame_payloads[-1]["metadata"] = clear_cached_frame_analysis(metadata)
        else:
            session.frame_payloads.append(
                {
                    "type": ClientEventType.LANDMARKS.value,
                    "frame_index": 0,
                    "timestamp": event.timestamp.isoformat(),
                    "image_base64": None,
                    "landmarks": event.landmarks or {},
                    "metadata": event.metadata or {},
                }
            )

        frame_bundle = self.frame_evaluator.build_frame_bundle(session.frame_payloads)
        latest_frame, face_detection, face_quality, landmark_spotcheck = frame_bundle[-1]
        self._apply_stream_progress(
            session,
            latest_frame=latest_frame,
            face_detection=face_detection,
            face_quality=face_quality,
            landmark_spotcheck=landmark_spotcheck,
            frame_bundle=frame_bundle,
        )
        await self.store.save_session(session)
        return session

    async def record_heartbeat(self, session_id: str) -> SessionRecord:
        session = await self._get_session_record(session_id)
        session.updated_at = datetime.now(tz=UTC)
        if session.status == SessionStatus.CREATED:
            session.status = SessionStatus.READY
            session.step_status = StepStatus.ACTIVE
            session.finalize_ready = False
        session.last_message = "Heartbeat acknowledged"
        await self.store.save_session(session)
        return session

    async def finalize_session(
        self,
        session_id: str,
        mode: VerificationMode = VerificationMode.FULL,
    ) -> VerificationResult:
        self._ensure_verifier_ready(action="finalization")
        session = await self._get_session_record(session_id)
        self.logger.info(
            "finalize requested",
            context={
                "session_id": session.session_id,
                "evaluation_mode": mode.value,
                "current_challenge_index": session.current_challenge_index,
                "completed_challenges": [step.value for step in session.completed_challenges],
                "total_challenges": session.total_challenges,
            },
        )

        if mode == VerificationMode.FULL and not session.finalize_ready:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Verification is still collecting security evidence. Keep facing the camera for a moment longer.",
            )

        session.status = SessionStatus.PROCESSING
        session.last_message = "Running verification pipeline"
        session.finalize_ready = False
        session.updated_at = datetime.now(tz=UTC)
        await self.store.save_session(session)

        frame_bundle = self.frame_evaluator.build_frame_bundle(session.frame_payloads)
        frames = [frame for frame, _, _, _ in frame_bundle]
        face_detections = [face_detection for _, face_detection, _, _ in frame_bundle]
        quality_evaluations = [quality for _, _, quality, _ in frame_bundle]
        landmark_spotchecks = [spotcheck for _, _, _, spotcheck in frame_bundle]
        usable_frame_bundle = [
            (frame, face_detection, quality, spotcheck)
            for frame, face_detection, quality, spotcheck in frame_bundle
            if face_detection.detected and quality.passed and spotcheck.passed
        ]
        usable_frames = [frame for frame, _, _, _ in usable_frame_bundle]
        usable_face_detections = [face_detection for _, face_detection, _, _ in usable_frame_bundle]
        face_detected = any(result.detected for result in face_detections)
        quality_frames_available = bool(usable_frames)
        liveness = self._final_liveness_evaluation(session, usable_frames if usable_frames else frames)
        antispoof = self.antispoof_evaluator.evaluate(usable_frames, usable_face_detections)
        deepfake = self.deepfake_evaluator.evaluate(
            usable_frames,
            usable_face_detections,
            max_samples=self.deepfake_sample_frames,
        )
        human_face = self._evaluate_human_face_session(usable_frames, usable_face_detections)
        self.logger.info(
            "anti-spoof verdict",
            context={
                "session_id": session.session_id,
                "passed": antispoof.passed,
                "spoof_score": antispoof.spoof_score,
                "max_spoof_score": antispoof.max_spoof_score,
                "flagged_frames": antispoof.flagged_frames,
            },
        )
        self.logger.info(
            "deepfake verdict",
            context={
                "session_id": session.session_id,
                "enabled": deepfake.enabled,
                "enforced": deepfake.enforced,
                "passed": deepfake.passed,
                "deepfake_score": deepfake.deepfake_score,
                "max_deepfake_score": deepfake.max_deepfake_score,
                "frames_processed": deepfake.frames_processed,
            },
        )

        decision = determine_finalization_decision(
            mode=mode,
            face_detected=face_detected,
            quality_frames_available=quality_frames_available,
            human_face_enabled=human_face.enabled,
            human_face_passed=human_face.passed,
            human_face_enforced=(
                human_face.enabled
                and self.settings.verifier_human_face_enforce_decision
                and mode != VerificationMode.LIVENESS_ONLY
            ),
            liveness_passed=liveness.passed,
            antispoof_passed=antispoof.passed,
            deepfake_enabled=deepfake.enabled,
            deepfake_passed=deepfake.passed,
            deepfake_enforced=(
                mode == VerificationMode.DEEPFAKE_ONLY
                or (deepfake.enabled and deepfake.enforced and mode != VerificationMode.LIVENESS_ONLY)
            ),
        )
        human = decision.human
        failure_reason = decision.failure_reason
        face_confidences = [item.confidence for item in face_detections if item.detected]
        face_confidence = sum(face_confidences) / len(face_confidences) if face_confidences else 0.0
        quality_score = (
            sum(item.score for item in quality_evaluations) / len(quality_evaluations)
            if quality_evaluations
            else 0.0
        )
        confidence = calculate_terminal_confidence(
            mode=mode,
            face_confidence=face_confidence,
            quality_score=quality_score,
            liveness_confidence=liveness.confidence,
            spoof_score=antispoof.spoof_score,
            max_spoof_score=antispoof.max_spoof_score,
            deepfake_score=deepfake.deepfake_score if deepfake.enabled else None,
            max_deepfake_score=deepfake.max_deepfake_score if deepfake.enabled else None,
        )

        proof_id: str | None = None
        transaction_digest: str | None = None
        proof_operation: str | None = None
        chain_network: str | None = None
        walrus_blob_id: str | None = None
        walrus_blob_object_id: str | None = None
        seal_identity: str | None = None
        evidence_schema_version: int | None = None
        model_hash: str | None = None
        expires_at = None

        attack_analysis = build_attack_analysis(
            human=human,
            failure_reason=failure_reason,
            spoof_score=antispoof.spoof_score,
            max_spoof_score=antispoof.max_spoof_score,
            antispoof_passed=antispoof.passed,
            deepfake_enabled=deepfake.enabled,
            deepfake_score=deepfake.deepfake_score,
            max_deepfake_score=deepfake.max_deepfake_score,
            deepfake_passed=deepfake.passed,
        )

        if human:
            session.status = SessionStatus.VERIFIED
            session.last_message = (
                "Verification approved. Ready to mint proof."
                if mode == VerificationMode.FULL
                else "Verification completed"
            )
        else:
            session.status = SessionStatus.FAILED
            session.last_message = failure_reason.replace("_", " ") if failure_reason else "Verification failed"

        result = VerificationResult(
            session_id=session.session_id,
            status=session.status,
            evaluation_mode=mode,
            human=human,
            challenge_type=session.challenge_type,
            challenge_sequence=session.challenge_sequence,
            current_challenge_index=session.current_challenge_index,
            total_challenges=session.total_challenges,
            completed_challenges=session.completed_challenges,
            confidence=confidence,
            spoof_score=antispoof.spoof_score,
            max_spoof_score=antispoof.max_spoof_score,
            human_face_score=human_face.human_face_score,
            human_face_message=human_face.message,
            human_face_enabled=human_face.enabled,
            deepfake_score=deepfake.deepfake_score,
            max_deepfake_score=deepfake.max_deepfake_score,
            deepfake_frames_processed=deepfake.frames_processed,
            deepfake_message=deepfake.message,
            deepfake_enabled=deepfake.enabled,
            attack_analysis=attack_analysis,
            proof_id=proof_id,
            transaction_digest=transaction_digest,
            proof_operation=proof_operation,
            chain_network=chain_network,
            walrus_blob_id=walrus_blob_id,
            walrus_blob_object_id=walrus_blob_object_id,
            seal_identity=seal_identity,
            evidence_schema_version=evidence_schema_version,
            model_hash=model_hash,
            blob_id=walrus_blob_id,
            expires_at=expires_at,
            failure_reason=failure_reason,
        )

        session.result = result
        session.frames_processed = len(frames)
        session.progress = 1.0
        session.step_progress = 1.0 if session.all_challenges_completed else session.step_progress
        session.updated_at = datetime.now(tz=UTC)
        session.debug = build_session_debug_payload(
            latest_frame=frames[-1] if frames else None,
            face_detection=face_detections[-1] if face_detections else None,
            face_quality=quality_evaluations[-1] if quality_evaluations else None,
            landmark_spotcheck=landmark_spotchecks[-1] if landmark_spotchecks else None,
            human_face=human_face,
            antispoof=antispoof,
            deepfake=deepfake,
            antispoof_preview=False,
            current_step=session.challenge_type,
            step_progress=session.step_progress,
            message=session.last_message,
        )
        await self.store.save_session(session)

        self.logger.info(
            "terminal result",
            context={
                "session_id": session.session_id,
                "status": session.status.value,
                "evaluation_mode": mode.value,
                "human": human,
                "challenge_type": session.challenge_type.value,
                "completed_challenges": [step.value for step in session.completed_challenges],
                "confidence": confidence,
                "spoof_score": antispoof.spoof_score,
                "deepfake_score": deepfake.deepfake_score,
                "human_face_score": human_face.human_face_score,
                "failure_reason": failure_reason,
                "attack_family": attack_analysis["suspected_attack_family"],
                "walrus_blob_id": walrus_blob_id,
                "seal_identity": seal_identity,
            },
        )
        return result

    async def prepare_wallet_claim(self, session_id: str) -> PreparedProofClaim:
        self._ensure_verifier_ready(action="proof claim preparation")
        session = await self._get_session_record(session_id)
        self._ensure_session_ready_for_proof_action(session, action="prepare a proof claim")

        if session.pending_proof_claim is not None:
            if session.pending_proof_claim.claim_expires_at_ms > int(datetime.now(tz=UTC).timestamp() * 1000):
                return session.pending_proof_claim
            self._cleanup_stored_blob(session.pending_proof_claim.walrus_blob_id)
            session.pending_proof_claim = None

        session.status = SessionStatus.PROCESSING
        session.last_message = "Preparing wallet claim"
        session.updated_at = datetime.now(tz=UTC)
        await self.store.save_session(session)

        try:
            pipeline_result, prepared_claim = self._build_prepared_wallet_claim(session)
        except HTTPException:
            raise
        except Exception as exc:
            self.logger.exception(
                "proof claim preparation failed after verification approval",
                context={
                    "session_id": session.session_id,
                    "wallet_address": session.wallet_address,
                    "error": str(exc),
                },
            )
            session.status = SessionStatus.VERIFIED
            session.last_message = "Could not prepare the wallet claim."
            session.updated_at = datetime.now(tz=UTC)
            await self.store.save_session(session)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Could not prepare the wallet claim for proof minting.",
            ) from exc

        session.result = self._merge_claim_metadata_into_result(session.result, prepared_claim)
        session.pending_proof_claim = prepared_claim
        session.status = SessionStatus.VERIFIED
        session.last_message = "Approve the wallet transaction to mint the proof."
        session.updated_at = datetime.now(tz=UTC)
        await self.store.save_session(session)
        return prepared_claim

    async def complete_wallet_claim(
        self,
        session_id: str,
        payload: CompleteProofClaimRequest,
    ) -> VerificationResult:
        session = await self._get_session_record(session_id)
        pending_claim = session.pending_proof_claim
        if pending_claim is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="No prepared wallet claim exists for this session.",
            )
        if session.result is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Session result is unavailable for proof completion.",
            )

        proof_id = pending_claim.proof_object_id
        if pending_claim.operation is ProofClaimOperation.MINT:
            proof_id = payload.proof_id or await self._resolve_active_proof_id(session.wallet_address)
        if not proof_id:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Wallet transaction succeeded, but the proof object could not be resolved yet.",
            )

        updated_result = session.result.model_copy(
            update={
                "proof_id": proof_id,
                "transaction_digest": payload.transaction_digest,
                "proof_operation": (
                    "renewed" if pending_claim.operation is ProofClaimOperation.RENEW else "minted"
                ),
                "chain_network": pending_claim.chain_network,
                "walrus_blob_id": pending_claim.walrus_blob_id,
                "walrus_blob_object_id": pending_claim.walrus_blob_object_id,
                "seal_identity": pending_claim.seal_identity,
                "evidence_schema_version": pending_claim.evidence_schema_version,
                "model_hash": pending_claim.model_hash,
                "blob_id": pending_claim.walrus_blob_id,
                "expires_at": datetime.fromtimestamp(pending_claim.expires_at_ms / 1000, tz=UTC),
            }
        )
        session.result = updated_result
        session.pending_proof_claim = None
        session.status = SessionStatus.VERIFIED
        session.last_message = "Proof minted successfully"
        session.expires_at = updated_result.expires_at or session.expires_at
        session.updated_at = datetime.now(tz=UTC)
        await self.store.save_session(session)
        return updated_result

    async def cancel_wallet_claim(self, session_id: str, reason: str | None = None) -> VerificationResult:
        session = await self._get_session_record(session_id)
        pending_claim = session.pending_proof_claim
        if pending_claim is None or session.result is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="No prepared wallet claim exists for this session.",
            )

        self._cleanup_stored_blob(pending_claim.walrus_blob_id)
        session.pending_proof_claim = None
        session.result = session.result.model_copy(
            update={
                "walrus_blob_id": None,
                "walrus_blob_object_id": None,
                "seal_identity": None,
                "evidence_schema_version": None,
                "model_hash": None,
                "blob_id": None,
            }
        )
        session.status = SessionStatus.VERIFIED
        session.last_message = reason or "Wallet mint cancelled."
        session.updated_at = datetime.now(tz=UTC)
        await self.store.save_session(session)
        return session.result

    async def mint_verified_session(self, session_id: str) -> VerificationResult:
        self._ensure_verifier_ready(action="proof minting")
        session = await self._get_session_record(session_id)

        if session.result is None or session.result.status is not SessionStatus.VERIFIED or not session.result.human:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Finalize verification successfully before minting a proof.",
            )

        if session.result.proof_id:
            return session.result

        if session.result.evaluation_mode is not VerificationMode.FULL:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Proof minting is only available for full verification sessions.",
            )

        session.status = SessionStatus.PROCESSING
        session.last_message = "Minting proof"
        session.updated_at = datetime.now(tz=UTC)
        await self.store.save_session(session)

        frame_bundle = self.frame_evaluator.build_frame_bundle(session.frame_payloads)
        frames = [frame for frame, _, _, _ in frame_bundle]
        quality_evaluations = [quality for _, _, quality, _ in frame_bundle]
        usable_frame_bundle = [
            (frame, face_detection, quality, spotcheck)
            for frame, face_detection, quality, spotcheck in frame_bundle
            if face_detection.detected and quality.passed and spotcheck.passed
        ]
        usable_frames = [frame for frame, _, _, _ in usable_frame_bundle]
        usable_face_detections = [face_detection for _, face_detection, _, _ in usable_frame_bundle]
        liveness = self._final_liveness_evaluation(session, usable_frames if usable_frames else frames)
        antispoof = self.antispoof_evaluator.evaluate(usable_frames, usable_face_detections)
        deepfake = self.deepfake_evaluator.evaluate(
            usable_frames,
            usable_face_detections,
            max_samples=self.deepfake_sample_frames,
        )
        human_face = self._evaluate_human_face_session(usable_frames, usable_face_detections)

        evidence = self.evidence_assembler.assemble(
            evidence_schema_version=_EVIDENCE_SCHEMA_VERSION,
            session_id=session.session_id,
            wallet_address=session.wallet_address,
            challenge_type=self._to_pipeline_challenge(session.challenge_type),
            challenge_sequence=[step.value for step in session.challenge_sequence],
            session_started_at=session.created_at.isoformat(),
            session_completed_at=datetime.now(tz=UTC).isoformat(),
            frames=usable_frames,
            liveness=liveness,
            antispoof=antispoof,
            deepfake=deepfake,
            human_face=human_face,
            quality_evaluations=quality_evaluations,
            face_detections=usable_face_detections,
            attack_analysis=session.result.attack_analysis,
            evaluation_mode=session.result.evaluation_mode.value,
            human=True,
            confidence=session.result.confidence,
        )

        try:
            encrypted_evidence = self.evidence_encryptor.encrypt_for_wallet(
                session.wallet_address,
                json.loads(
                    json.dumps(
                        asdict(evidence),
                        default=lambda value: value.value if hasattr(value, "value") else value,
                    )
                ),
            )
            stored_blob = self.evidence_store.put_encrypted_blob(
                encrypted_evidence.encrypted_bytes,
                metadata={
                    "session_id": session.session_id,
                    "wallet_address": session.wallet_address,
                    "challenge_type": session.challenge_type.value,
                    "seal_identity": encrypted_evidence.seal_identity,
                    "evidence_schema_version": evidence.evidence_schema_version,
                },
            )
            walrus_blob_id = stored_blob.blob_id
            walrus_blob_object_id = stored_blob.blob_object_id
            seal_identity = encrypted_evidence.seal_identity
            evidence_schema_version = evidence.evidence_schema_version
            model_hash = evidence.model_hashes.get("verifier_bundle")
            pipeline_result = self._pipeline_result(
                session_id=session.session_id,
                wallet_address=session.wallet_address,
                challenge_type=self._to_pipeline_challenge(session.challenge_type),
                status=SessionStatus.VERIFIED,
                human=True,
                confidence=session.result.confidence,
                spoof_score=session.result.spoof_score,
                walrus_blob_id=walrus_blob_id,
                walrus_blob_object_id=walrus_blob_object_id,
                seal_identity=seal_identity,
                evidence_schema_version=evidence_schema_version,
                model_hash=model_hash,
                failure_reason=None,
            )
            active_proof = self.proof_minter.find_active_proof(session.wallet_address)
            planned_operation = "renewed" if active_proof is not None else "minted"
            if active_proof is not None:
                proof_result = self.proof_minter.renew_proof(
                    pipeline_result,
                    active_proof.proof_id,
                )
            else:
                try:
                    proof_result = self.proof_minter.mint_proof(pipeline_result)
                except CommandExecutionError as exc:
                    if not self._looks_like_duplicate_active_proof_error(exc):
                        raise
                    active_proof = self.proof_minter.find_active_proof(session.wallet_address)
                    if active_proof is None:
                        raise
                    planned_operation = "renewed"
                    proof_result = self.proof_minter.renew_proof(
                        pipeline_result,
                        active_proof.proof_id,
                    )
        except HTTPException:
            raise
        except Exception as exc:
            if "walrus_blob_id" in locals():
                self._cleanup_stored_blob(walrus_blob_id)
            self.logger.exception(
                "proof mint failed after verification approval",
                context={
                    "session_id": session.session_id,
                    "wallet_address": session.wallet_address,
                    "error": str(exc),
                },
            )
            session.status = SessionStatus.VERIFIED
            session.last_message = "Proof mint failed after verification approval."
            session.updated_at = datetime.now(tz=UTC)
            await self.store.save_session(session)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Proof minting failed after verification approval.",
            ) from exc

        if not proof_result.success:
            self._cleanup_stored_blob(walrus_blob_id)
            session.status = SessionStatus.VERIFIED
            session.last_message = "Proof mint failed after verification approval."
            session.updated_at = datetime.now(tz=UTC)
            await self.store.save_session(session)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=proof_result.reason or "Proof minting failed after verification approval.",
            )

        updated_result = session.result.model_copy(
            update={
                "proof_id": proof_result.proof_id,
                "transaction_digest": proof_result.transaction_digest,
                "proof_operation": proof_result.proof_operation or planned_operation,
                "chain_network": (
                    proof_result.chain_network
                    or str(proof_result.metadata.get("network") or "")
                    or None
                ),
                "walrus_blob_id": proof_result.walrus_blob_id or walrus_blob_id,
                "walrus_blob_object_id": proof_result.walrus_blob_object_id or walrus_blob_object_id,
                "seal_identity": proof_result.seal_identity or seal_identity,
                "evidence_schema_version": proof_result.evidence_schema_version or evidence_schema_version,
                "model_hash": proof_result.model_hash or model_hash,
                "blob_id": proof_result.walrus_blob_id or walrus_blob_id,
                "expires_at": self._parse_datetime_string(proof_result.expires_at),
            }
        )
        session.result = updated_result
        session.status = SessionStatus.VERIFIED
        session.last_message = "Proof minted successfully"
        session.expires_at = updated_result.expires_at or session.expires_at
        session.updated_at = datetime.now(tz=UTC)
        await self.store.save_session(session)
        return updated_result

    def _ensure_session_ready_for_proof_action(self, session: SessionRecord, *, action: str) -> None:
        if session.result is None or session.result.status is not SessionStatus.VERIFIED or not session.result.human:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Finalize verification successfully before attempting to {action}.",
            )

        if session.result.proof_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This session already has a minted proof.",
            )

        if session.result.evaluation_mode is not VerificationMode.FULL:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Proof minting is only available for full verification sessions.",
            )

    def _build_prepared_wallet_claim(
        self,
        session: SessionRecord,
    ) -> tuple[VerificationResult, PreparedProofClaim]:
        proof_confidence = max(
            session.result.confidence if session.result else 0.0,
            self.settings.verifier_proof_minimum_confidence,
        )
        frame_bundle = self.frame_evaluator.build_frame_bundle(session.frame_payloads)
        frames = [frame for frame, _, _, _ in frame_bundle]
        quality_evaluations = [quality for _, _, quality, _ in frame_bundle]
        usable_frame_bundle = [
            (frame, face_detection, quality, spotcheck)
            for frame, face_detection, quality, spotcheck in frame_bundle
            if face_detection.detected and quality.passed and spotcheck.passed
        ]
        usable_frames = [frame for frame, _, _, _ in usable_frame_bundle]
        usable_face_detections = [face_detection for _, face_detection, _, _ in usable_frame_bundle]
        liveness = self._final_liveness_evaluation(session, usable_frames if usable_frames else frames)
        antispoof = self.antispoof_evaluator.evaluate(usable_frames, usable_face_detections)
        deepfake = self.deepfake_evaluator.evaluate(
            usable_frames,
            usable_face_detections,
            max_samples=self.deepfake_sample_frames,
        )
        human_face = self._evaluate_human_face_session(usable_frames, usable_face_detections)

        evidence = self.evidence_assembler.assemble(
            evidence_schema_version=_EVIDENCE_SCHEMA_VERSION,
            session_id=session.session_id,
            wallet_address=session.wallet_address,
            challenge_type=self._to_pipeline_challenge(session.challenge_type),
            challenge_sequence=[step.value for step in session.challenge_sequence],
            session_started_at=session.created_at.isoformat(),
            session_completed_at=datetime.now(tz=UTC).isoformat(),
            frames=usable_frames,
            liveness=liveness,
            antispoof=antispoof,
            deepfake=deepfake,
            human_face=human_face,
            quality_evaluations=quality_evaluations,
            face_detections=usable_face_detections,
            attack_analysis=session.result.attack_analysis if session.result else None,
            evaluation_mode=session.result.evaluation_mode.value if session.result else VerificationMode.FULL.value,
            human=True,
            confidence=proof_confidence,
        )

        encrypted_evidence = self.evidence_encryptor.encrypt_for_wallet(
            session.wallet_address,
            json.loads(
                json.dumps(
                    asdict(evidence),
                    default=lambda value: value.value if hasattr(value, "value") else value,
                )
            ),
        )
        stored_blob = self.evidence_store.put_encrypted_blob(
            encrypted_evidence.encrypted_bytes,
            metadata={
                "session_id": session.session_id,
                "wallet_address": session.wallet_address,
                "challenge_type": session.challenge_type.value,
                "seal_identity": encrypted_evidence.seal_identity,
                "evidence_schema_version": evidence.evidence_schema_version,
            },
        )
        walrus_blob_id = stored_blob.blob_id
        walrus_blob_object_id = stored_blob.blob_object_id
        seal_identity = encrypted_evidence.seal_identity
        evidence_schema_version = evidence.evidence_schema_version
        model_hash = evidence.model_hashes.get("verifier_bundle")

        pipeline_result = self._pipeline_result(
            session_id=session.session_id,
            wallet_address=session.wallet_address,
            challenge_type=self._to_pipeline_challenge(session.challenge_type),
            status=SessionStatus.VERIFIED,
            human=True,
            confidence=proof_confidence,
            spoof_score=session.result.spoof_score if session.result else 0.0,
            walrus_blob_id=walrus_blob_id,
            walrus_blob_object_id=walrus_blob_object_id,
            seal_identity=seal_identity,
            evidence_schema_version=evidence_schema_version,
            model_hash=model_hash,
            failure_reason=None,
        )

        active_proof = self.proof_minter.find_active_proof(session.wallet_address)
        claim_issued_at = datetime.now(tz=UTC)
        proof_expires_at = claim_issued_at + timedelta(days=self.settings.verifier_sui_proof_ttl_days)
        claim_expires_at = claim_issued_at + timedelta(seconds=self.settings.verifier_sui_claim_ttl_seconds)
        prepared_claim = self.proof_minter.prepare_wallet_claim(
            pipeline_result,
            operation=ProofClaimOperation.RENEW if active_proof is not None else ProofClaimOperation.MINT,
            claim_id=uuid4().hex,
            claim_expires_at_ms=int(claim_expires_at.timestamp() * 1000),
            issued_at_ms=int(claim_issued_at.timestamp() * 1000),
            expires_at_ms=int(proof_expires_at.timestamp() * 1000),
            proof_object_id=active_proof.proof_id if active_proof is not None else None,
        )
        return pipeline_result, prepared_claim

    async def _resolve_active_proof_id(self, wallet_address: str) -> str | None:
        for _ in range(5):
            active_proof = self.proof_minter.find_active_proof(wallet_address)
            if active_proof is not None:
                return active_proof.proof_id
            await asyncio.sleep(0.5)
        return None

    def _merge_claim_metadata_into_result(
        self,
        result: VerificationResult | None,
        claim: PreparedProofClaim,
    ) -> VerificationResult:
        if result is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Session result is unavailable for proof preparation.",
            )
        return result.model_copy(
            update={
                "chain_network": claim.chain_network,
                "walrus_blob_id": claim.walrus_blob_id,
                "walrus_blob_object_id": claim.walrus_blob_object_id,
                "seal_identity": claim.seal_identity,
                "evidence_schema_version": claim.evidence_schema_version,
                "model_hash": claim.model_hash,
                "blob_id": claim.walrus_blob_id,
                "expires_at": datetime.fromtimestamp(claim.expires_at_ms / 1000, tz=UTC),
            }
        )

    def _looks_like_duplicate_active_proof_error(self, error: CommandExecutionError) -> bool:
        message = str(error)
        return (
            "verify_and_mint" in message
            and ("code 1" in message or "E_ACTIVE_PROOF_EXISTS" in message)
        )

    async def get_health(self) -> HealthResponse:
        redis_ok = await self.store.ping()
        deepfake_ready = (not self.deepfake_evaluator.enabled) or self.deepfake_evaluator.models_ready
        human_face_ready = (not self.human_face_evaluator.enabled) or self.human_face_evaluator.models_ready
        models_ready = (
            self.face_detector.models_ready
            and self.antispoof_evaluator.models_ready
            and deepfake_ready
            and human_face_ready
        )
        return HealthResponse(
            status="ready" if redis_ok else "degraded",
            redis="ready" if redis_ok else "degraded",
            models="ready" if models_ready else "degraded",
            chain_adapter=self._adapter_health_status(self.settings.effective_chain_adapter_mode),
            storage_adapter=self._adapter_health_status(self.settings.effective_storage_adapter_mode),
            encryption_adapter=self._adapter_health_status(
                self.settings.effective_encryption_adapter_mode
            ),
            model_details={
                "face_detector": {
                    "ready": self.face_detector.models_ready,
                    "runtime": self.face_detector.runtime_label,
                },
                "antispoof": {
                    "ready": self.antispoof_evaluator.models_ready,
                    "runtime": self.antispoof_evaluator.runtime_label,
                    "threshold": self.settings.verifier_antispoof_threshold,
                    "hard_fail_threshold": self.settings.verifier_antispoof_hard_fail_threshold,
                },
                "deepfake": {
                    "enabled": self.deepfake_evaluator.enabled,
                    "ready": self.deepfake_evaluator.models_ready,
                    "runtime": self.deepfake_evaluator.runtime_label,
                    "threshold": self.settings.verifier_deepfake_threshold,
                    "enforced": self.settings.verifier_deepfake_enforce_decision,
                    "sample_frames": self.deepfake_sample_frames,
                    "model_hash": self.deepfake_evaluator.model_hash,
                },
                "human_face": {
                    "enabled": self.human_face_evaluator.enabled,
                    "ready": self.human_face_evaluator.models_ready,
                    "runtime": self.human_face_evaluator.runtime_label,
                    "threshold": self.settings.verifier_human_face_threshold,
                    "enforced": self.settings.verifier_human_face_enforce_decision,
                    "model_hash": self.human_face_evaluator.model_hash,
                },
            },
            tuning={
                "minimum_step_frames": self.minimum_step_frames,
                "blink_closed_threshold": self.settings.verifier_liveness_blink_closed_threshold,
                "blink_open_threshold": self.settings.verifier_liveness_blink_open_threshold,
                "blink_min_closed_frames": self.settings.verifier_liveness_blink_min_closed_frames,
                "quality_blur_threshold": self.settings.verifier_quality_blur_threshold,
                "quality_min_face_size": self.settings.verifier_quality_min_face_size,
                "quality_max_yaw_degrees": self.settings.verifier_quality_max_yaw_degrees,
                "quality_max_pitch_degrees": self.settings.verifier_quality_max_pitch_degrees,
                "quality_min_brightness": self.settings.verifier_quality_min_brightness,
                "quality_max_brightness": self.settings.verifier_quality_max_brightness,
                "human_face_threshold": self.settings.verifier_human_face_threshold,
                "landmark_spotcheck_max_center_mismatch_px": self.settings.verifier_landmark_spotcheck_max_center_mismatch_px,
                "turn_yaw_threshold_degrees": self.settings.verifier_liveness_turn_yaw_threshold_degrees,
                "turn_offset_threshold": self.settings.verifier_liveness_turn_offset_threshold,
                "nod_pitch_threshold": self.settings.verifier_liveness_nod_pitch_threshold,
                "nod_pitch_ratio_threshold": self.settings.verifier_liveness_nod_pitch_ratio_threshold,
                "smile_ratio_threshold": self.settings.verifier_liveness_smile_ratio_threshold,
                "motion_min_displacement": self.settings.verifier_liveness_motion_min_displacement,
                "motion_max_still_ratio": self.settings.verifier_liveness_motion_max_still_ratio,
                "motion_min_transitions": self.settings.verifier_liveness_motion_min_transitions,
                "deepfake_threshold": self.settings.verifier_deepfake_threshold,
                "deepfake_sample_frames": self.deepfake_sample_frames,
                "deepfake_enforced": self.settings.verifier_deepfake_enforce_decision,
                "proof_minimum_confidence": self.settings.verifier_proof_minimum_confidence,
            },
        )

    def _admin_frame_payload(self, payload) -> dict[str, object]:
        return {
            "type": ClientEventType.FRAME.value,
            "frame_index": payload.frame_index,
            "timestamp": payload.timestamp.isoformat(),
            "image_base64": payload.image_base64,
            "landmarks": payload.landmarks or {},
            "metadata": payload.metadata or {},
        }

    def _admin_frame_bundle(
        self,
        payloads,
    ) -> list[
        tuple[
            FrameInput,
            FaceDetectionResult,
            FaceQualityEvaluation,
            LandmarkSpotCheckEvaluation,
        ]
    ]:
        return self.frame_evaluator.build_frame_bundle(
            [self._admin_frame_payload(payload) for payload in payloads]
        )

    def _split_frame_bundle(
        self,
        frame_bundle: list[
            tuple[
                FrameInput,
                FaceDetectionResult,
                FaceQualityEvaluation,
                LandmarkSpotCheckEvaluation,
            ]
        ],
    ) -> tuple[
        list[FrameInput],
        list[FaceDetectionResult],
        list[FaceQualityEvaluation],
        list[LandmarkSpotCheckEvaluation],
        list[FrameInput],
        list[FaceDetectionResult],
        list[int],
    ]:
        frames = [frame for frame, _, _, _ in frame_bundle]
        face_detections = [face_detection for _, face_detection, _, _ in frame_bundle]
        quality_evaluations = [quality for _, _, quality, _ in frame_bundle]
        landmark_spotchecks = [spotcheck for _, _, _, spotcheck in frame_bundle]
        usable_frames: list[FrameInput] = []
        usable_face_detections: list[FaceDetectionResult] = []
        accepted_indices: list[int] = []
        for frame, face_detection, quality, spotcheck in frame_bundle:
            if face_detection.detected and quality.passed and spotcheck.passed:
                usable_frames.append(frame)
                usable_face_detections.append(face_detection)
                accepted_indices.append(frame.frame_index)
        return (
            frames,
            face_detections,
            quality_evaluations,
            landmark_spotchecks,
            usable_frames,
            usable_face_detections,
            accepted_indices,
        )

    def _face_detection_payload(
        self,
        face_detection: FaceDetectionResult | None,
    ) -> dict[str, Any]:
        bounding_box = None
        if face_detection is not None and face_detection.bounding_box is not None:
            bounding_box = {
                "x": face_detection.bounding_box.x,
                "y": face_detection.bounding_box.y,
                "width": face_detection.bounding_box.width,
                "height": face_detection.bounding_box.height,
            }
        return {
            "detected": bool(face_detection.detected) if face_detection is not None else False,
            "confidence": face_detection.confidence if face_detection is not None else 0.0,
            "bounding_box": bounding_box,
            "message": face_detection.message if face_detection is not None else "No face detected in frame",
        }

    def _quality_payload(
        self,
        face_quality: FaceQualityEvaluation | None,
    ) -> dict[str, Any]:
        return {
            "passed": face_quality.passed if face_quality is not None else False,
            "score": face_quality.score if face_quality is not None else 0.0,
            "primary_issue": face_quality.primary_issue if face_quality is not None else None,
            "message": face_quality.message if face_quality is not None else "Improve frame quality",
            "feedback": face_quality.feedback if face_quality is not None else [],
            "checks": face_quality.checks if face_quality is not None else {},
            "metrics": face_quality.metrics if face_quality is not None else {},
        }

    def _spotcheck_payload(
        self,
        spotcheck: LandmarkSpotCheckEvaluation | None,
    ) -> dict[str, Any]:
        return {
            "enforced": spotcheck.enforced if spotcheck is not None else False,
            "passed": spotcheck.passed if spotcheck is not None else True,
            "message": spotcheck.message if spotcheck is not None else "Landmark spot-check unavailable",
            "mismatch_pixels": spotcheck.mismatch_pixels if spotcheck is not None else None,
            "threshold_pixels": spotcheck.threshold_pixels if spotcheck is not None else None,
            "anchors_used": spotcheck.anchors_used if spotcheck is not None else 0,
            "landmark_center": spotcheck.landmark_center if spotcheck is not None else None,
            "face_center": spotcheck.face_center if spotcheck is not None else None,
        }

    def _human_face_payload(
        self,
        human_face: HumanFaceEvaluation | None,
    ) -> dict[str, Any]:
        return {
            "enabled": human_face.enabled if human_face is not None else False,
            "enforced": human_face.enforced if human_face is not None else False,
            "passed": human_face.passed if human_face is not None else False,
            "score": human_face.human_face_score if human_face is not None else None,
            "top_label": human_face.top_label if human_face is not None else None,
            "frames_processed": human_face.frames_processed if human_face is not None else 0,
            "message": (
                human_face.message if human_face is not None else "Human-face scoring disabled"
            ),
        }

    def _liveness_payload(self, liveness: LivenessEvaluation) -> dict[str, Any]:
        return {
            "passed": liveness.passed,
            "progress": liveness.progress,
            "frames_processed": liveness.frames_processed,
            "matched_signals": liveness.matched_signals,
            "required_signals": liveness.required_signals,
            "confidence": liveness.confidence,
            "message": liveness.message,
            "challenge_type": liveness.challenge_type.value,
        }

    def _antispoof_payload(
        self,
        antispoof: AntiSpoofEvaluation,
        *,
        preview: bool,
    ) -> dict[str, Any]:
        return {
            "passed": antispoof.passed,
            "spoof_score": antispoof.spoof_score,
            "max_spoof_score": antispoof.max_spoof_score,
            "frames_processed": antispoof.frames_processed,
            "flagged_frames": antispoof.flagged_frames,
            "message": antispoof.message,
            "model_hash": antispoof.model_hash,
            "preview": preview,
        }

    def _deepfake_payload(self, deepfake: DeepfakeEvaluation) -> dict[str, Any]:
        return {
            "enabled": deepfake.enabled,
            "enforced": deepfake.enforced,
            "passed": deepfake.passed,
            "deepfake_score": deepfake.deepfake_score,
            "max_deepfake_score": deepfake.max_deepfake_score,
            "frames_processed": deepfake.frames_processed,
            "flagged_frames": deepfake.flagged_frames,
            "message": deepfake.message,
            "model_hash": deepfake.model_hash,
            "preview": False,
        }

    def _evaluate_human_face(
        self,
        frame: FrameInput,
        face_detection: FaceDetectionResult | None,
    ) -> HumanFaceEvaluation:
        return self.human_face_evaluator.evaluate(frame, face_detection)

    def _evaluate_human_face_session(
        self,
        frames: list[FrameInput],
        face_detections: list[FaceDetectionResult],
    ) -> HumanFaceEvaluation:
        if not frames or not face_detections:
            return HumanFaceEvaluation(
                enabled=self.human_face_evaluator.enabled,
                enforced=self.human_face_evaluator.enforced,
                passed=True,
                human_face_score=None,
                top_label=None,
                frames_processed=0,
                model_hash=self.human_face_evaluator.model_hash,
                message="No accepted frames available for human-face scoring",
            )

        sampled_frames = frames[-min(len(frames), 4):]
        detections_by_index = {d.frame_index: d for d in face_detections}
        evaluations = [
            self._evaluate_human_face(frame, detections_by_index.get(frame.frame_index))
            for frame in sampled_frames
        ]
        scored = [item for item in evaluations if item.human_face_score is not None]
        if not scored:
            return HumanFaceEvaluation(
                enabled=self.human_face_evaluator.enabled,
                enforced=self.human_face_evaluator.enforced,
                passed=False,
                human_face_score=None,
                top_label=None,
                frames_processed=0,
                model_hash=self.human_face_evaluator.model_hash,
                message="Human-face scoring unavailable for accepted frames",
            )

        average_score = round(
            sum(float(item.human_face_score or 0.0) for item in scored) / len(scored),
            4,
        )
        passed = average_score >= self.settings.verifier_human_face_threshold
        top_label = max(
            scored,
            key=lambda item: float(item.human_face_score or 0.0),
        ).top_label
        return HumanFaceEvaluation(
            enabled=scored[-1].enabled,
            enforced=scored[-1].enforced,
            passed=passed,
            human_face_score=average_score,
            top_label=top_label,
            frames_processed=len(scored),
            model_hash=scored[-1].model_hash,
            message=_session_human_face_message(passed, average_score, top_label),
        )

    async def _get_session_record(self, session_id: str) -> SessionRecord:
        session = await self.store.get_session(session_id)
        if session is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found",
            )
        return session

    def session_ready_event(self, session: SessionRecord) -> dict[str, object]:
        return {
            "type": ServerEventType.SESSION_READY,
            "payload": {
                "session_id": session.session_id,
                "message": f"Session ready. Start with {self._step_label(session.challenge_type)}.",
            },
        }

    def challenge_update_event(self, session: SessionRecord) -> dict[str, object]:
        return {
            "type": ServerEventType.CHALLENGE_UPDATE,
            "payload": session.to_progress().model_dump(mode="json"),
        }

    def progress_event(self, session: SessionRecord) -> dict[str, object]:
        return {
            "type": ServerEventType.PROGRESS,
            "payload": session.to_progress().model_dump(mode="json"),
        }

    def processing_event(self, session_id: str) -> dict[str, object]:
        return {
            "type": ServerEventType.PROCESSING,
            "payload": {
                "session_id": session_id,
                "status": SessionStatus.PROCESSING,
                "message": "Running verification pipeline",
            },
        }

    def verified_event(self, result: VerificationResult) -> dict[str, object]:
        return {
            "type": ServerEventType.VERIFIED,
            "payload": result.model_dump(mode="json"),
        }

    def failed_event(self, result: VerificationResult) -> dict[str, object]:
        return {
            "type": ServerEventType.FAILED,
            "payload": result.model_dump(mode="json"),
        }

    def terminal_event(self, result: VerificationResult) -> dict[str, object]:
        if result.status == SessionStatus.VERIFIED:
            return self.verified_event(result)
        return self.failed_event(result)

    def error_event(self, message: str, session_id: str | None = None) -> dict[str, object]:
        return {
            "type": ServerEventType.ERROR,
            "payload": {
                "session_id": session_id or "",
                "code": "internal_error",
                "message": message,
                "retryable": True,
            },
        }

    def _select_challenge_sequence(self, session_id: str) -> list[ChallengeType]:
        rng = random.Random(session_id)
        sequence_length = 2 if rng.random() < 0.7 else 3
        for _ in range(128):
            sequence = rng.sample(_FRIENDLY_CHALLENGE_POOL, k=sequence_length)
            if self._sequence_is_valid(sequence):
                return sequence

        fallback = [ChallengeType.TURN_RIGHT, ChallengeType.SMILE]
        if sequence_length == 3:
            fallback = [ChallengeType.TURN_LEFT, ChallengeType.SMILE, ChallengeType.OPEN_MOUTH]
        return fallback

    def _resolve_challenge_sequence(
        self,
        payload: SessionCreateRequest,
        session_id: str,
    ) -> list[ChallengeType]:
        if payload.challenge_sequence:
            return list(payload.challenge_sequence)
        return self._select_challenge_sequence(session_id)

    def _sequence_is_valid(self, sequence: list[ChallengeType]) -> bool:
        if len(set(sequence)) != len(sequence):
            return False
        head_motion_count = sum(step in _HEAD_MOTION_CHALLENGES for step in sequence)
        expression_count = sum(step in _FRIENDLY_EXPRESSION_CHALLENGES for step in sequence)

        if head_motion_count == 0 or expression_count == 0:
            return False
        if len(sequence) == 2 and head_motion_count != 1:
            return False
        if len(sequence) == 3 and head_motion_count > 2:
            return False
        return True

    def _apply_stream_progress(
        self,
        session: SessionRecord,
        *,
        latest_frame: FrameInput,
        face_detection: FaceDetectionResult,
        face_quality: FaceQualityEvaluation,
        landmark_spotcheck: LandmarkSpotCheckEvaluation,
        frame_bundle: list[
            tuple[
                FrameInput,
                FaceDetectionResult,
                FaceQualityEvaluation,
                LandmarkSpotCheckEvaluation,
            ]
        ],
    ) -> None:
        active_bundle = [
            (frame, detection, quality, spotcheck)
            for frame, detection, quality, spotcheck in frame_bundle
            if frame.frame_index >= session.step_started_frame_index
        ]
        active_frames = [
            frame
            for frame, detection, quality, spotcheck in active_bundle
            if detection.detected and quality.passed and spotcheck.passed
        ]
        preview_bundle = [
            (frame, detection)
            for frame, detection, quality, spotcheck in frame_bundle
            if detection.detected and quality.passed and spotcheck.passed
        ][-_ANTI_SPOOF_PREVIEW_FRAME_LIMIT:]
        antispoof_preview = self._preview_antispoof(preview_bundle)
        human_face = self._evaluate_human_face(latest_frame, face_detection)
        current_step = session.challenge_type
        liveness = self.liveness_evaluator.evaluate(
            self._to_pipeline_challenge(current_step),
            active_frames,
        )
        has_minimum_step_frames = len(active_frames) >= self.minimum_step_frames

        session.status = SessionStatus.STREAMING
        session.finalize_ready = False
        session.updated_at = datetime.now(tz=UTC)

        if not session.all_challenges_completed and liveness.passed and has_minimum_step_frames:
            self._complete_current_step(session, latest_frame.frame_index)
            if session.all_challenges_completed:
                session.progress = 1.0
                session.step_progress = 1.0
                session.step_status = StepStatus.COMPLETED
                session.finalize_ready = self._can_finalize_stream_session(
                    face_detection=face_detection,
                    face_quality=face_quality,
                    human_face=human_face,
                )
                session.last_message = (
                    "Challenge sequence complete. Mint is ready."
                    if session.finalize_ready
                    else "Challenge sequence complete. Hold steady while security checks finish."
                )
            else:
                session.progress = round(len(session.completed_challenges) / session.total_challenges, 4)
                session.step_progress = 0.0
                session.step_status = StepStatus.ACTIVE
                session.finalize_ready = False
                session.last_message = f"Step complete. Next: {self._step_label(session.challenge_type)}."

            session.debug = build_session_debug_payload(
                latest_frame=latest_frame,
                face_detection=face_detection,
                face_quality=face_quality,
                landmark_spotcheck=landmark_spotcheck,
                human_face=human_face,
                antispoof=antispoof_preview,
                current_step=session.challenge_type,
                step_progress=session.step_progress,
                message=session.last_message,
            )
            self.logger.info(
                "step advanced",
                context={
                    "session_id": session.session_id,
                    "completed_challenges": [step.value for step in session.completed_challenges],
                    "current_challenge_index": session.current_challenge_index,
                    "challenge_type": session.challenge_type.value,
                    "step_started_frame_index": session.step_started_frame_index,
                },
            )
            return

        if session.all_challenges_completed:
            session.progress = 1.0
            session.step_progress = 1.0
            session.step_status = StepStatus.COMPLETED
            session.finalize_ready = self._can_finalize_stream_session(
                face_detection=face_detection,
                face_quality=face_quality,
                human_face=human_face,
            )
            session.last_message = (
                "Challenge sequence complete. Mint is ready."
                if session.finalize_ready
                else "Challenge sequence complete. Hold steady while security checks finish."
            )
            session.debug = build_session_debug_payload(
                latest_frame=latest_frame,
                face_detection=face_detection,
                face_quality=face_quality,
                landmark_spotcheck=landmark_spotcheck,
                human_face=human_face,
                antispoof=antispoof_preview,
                current_step=current_step,
                step_progress=session.step_progress,
                message=session.last_message,
            )
            return

        hold_progress = min(len(active_frames) / self.minimum_step_frames, 1.0)
        session.step_progress = (
            liveness.progress
            if has_minimum_step_frames or not liveness.passed
            else round(min(liveness.progress, 0.85 * hold_progress), 4)
        )
        session.step_status = StepStatus.COMPLETED if session.all_challenges_completed else StepStatus.ACTIVE
        completed_units = len(session.completed_challenges) + session.step_progress
        session.progress = round(min(0.95, completed_units / max(session.total_challenges, 1)), 4)
        session.finalize_ready = False

        preferred_message = face_quality.message if not face_quality.passed else liveness.message
        if face_quality.passed and not landmark_spotcheck.passed:
            preferred_message = landmark_spotcheck.message
        if face_quality.passed and liveness.passed and not has_minimum_step_frames:
            preferred_message = "Hold that motion for a moment"
        if not face_detection.detected and liveness.progress <= 0:
            preferred_message = face_detection.message
        session.last_message = preferred_message or self._progress_message(session.frames_processed)
        session.debug = build_session_debug_payload(
            latest_frame=latest_frame,
            face_detection=face_detection,
            face_quality=face_quality,
            landmark_spotcheck=landmark_spotcheck,
            human_face=human_face,
            antispoof=antispoof_preview,
            current_step=current_step,
            step_progress=session.step_progress,
            message=session.last_message,
        )
        self.logger.info(
            "step waiting",
            context={
                "session_id": session.session_id,
                "challenge_type": current_step.value,
                "current_challenge_index": session.current_challenge_index,
                "step_progress": liveness.progress,
                "frames_processed": session.frames_processed,
            },
        )

    def _complete_current_step(self, session: SessionRecord, completed_frame_index: int) -> None:
        completed_step = session.challenge_type
        if not session.completed_challenges or session.completed_challenges[-1] != completed_step:
            session.completed_challenges.append(completed_step)

        session.step_started_frame_index = completed_frame_index + 1
        if session.all_challenges_completed:
            session.current_challenge_index = max(session.total_challenges - 1, 0)
            session.step_status = StepStatus.COMPLETED
        else:
            session.current_challenge_index = min(len(session.completed_challenges), session.total_challenges - 1)
            session.step_status = StepStatus.ACTIVE

    def _preview_antispoof(
        self,
        preview_bundle: list[tuple[FrameInput, FaceDetectionResult]],
    ) -> AntiSpoofEvaluation | None:
        if not preview_bundle:
            return None

        frames = [frame for frame, _ in preview_bundle]
        detections = [detection for _, detection in preview_bundle]
        return self.antispoof_evaluator.evaluate(frames, detections)

    def _can_finalize_stream_session(
        self,
        *,
        face_detection: FaceDetectionResult,
        face_quality: FaceQualityEvaluation,
        human_face: HumanFaceEvaluation,
    ) -> bool:
        if not face_detection.detected or not face_quality.passed:
            return False
        return True

    def _final_liveness_evaluation(
        self,
        session: SessionRecord,
        frames: list[FrameInput],
    ) -> LivenessEvaluation:
        progress = 1.0 if session.all_challenges_completed else min(session.progress, 0.99)
        return LivenessEvaluation(
            challenge_type=self._to_pipeline_challenge(session.challenge_type),
            passed=session.all_challenges_completed,
            progress=progress,
            frames_processed=len(frames),
            matched_signals=len(session.completed_challenges),
            required_signals=session.total_challenges,
            confidence=0.99 if session.all_challenges_completed else min(0.49, progress * 0.7),
            message=(
                "Challenge sequence completed"
                if session.all_challenges_completed
                else session.last_message or "Challenge sequence incomplete"
            ),
            detected_signals=[],
        )

    def _progress_message(self, frames_processed: int) -> str:
        if frames_processed < 3:
            return "Keep your face centered"
        if frames_processed < 6:
            return "Challenge movement detected"
        if frames_processed < 9:
            return "Almost done"
        return "Ready to finalize verification"

    def _step_label(self, challenge_type: ChallengeType) -> str:
        return challenge_type.value.replace("_", " ")

    def _pipeline_result(
        self,
        *,
        session_id: str,
        wallet_address: str,
        challenge_type: PipelineChallengeType,
        status: SessionStatus,
        human: bool,
        confidence: float,
        spoof_score: float,
        walrus_blob_id: str | None,
        walrus_blob_object_id: str | None,
        seal_identity: str | None,
        evidence_schema_version: int | None,
        model_hash: str | None,
        failure_reason: str | None,
    ):
        from app.pipeline.types import VerificationResult as PipelineVerificationResult

        return PipelineVerificationResult(
            session_id=session_id,
            wallet_address=wallet_address,
            challenge_type=challenge_type,
            status=PipelineSessionStatus(status.value if isinstance(status, SessionStatus) else status),
            human=human,
            confidence=confidence,
            spoof_score=spoof_score,
            walrus_blob_id=walrus_blob_id,
            walrus_blob_object_id=walrus_blob_object_id,
            seal_identity=seal_identity,
            evidence_schema_version=evidence_schema_version,
            model_hash=model_hash,
            blob_id=walrus_blob_id,
            metadata={"failure_reason": failure_reason} if failure_reason else {},
        )

    def _cleanup_stored_blob(self, blob_id: str | None) -> None:
        if blob_id is None:
            return
        try:
            deleted = self.evidence_store.delete_blob(blob_id)
        except Exception as exc:
            self.logger.warning(
                "stored evidence blob cleanup raised after proof finalization failure",
                context={"walrus_blob_id": blob_id, "error": str(exc)},
            )
            return
        if deleted:
            return
        self.logger.warning(
            "stored evidence blob could not be deleted after proof finalization failure",
            context={"walrus_blob_id": blob_id},
        )

    def _parse_datetime_string(self, value: str | None) -> datetime | None:
        if value is None:
            return None
        return datetime.fromisoformat(value)

    def _adapter_health_status(self, mode: str) -> str:
        if mode in {"mock", "memory"}:
            return "mock"
        if mode:
            return "ready"
        return "not_configured"

    def _ensure_verifier_ready(self, *, action: str) -> None:
        ready, not_ready_models = self._verification_models_ready()
        if ready:
            return

        model_phrase = ", ".join(not_ready_models) if not_ready_models else "required models"
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Verifier models are still loading for {action}. Waiting on: {model_phrase}.",
        )

    def _verification_models_ready(self) -> tuple[bool, list[str]]:
        model_statuses = [
            ("face_detector", self.face_detector.models_ready),
            ("antispoof", self.antispoof_evaluator.models_ready),
        ]
        if self.deepfake_evaluator.enabled:
            model_statuses.append(("deepfake", self.deepfake_evaluator.models_ready))
        if self.human_face_evaluator.enabled:
            model_statuses.append(("human_face", self.human_face_evaluator.models_ready))

        not_ready_models = [label for label, ready in model_statuses if not ready]
        return (len(not_ready_models) == 0, not_ready_models)

    def _to_pipeline_challenge(
        self,
        challenge_type: ChallengeType | str,
    ) -> PipelineChallengeType:
        return PipelineChallengeType(
            challenge_type.value if isinstance(challenge_type, ChallengeType) else challenge_type
        )


def _session_human_face_message(
    passed: bool,
    score: float | None,
    top_label: str | None,
) -> str:
    if score is None:
        return "Human-face score unavailable for this session"
    if passed:
        return f"Human-face session average passed ({score:.2f}, top label: {top_label or 'unknown'})"
    return f"Human-face session average flagged a non-human or ambiguous subject ({score:.2f}, top label: {top_label or 'unknown'})"
