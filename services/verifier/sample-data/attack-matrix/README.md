# Attack Matrix Workflow

Store labeled attack-matrix verifier outcomes here as newline-delimited JSON (`.ndjson`).

This dataset is not for training. It is for measuring the current verifier stack by canonical attack class so release checks can answer:

- which attacks still pass
- which gate catches each attack
- how confidence and spoof scores distribute by class

Run the analyzer with:

```bash
cd /Users/skadi2910/projects/sui-liveness-detection/services/verifier
.venv/bin/python scripts/analyze_attack_matrix.py sample-data/attack-matrix/local-dev.ndjson
```

Copy the template file to start a local dataset:

```bash
cp sample-data/attack-matrix/local-dev.template.ndjson sample-data/attack-matrix/local-dev.ndjson
```

Minimal row shape:

```json
{
  "sample_id": "sess_attack_001",
  "label": "spoof",
  "attack_type": "screen_replay",
  "challenge_type": "turn_right",
  "status": "failed",
  "human": false,
  "failure_reason": "spoof_detected",
  "confidence": 0.18,
  "spoof_score": 0.91,
  "max_spoof_score": 0.97,
  "notes": "phone replay of a prerecorded clip"
}
```

Canonical classes tracked by the analyzer:

- `live`
- `print`
- `replay`
- `talking_head`
- `face_swap`
- `non_human`
- `injection`

Common `attack_type` aliases are normalized into those classes:

- `screen_replay`, `prerecorded_video` -> `replay`
- `ai_video`, `talking_head_replay` -> `talking_head`
- `face_swap_replay` -> `face_swap`
- `virtual_camera` -> `injection`
- `animal`, `cartoon`, `plush` -> `non_human`

Suggested fields:

- `sample_id`
- `label`
- `attack_type`
- `challenge_type`
- `status`
- `human`
- `failure_reason`
- `confidence`
- `spoof_score`
- `max_spoof_score`
- `capture_medium`
- `source_split`
- `notes`

Expected targets:

- `live` pass rate should stay high
- all spoof classes should have `0%` pass rate
- any non-zero spoof pass rate should be treated as a release-blocking investigation
