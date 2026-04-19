# Sui Human

Sui Human is a wallet-aware Proof-of-Human verification system that combines live liveness checks, anti-spoofing, deepfake screening, encrypted evidence retention, Walrus storage, and Sui-based proof minting.

The current product flow is:

1. Connect a Sui wallet in the web app.
2. Complete the live verification challenge.
3. Finalize verification on the verifier backend.
4. Sign the proof transaction from the frontend wallet.
5. Receive a Sui proof receipt with linked on-chain metadata.

## Tech Stack

- ![Next.js](https://img.shields.io/badge/Next.js-16-000000?logo=nextdotjs&logoColor=white) ![React](https://img.shields.io/badge/React-19-20232A?logo=react&logoColor=61DAFB) ![TypeScript](https://img.shields.io/badge/TypeScript-5-3178C6?logo=typescript&logoColor=white) Frontend application and wallet-driven verification UX
- ![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS-3-0F172A?logo=tailwindcss&logoColor=38BDF8) ![Vitest](https://img.shields.io/badge/Vitest-Tested-729B1B?logo=vitest&logoColor=white) UI styling and frontend test coverage
- ![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688?logo=fastapi&logoColor=white) ![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white) Verification API, session orchestration, evidence assembly, and claim preparation
- ![ONNX Runtime](https://img.shields.io/badge/ONNX_Runtime-Inference-005CED?logo=onnx&logoColor=white) ![OpenCV](https://img.shields.io/badge/OpenCV-Vision-5C3EE8?logo=opencv&logoColor=white) ![Ultralytics](https://img.shields.io/badge/YOLOv8-Face_Detection-111827) Model inference for face detection, anti-spoofing, and deepfake screening
- ![Sui](https://img.shields.io/badge/Sui-Testnet-6FBCF0?logoColor=white) ![Move](https://img.shields.io/badge/Move-Smart_Contracts-4B5563) Non-transferable proof contract, claim validation, renewal, and revocation
- ![Walrus](https://img.shields.io/badge/Walrus-Encrypted_Storage-1F2937) ![Seal](https://img.shields.io/badge/Seal-Evidence_Encryption-111827) Encrypted evidence storage and retrieval pipeline
- ![Mysten dApp Kit](https://img.shields.io/badge/Mysten-dApp_Kit-0F172A) ![npm](https://img.shields.io/badge/npm-Workspace-CB3837?logo=npm&logoColor=white) Wallet integration and shared frontend/backend contracts

## What This Repository Contains

- `apps/web`
  The Next.js application for the end-user journey, wallet connection, live camera flow, result receipt, and proof mint signing.

- `services/verifier`
  The FastAPI verifier service that manages verification sessions, model evaluation, final verdicts, encrypted evidence assembly, Walrus upload, and wallet-claim preparation.

- `contracts/move`
  The Sui Move package that defines the Proof-of-Human object, registry, claim-based mint flow, renewals, revocations, and owner checks.

- `packages/shared`
  Shared contracts and types used across the frontend and backend.

- `docs`
  Specs, implementation plans, progress checkpoints, and design artifacts.

## Core Capabilities

- Live challenge flow with webcam-based liveness interactions
- Face detection, human-face screening, anti-spoofing, and deepfake analysis
- Finalize-then-mint UX with wallet-signed proof transactions
- Claim-based Sui proof minting and renewal
- Seal-encrypted evidence payloads
- Walrus-backed encrypted evidence storage
- SuiScan-ready proof and transaction receipts

## Architecture

```text
apps/web
  -> starts verification session
  -> streams camera frames and challenge metadata
  -> requests final server verdict
  -> requests a prepared proof claim
  -> signs and submits the Sui transaction from the wallet

services/verifier
  -> evaluates liveness, anti-spoof, deepfake, human-face gates
  -> assembles retained evidence
  -> encrypts evidence with Seal
  -> stores ciphertext in Walrus
  -> prepares a signed proof claim for the wallet
  -> records final proof receipt metadata

contracts/move
  -> validates the prepared claim on-chain
  -> mints or renews ProofOfHuman
  -> supports revoke and owner-side approval checks
```

## Current User Flow

1. Open `/app`.
2. Connect a Sui wallet.
3. Start a new verification session.
4. Complete the live challenge sequence.
5. Click `Finalize verification`.
6. If the backend returns `verified`, click `Mint proof`.
7. Approve the transaction in the wallet.
8. Review the proof receipt and SuiScan links.

## Prerequisites

For the full local flow, install:

- Node.js 20+
- npm
- Python 3.11+
- Sui CLI configured for `testnet`
- Walrus CLI configured for `testnet`
- A browser wallet that can sign Sui transactions on testnet

Optional but recommended for the real pipeline:

- Local verifier model assets for face detection, anti-spoof, and deepfake evaluation
- Seal server configuration for testnet

## Local Development

### 1. Install frontend dependencies

```bash
cd /Users/skadi2910/projects/sui-liveness-detection/apps/web
npm install
```

### 2. Install verifier dependencies

```bash
cd /Users/skadi2910/projects/sui-liveness-detection/services/verifier
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### 3. Configure environment files

Frontend:

- [apps/web/.env.example](/Users/skadi2910/projects/sui-liveness-detection/apps/web/.env.example)
- local file: `apps/web/.env.local`

Verifier:

- [services/verifier/.env.example](/Users/skadi2910/projects/sui-liveness-detection/services/verifier/.env.example)
- local file: `services/verifier/.env`

At minimum, make sure these are configured for the real flow:

- frontend package/network config
- verifier Sui package id, registry object id, verifier cap id
- Walrus config path, context, and wallet path
- Seal command/server settings

### 4. Start the verifier backend

```bash
cd /Users/skadi2910/projects/sui-liveness-detection/services/verifier
source .venv/bin/activate
.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Backend health:

- [http://127.0.0.1:8000/api/health](http://127.0.0.1:8000/api/health)

### 5. Start the frontend

```bash
cd /Users/skadi2910/projects/sui-liveness-detection/apps/web
npm run dev
```

Frontend app:

- [http://localhost:3000/app](http://localhost:3000/app)

## Useful Commands

### Frontend

```bash
cd /Users/skadi2910/projects/sui-liveness-detection/apps/web
npm run dev
npm run build
npm run test
```

### Verifier

```bash
cd /Users/skadi2910/projects/sui-liveness-detection/services/verifier
source .venv/bin/activate
PYTHONPATH=. pytest
```

### Shared package typecheck

```bash
cd /Users/skadi2910/projects/sui-liveness-detection/packages/shared
../../apps/web/node_modules/.bin/tsc --noEmit -p tsconfig.json
```

### Move package

```bash
cd /Users/skadi2910/projects/sui-liveness-detection
sui move build --path contracts/move
sui move test --path contracts/move
```

## Repository Layout

```text
apps/
  web/
contracts/
  move/
docs/
infra/
packages/
  shared/
services/
  verifier/
```

## Important Notes

- The verifier currently supports both real adapter modes and local development fallbacks.
- The proof mint flow is wallet-signed from the frontend, which makes failures easier to inspect in normal dapp UX.
- The verifier may report `redis: degraded` in local development when running without a dedicated Redis service. That does not block the normal single-machine testing loop.
- Proof receipt and transaction inspection are intended to happen through SuiScan links in the app flow.

## Related Docs

- [docs/17-frontend-smart-contract-integration-progress.md](/Users/skadi2910/projects/sui-liveness-detection/docs/17-frontend-smart-contract-integration-progress.md)
- [docs/15-sui-walrus-seal-implementation-plan.md](/Users/skadi2910/projects/sui-liveness-detection/docs/15-sui-walrus-seal-implementation-plan.md)
- [services/verifier/README.md](/Users/skadi2910/projects/sui-liveness-detection/services/verifier/README.md)

## Status

This repository now contains a working integrated flow for:

- verification session creation
- liveness and model-based finalization
- Seal encryption
- Walrus upload
- wallet-signed Sui proof minting

The next iterations should focus on:

- richer proof history and dashboard surfaces
- owner-side decrypt UX
- stronger cleanup and recovery around interrupted proof claim flows
