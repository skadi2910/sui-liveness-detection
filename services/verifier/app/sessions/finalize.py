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
    human_face_enabled: bool = False,
    human_face_passed: bool = True,
    human_face_enforced: bool = False,
    liveness_passed: bool,
    antispoof_passed: bool,
    deepfake_enabled: bool = False,
    deepfake_passed: bool = True,
    deepfake_enforced: bool = False,
) -> FinalizationDecision:
    if mode == VerificationMode.LIVENESS_ONLY:
        human = face_detected and quality_frames_available and liveness_passed
        failure_reason = _failure_reason(
            face_detected=face_detected,
            quality_frames_available=quality_frames_available,
            human_face_enabled=human_face_enabled,
            human_face_passed=True,
            human_face_enforced=False,
            liveness_passed=liveness_passed,
            antispoof_passed=True,
            deepfake_enabled=deepfake_enabled,
            deepfake_passed=True,
            deepfake_enforced=False,
        )
        return FinalizationDecision(human=human, failure_reason=failure_reason)

    if mode == VerificationMode.ANTISPOOF_ONLY:
        human = (
            face_detected
            and quality_frames_available
            and ((not human_face_enforced) or human_face_passed)
            and antispoof_passed
            and ((not deepfake_enforced) or deepfake_passed)
        )
        failure_reason = _failure_reason(
            face_detected=face_detected,
            quality_frames_available=quality_frames_available,
            human_face_enabled=human_face_enabled,
            human_face_passed=human_face_passed,
            human_face_enforced=human_face_enforced,
            liveness_passed=True,
            antispoof_passed=antispoof_passed,
            deepfake_enabled=deepfake_enabled,
            deepfake_passed=deepfake_passed,
            deepfake_enforced=deepfake_enforced,
        )
        return FinalizationDecision(human=human, failure_reason=failure_reason)

    if mode == VerificationMode.DEEPFAKE_ONLY:
        human = (
            face_detected
            and quality_frames_available
            and ((not human_face_enforced) or human_face_passed)
            and deepfake_enabled
            and deepfake_passed
        )
        failure_reason = _failure_reason(
            face_detected=face_detected,
            quality_frames_available=quality_frames_available,
            human_face_enabled=human_face_enabled,
            human_face_passed=human_face_passed,
            human_face_enforced=human_face_enforced,
            liveness_passed=True,
            antispoof_passed=True,
            deepfake_enabled=deepfake_enabled,
            deepfake_passed=deepfake_passed,
            deepfake_enforced=True,
        )
        return FinalizationDecision(human=human, failure_reason=failure_reason)

    human = (
        face_detected
        and quality_frames_available
        and ((not human_face_enforced) or human_face_passed)
        and liveness_passed
        and antispoof_passed
        and ((not deepfake_enforced) or deepfake_passed)
    )
    failure_reason = _failure_reason(
        face_detected=face_detected,
        quality_frames_available=quality_frames_available,
        human_face_enabled=human_face_enabled,
        human_face_passed=human_face_passed,
        human_face_enforced=human_face_enforced,
        liveness_passed=liveness_passed,
        antispoof_passed=antispoof_passed,
        deepfake_enabled=deepfake_enabled,
        deepfake_passed=deepfake_passed,
        deepfake_enforced=deepfake_enforced,
    )
    return FinalizationDecision(human=human, failure_reason=failure_reason)


def build_attack_analysis(
    *,
    human: bool,
    failure_reason: str | None,
    spoof_score: float,
    max_spoof_score: float | None,
    antispoof_passed: bool,
    deepfake_enabled: bool,
    deepfake_score: float | None,
    max_deepfake_score: float | None,
    deepfake_passed: bool,
) -> dict[str, object]:
    presentation_attack_detected = not antispoof_passed
    deepfake_detected = deepfake_enabled and not deepfake_passed

    if human:
        failure_category = "none"
        suspected_attack_family = "none"
        note = "No attack signal blocked the final verification result."
    elif failure_reason == "no_human_face_detected":
        failure_category = "non_human_face"
        suspected_attack_family = "non_human_face"
        note = "The human-face gate flagged the subject as non-human or ambiguous."
    elif presentation_attack_detected and deepfake_detected:
        failure_category = "attack_detected"
        suspected_attack_family = "combined_attack_signals"
        note = (
            "Both presentation-attack and deepfake signals crossed their configured thresholds."
        )
    elif deepfake_detected:
        failure_category = "attack_detected"
        suspected_attack_family = "deepfake_attack"
        note = "Deepfake scoring crossed the configured rejection threshold."
    elif presentation_attack_detected:
        failure_category = "attack_detected"
        suspected_attack_family = "presentation_attack"
        note = "Presentation-attack scoring crossed the configured rejection threshold."
    else:
        failure_category = _categorize_failure_reason(failure_reason)
        suspected_attack_family = "none"
        note = _failure_note_for_category(failure_category)

    return {
        "failure_category": failure_category,
        "suspected_attack_family": suspected_attack_family,
        "presentation_attack_detected": presentation_attack_detected,
        "presentation_attack_score": spoof_score,
        "presentation_attack_peak": max_spoof_score,
        "deepfake_detected": deepfake_detected,
        "deepfake_score": deepfake_score,
        "deepfake_peak": max_deepfake_score,
        "note": note,
    }


def calculate_terminal_confidence(
    *,
    mode: VerificationMode,
    face_confidence: float,
    quality_score: float,
    liveness_confidence: float,
    spoof_score: float,
    max_spoof_score: float | None = None,
    deepfake_score: float | None = None,
    max_deepfake_score: float | None = None,
) -> float:
    effective_spoof_score = max(
        max(0.0, min(1.0, spoof_score)),
        max(0.0, min(1.0, max_spoof_score if max_spoof_score is not None else spoof_score)),
    )
    effective_deepfake_score = None
    if deepfake_score is not None or max_deepfake_score is not None:
        baseline_deepfake_score = deepfake_score if deepfake_score is not None else 0.0
        effective_deepfake_score = max(
            max(0.0, min(1.0, baseline_deepfake_score)),
            max(
                0.0,
                min(
                    1.0,
                    max_deepfake_score if max_deepfake_score is not None else baseline_deepfake_score,
                ),
            ),
        )
    deepfake_confidence = (
        max(0.0, min(1.0, 1 - effective_deepfake_score))
        if effective_deepfake_score is not None
        else None
    )

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
        components = [
            (face_confidence, 0.35),
            (quality_score, 0.25),
            (1 - effective_spoof_score, 0.4 if deepfake_confidence is None else 0.25),
        ]
        if deepfake_confidence is not None:
            components.append((deepfake_confidence, 0.15))
        return round(
            _apply_attack_risk_cap(
                min(
                    0.99,
                    max(
                        0.0,
                        _weighted_confidence(components),
                    ),
                ),
                effective_spoof_score,
                effective_deepfake_score,
            ),
            4,
        )

    if mode == VerificationMode.DEEPFAKE_ONLY:
        baseline_deepfake_confidence = 0.5 if deepfake_confidence is None else deepfake_confidence
        components = [
            (face_confidence, 0.3),
            (quality_score, 0.25),
            (baseline_deepfake_confidence, 0.45),
        ]
        return round(
            _apply_attack_risk_cap(
                min(
                    0.99,
                    max(
                        0.0,
                        _weighted_confidence(components),
                    ),
                ),
                effective_spoof_score,
                effective_deepfake_score,
            ),
            4,
        )

    components = [
        (face_confidence, 0.25),
        (quality_score, 0.2),
        (liveness_confidence, 0.35 if deepfake_confidence is None else 0.3),
        (1 - effective_spoof_score, 0.2 if deepfake_confidence is None else 0.15),
    ]
    if deepfake_confidence is not None:
        components.append((deepfake_confidence, 0.1))

    return round(
        _apply_attack_risk_cap(
            min(
                0.99,
                max(
                    0.0,
                    _weighted_confidence(components),
                ),
            ),
            effective_spoof_score,
            effective_deepfake_score,
        ),
        4,
    )


def _weighted_confidence(components: list[tuple[float, float]]) -> float:
    total_weight = sum(weight for _, weight in components if weight > 0)
    if total_weight <= 0:
        return 0.0
    return sum(value * weight for value, weight in components) / total_weight


def _apply_attack_risk_cap(
    base_confidence: float,
    spoof_risk: float,
    deepfake_risk: float | None,
) -> float:
    strongest_attack_risk = max(
        spoof_risk,
        deepfake_risk if deepfake_risk is not None else 0.0,
    )
    if strongest_attack_risk <= 0.5:
        return base_confidence
    return min(base_confidence, max(0.0, 1 - strongest_attack_risk))


def _failure_reason(
    *,
    face_detected: bool,
    quality_frames_available: bool,
    human_face_enabled: bool,
    human_face_passed: bool,
    human_face_enforced: bool,
    liveness_passed: bool,
    antispoof_passed: bool,
    deepfake_enabled: bool,
    deepfake_passed: bool,
    deepfake_enforced: bool,
) -> str | None:
    if not face_detected:
        return "no_face_detected"
    if not quality_frames_available:
        return "insufficient_frame_quality"
    if human_face_enforced and not human_face_enabled:
        return "human_face_unavailable"
    if human_face_enforced and not human_face_passed:
        return "no_human_face_detected"
    if not antispoof_passed:
        return "spoof_detected"
    if deepfake_enforced and not deepfake_enabled:
        return "deepfake_unavailable"
    if deepfake_enforced and not deepfake_passed:
        return "deepfake_detected"
    if not liveness_passed:
        return "challenge_failed"
    return None


def _categorize_failure_reason(failure_reason: str | None) -> str:
    if failure_reason == "no_face_detected":
        return "no_face"
    if failure_reason == "insufficient_frame_quality":
        return "quality_failure"
    if failure_reason == "challenge_failed":
        return "liveness_failure"
    if failure_reason == "human_face_unavailable":
        return "human_face_unavailable"
    if failure_reason == "no_human_face_detected":
        return "non_human_face"
    if failure_reason == "deepfake_unavailable":
        return "deepfake_unavailable"
    if failure_reason in {
        "mint_failed",
        "renew_failed",
        "confidence_below_threshold",
        "session_not_verified",
        "evidence_encrypt_failed",
        "evidence_store_failed",
        "active_proof_lookup_failed",
    }:
        return "proof_mint_failure"
    if failure_reason:
        return "verification_failure"
    return "none"


def _failure_note_for_category(category: str) -> str:
    if category == "no_face":
        return "The verifier could not keep a usable face lock during the session."
    if category == "quality_failure":
        return "The verifier did not receive enough frames that passed the quality gate."
    if category == "liveness_failure":
        return "The active liveness sequence did not complete successfully."
    if category == "human_face_unavailable":
        return "Human-face enforcement was enabled, but the human-face model was unavailable."
    if category == "non_human_face":
        return "The verifier classified the presented subject as non-human or ambiguous."
    if category == "deepfake_unavailable":
        return "Deepfake-only evaluation was requested, but the deepfake model was unavailable."
    if category == "proof_mint_failure":
        return "Verification passed locally, but proof minting failed afterward."
    if category == "verification_failure":
        return "The session failed without a more specific attack classification."
    return "No attack signal blocked the final verification result."
