# API And Shared Types

## Goal

Keep frontend, backend, and future agent work aligned through a single set of shared payload contracts.

## Shared Enums

### `ChallengeType`

- `blink_twice`
- `turn_left`
- `turn_right`
- `open_mouth`

### `SessionStatus`

- `created`
- `ready`
- `streaming`
- `processing`
- `verified`
- `failed`
- `expired`

## Shared Objects

### `VerificationProgress`

```json
{
  "session_id": "sess_123",
  "status": "streaming",
  "challenge_type": "blink_twice",
  "progress": 0.6,
  "frames_processed": 18,
  "message": "Blink detected once"
}
```

### `VerificationResult`

```json
{
  "session_id": "sess_123",
  "status": "verified",
  "human": true,
  "confidence": 0.94,
  "spoof_score": 0.03,
  "proof_id": "0xproof",
  "blob_id": "walrus_blob_123",
  "expires_at": "2026-07-16T14:00:00Z"
}
```

### `EvidenceBlob`

```json
{
  "session_id": "sess_123",
  "wallet_address": "0xabc...",
  "challenge_type": "blink_twice",
  "frame_hashes": [
    "sha256:..."
  ],
  "landmark_snapshot": {
    "source": "mediapipe",
    "frame_index": 18
  },
  "spoof_score_summary": {
    "max": 0.10,
    "final": 0.03
  },
  "model_hashes": {
    "antispoof": "sha256:...",
    "face_detector": "sha256:..."
  },
  "captured_at": "2026-04-17T14:00:00Z"
}
```

## Session REST Contracts

### `POST /api/sessions`

Request fields:

- `wallet_address`
- `client.platform`
- `client.user_agent`

Response fields:

- `session_id`
- `status`
- `challenge_type`
- `expires_at`
- `ws_url`

### `GET /api/sessions/{session_id}`

Response fields:

- `session_id`
- `status`
- `challenge_type`
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

## WebSocket Event Shapes

### Client Events

```json
{
  "type": "frame",
  "timestamp": "2026-04-17T14:00:01Z",
  "image_base64": "..."
}
```

```json
{
  "type": "heartbeat",
  "timestamp": "2026-04-17T14:00:02Z"
}
```

### Server Events

```json
{
  "type": "progress",
  "payload": {
    "session_id": "sess_123",
    "status": "streaming",
    "challenge_type": "blink_twice",
    "progress": 0.5,
    "frames_processed": 10,
    "message": "Keep your face centered"
  }
}
```

```json
{
  "type": "verified",
  "payload": {
    "session_id": "sess_123",
    "status": "verified",
    "human": true,
    "confidence": 0.94,
    "spoof_score": 0.03,
    "proof_id": "0xproof",
    "blob_id": "walrus_blob_123",
    "expires_at": "2026-07-16T14:00:00Z"
  }
}
```

## Contract Hygiene Rules

- Shared contracts must be versioned in `packages/shared`.
- Frontend and backend tests should validate payload parity from the same fixture set.
- Chain-specific values may be optional during early phases, but the field names must not churn.
