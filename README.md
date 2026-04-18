# Sui Human

Sui Human is a Proof-of-Human AI identity verifier built around three tracks:

- `apps/web`: Next.js MVP demo for camera capture, challenge UX, and wallet-driven verification flow.
- `services/verifier`: FastAPI verification service for sessions, liveness, anti-spoofing, and evidence assembly.
- `contracts/move`: Sui Move package for Proof-of-Human SBT minting, renewal, revocation, and verification queries.

This repository currently contains the implementation spec pack, repo skeleton, and agent work plan so parallel contributors can start building without redefining the architecture.

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

## Current Status

- The spec pack in `docs/` is the source of truth for MVP scope and sequencing.
- The repo is intentionally scaffold-first so frontend, backend, and blockchain agents can work in parallel.
- The preferred build order is frontend MVP demo, backend verifier pipeline, then Sui/Walrus/Seal/zkLogin integration.
- The local verifier and webcam testing harness are now scaffolded for flow testing.
- The current MVP uses pretrained models end to end; project-native sample capture is for calibration and validation, not retraining.
- The browser harness can export completed sessions as NDJSON calibration rows for local threshold tuning.

## Progress Tracking

- Current implementation checkpoint: [docs/10-progress-log.md](/Users/skadi2910/projects/sui-liveness-detection/docs/10-progress-log.md)

## Local Development

For the current local MVP:

- backend service: `services/verifier`
- frontend harness: `apps/web`
- local compose stack: [docker-compose.yml](/Users/skadi2910/projects/sui-liveness-detection/docker-compose.yml)

## Next Build Targets

1. Scaffold `apps/web` with a simple monospace Next.js App Router experience.
2. Scaffold `services/verifier` with FastAPI, Redis session management, and WebSocket session flow.
3. Scaffold `contracts/move` with a non-transferable `ProofOfHuman` object and integration adapters.
