from __future__ import annotations

import argparse
from collections import defaultdict
import json
from pathlib import Path
from statistics import median
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Summarize project-native calibration samples for the pretrained verifier stack.",
    )
    parser.add_argument(
        "input_path",
        type=Path,
        help="Path to a NDJSON calibration file.",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=5,
        help="Number of threshold candidates to print.",
    )
    return parser.parse_args()


def load_records(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, raw_line in enumerate(handle, start=1):
            line = raw_line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON on line {line_number}: {exc}") from exc
            if not isinstance(payload, dict):
                raise ValueError(f"Expected an object on line {line_number}")
            records.append(payload)
    if not records:
        raise ValueError(f"No records found in {path}")
    return records


def summarize_counts(records: list[dict[str, Any]]) -> None:
    by_label: dict[str, int] = defaultdict(int)
    by_challenge: dict[str, int] = defaultdict(int)
    by_pair: dict[tuple[str, str], int] = defaultdict(int)

    for record in records:
        label = str(record.get("label", "unknown"))
        challenge_type = str(record.get("challenge_type", "unknown"))
        by_label[label] += 1
        by_challenge[challenge_type] += 1
        by_pair[(challenge_type, label)] += 1

    print("Counts by label:")
    for label, count in sorted(by_label.items()):
        print(f"  {label}: {count}")

    print("\nCounts by challenge:")
    for challenge_type, count in sorted(by_challenge.items()):
        print(f"  {challenge_type}: {count}")

    print("\nCounts by challenge + label:")
    for (challenge_type, label), count in sorted(by_pair.items()):
        print(f"  {challenge_type} / {label}: {count}")


def summarize_attack_coverage(records: list[dict[str, Any]]) -> None:
    by_attack: dict[str, int] = defaultdict(int)
    by_medium: dict[str, int] = defaultdict(int)
    missing_attack_labels = 0

    for record in records:
        label = _normalize_label(record)
        if label == "spoof":
            attack_type = _normalize_attack_type(record)
            by_attack[attack_type] += 1
            if attack_type == "unknown_spoof":
                missing_attack_labels += 1

        capture_medium = record.get("capture_medium")
        if isinstance(capture_medium, str) and capture_medium.strip():
            by_medium[capture_medium.strip()] += 1

    if by_attack:
        print("\nSpoof coverage by attack type:")
        for attack_type, count in sorted(by_attack.items()):
            print(f"  {attack_type}: {count}")
        if missing_attack_labels:
            print(
                "  warning: "
                f"{missing_attack_labels} spoof sample(s) have no `attack_type`; "
                "APCER-by-attack will be less informative until these are labeled."
            )

    if by_medium:
        print("\nCoverage by capture medium:")
        for capture_medium, count in sorted(by_medium.items()):
            print(f"  {capture_medium}: {count}")


def summarize_numeric_metrics(records: list[dict[str, Any]]) -> None:
    metric_values: dict[tuple[str, str, str], list[float]] = defaultdict(list)

    for record in records:
        challenge_type = str(record.get("challenge_type", "unknown"))
        label = str(record.get("label", "unknown"))
        landmark_metrics = record.get("landmark_metrics", {})
        if isinstance(landmark_metrics, dict):
            for name, value in landmark_metrics.items():
                if isinstance(value, (int, float)):
                    metric_values[(challenge_type, label, name)].append(float(value))

        for name in ("spoof_score", "max_spoof_score", "confidence", "challenge_progress"):
            value = record.get(name)
            if isinstance(value, (int, float)):
                metric_values[(challenge_type, label, name)].append(float(value))

    if not metric_values:
        print("\nNo numeric metrics found.")
        return

    print("\nNumeric metric summaries:")
    for (challenge_type, label, name), values in sorted(metric_values.items()):
        values = sorted(values)
        print(
            "  "
            f"{challenge_type} / {label} / {name}: "
            f"n={len(values)} min={values[0]:.4f} med={median(values):.4f} max={values[-1]:.4f}"
        )


def percentile(values: list[float], ratio: float) -> float:
    if not values:
        raise ValueError("percentile() requires at least one value")
    if len(values) == 1:
        return values[0]
    ordered = sorted(values)
    clamped_ratio = min(max(ratio, 0.0), 1.0)
    index = (len(ordered) - 1) * clamped_ratio
    lower = int(index)
    upper = min(lower + 1, len(ordered) - 1)
    weight = index - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def _normalize_label(record: dict[str, Any]) -> str:
    label = record.get("label")
    if isinstance(label, str):
        normalized = label.strip().lower()
        if normalized in {"human", "spoof"}:
            return normalized
    return "unknown"


def _normalize_attack_type(record: dict[str, Any]) -> str:
    if _normalize_label(record) == "human":
        return "bona_fide"

    attack_type = record.get("attack_type")
    if isinstance(attack_type, str):
        normalized = attack_type.strip().lower()
        if normalized:
            return normalized
    return "unknown_spoof"


def _predict_human(record: dict[str, Any], *, threshold: float, hard_fail_threshold: float) -> bool:
    return (
        float(record["spoof_score"]) < threshold
        and float(record["max_spoof_score"]) < hard_fail_threshold
    )


def compute_pad_metrics(
    records: list[dict[str, Any]],
    *,
    threshold: float,
    hard_fail_threshold: float,
) -> dict[str, Any]:
    labeled = [
        record
        for record in records
        if _normalize_label(record) in {"human", "spoof"}
        and isinstance(record.get("spoof_score"), (int, float))
        and isinstance(record.get("max_spoof_score"), (int, float))
    ]
    if not labeled:
        raise ValueError("No labeled anti-spoof samples found.")

    counts = {"tp": 0, "tn": 0, "fp": 0, "fn": 0}
    spoof_totals: dict[str, int] = defaultdict(int)
    spoof_false_accepts: dict[str, int] = defaultdict(int)

    for record in labeled:
        actual_human = _normalize_label(record) == "human"
        predicted_human = _predict_human(
            record,
            threshold=threshold,
            hard_fail_threshold=hard_fail_threshold,
        )

        if predicted_human and actual_human:
            counts["tp"] += 1
        elif predicted_human and not actual_human:
            counts["fp"] += 1
        elif not predicted_human and actual_human:
            counts["fn"] += 1
        else:
            counts["tn"] += 1

        if not actual_human:
            attack_type = _normalize_attack_type(record)
            spoof_totals[attack_type] += 1
            if predicted_human:
                spoof_false_accepts[attack_type] += 1

    human_total = counts["tp"] + counts["fn"]
    spoof_total = counts["tn"] + counts["fp"]
    human_recall = counts["tp"] / human_total if human_total else 0.0
    spoof_recall = counts["tn"] / spoof_total if spoof_total else 0.0
    balanced_accuracy = (human_recall + spoof_recall) / 2
    bpcer = counts["fn"] / human_total if human_total else 0.0

    apcer_by_attack = {
        attack_type: spoof_false_accepts.get(attack_type, 0) / total
        for attack_type, total in sorted(spoof_totals.items())
        if total
    }
    apcer_avg = (
        sum(apcer_by_attack.values()) / len(apcer_by_attack)
        if apcer_by_attack
        else 0.0
    )
    apcer_max = max(apcer_by_attack.values(), default=0.0)
    acer = (apcer_avg + bpcer) / 2
    worst_attacks = (
        sorted(
            attack_type
            for attack_type, value in apcer_by_attack.items()
            if value == apcer_max
        )
        if apcer_max > 0
        else []
    )

    return {
        "threshold": threshold,
        "hard_fail_threshold": hard_fail_threshold,
        "balanced_accuracy": balanced_accuracy,
        "human_recall": human_recall,
        "spoof_recall": spoof_recall,
        "false_accept_rate": counts["fp"] / spoof_total if spoof_total else 0.0,
        "false_reject_rate": bpcer,
        "bpcer": bpcer,
        "apcer_avg": apcer_avg,
        "apcer_max": apcer_max,
        "acer": acer,
        "apcer_by_attack": apcer_by_attack,
        "worst_attacks": worst_attacks,
        "counts": counts,
    }


def sweep_antispoof_thresholds(records: list[dict[str, Any]], top_n: int) -> None:
    labeled = [
        record
        for record in records
        if record.get("label") in {"human", "spoof"}
        and isinstance(record.get("spoof_score"), (int, float))
        and isinstance(record.get("max_spoof_score"), (int, float))
    ]
    if not labeled:
        print("\nNo labeled anti-spoof samples found.")
        return

    spoof_scores = sorted({float(record["spoof_score"]) for record in labeled} | {1.0})
    max_scores = sorted({float(record["max_spoof_score"]) for record in labeled} | {1.0})
    candidates: list[dict[str, Any]] = []

    for threshold in spoof_scores:
        for hard_fail_threshold in max_scores:
            if hard_fail_threshold < threshold:
                continue
            candidates.append(
                compute_pad_metrics(
                    labeled,
                    threshold=threshold,
                    hard_fail_threshold=hard_fail_threshold,
                )
            )

    ranked = sorted(
        candidates,
        key=lambda item: (
            item["apcer_max"],
            item["acer"],
            item["bpcer"],
            -item["balanced_accuracy"],
            item["threshold"],
            item["hard_fail_threshold"],
        ),
    )

    print("\nTop anti-spoof threshold candidates (PAD-oriented):")
    for item in ranked[:top_n]:
        worst_attack_text = ",".join(item["worst_attacks"]) if item["worst_attacks"] else "n/a"
        print(
            "  "
            f"threshold={item['threshold']:.4f} "
            f"hard_fail={item['hard_fail_threshold']:.4f} "
            f"bpcer={item['bpcer']:.4f} "
            f"apcer_avg={item['apcer_avg']:.4f} "
            f"apcer_max={item['apcer_max']:.4f} "
            f"acer={item['acer']:.4f} "
            f"worst_attack={worst_attack_text} "
            f"balanced_acc={item['balanced_accuracy']:.4f} "
            f"human_recall={item['human_recall']:.4f} "
            f"spoof_recall={item['spoof_recall']:.4f} "
            f"far={item['false_accept_rate']:.4f} "
            f"frr={item['false_reject_rate']:.4f}"
        )


def _collect_landmark_metric(
    records: list[dict[str, Any]],
    *,
    challenge_type: str,
    label: str,
    metric_name: str,
) -> list[float]:
    values: list[float] = []
    for record in records:
        if str(record.get("challenge_type")) != challenge_type or str(record.get("label")) != label:
            continue
        metrics = record.get("landmark_metrics")
        if not isinstance(metrics, dict):
            continue
        value = metrics.get(metric_name)
        if isinstance(value, (int, float)):
            values.append(float(value))
    return values


def recommend_liveness_thresholds(records: list[dict[str, Any]]) -> None:
    print("\nLiveness threshold suggestions (heuristic, calibration-only):")

    blink_mins = _collect_landmark_metric(
        records,
        challenge_type="blink_twice",
        label="human",
        metric_name="ear_min",
    )
    blink_maxes = _collect_landmark_metric(
        records,
        challenge_type="blink_twice",
        label="human",
        metric_name="ear_max",
    )
    if blink_mins and blink_maxes:
        closed_threshold = round(percentile(blink_mins, 0.9), 4)
        open_threshold = round(max(percentile(blink_maxes, 0.25), closed_threshold + 0.02), 4)
        print(
            "  "
            f"blink_closed_threshold={closed_threshold:.4f} "
            f"blink_open_threshold={open_threshold:.4f} "
            "(derived from successful human blink sessions)"
        )
    else:
        print("  blink thresholds: need human `blink_twice` samples with `ear_min` and `ear_max`")

    left_yaw = [
        abs(value)
        for value in _collect_landmark_metric(
            records,
            challenge_type="turn_left",
            label="human",
            metric_name="yaw_min",
        )
    ]
    right_yaw = _collect_landmark_metric(
        records,
        challenge_type="turn_right",
        label="human",
        metric_name="yaw_max",
    )
    yaw_peaks = left_yaw + [abs(value) for value in right_yaw]
    if yaw_peaks:
        yaw_threshold = round(max(percentile(yaw_peaks, 0.25), 8.0), 4)
        print(
            "  "
            f"turn_yaw_threshold_degrees={yaw_threshold:.4f} "
            "(lower-quartile of successful human turn peaks)"
        )
    else:
        print("  turn yaw threshold: need human `turn_left`/`turn_right` samples with `yaw_min`/`yaw_max`")

    mouth_peaks = _collect_landmark_metric(
        records,
        challenge_type="open_mouth",
        label="human",
        metric_name="mouth_ratio_max",
    )
    if mouth_peaks:
        mouth_threshold = round(percentile(mouth_peaks, 0.25), 4)
        print(
            "  "
            f"mouth_open_threshold={mouth_threshold:.4f} "
            "(lower-quartile of successful human mouth-open peaks)"
        )
    else:
        print("  mouth threshold: need human `open_mouth` samples with `mouth_ratio_max`")


def main() -> int:
    args = parse_args()
    records = load_records(args.input_path)
    print(f"Loaded {len(records)} calibration samples from {args.input_path}")
    summarize_counts(records)
    summarize_attack_coverage(records)
    summarize_numeric_metrics(records)
    sweep_antispoof_thresholds(records, top_n=args.top)
    recommend_liveness_thresholds(records)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
