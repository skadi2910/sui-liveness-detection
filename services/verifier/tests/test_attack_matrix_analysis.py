from __future__ import annotations

from scripts.analyze_attack_matrix import compute_attack_matrix, normalize_attack_class, render_attack_matrix_report


def test_normalize_attack_class_maps_common_aliases() -> None:
    assert normalize_attack_class({"label": "human"}) == "live"
    assert normalize_attack_class({"label": "spoof", "attack_type": "screen_replay"}) == "replay"
    assert normalize_attack_class({"label": "spoof", "attack_type": "ai_video"}) == "talking_head"
    assert normalize_attack_class({"label": "spoof", "attack_type": "virtual_camera"}) == "injection"
    assert normalize_attack_class({"label": "spoof", "attack_type": "cartoon"}) == "non_human"


def test_compute_attack_matrix_reports_targets_and_failure_reasons() -> None:
    records = [
        {
            "label": "human",
            "status": "verified",
            "human": True,
            "confidence": 0.97,
            "spoof_score": 0.04,
        },
        {
            "label": "human",
            "status": "failed",
            "human": False,
            "failure_reason": "challenge_failed",
            "confidence": 0.42,
            "spoof_score": 0.21,
        },
        {
            "label": "spoof",
            "attack_type": "print",
            "status": "failed",
            "human": False,
            "failure_reason": "spoof_detected",
            "confidence": 0.12,
            "spoof_score": 0.92,
        },
        {
            "label": "spoof",
            "attack_type": "screen_replay",
            "status": "verified",
            "human": True,
            "confidence": 0.78,
            "spoof_score": 0.22,
        },
    ]

    report = compute_attack_matrix(records)

    assert report["classes"]["live"]["samples"] == 2
    assert report["classes"]["live"]["pass_rate"] == 0.5
    assert report["classes"]["live"]["meets_target"] is False
    assert report["classes"]["live"]["failure_reasons"]["challenge_failed"] == 1

    assert report["classes"]["print"]["pass_rate"] == 0.0
    assert report["classes"]["print"]["meets_target"] is True
    assert report["classes"]["replay"]["pass_rate"] == 1.0
    assert report["classes"]["replay"]["meets_target"] is False
    assert report["target_misses"] == ["live", "replay"]


def test_render_attack_matrix_report_mentions_missing_classes() -> None:
    report = compute_attack_matrix(
        [
            {
                "label": "spoof",
                "attack_type": "print",
                "status": "failed",
                "human": False,
                "failure_reason": "spoof_detected",
                "confidence": 0.14,
                "spoof_score": 0.88,
            }
        ]
    )

    text = render_attack_matrix_report(report)

    assert "Attack matrix summary:" in text
    assert "print:" in text
    assert "missing_classes=live" in text
