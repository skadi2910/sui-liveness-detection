from __future__ import annotations

from dataclasses import dataclass

from app.sessions.models import VerificationMode


@dataclass(frozen=True)
class FinalizationDecision:
    human: bool
    failure_reason: str | None


def determine_finalization_decision(
    *,
    mode: VerificationMode,
    face_detected: bool,
    quality_frames_available: bool,
    liveness_passed: bool,
    antispoof_passed: bool,
) -> FinalizationDecision:
    if mode == VerificationMode.LIVENESS_ONLY:
        human = face_detected and quality_frames_available and liveness_passed
        failure_reason = _failure_reason(
            face_detected=face_detected,
            quality_frames_available=quality_frames_available,
            liveness_passed=liveness_passed,
            antispoof_passed=True,
        )
        return FinalizationDecision(human=human, failure_reason=failure_reason)

    if mode == VerificationMode.ANTISPOOF_ONLY:
        human = face_detected and quality_frames_available and antispoof_passed
        failure_reason = _failure_reason(
            face_detected=face_detected,
            quality_frames_available=quality_frames_available,
            liveness_passed=True,
            antispoof_passed=antispoof_passed,
        )
        return FinalizationDecision(human=human, failure_reason=failure_reason)

    human = face_detected and quality_frames_available and liveness_passed and antispoof_passed
    failure_reason = _failure_reason(
        face_detected=face_detected,
        quality_frames_available=quality_frames_available,
        liveness_passed=liveness_passed,
        antispoof_passed=antispoof_passed,
    )
    return FinalizationDecision(human=human, failure_reason=failure_reason)


def calculate_terminal_confidence(
    *,
    mode: VerificationMode,
    face_confidence: float,
    quality_score: float,
    liveness_confidence: float,
    spoof_score: float,
) -> float:
    if mode == VerificationMode.LIVENESS_ONLY:
        return round(
            min(
                0.99,
                max(
                    0.0,
                    (face_confidence * 0.35)
                    + (quality_score * 0.25)
                    + (liveness_confidence * 0.4),
                ),
            ),
            4,
        )

    if mode == VerificationMode.ANTISPOOF_ONLY:
        return round(
            min(
                0.99,
                max(
                    0.0,
                    (face_confidence * 0.35)
                    + (quality_score * 0.25)
                    + ((1 - spoof_score) * 0.4),
                ),
            ),
            4,
        )

    return round(
        min(
            0.99,
            max(
                0.0,
                (face_confidence * 0.25)
                + (quality_score * 0.2)
                + (liveness_confidence * 0.35)
                + ((1 - spoof_score) * 0.2),
            ),
        ),
        4,
    )


def _failure_reason(
    *,
    face_detected: bool,
    quality_frames_available: bool,
    liveness_passed: bool,
    antispoof_passed: bool,
) -> str | None:
    if not face_detected:
        return "no_face_detected"
    if not quality_frames_available:
        return "insufficient_frame_quality"
    if not antispoof_passed:
        return "spoof_detected"
    if not liveness_passed:
        return "challenge_failed"
    return None
