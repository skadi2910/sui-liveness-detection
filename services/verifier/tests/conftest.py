from __future__ import annotations

from datetime import UTC, datetime

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.adapters.evidence_encryptor import MockEvidenceEncryptor
from app.adapters.evidence_store import InMemoryEvidenceStore
from app.adapters.proof_minter import MockProofMinter
from app.api.routes import router as api_router
from app.api.websocket import router as websocket_router
from app.core.config import Settings
from app.pipeline.antispoof import MockAntiSpoofEvaluator
from app.pipeline.evidence import EvidenceAssembler
from app.pipeline.face import MockFaceDetector
from app.pipeline.liveness import MockLivenessEvaluator
from app.pipeline.quality import HeuristicFaceQualityEvaluator
from app.sessions.models import SessionRecord, SessionStatus, WalletCooldown
from app.sessions.service import VerificationSessionService
from app.sessions.store import active_sessions


class InMemorySessionStore:
    def __init__(self) -> None:
        self._sessions: dict[str, SessionRecord] = {}
        self._cooldowns: dict[str, WalletCooldown] = {}

    async def create_session(self, session: SessionRecord) -> SessionRecord:
        self._sessions[session.session_id] = session.model_copy(deep=True)
        return session

    async def get_session(self, session_id: str) -> SessionRecord | None:
        session = self._sessions.get(session_id)
        return session.model_copy(deep=True) if session is not None else None

    async def save_session(self, session: SessionRecord) -> SessionRecord:
        self._sessions[session.session_id] = session.model_copy(deep=True)
        return session

    async def find_active_session_by_wallet(self, wallet_address: str) -> SessionRecord | None:
        for session in active_sessions(self._sessions.values()):
            if session.wallet_address == wallet_address:
                return session.model_copy(deep=True)
        return None

    async def get_wallet_cooldown(self, wallet_address: str) -> WalletCooldown | None:
        cooldown = self._cooldowns.get(wallet_address)
        if cooldown is None:
            return None
        if cooldown.blocked_until <= datetime.now(tz=UTC):
            self._cooldowns.pop(wallet_address, None)
            return None
        return cooldown.model_copy(deep=True)

    async def set_wallet_cooldown(self, cooldown: WalletCooldown) -> None:
        self._cooldowns[cooldown.wallet_address] = cooldown.model_copy(deep=True)

    async def ping(self) -> bool:
        return True

    def backend_label(self) -> str:
        return "memory"


@pytest.fixture
def verifier_app(tmp_path) -> FastAPI:
    settings = Settings(
        VERIFIER_ENV="test",
        VERIFIER_SESSION_TTL_SECONDS=300,
        VERIFIER_ALLOWED_ORIGINS="http://testserver",
        VERIFIER_CALIBRATION_OUTPUT_PATH=str(tmp_path / "local-dev.ndjson"),
        VERIFIER_ATTACK_MATRIX_OUTPUT_PATH=str(tmp_path / "attack-matrix.ndjson"),
    )
    app = FastAPI()
    app.include_router(api_router)
    app.include_router(websocket_router)
    app.state.session_service = VerificationSessionService(
        store=InMemorySessionStore(),
        settings=settings,
        face_detector=MockFaceDetector(),
        face_quality_evaluator=HeuristicFaceQualityEvaluator(
            blur_threshold=settings.verifier_quality_blur_threshold,
            min_face_size=settings.verifier_quality_min_face_size,
            max_yaw_degrees=settings.verifier_quality_max_yaw_degrees,
            max_pitch_degrees=settings.verifier_quality_max_pitch_degrees,
            min_brightness=settings.verifier_quality_min_brightness,
            max_brightness=settings.verifier_quality_max_brightness,
        ),
        liveness_evaluator=MockLivenessEvaluator(
            blink_closed_threshold=settings.verifier_liveness_blink_closed_threshold,
            blink_open_threshold=settings.verifier_liveness_blink_open_threshold,
            blink_min_closed_frames=settings.verifier_liveness_blink_min_closed_frames,
            turn_yaw_threshold_degrees=settings.verifier_liveness_turn_yaw_threshold_degrees,
            turn_offset_threshold=settings.verifier_liveness_turn_offset_threshold,
            mouth_open_threshold=settings.verifier_liveness_mouth_open_threshold,
            nod_pitch_threshold=settings.verifier_liveness_nod_pitch_threshold,
            nod_pitch_ratio_threshold=settings.verifier_liveness_nod_pitch_ratio_threshold,
            smile_ratio_threshold=settings.verifier_liveness_smile_ratio_threshold,
            motion_min_displacement=settings.verifier_liveness_motion_min_displacement,
            motion_max_still_ratio=settings.verifier_liveness_motion_max_still_ratio,
            motion_min_transitions=settings.verifier_liveness_motion_min_transitions,
        ),
        antispoof_evaluator=MockAntiSpoofEvaluator(),
        evidence_assembler=EvidenceAssembler(),
        proof_minter=MockProofMinter(minimum_confidence=0.6),
        evidence_store=InMemoryEvidenceStore(),
        evidence_encryptor=MockEvidenceEncryptor(),
    )
    return app


@pytest.fixture
def client(verifier_app: FastAPI) -> TestClient:
    with TestClient(verifier_app) as test_client:
        yield test_client
