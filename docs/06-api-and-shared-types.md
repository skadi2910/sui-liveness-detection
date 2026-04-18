# API And Shared Types

## Goal

Keep frontend, backend, admin QA, and future chain/storage work aligned through one stable contract layer in `packages/shared`.

## Contract Design Principles

- Public verifier APIs stay **session-oriented**, not model-oriented.
- Admin / QA APIs may expose stage-by-stage diagnostics.
- New verifier heads should extend existing result/debug payloads instead of creating breaking public routes.
- Shared field names should stay stable across mock, local, Docker, and future chain-integrated phases.

## Shared Enums

### `ChallengeType`

- `blink_twice`
- `turn_left`
- `turn_right`
- `nod_head`
- `smile`
- `open_mouth`

### `SessionStatus`

- `created`
- `ready`
- `streaming`
- `processing`
- `verified`
- `failed`
- `expired`

### `VerificationMode`

- `full`
- `liveness_only`
- `antispoof_only`
- `deepfake_only`

## Public REST Contracts

### `POST /api/sessions`

Request fields:

- `wallet_address`
- `client.platform`
- `client.user_agent`
- optional admin/QA fields such as:
  - `mode`
  - `challenge_sequence`

Response fields:

- `session_id`
- `status`
- `challenge_type`
- `challenge_sequence`
- `expires_at`
- `ws_url`

### `GET /api/sessions/{session_id}`

Response fields:

- `session_id`
- `status`
- `challenge_type`
- `challenge_sequence`
- `created_at`
- `expires_at`
- `result`

### `GET /api/health`

Response fields:

- `status`
- `redis`
- `models`
- `chain_adapter`
- `storage_adapter`
- `encryption_adapter`
- `model_details`
- `tuning`

Current `model_details` includes runtime state for:

- `face_detector`
- `antispoof`
- `deepfake`
- `human_face`

## Admin REST Contracts

### `POST /api/admin/evaluate/frame`

Admin-only frame diagnostic endpoint.

Response shape includes:

- `evaluation_mode`
- `accepted_for_liveness`
- `accepted_for_spoof`
- `face_detection`
- `quality`
- `landmark_spotcheck`
- `human_face`
- `liveness`
- `antispoof`
- `deepfake`

### `POST /api/admin/evaluate/session`

Admin-only session diagnostic endpoint.

Response shape includes:

- `evaluation_mode`
- `frames_processed`
- `accepted_frame_indices`
- `face_detected`
- `quality_frames_available`
- `face_detection`
- `quality`
- `landmark_spotcheck`
- `human_face`
- `liveness`
- `antispoof`
- `deepfake`
- `verdict_preview`

### `POST /api/admin/calibration/append`

Admin-only append endpoint for saving calibration rows.

### `POST /api/admin/attack-matrix/append`

Admin-only append endpoint for saving attack-matrix rows.

## WebSocket Contracts

### Public Stream Route

- canonical route: `GET /ws/sessions/{session_id}/stream`
- compatibility alias: `GET /ws/verify/{session_id}`

### Client Events

- `frame`
- `landmarks`
- `heartbeat`
- `finalize`

`finalize` may carry:

- `mode`

### Server Events

- `session_ready`
- `challenge_update`
- `progress`
- `processing`
- `verified`
- `failed`
- `error`

## Shared Objects

### `VerificationProgress`

Current progress payloads include:

- `session_id`
- `status`
- `challenge_type`
- `challenge_sequence`
- `current_challenge_index`
- `total_challenges`
- `completed_challenges`
- `progress`
- `step_progress`
- `frames_processed`
- `message`
- `debug`

### `VerificationDebugPayload`

Current live debug payload includes:

- `face_detection`
- `quality`
- `landmark_spotcheck`
- `human_face`
- `antispoof`
- optional `deepfake` at terminal/finalize output
- current step / progress messaging

### `VerificationResult`

Current terminal result payload includes:

- `session_id`
- `status`
- `evaluation_mode`
- `human`
- `confidence`
- `spoof_score`
- `max_spoof_score`
- `human_face_score`
- `human_face_message`
- `human_face_enabled`
- `deepfake_score`
- `max_deepfake_score`
- `deepfake_frames_processed`
- `deepfake_message`
- `deepfake_enabled`
- `attack_analysis`
- `proof_id`
- `blob_id`
- `expires_at`
- `failure_reason`

### `attack_analysis`

Structured terminal attack diagnostics may include:

- `failure_category`
- `suspected_attack_family`
- `presentation_attack_detected`
- `presentation_attack_score`
- `presentation_attack_peak`
- `deepfake_detected`
- `deepfake_score`
- `deepfake_peak`
- `note`

This is now the preferred way to interpret failed attack sessions rather than relying only on `failure_reason`.

### `EvidenceBlob`

`EvidenceBlob` represents the retained evidence package before encryption.

Current retained evidence should include:

- session identifiers and timestamps
- challenge sequence / summary
- frame hashes
- landmark trace summary
- quality / anti-spoof / deepfake summaries
- human-face summary
- model hashes
- final verdict context

The full payload should be serialized to JSON and encrypted as one unit before Walrus storage.

## Chain-And-Storage Fields

These values may remain optional during mock phases, but the naming should stay stable:

- `proof_id`
- `blob_id`
- `seal_identity`
- `expires_at`

## Contract Hygiene Rules

- Shared contracts must be versioned in `packages/shared`.
- Frontend and backend tests should validate payload parity from the same fixture set.
- Chain/storage values may stay optional during local phases, but field names should not churn.
- New verifier heads should extend `debug`, `health`, and `result` payloads before introducing new public surface area.
