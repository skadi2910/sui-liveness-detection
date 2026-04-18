from __future__ import annotations

from app.sessions.finalize import calculate_terminal_confidence
from app.sessions.models import VerificationMode


def test_terminal_confidence_uses_deepfake_signal_when_available() -> None:
    without_deepfake = calculate_terminal_confidence(
        mode=VerificationMode.FULL,
        face_confidence=0.9,
        quality_score=0.9,
        liveness_confidence=0.9,
        spoof_score=0.1,
        max_spoof_score=0.1,
        deepfake_score=None,
        max_deepfake_score=None,
    )
    with_high_deepfake_risk = calculate_terminal_confidence(
        mode=VerificationMode.FULL,
        face_confidence=0.9,
        quality_score=0.9,
        liveness_confidence=0.9,
        spoof_score=0.1,
        max_spoof_score=0.1,
        deepfake_score=0.8,
        max_deepfake_score=0.8,
    )

    assert with_high_deepfake_risk < without_deepfake


def test_terminal_confidence_uses_deepfake_signal_in_antispoof_only_mode() -> None:
    without_deepfake = calculate_terminal_confidence(
        mode=VerificationMode.ANTISPOOF_ONLY,
        face_confidence=0.88,
        quality_score=0.84,
        liveness_confidence=0.0,
        spoof_score=0.12,
        max_spoof_score=0.12,
        deepfake_score=None,
        max_deepfake_score=None,
    )
    with_high_deepfake_risk = calculate_terminal_confidence(
        mode=VerificationMode.ANTISPOOF_ONLY,
        face_confidence=0.88,
        quality_score=0.84,
        liveness_confidence=0.0,
        spoof_score=0.12,
        max_spoof_score=0.12,
        deepfake_score=0.82,
        max_deepfake_score=0.82,
    )

    assert with_high_deepfake_risk < without_deepfake


def test_terminal_confidence_uses_deepfake_signal_in_deepfake_only_mode() -> None:
    without_deepfake = calculate_terminal_confidence(
        mode=VerificationMode.DEEPFAKE_ONLY,
        face_confidence=0.88,
        quality_score=0.84,
        liveness_confidence=0.0,
        spoof_score=0.12,
        max_spoof_score=0.12,
        deepfake_score=None,
        max_deepfake_score=None,
    )
    with_high_deepfake_risk = calculate_terminal_confidence(
        mode=VerificationMode.DEEPFAKE_ONLY,
        face_confidence=0.88,
        quality_score=0.84,
        liveness_confidence=0.0,
        spoof_score=0.12,
        max_spoof_score=0.12,
        deepfake_score=0.82,
        max_deepfake_score=0.82,
    )

    assert with_high_deepfake_risk < without_deepfake


def test_terminal_confidence_uses_peak_attack_scores_for_failed_attack_sessions() -> None:
    low_peak_risk = calculate_terminal_confidence(
        mode=VerificationMode.FULL,
        face_confidence=0.96,
        quality_score=0.93,
        liveness_confidence=0.95,
        spoof_score=0.18,
        max_spoof_score=0.18,
        deepfake_score=0.2,
        max_deepfake_score=0.2,
    )
    high_peak_risk = calculate_terminal_confidence(
        mode=VerificationMode.FULL,
        face_confidence=0.96,
        quality_score=0.93,
        liveness_confidence=0.95,
        spoof_score=0.18,
        max_spoof_score=0.87,
        deepfake_score=0.2,
        max_deepfake_score=0.76,
    )

    assert high_peak_risk < low_peak_risk
    assert high_peak_risk < 0.5
