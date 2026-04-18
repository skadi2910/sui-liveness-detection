"""Pipeline primitives for deterministic local verification flows."""

from .antispoof import AntiSpoofEvaluator, MockAntiSpoofEvaluator
from .evidence import EvidenceAssembler
from .face import FaceDetector, MockFaceDetector
from .liveness import LivenessEvaluator, MockLivenessEvaluator
from .quality import FaceQualityEvaluation, FaceQualityEvaluator, HeuristicFaceQualityEvaluator
from .types import (
    AntiSpoofEvaluation,
    ChallengeSignal,
    ChallengeType,
    EvidenceBlob,
    FaceBoundingBox,
    FaceDetectionResult,
    FrameInput,
    LivenessEvaluation,
    SessionStatus,
    VerificationResult,
)

__all__ = [
    "AntiSpoofEvaluation",
    "AntiSpoofEvaluator",
    "ChallengeSignal",
    "ChallengeType",
    "EvidenceAssembler",
    "EvidenceBlob",
    "FaceBoundingBox",
    "FaceDetectionResult",
    "FaceQualityEvaluation",
    "FaceQualityEvaluator",
    "FaceDetector",
    "FrameInput",
    "HeuristicFaceQualityEvaluator",
    "LivenessEvaluation",
    "LivenessEvaluator",
    "MockAntiSpoofEvaluator",
    "MockFaceDetector",
    "MockLivenessEvaluator",
    "SessionStatus",
    "VerificationResult",
]
