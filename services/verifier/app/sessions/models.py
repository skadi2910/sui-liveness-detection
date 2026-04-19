from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, model_validator


def utc_now() -> datetime:
    return datetime.now(tz=UTC)


class ChallengeType(str, Enum):
    BLINK_TWICE = "blink_twice"
    TURN_LEFT = "turn_left"
    TURN_RIGHT = "turn_right"
    NOD_HEAD = "nod_head"
    SMILE = "smile"
    OPEN_MOUTH = "open_mouth"


class SessionStatus(str, Enum):
    CREATED = "created"
    READY = "ready"
    STREAMING = "streaming"
    PROCESSING = "processing"
    VERIFIED = "verified"
    FAILED = "failed"
    EXPIRED = "expired"


class ClientEventType(str, Enum):
    FRAME = "frame"
    LANDMARKS = "landmarks"
    HEARTBEAT = "heartbeat"
    FINALIZE = "finalize"


class ServerEventType(str, Enum):
    SESSION_READY = "session_ready"
    CHALLENGE_UPDATE = "challenge_update"
    PROGRESS = "progress"
    PROCESSING = "processing"
    VERIFIED = "verified"
    FAILED = "failed"
    ERROR = "error"


class StepStatus(str, Enum):
    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"


class VerificationMode(str, Enum):
    FULL = "full"
    LIVENESS_ONLY = "liveness_only"
    ANTISPOOF_ONLY = "antispoof_only"
    DEEPFAKE_ONLY = "deepfake_only"


class ClientInfo(BaseModel):
    platform: str
    user_agent: str | None = None


class SessionCreateRequest(BaseModel):
    wallet_address: str = Field(min_length=3)
    client: ClientInfo
    challenge_sequence: list[ChallengeType] | None = Field(default=None, min_length=1, max_length=3)

    @model_validator(mode="after")
    def validate_sequence(self) -> "SessionCreateRequest":
        if self.challenge_sequence is None:
            return self
        if len(set(self.challenge_sequence)) != len(self.challenge_sequence):
            raise ValueError("challenge_sequence must not repeat challenges")
        return self


class VerificationProgress(BaseModel):
    session_id: str
    status: SessionStatus
    challenge_type: ChallengeType
    challenge_sequence: list[ChallengeType]
    current_challenge_index: int = Field(ge=0)
    total_challenges: int = Field(ge=0)
    completed_challenges: list[ChallengeType] = Field(default_factory=list)
    step_status: StepStatus
    progress: float = Field(ge=0.0, le=1.0)
    finalize_ready: bool = False
    frames_processed: int = Field(ge=0)
    message: str
    debug: dict[str, Any] | None = None


class VerificationResult(BaseModel):
    session_id: str
    status: SessionStatus
    evaluation_mode: VerificationMode = VerificationMode.FULL
    human: bool
    challenge_type: ChallengeType
    challenge_sequence: list[ChallengeType] = Field(default_factory=list)
    current_challenge_index: int = Field(ge=0)
    total_challenges: int = Field(ge=0)
    completed_challenges: list[ChallengeType] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)
    spoof_score: float = Field(ge=0.0, le=1.0)
    max_spoof_score: float | None = Field(default=None, ge=0.0, le=1.0)
    human_face_score: float | None = Field(default=None, ge=0.0, le=1.0)
    human_face_message: str | None = None
    human_face_enabled: bool = False
    deepfake_score: float | None = Field(default=None, ge=0.0, le=1.0)
    max_deepfake_score: float | None = Field(default=None, ge=0.0, le=1.0)
    deepfake_frames_processed: int = Field(default=0, ge=0)
    deepfake_message: str | None = None
    deepfake_enabled: bool = False
    attack_analysis: dict[str, Any] | None = None
    proof_id: str | None = None
    transaction_digest: str | None = None
    proof_operation: str | None = None
    chain_network: str | None = None
    walrus_blob_id: str | None = None
    walrus_blob_object_id: str | None = None
    seal_identity: str | None = None
    evidence_schema_version: int | None = None
    model_hash: str | None = None
    blob_id: str | None = None
    expires_at: datetime | None = None
    failure_reason: str | None = None


class ProofClaimOperation(str, Enum):
    MINT = "mint"
    RENEW = "renew"


class PreparedProofClaim(BaseModel):
    session_id: str
    wallet_address: str
    operation: ProofClaimOperation
    package_id: str
    registry_object_id: str
    module_name: str
    clock_object_id: str = "0x6"
    claim_id: str
    claim_expires_at_ms: int = Field(ge=0)
    proof_object_id: str | None = None
    walrus_blob_id: str
    walrus_blob_object_id: str
    seal_identity: str
    evidence_schema_version: int = Field(ge=0)
    model_hash: str | None = None
    confidence_bps: int = Field(ge=0)
    issued_at_ms: int = Field(ge=0)
    expires_at_ms: int = Field(ge=0)
    challenge_type: str
    signature_b64: str
    chain_network: str | None = None


class CompleteProofClaimRequest(BaseModel):
    transaction_digest: str = Field(min_length=3)
    proof_id: str | None = Field(default=None, min_length=3)


class CancelProofClaimRequest(BaseModel):
    reason: str | None = None


class EvidenceBlob(BaseModel):
    session_id: str
    wallet_address: str
    challenge_type: ChallengeType
    frame_hashes: list[str]
    landmark_snapshot: dict[str, Any] | None = None
    spoof_score_summary: dict[str, float] | None = None
    model_hashes: dict[str, str] | None = None
    captured_at: datetime


class SessionCreateResponse(BaseModel):
    session_id: str
    status: SessionStatus
    challenge_type: ChallengeType
    challenge_sequence: list[ChallengeType]
    current_challenge_index: int = Field(ge=0)
    total_challenges: int = Field(ge=0)
    completed_challenges: list[ChallengeType] = Field(default_factory=list)
    expires_at: datetime
    ws_url: str


class SessionResponse(BaseModel):
    session_id: str
    status: SessionStatus
    challenge_type: ChallengeType
    challenge_sequence: list[ChallengeType]
    current_challenge_index: int = Field(ge=0)
    total_challenges: int = Field(ge=0)
    completed_challenges: list[ChallengeType] = Field(default_factory=list)
    created_at: datetime
    expires_at: datetime
    result: VerificationResult | None = None


class HealthResponse(BaseModel):
    status: str
    redis: str
    models: str
    chain_adapter: str
    storage_adapter: str
    encryption_adapter: str
    model_details: dict[str, Any] | None = None
    tuning: dict[str, Any] | None = None


class CalibrationAppendRequest(BaseModel):
    record: dict[str, Any]


class CalibrationAppendResponse(BaseModel):
    saved: bool
    sample_id: str | None = None
    output_path: str


class AdminFramePayload(BaseModel):
    frame_index: int = Field(default=0, ge=0)
    timestamp: datetime = Field(default_factory=utc_now)
    image_base64: str | None = None
    landmarks: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class AdminEvaluateFrameRequest(BaseModel):
    frame: AdminFramePayload
    challenge_type: ChallengeType = ChallengeType.BLINK_TWICE
    mode: VerificationMode = VerificationMode.FULL


class AdminEvaluateFrameResponse(BaseModel):
    challenge_type: ChallengeType
    evaluation_mode: VerificationMode
    accepted_for_liveness: bool
    accepted_for_spoof: bool
    face_detection: dict[str, Any]
    quality: dict[str, Any]
    landmark_spotcheck: dict[str, Any]
    human_face: dict[str, Any]
    liveness: dict[str, Any]
    antispoof: dict[str, Any]
    deepfake: dict[str, Any]


class AdminEvaluateSessionRequest(BaseModel):
    frames: list[AdminFramePayload] = Field(min_length=1)
    challenge_type: ChallengeType = ChallengeType.BLINK_TWICE
    mode: VerificationMode = VerificationMode.FULL


class AdminEvaluateSessionResponse(BaseModel):
    challenge_type: ChallengeType
    evaluation_mode: VerificationMode
    frames_processed: int = Field(ge=0)
    accepted_frame_indices: list[int] = Field(default_factory=list)
    face_detected: bool
    quality_frames_available: bool
    face_detection: dict[str, Any]
    quality: dict[str, Any]
    landmark_spotcheck: dict[str, Any]
    human_face: dict[str, Any]
    liveness: dict[str, Any]
    antispoof: dict[str, Any]
    deepfake: dict[str, Any]
    verdict_preview: dict[str, Any]


class SessionRecord(BaseModel):
    session_id: str
    wallet_address: str
    status: SessionStatus
    challenge_sequence: list[ChallengeType]
    current_challenge_index: int = 0
    completed_challenges: list[ChallengeType] = Field(default_factory=list)
    total_challenges: int = 0
    step_started_frame_index: int = 0
    step_status: StepStatus = StepStatus.PENDING
    step_progress: float = 0.0
    debug: dict[str, Any] | None = None
    client: ClientInfo
    created_at: datetime
    expires_at: datetime
    updated_at: datetime
    result: VerificationResult | None = None
    frames_processed: int = 0
    progress: float = 0.0
    finalize_ready: bool = False
    last_message: str = "Session created"
    frame_payloads: list[dict[str, Any]] = Field(default_factory=list)
    pending_proof_claim: PreparedProofClaim | None = None

    @model_validator(mode="before")
    @classmethod
    def _hydrate_sequence_state(cls, value: Any) -> Any:
        if not isinstance(value, dict):
            return value

        hydrated = dict(value)
        legacy_challenge = hydrated.get("challenge_type")
        challenge_sequence = hydrated.get("challenge_sequence")
        if not challenge_sequence and legacy_challenge is not None:
            challenge_sequence = [legacy_challenge]
            hydrated["challenge_sequence"] = challenge_sequence

        if "completed_challenges" not in hydrated:
            hydrated["completed_challenges"] = []
        if "current_challenge_index" not in hydrated:
            hydrated["current_challenge_index"] = 0
        if "total_challenges" not in hydrated:
            hydrated["total_challenges"] = len(challenge_sequence or [])
        if "step_started_frame_index" not in hydrated:
            hydrated["step_started_frame_index"] = 0
        if "step_status" not in hydrated:
            hydrated["step_status"] = StepStatus.PENDING
        if "step_progress" not in hydrated:
            hydrated["step_progress"] = 0.0
        return hydrated

    @property
    def all_challenges_completed(self) -> bool:
        return self.total_challenges > 0 and len(self.completed_challenges) >= self.total_challenges

    @property
    def challenge_type(self) -> ChallengeType:
        if self.completed_challenges and self.all_challenges_completed:
            return self.completed_challenges[-1]
        if not self.challenge_sequence:
            return ChallengeType.BLINK_TWICE
        bounded_index = min(max(self.current_challenge_index, 0), len(self.challenge_sequence) - 1)
        return self.challenge_sequence[bounded_index]

    def to_response(self) -> SessionResponse:
        return SessionResponse(
            session_id=self.session_id,
            status=self.status,
            challenge_type=self.challenge_type,
            challenge_sequence=self.challenge_sequence,
            current_challenge_index=self.current_challenge_index,
            total_challenges=self.total_challenges,
            completed_challenges=self.completed_challenges,
            created_at=self.created_at,
            expires_at=self.expires_at,
            result=self.result,
        )

    def to_progress(self) -> VerificationProgress:
        return VerificationProgress(
            session_id=self.session_id,
            status=self.status,
            challenge_type=self.challenge_type,
            challenge_sequence=self.challenge_sequence,
            current_challenge_index=self.current_challenge_index,
            total_challenges=self.total_challenges,
            completed_challenges=self.completed_challenges,
            step_status=self.step_status,
            progress=self.progress,
            finalize_ready=self.finalize_ready,
            frames_processed=self.frames_processed,
            message=self.last_message,
            debug=self.debug,
        )


class WalletCooldown(BaseModel):
    wallet_address: str
    blocked_until: datetime


class WebSocketClientEvent(BaseModel):
    type: ClientEventType
    timestamp: datetime = Field(default_factory=utc_now)
    image_base64: str | None = None
    landmarks: dict[str, Any] | None = None
    metadata: dict[str, Any] | None = None
    mode: VerificationMode | None = None


class WebSocketServerEvent(BaseModel):
    type: ServerEventType
    payload: dict[str, Any] | VerificationProgress | VerificationResult | SessionResponse
