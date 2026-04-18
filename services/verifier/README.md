# `services/verifier`

This workspace will host the FastAPI verification backend.

Primary responsibilities:

- REST session lifecycle endpoints
- WebSocket frame ingestion
- Redis-backed challenge state
- anti-spoof and liveness orchestration
- evidence blob assembly
- adapters for Sui, Walrus, and Seal

See [docs/04-backend-spec.md](/Users/skadi2910/projects/sui-liveness-detection/docs/04-backend-spec.md) for the implementation spec.

## Current Local Verifier

The current backend is a runnable FastAPI MVP scaffold with:

- `POST /api/sessions`
- `GET /api/sessions/{session_id}`
- `GET /api/health`
- `GET /ws/verify/{session_id}`

The active pipeline is deterministic and mock-driven for local testing:

- mock face detection
- mock liveness challenge evaluation
- mock anti-spoof scoring
- mock evidence encryption and storage
- mock proof minting

This means the service is ready for local flow testing now, while real ONNX and blockchain integrations remain a separate implementation phase.

## Real Model Loaders

The verifier now supports real model loader configuration in addition to mock mode:

- YOLOv8 face detector through `VERIFIER_FACE_MODEL_MODE` and `VERIFIER_FACE_MODEL_PATH`
- Silent-Face anti-spoof ONNX ensemble through `VERIFIER_ANTISPOOF_MODEL_MODE` and `VERIFIER_ANTISPOOF_MODEL_DIR`

Expected modes:

- `mock`
- `auto`

In `auto`, the service attempts to load the configured model assets and falls back to mock behavior if the files are missing or incompatible.

## Bootstrap

The backend skeleton now includes:

- `app/main.py` for FastAPI app creation
- `app/api/` for REST and WebSocket entrypoints
- `app/core/` for config and logging
- `app/sessions/` for typed models, session service logic, and Redis-ready storage

Install dependencies with:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```
