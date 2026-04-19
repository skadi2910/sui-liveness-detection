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
- `GET /ws/sessions/{session_id}/stream`
- compatibility alias: `GET /ws/verify/{session_id}`
- admin QA endpoints for frame/session evaluation and dataset append flows

The active pipeline is deterministic and mock-driven for local testing by default:

- mock face detection
- mock liveness challenge evaluation
- mock anti-spoof scoring
- mock evidence encryption and storage
- mock proof minting

This means the service is ready for local flow testing now, while the real adapter modes can be enabled incrementally through environment configuration.

## Real Seal, Walrus, And Sui Adapters

The verifier now supports explicit adapter modes in addition to the legacy boolean flags:

- `VERIFIER_CHAIN_ADAPTER_MODE=mock|sui_cli`
- `VERIFIER_STORAGE_ADAPTER_MODE=memory|walrus_cli`
- `VERIFIER_ENCRYPTION_ADAPTER_MODE=mock|seal_command`

The legacy booleans still work as a fallback:

- `VERIFIER_CHAIN_ADAPTER_ENABLED=true` maps to `sui_cli`
- `VERIFIER_STORAGE_ADAPTER_ENABLED=true` maps to `walrus_cli`
- `VERIFIER_ENCRYPTION_ADAPTER_ENABLED=true` maps to `seal_command`

### Sui CLI proof minting

Set the following when using `sui_cli`:

- `VERIFIER_SUI_CLIENT_CONFIG_PATH`
- `VERIFIER_SUI_ENV_ALIAS`
- `VERIFIER_SUI_EXPECTED_ACTIVE_ADDRESS`
- `VERIFIER_SUI_PACKAGE_ID`
- `VERIFIER_SUI_REGISTRY_OBJECT_ID`
- `VERIFIER_SUI_VERIFIER_CAP_OBJECT_ID`

The active address in the referenced Sui config should be the verifier-controlled signer that owns the `VerifierCap`.

### Walrus CLI storage

Set the following when using `walrus_cli`:

- `VERIFIER_WALRUS_CONFIG_PATH`
- `VERIFIER_WALRUS_CONTEXT`
- `VERIFIER_WALRUS_WALLET_PATH`

The store adapter uploads only Seal-encrypted bytes and deletes uploaded blobs on a best-effort basis if minting or renewing the proof fails afterward.

### Seal command bridge

Set the following when using `seal_command`:

- `VERIFIER_SEAL_ENCRYPT_COMMAND`
- optional `VERIFIER_SEAL_DECRYPT_COMMAND`
- optional `VERIFIER_SEAL_COMMAND_CWD`
- `VERIFIER_SEAL_SERVER_CONFIGS`
- `VERIFIER_SEAL_THRESHOLD`
- optional `VERIFIER_SEAL_SUI_NETWORK`
- optional `VERIFIER_SEAL_SUI_BASE_URL`
- optional `VERIFIER_SEAL_VERIFY_KEY_SERVERS`
- optional `VERIFIER_SEAL_TIMEOUT_MS`

The verifier expects the encrypt command to read JSON on stdin and return JSON with:

- `encrypted_bytes_b64`
- `seal_identity`
- optional `policy_version`
- optional `metadata`

The optional decrypt command should return `decrypted_bytes_b64`.

This keeps the Python verifier runtime decoupled from the current TypeScript-first Seal SDK while still allowing a real backend-owned encryption path.

For the repo-owned helper introduced in this branch, use:

```bash
VERIFIER_ENCRYPTION_ADAPTER_MODE=seal_command
VERIFIER_SEAL_ENCRYPT_COMMAND="node apps/web/scripts/seal-encrypt.mjs"
VERIFIER_SEAL_COMMAND_CWD="../.."
VERIFIER_SEAL_SERVER_CONFIGS='[{"objectId":"0x...","weight":1}]'
VERIFIER_SEAL_THRESHOLD=1
VERIFIER_SEAL_SUI_NETWORK="testnet"
VERIFIER_SEAL_SUI_BASE_URL="https://fullnode.testnet.sui.io:443"
```

The helper inherits `VERIFIER_SUI_PACKAGE_ID`, so it encrypts under the same package namespace that the SBT minting flow uses for `seal_approve_owner`.

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
