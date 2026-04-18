from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import hashlib
from typing import Any


def _normalize_datetime(value: datetime | str | None) -> datetime:
    if value is None:
        return datetime.utcnow()
    if isinstance(value, datetime):
        return value
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed.replace(tzinfo=None)


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


@dataclass(slots=True)
class FrameInput:
    frame_index: int
    timestamp: datetime | str | None = None
    image_base64: str | None = None
    landmarks: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.timestamp = _normalize_datetime(self.timestamp)

    def fingerprint(self, salt: str = "") -> str:
        payload = "|".join(
            [
                salt,
                str(self.frame_index),
                self.timestamp.isoformat(),
                self.image_base64 or "",
                repr(sorted(self.landmarks.items())),
                repr(sorted(self.metadata.items())),
            ]
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def pseudo_score(self, salt: str, minimum: float = 0.0, maximum: float = 1.0) -> float:
        digest = self.fingerprint(salt)
        unit = int(digest[:8], 16) / 0xFFFFFFFF
        return round(minimum + ((maximum - minimum) * unit), 4)

    def get_flag(self, key: str, default: Any = None) -> Any:
        if key in self.metadata:
            return self.metadata[key]
        return self.landmarks.get(key, default)


@dataclass(slots=True)
class FaceBoundingBox:
    x: float
    y: float
    width: float
    height: float


@dataclass(slots=True)
class FaceDetectionResult:
    detected: bool
    confidence: float
    frame_index: int
    bounding_box: FaceBoundingBox | None = None
    landmarks_source: str = "mock"
    face_hash: str | None = None
    message: str = ""


@dataclass(slots=True)
class ChallengeSignal:
    name: str
    value: float
    detected: bool
    frame_index: int
    source: str = "metadata"


@dataclass(slots=True)
class LivenessEvaluation:
    challenge_type: ChallengeType
    passed: bool
    progress: float
    frames_processed: int
    matched_signals: int
    required_signals: int
    confidence: float
    message: str
    detected_signals: list[ChallengeSignal] = field(default_factory=list)


@dataclass(slots=True)
class AntiSpoofEvaluation:
    passed: bool
    spoof_score: float
    max_spoof_score: float
    frames_processed: int
    flagged_frames: list[int] = field(default_factory=list)
    model_hash: str = "sha256:mock-antispoof-v1"
    message: str = ""


@dataclass(slots=True)
class EvidenceBlob:
    session_id: str
    wallet_address: str
    challenge_type: ChallengeType
    frame_hashes: list[str]
    landmark_snapshot: dict[str, Any]
    spoof_score_summary: dict[str, float]
    model_hashes: dict[str, str]
    captured_at: str
    challenge_summary: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class VerificationResult:
    session_id: str
    wallet_address: str
    challenge_type: ChallengeType
    status: SessionStatus
    human: bool
    confidence: float
    spoof_score: float
    proof_id: str | None = None
    blob_id: str | None = None
    expires_at: str | None = None
    evidence: EvidenceBlob | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
