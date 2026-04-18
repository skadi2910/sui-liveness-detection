# Product Brief

## Product

Sui Human is a proof-of-human verification product that combines browser-based liveness checks, AI anti-spoofing, and Sui-native identity proofs. A successful verification mints a non-transferable on-chain proof object tied to a Sui address.

## Problem

Bots, replay attacks, and synthetic identities undermine airdrops, gated communities, and Sybil-sensitive dapps. Existing systems often centralize biometric data or require traditional KYC, which increases privacy and trust concerns.

## Core Value

- Verify that a live human completed the challenge.
- Mint an on-chain proof without storing raw biometrics on-chain.
- Preserve user ownership of identity and evidence access.
- Give third-party Sui apps a simple verification surface.

## MVP Goals

- Deliver a web-based verification experience that works on desktop browsers.
- Support session creation, camera capture, liveness challenge completion, anti-spoof evaluation, and final verification result display.
- Mint a `ProofOfHuman` SBT-like object on Sui testnet once the verifier is stable.
- Define Walrus and Seal integration points up front so privacy features can be added without API churn.

## Primary Users

- End users who want to prove they are human without traditional KYC.
- Dapp teams that want a reusable proof-of-humanity primitive.
- Internal operators and developers validating model quality and deployment reliability.

## Non-Goals For Initial Delivery

- Government-ID verification or full KYC.
- Native mobile apps.
- Mainnet launch.
- Multi-chain portability.
- Advanced deepfake detection beyond the CPU-friendly MVP path.

## Success Criteria

- A user can complete a webcam challenge flow end to end from the browser.
- The verifier service can manage challenge state, stream progress, and return a deterministic outcome.
- The repo structure and docs are clean enough for multiple agents to work in parallel without interface drift.
- The chain integration phase can plug into the existing API and evidence contracts without redesigning the frontend or backend.
