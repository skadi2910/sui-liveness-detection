from __future__ import annotations

from dataclasses import asdict
from datetime import UTC, datetime, timedelta
import json
import random
from typing import Any
from uuid import uuid4

from fastapi import HTTPException, status

from app.adapters.evidence_encryptor import EvidenceEncryptor
from app.adapters.evidence_store import EvidenceStore
from app.adapters.proof_minter import ProofMinter
from app.core.config import Settings, resolve_data_path
from app.core.logging import get_logger
from app.pipeline.antispoof import AntiSpoofEvaluator
from app.pipeline.evidence import EvidenceAssembler
from app.pipeline.face import FaceDetector
from app.pipeline.landmark_metrics import LandmarkSpotCheckEvaluation
from app.pipeline.liveness import LivenessEvaluator
from app.pipeline.quality import FaceQualityEvaluation, FaceQualityEvaluator
from app.pipeline.types import (
    AntiSpoofEvaluation,
    ChallengeType as PipelineChallengeType,
    FaceDetectionResult,
    FrameInput,
    LivenessEvaluation,
    SessionStatus as PipelineSessionStatus,
)
from app.sessions.debug import build_session_debug_payload
from app.sessions.finalize import (
    calculate_terminal_confidence,
    determine_finalization_decision,
)
from app.sessions.frame_pipeline import (
    SessionFrameEvaluator,
    clear_cached_frame_analysis,
)
from app.sessions.models import (
    CalibrationAppendResponse,
    ChallengeType,
    ClientEventType,
    HealthResponse,
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
_ANTI_SPOOF_PREVIEW_FRAME_LIMIT = 8


class VerificationSessionService:
    def __init__(
        self,
        store: SessionStore,
        settings: Settings,
        face_detector: FaceDetector,
        face_quality_evaluator: FaceQualityEvaluator,
        liveness_evaluator: LivenessEvaluator,
        antispoof_evaluator: AntiSpoofEvaluator,
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
        self.evidence_assembler = evidence_assembler
        self.proof_minter = proof_minter
        self.evidence_store = evidence_store
        self.evidence_encryptor = evidence_encryptor
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
        challenge_sequence = self._select_challenge_sequence(session_id)
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
            ws_url=f"/ws/verify/{session.session_id}",
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
        session = await self._get_session_record(session_id)
        if session.status == SessionStatus.CREATED:
            session.status = SessionStatus.READY
            session.step_status = StepStatus.ACTIVE
            session.last_message = f"Start with {self._step_label(session.challenge_type)}."
            session.updated_at = datetime.now(tz=UTC)
            await self.store.save_session(session)
        return session

    async def record_frame(self, session_id: str, event: WebSocketClientEvent) -> SessionRecord:
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
        session.last_message = "Heartbeat acknowledged"
        await self.store.save_session(session)
        return session

    async def finalize_session(
        self,
        session_id: str,
        mode: VerificationMode = VerificationMode.FULL,
    ) -> VerificationResult:
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

        session.status = SessionStatus.PROCESSING
        session.last_message = "Running verification pipeline"
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

        decision = determine_finalization_decision(
            mode=mode,
            face_detected=face_detected,
            quality_frames_available=quality_frames_available,
            liveness_passed=liveness.passed,
            antispoof_passed=antispoof.passed,
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
        )

        proof_id: str | None = None
        blob_id: str | None = None
        expires_at = None

        if human and mode == VerificationMode.FULL:
            evidence = self.evidence_assembler.assemble(
                session_id=session.session_id,
                wallet_address=session.wallet_address,
                challenge_type=self._to_pipeline_challenge(session.challenge_type),
                frames=usable_frames,
                liveness=liveness,
                antispoof=antispoof,
                face_detections=usable_face_detections,
            )
            encrypted_blob = self.evidence_encryptor.encrypt_for_wallet(
                session.wallet_address,
                json.loads(
                    json.dumps(
                        asdict(evidence),
                        default=lambda value: value.value if hasattr(value, "value") else value,
                    )
                ),
            )
            blob_id = self.evidence_store.put_encrypted_blob(
                encrypted_blob,
                metadata={
                    "session_id": session.session_id,
                    "wallet_address": session.wallet_address,
                    "challenge_type": session.challenge_type.value,
                },
            )

            mint_result = self.proof_minter.mint_proof(
                self._pipeline_result(
                    session_id=session.session_id,
                    wallet_address=session.wallet_address,
                    challenge_type=self._to_pipeline_challenge(session.challenge_type),
                    status=SessionStatus.VERIFIED,
                    human=True,
                    confidence=confidence,
                    spoof_score=antispoof.spoof_score,
                    blob_id=blob_id,
                    failure_reason=None,
                )
            )
            if mint_result.success:
                proof_id = mint_result.proof_id
                expires_at = self._parse_datetime_string(mint_result.expires_at)
            else:
                human = False
                failure_reason = mint_result.reason or "mint_failed"

        if human:
            session.status = SessionStatus.VERIFIED
            session.last_message = "Verification completed"
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
            proof_id=proof_id,
            blob_id=blob_id,
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
            antispoof=antispoof,
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
                "failure_reason": failure_reason,
            },
        )
        return result

    async def get_health(self) -> HealthResponse:
        redis_ok = await self.store.ping()
        models_ready = self.face_detector.models_ready and self.antispoof_evaluator.models_ready
        return HealthResponse(
            status="ready" if redis_ok else "degraded",
            redis="ready" if redis_ok else "degraded",
            models="ready" if models_ready else "degraded",
            chain_adapter=(
                "ready"
                if self.settings.verifier_chain_adapter_enabled
                else "not_configured"
            ),
            storage_adapter=(
                "ready"
                if self.settings.verifier_storage_adapter_enabled
                else "not_configured"
            ),
            encryption_adapter=(
                "ready"
                if self.settings.verifier_encryption_adapter_enabled
                else "not_configured"
            ),
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
                "landmark_spotcheck_max_center_mismatch_px": self.settings.verifier_landmark_spotcheck_max_center_mismatch_px,
                "turn_yaw_threshold_degrees": self.settings.verifier_liveness_turn_yaw_threshold_degrees,
                "turn_offset_threshold": self.settings.verifier_liveness_turn_offset_threshold,
                "nod_pitch_threshold": self.settings.verifier_liveness_nod_pitch_threshold,
                "nod_pitch_ratio_threshold": self.settings.verifier_liveness_nod_pitch_ratio_threshold,
                "smile_ratio_threshold": self.settings.verifier_liveness_smile_ratio_threshold,
                "motion_min_displacement": self.settings.verifier_liveness_motion_min_displacement,
                "motion_max_still_ratio": self.settings.verifier_liveness_motion_max_still_ratio,
                "motion_min_transitions": self.settings.verifier_liveness_motion_min_transitions,
            },
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
        active_pool = [
            ChallengeType.BLINK_TWICE,
            ChallengeType.TURN_LEFT,
            ChallengeType.TURN_RIGHT,
            ChallengeType.NOD_HEAD,
            ChallengeType.SMILE,
        ]
        sequence_length = 2 if rng.random() < 0.5 else 3
        for _ in range(128):
            sequence = rng.sample(active_pool, k=sequence_length)
            if self._sequence_is_valid(sequence):
                return sequence

        fallback = [ChallengeType.BLINK_TWICE, ChallengeType.TURN_RIGHT]
        if sequence_length == 3:
            fallback = [ChallengeType.NOD_HEAD, ChallengeType.SMILE, ChallengeType.BLINK_TWICE]
        return fallback

    def _sequence_is_valid(self, sequence: list[ChallengeType]) -> bool:
        if len(set(sequence)) != len(sequence):
            return False
        if len(sequence) == 2 and set(sequence) == {ChallengeType.BLINK_TWICE, ChallengeType.SMILE}:
            return False
        if len(sequence) == 3 and not any(step in _HEAD_MOTION_CHALLENGES for step in sequence):
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
        current_step = session.challenge_type
        liveness = self.liveness_evaluator.evaluate(
            self._to_pipeline_challenge(current_step),
            active_frames,
        )
        has_minimum_step_frames = len(active_frames) >= self.minimum_step_frames

        session.status = SessionStatus.STREAMING
        session.updated_at = datetime.now(tz=UTC)

        if not session.all_challenges_completed and liveness.passed and has_minimum_step_frames:
            self._complete_current_step(session, latest_frame.frame_index)
            if session.all_challenges_completed:
                session.progress = 1.0
                session.step_progress = 1.0
                session.step_status = StepStatus.COMPLETED
                session.last_message = "Challenge sequence complete. Finalize to verify."
            else:
                session.progress = round(len(session.completed_challenges) / session.total_challenges, 4)
                session.step_progress = 0.0
                session.step_status = StepStatus.ACTIVE
                session.last_message = f"Step complete. Next: {self._step_label(session.challenge_type)}."

            session.debug = build_session_debug_payload(
                latest_frame=latest_frame,
                face_detection=face_detection,
                face_quality=face_quality,
                landmark_spotcheck=landmark_spotcheck,
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

        hold_progress = min(len(active_frames) / self.minimum_step_frames, 1.0)
        session.step_progress = (
            liveness.progress
            if has_minimum_step_frames or not liveness.passed
            else round(min(liveness.progress, 0.85 * hold_progress), 4)
        )
        session.step_status = StepStatus.COMPLETED if session.all_challenges_completed else StepStatus.ACTIVE
        completed_units = len(session.completed_challenges) + session.step_progress
        session.progress = round(min(0.95, completed_units / max(session.total_challenges, 1)), 4)

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
        blob_id: str | None,
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
            blob_id=blob_id,
            metadata={"failure_reason": failure_reason} if failure_reason else {},
        )

    def _parse_datetime_string(self, value: str | None) -> datetime | None:
        if value is None:
            return None
        return datetime.fromisoformat(value)

    def _to_pipeline_challenge(
        self,
        challenge_type: ChallengeType | str,
    ) -> PipelineChallengeType:
        return PipelineChallengeType(
            challenge_type.value if isinstance(challenge_type, ChallengeType) else challenge_type
        )
