from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
from statistics import median
from typing import Any

from scripts.analyze_calibration_samples import load_records


CANONICAL_ATTACK_CLASSES = (
    "live",
    "print",
    "replay",
    "talking_head",
    "face_swap",
    "non_human",
    "injection",
    "unknown_spoof",
)

_ATTACK_CLASS_ALIASES = {
    "bona_fide": "live",
    "human": "live",
    "live": "live",
    "print": "print",
    "printed_photo": "print",
    "screen_replay": "replay",
    "prerecorded_video": "replay",
    "replay": "replay",
    "ai_video": "talking_head",
    "talking_head": "talking_head",
    "talking_head_replay": "talking_head",
    "face_swap": "face_swap",
    "face_swap_replay": "face_swap",
    "non_human": "non_human",
    "animal": "non_human",
    "cartoon": "non_human",
    "plush": "non_human",
    "virtual_camera": "injection",
    "injection": "injection",
    "obs_virtual_camera": "injection",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Summarize verifier attack-matrix outcomes by canonical attack class.",
    )
    parser.add_argument(
        "input_path",
        type=Path,
        help="Path to a NDJSON attack-matrix file.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the computed report as JSON instead of a text summary.",
    )
    return parser.parse_args()


def normalize_attack_class(record: dict[str, Any]) -> str:
    label = str(record.get("label", "")).strip().lower()
    if label == "human":
        return "live"

    attack_type = str(record.get("attack_type", "")).strip().lower()
    if attack_type:
        return _ATTACK_CLASS_ALIASES.get(attack_type, attack_type)

    if label == "spoof":
        return "unknown_spoof"
    return "unknown_spoof"


def record_passed(record: dict[str, Any]) -> bool:
    human = record.get("human")
    if isinstance(human, bool):
        return human

    status = str(record.get("status", "")).strip().lower()
    if status == "verified":
        return True
    if status in {"failed", "expired"}:
        return False

    return False


def _normalize_failure_reason(record: dict[str, Any]) -> str:
    value = record.get("failure_reason")
    if isinstance(value, str) and value.strip():
        return value.strip().lower()
    if record_passed(record):
        return "passed"
    return "unknown_failure"


def _confidence_summary(values: list[float]) -> dict[str, float | None]:
    if not values:
        return {"min": None, "median": None, "max": None}
    ordered = sorted(values)
    return {
        "min": round(ordered[0], 4),
        "median": round(float(median(ordered)), 4),
        "max": round(ordered[-1], 4),
    }


def compute_attack_matrix(records: list[dict[str, Any]]) -> dict[str, Any]:
    per_class_records: dict[str, list[dict[str, Any]]] = defaultdict(list)
    ignored_records = 0

    for record in records:
        if not isinstance(record, dict):
            ignored_records += 1
            continue
        attack_class = normalize_attack_class(record)
        per_class_records[attack_class].append(record)

    class_reports: dict[str, dict[str, Any]] = {}
    target_misses: list[str] = []

    for attack_class in sorted(per_class_records):
        attack_records = per_class_records[attack_class]
        passed_count = sum(1 for record in attack_records if record_passed(record))
        total = len(attack_records)
        pass_rate = passed_count / total if total else 0.0
        confidence_values = [
            float(record["confidence"])
            for record in attack_records
            if isinstance(record.get("confidence"), (int, float))
        ]
        spoof_score_values = [
            float(record["spoof_score"])
            for record in attack_records
            if isinstance(record.get("spoof_score"), (int, float))
        ]
        failure_reasons = Counter(_normalize_failure_reason(record) for record in attack_records)
        target_pass_rate = 0.95 if attack_class == "live" else 0.0
        meets_target = pass_rate >= target_pass_rate if attack_class == "live" else pass_rate <= target_pass_rate
        if not meets_target:
            target_misses.append(attack_class)

        class_reports[attack_class] = {
            "samples": total,
            "passes": passed_count,
            "pass_rate": round(pass_rate, 4),
            "target_pass_rate": target_pass_rate,
            "meets_target": meets_target,
            "failure_reasons": dict(sorted(failure_reasons.items())),
            "confidence": _confidence_summary(confidence_values),
            "spoof_score": _confidence_summary(spoof_score_values),
        }

    missing_classes = [
        attack_class
        for attack_class in CANONICAL_ATTACK_CLASSES
        if attack_class not in class_reports
    ]

    return {
        "classes": class_reports,
        "missing_classes": missing_classes,
        "target_misses": sorted(target_misses),
        "ignored_records": ignored_records,
    }


def render_attack_matrix_report(report: dict[str, Any]) -> str:
    lines = ["Attack matrix summary:"]

    classes = report.get("classes", {})
    if not classes:
        lines.append("  no attack-matrix samples found")
        return "\n".join(lines)

    for attack_class, values in sorted(classes.items()):
        confidence = values["confidence"]
        spoof_score = values["spoof_score"]
        lines.append(
            "  "
            f"{attack_class}: "
            f"samples={values['samples']} "
            f"passes={values['passes']} "
            f"pass_rate={values['pass_rate']:.4f} "
            f"target={values['target_pass_rate']:.2f} "
            f"meets_target={'yes' if values['meets_target'] else 'no'}"
        )
        lines.append(
            "    "
            f"failure_reasons={json.dumps(values['failure_reasons'], sort_keys=True)} "
            f"confidence={json.dumps(confidence, sort_keys=True)} "
            f"spoof_score={json.dumps(spoof_score, sort_keys=True)}"
        )

    missing_classes = report.get("missing_classes", [])
    if missing_classes:
        lines.append(f"  missing_classes={','.join(missing_classes)}")

    target_misses = report.get("target_misses", [])
    if target_misses:
        lines.append(f"  target_misses={','.join(target_misses)}")
    else:
        lines.append("  target_misses=none")

    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    records = load_records(args.input_path)
    report = compute_attack_matrix(records)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(render_attack_matrix_report(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
