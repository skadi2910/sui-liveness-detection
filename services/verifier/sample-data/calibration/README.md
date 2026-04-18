# Calibration Sample Workflow

Store project-native verifier samples here as newline-delimited JSON (`.ndjson`).

These rows are for calibration and QA only. The MVP is already using pretrained models:

- YOLOv8-Face for face detection
- Silent-Face for anti-spoofing
- MediaPipe Face Landmarker for browser-side landmarks

You are not collecting a training dataset here. You are collecting local validation data to tune thresholds and confirm that the pretrained stack behaves well on your real devices and lighting conditions.

The current verifier does not have a separate deepfake detector. For now, deepfake-style tests should be labeled as spoof attacks with a specific `attack_type` such as `ai_video`, `face_swap_replay`, or `virtual_camera`.

Recommended capture flow:

1. Run local verifier sessions with the webcam harness.
2. After each session, export or append one JSON object describing the result and aggregated landmark-derived metrics.
3. Label each row as `human` or `spoof`.
4. For spoof rows, always add an `attack_type`.
5. Keep calibration and holdout samples separate with `source_split`.
6. Run the analyzer:

```bash
cd /Users/skadi2910/projects/sui-liveness-detection/services/verifier
.venv/bin/python scripts/analyze_calibration_samples.py sample-data/calibration/local-dev.ndjson
```

There is also a template file you can copy to start a local dataset:

```bash
cp sample-data/calibration/local-dev.template.ndjson sample-data/calibration/local-dev.ndjson
```

Minimal row shape:

```json
{
  "sample_id": "sess_1234",
  "label": "human",
  "challenge_type": "turn_left",
  "status": "verified",
  "human": true,
  "attack_type": "bona_fide",
  "capture_medium": "camera",
  "source_split": "holdout",
  "spoof_score": 0.08,
  "max_spoof_score": 0.11,
  "confidence": 0.93,
  "challenge_progress": 1.0,
  "landmark_metrics": {
    "point_count_max": 478,
    "yaw_min": -28.4,
    "yaw_max": -3.1,
    "ear_min": 0.19,
    "ear_max": 0.31,
    "mouth_ratio_max": 0.17
  },
  "model_strategy": "pretrained-calibration-only",
  "notes": "desktop webcam, office lighting"
}
```

Suggested fields when available:

- `sample_id`
- `label`
- `attack_type`
- `capture_medium`
- `source_split`
- `challenge_type`
- `status`
- `human`
- `spoof_score`
- `max_spoof_score`
- `confidence`
- `challenge_progress`
- `landmark_metrics`
- `model_strategy`
- `notes`

Recommended `attack_type` values for the current MVP:

- `bona_fide`
- `print`
- `screen_replay`
- `prerecorded_video`
- `virtual_camera`
- `ai_image`
- `ai_video`
- `face_swap_replay`
- `unknown_spoof`

Recommended `source_split` values:

- `train_calibration`
- `dev`
- `holdout`

The analyzer currently does four things:

- summarizes counts and numeric metric ranges by challenge and label
- summarizes attack coverage by `attack_type` and `capture_medium`
- sweeps `spoof_score` and `max_spoof_score` thresholds to suggest anti-spoof calibration candidates using PAD-style metrics
- suggests heuristic blink, turn, and mouth liveness thresholds from successful human sessions

The PAD-oriented threshold sweep reports:

- `BPCER` for rejected bona fide samples
- `APCER` averaged across attack types
- `APCER_max` for the worst attack type
- `ACER` as a quick threshold-comparison summary

Use `APCER_max` as the main shipping guardrail. A good average can hide one weak attack class.

Recommended landmark metric keys for best threshold suggestions:

- `ear_min`
- `ear_max`
- `yaw_min`
- `yaw_max`
- `yaw_abs_peak`
- `mouth_ratio_max`
