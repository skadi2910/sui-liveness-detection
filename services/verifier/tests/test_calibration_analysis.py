from __future__ import annotations

from scripts.analyze_calibration_samples import compute_pad_metrics


def test_compute_pad_metrics_reports_attack_specific_apcer() -> None:
    records = [
        {
            "label": "human",
            "spoof_score": 0.03,
            "max_spoof_score": 0.05,
        },
        {
            "label": "human",
            "spoof_score": 0.08,
            "max_spoof_score": 0.1,
        },
        {
            "label": "spoof",
            "attack_type": "print",
            "spoof_score": 0.81,
            "max_spoof_score": 0.92,
        },
        {
            "label": "spoof",
            "attack_type": "screen_replay",
            "spoof_score": 0.2,
            "max_spoof_score": 0.24,
        },
    ]

    metrics = compute_pad_metrics(
        records,
        threshold=0.35,
        hard_fail_threshold=0.75,
    )

    assert metrics["bpcer"] == 0.0
    assert metrics["apcer_by_attack"]["print"] == 0.0
    assert metrics["apcer_by_attack"]["screen_replay"] == 1.0
    assert metrics["apcer_avg"] == 0.5
    assert metrics["apcer_max"] == 1.0
    assert metrics["acer"] == 0.25
    assert metrics["worst_attacks"] == ["screen_replay"]


def test_compute_pad_metrics_falls_back_to_unknown_spoof_attack_type() -> None:
    records = [
        {
            "label": "human",
            "spoof_score": 0.04,
            "max_spoof_score": 0.06,
        },
        {
            "label": "spoof",
            "spoof_score": 0.12,
            "max_spoof_score": 0.16,
        },
    ]

    metrics = compute_pad_metrics(
        records,
        threshold=0.35,
        hard_fail_threshold=0.75,
    )

    assert metrics["apcer_by_attack"]["unknown_spoof"] == 1.0
    assert metrics["worst_attacks"] == ["unknown_spoof"]
