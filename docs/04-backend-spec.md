# Backend Spec

## Goal

Build a FastAPI verifier service that owns session orchestration, liveness decisioning, anti-spoof checks, and downstream proof handoff.

## Stack

- Python 3.13+
- FastAPI
- Uvicorn
- Redis
- OpenCV
- ONNX Runtime
- optional FFmpeg utilities

Bootstrap should assume `venv` + `pip` because `uv` is not currently installed locally.

## Service Responsibilities

- create verification sessions
- select and track challenge state
- accept frame or event streams over WebSocket
- run face-detection, challenge-evaluation, and anti-spoof orchestration
- emit progress and final outcome payloads
- assemble evidence metadata without persisting raw video frames
- call adapters for chain minting, storage, and encryption

## Proposed Layout

```text
services/verifier/
  app/
    main.py
    api/
      routes.py
      websocket.py
    core/
      config.py
      logging.py
    sessions/
      service.py
      models.py
      redis_store.py
    pipeline/
      face.py
      liveness.py
      antispoof.py
      evidence.py
    adapters/
      proof_minter.py
      evidence_store.py
      evidence_encryptor.py
```

## REST Interface

### `POST /api/sessions`

Creates a verification session.

Request:

```json
{
  "wallet_address": "0xabc...",
  "client": {
    "platform": "web",
    "user_agent": "Mozilla/5.0"
  }
}
```

Response:

```json
{
  "session_id": "sess_123",
  "status": "created",
  "challenge_type": "blink_twice",
  "expires_at": "2026-04-17T14:00:00Z",
  "ws_url": "/ws/verify/sess_123"
}
```

### `GET /api/sessions/{session_id}`

Returns current session state and final result when available.

### `GET /api/health`

Returns service, Redis, and model readiness.

## WebSocket Interface

### `GET /ws/verify/{session_id}`

Bidirectional channel for challenge progress and verification events.

Client-to-server message families:

- `frame`
- `landmarks`
- `heartbeat`
- `finalize`

Server-to-client message families:

- `session_ready`
- `challenge_update`
- `progress`
- `processing`
- `verified`
- `failed`
- `error`

## Session Rules

- Session TTL defaults to 10 minutes in Redis.
- A wallet address may have at most one active verification session at a time.
- Rate limit repeated attempts per wallet for 10 minutes after a terminal state.
- Session state must survive WebSocket reconnects inside the TTL window.

## Evidence Rules

- Never persist raw video frames as the default behavior.
- Evidence blob for later Walrus/Seal integration should include frame hashes, challenge summary, spoof score summary, and timestamps.
- The evidence assembly layer should be independent from any specific storage provider.

## Adapter Contracts

### `ProofMinter`

- `mint_proof(session_result) -> MintResult`
- `renew_proof(wallet_address, previous_proof_id) -> RenewResult`

### `EvidenceStore`

- `put_encrypted_blob(blob_bytes, metadata) -> blob_id`
- `delete_blob(blob_id) -> bool`

### `EvidenceEncryptor`

- `encrypt_for_wallet(wallet_address, payload) -> encrypted_bytes`
- `decrypt_for_dispute(policy_input) -> payload`

## Backend Definition Of Done

- REST endpoints and WebSocket channel match shared contracts.
- Redis-backed session recovery works across reconnects.
- One challenge type can complete end to end with deterministic pass and fail paths.
- Minting is pluggable through `ProofMinter` and can be mocked for early frontend integration.
