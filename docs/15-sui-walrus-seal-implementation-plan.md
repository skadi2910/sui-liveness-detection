# Sui / Walrus / Seal Implementation Plan

**Date:** April 18, 2026
**Based on:** [docs/05-sui-walrus-seal-spec.md](/Users/skadi2910/projects/sui-liveness-detection/docs/05-sui-walrus-seal-spec.md), [docs/04-backend-spec.md](/Users/skadi2910/projects/sui-liveness-detection/docs/04-backend-spec.md), and the current verifier codebase

## Goal

Implement the Sui-native proof object plus Walrus and Seal integration without breaking the existing frontend and verifier milestones.

The plan below keeps all chain, storage, and encryption work behind the existing adapter seams so we can move from mock to real infrastructure in controlled phases.

## Current Repo State

What already exists:

- mock adapter seams in:
  - `services/verifier/app/adapters/proof_minter.py`
  - `services/verifier/app/adapters/evidence_store.py`
  - `services/verifier/app/adapters/evidence_encryptor.py`
- end-to-end verifier flow already encrypts, stores, and mints during `finalize_session` in `services/verifier/app/sessions/service.py`
- shared result contracts already expose basic proof fields in `packages/shared/src/contracts.ts`
- retained evidence assembly already exists in `services/verifier/app/pipeline/evidence.py`

What is still missing:

- Move package contents under `contracts/move`
- richer proof, Walrus, and Seal result shapes
- real Sui testnet adapter
- real Seal encryption adapter
- real Walrus storage adapter
- owner retrieval and decryption flow in the frontend
- zkLogin support

## Planning Decisions To Lock Early

These decisions should be treated as implementation defaults unless a later product or legal review changes them.

### 1. Proof lineage

Use in-place renewal for the MVP.

- `renew` updates expiry and public audit metadata for the same logical proof
- downstream dapps can treat one proof object as the current source of truth
- versioned proof history can be added later if needed

### 2. Evidence retention

Seal encrypts the entire retained evidence package as one JSON blob.

- Walrus stores ciphertext only
- no raw video by default
- no reusable face embeddings or templates
- envelope encryption is a future optimization, not an MVP requirement

### 3. Backend contract shape

Adapters must return structured metadata, not single primitive values.

Required public fields across backend and shared contracts:

- `proof_id`
- `transaction_digest`
- `walrus_blob_id`
- `walrus_blob_object_id`
- `seal_identity`
- `evidence_schema_version`
- `expires_at`
- `confidence`
- `model_hash`
- `challenge_type`

### 4. Failure handling

If encryption or storage succeeds but minting fails, the backend must try to clean up stored ciphertext.

- delete the Walrus blob where possible
- if cleanup fails, log the orphaned reference for operator review
- do not return a successful proof result when minting failed

### 5. Decryption authority split

Owner access and dispute access remain separate policy surfaces.

- implement `seal_approve_owner` in the first contract wave
- keep `seal_approve_dispute` as a later entry point
- do not couple dispute access to the owner flow

## Execution Order

1. Expand shared and backend contracts to the final metadata shape.
2. Upgrade the mock adapters to behave like the final system.
3. Build the Move package and test its core rules locally.
4. Add a real Sui testnet `ProofMinter`.
5. Add a real Seal-backed `EvidenceEncryptor`.
6. Add a real Walrus-backed `EvidenceStore`.
7. Add frontend owner retrieval and decryption.
8. Add zkLogin after the primary wallet flow is stable.

This order keeps the frontend and verifier unblocked while the chain and privacy layers mature.

## Phase 1: Expand Contracts And Mock Behavior

### Objective

Make the current mock-backed implementation match the final Sui/Walrus/Seal data model before real infrastructure is introduced.

### Files To Change

- `services/verifier/app/adapters/proof_minter.py`
- `services/verifier/app/adapters/evidence_store.py`
- `services/verifier/app/adapters/evidence_encryptor.py`
- `services/verifier/app/sessions/service.py`
- `services/verifier/app/sessions/models.py`
- `services/verifier/app/pipeline/types.py`
- `services/verifier/app/pipeline/evidence.py`
- `packages/shared/src/contracts.ts`
- `packages/shared/src/fixtures.ts`
- verifier tests that assert result payloads

### Required Changes

#### 1. Expand `MintResult`

`MintResult` should carry:

- `proof_id`
- `transaction_digest`
- `expires_at`
- `walrus_blob_id`
- `walrus_blob_object_id`
- `seal_identity`
- `evidence_schema_version`
- public proof metadata map

The current `metadata` bag can remain, but the critical fields above should become first-class properties.

#### 2. Expand the evidence store return shape

Replace `put_encrypted_blob(...) -> str` with a structured result such as:

- `blob_id`
- `blob_object_id`
- optional provider metadata
- creation timestamp

This matches the spec requirement to preserve the Walrus blob object reference for later lifecycle management.

#### 3. Expand the encryptor return shape

Replace `encrypt_for_wallet(...) -> bytes` with a structured result such as:

- `encrypted_bytes`
- `seal_identity`
- optional encryption metadata
- optional policy version

The payload is still encrypted as one blob, but the caller now also receives the stable Seal identity that must be written on-chain.

#### 4. Expand `VerificationResult`

The result returned by the verifier should expose:

- `proof_id`
- `transaction_digest`
- `walrus_blob_id`
- `walrus_blob_object_id`
- `seal_identity`
- `evidence_schema_version`
- `expires_at`

This must be mirrored in both:

- `services/verifier/app/sessions/models.py`
- `packages/shared/src/contracts.ts`

#### 5. Enrich the retained evidence package

Update `services/verifier/app/pipeline/evidence.py` and `services/verifier/app/pipeline/types.py` so the retained evidence package includes:

- session identifiers and timestamps
- wallet-linked verification context
- challenge sequence or challenge summary
- frame hashes
- landmark snapshot or landmark trace summary
- human-face summary
- aggregate quality summary
- anti-spoof summary
- deepfake summary
- structured attack analysis
- model hashes
- final verdict context

Do not add raw video or reusable biometric templates.

#### 6. Add cleanup handling in `finalize_session`

`services/verifier/app/sessions/service.py` should:

- encrypt evidence
- store ciphertext
- mint proof
- delete the stored blob if minting fails after storage succeeded

### Deliverables

- final shared/backend contract shape stabilized before real integrations
- mocks produce realistic Sui/Walrus/Seal fields
- richer evidence package available for future Seal/Walrus use

### Acceptance Criteria

- existing `full` verification flow still completes locally
- result payloads include the new fields
- mock storage and encryption still work in tests
- mint failure after storage does not leave untracked blobs

## Phase 2: Build The Move Package MVP

### Objective

Create the first working Move package for the non-transferable proof object and policy entry points.

### Files To Create

- `contracts/move/Move.toml`
- `contracts/move/sources/proof_of_human.move`
- `contracts/move/tests/` test files as needed
- optional helper modules for policy or registry logic

### Required Contract Features

#### 1. `ProofOfHuman`

Create a `ProofOfHuman` object with `key` and without `store`.

Recommended stored fields:

- `id`
- `owner`
- `walrus_blob_id`
- `walrus_blob_object_id`
- `seal_identity`
- `evidence_schema_version`
- `model_hash`
- `confidence_bps`
- `issued_at_ms`
- `expires_at_ms`
- `challenge_type`

#### 2. `ProofRegistry`

Create a shared registry object to support:

- configuration
- minimum confidence threshold
- proof TTL or renewal rules
- owner-to-proof lookup
- uniqueness enforcement for unexpired proofs

#### 3. Required entry points

Implement:

- `verify_and_mint`
- `has_valid_proof`
- `renew`
- `revoke`
- `get_proof_details`
- `seal_approve_owner`

Keep `seal_approve_dispute` out of the critical path if needed, but preserve the contract surface plan for it.

#### 4. Soulbound behavior

Do not expose arbitrary transfer paths for `ProofOfHuman`.

### Deliverables

- compilable Move package
- local contract tests proving expiry, uniqueness, renewal, and owner access rules

### Acceptance Criteria

- unexpired-proof uniqueness is enforced
- renewal updates the same proof lineage for MVP
- owner-driven revoke works
- public detail helper does not leak biometric payloads
- owner approval path checks both proof ownership and matching `seal_identity`

## Phase 3: Add A Real Sui Testnet `ProofMinter`

### Objective

Replace the mock minter with a real testnet-backed adapter without changing the verifier API surface.

### Files To Change

- `services/verifier/app/adapters/proof_minter.py`
- `services/verifier/app/main.py`
- `services/verifier/app/core/config.py`
- environment templates and README files as needed

### Required Changes

- add a real adapter implementation alongside the mock
- wire package id, registry id, network, and signer config through settings
- map verifier results into `verify_and_mint`
- map renewal inputs into `renew`
- return on-chain object id and transaction digest

### Deliverables

- adapter toggle between mock and Sui testnet
- stable backend response shape regardless of adapter choice

### Acceptance Criteria

- successful `full` verification can mint on testnet through the backend
- configured minimum confidence is enforced by chain logic
- a wallet with an unexpired proof cannot mint a second active proof
- `has_valid_proof` is callable for downstream use

## Phase 4: Add A Real Seal `EvidenceEncryptor`

### Objective

Replace the mock wrapper encryptor with a Seal-backed implementation that produces a stable `seal_identity`.

### Files To Change

- `services/verifier/app/adapters/evidence_encryptor.py`
- `services/verifier/app/main.py`
- `services/verifier/app/core/config.py`

### Required Changes

- keep the input shape as whole-payload JSON bytes
- return ciphertext plus `seal_identity`
- preserve a policy abstraction that can later support dispute access

### Deliverables

- adapter toggle between mock and Seal-backed encryption
- no verifier API changes required after the swap

### Acceptance Criteria

- full evidence package is encrypted as one blob
- backend stores and forwards `seal_identity` to the proof minter
- owner decryption policy can be evaluated from proof metadata later

## Phase 5: Add A Real Walrus `EvidenceStore`

### Objective

Replace the in-memory store with Walrus-backed ciphertext storage.

### Files To Change

- `services/verifier/app/adapters/evidence_store.py`
- `services/verifier/app/main.py`
- `services/verifier/app/core/config.py`

### Required Changes

- upload ciphertext bytes only
- return durable `blob_id`
- preserve the Walrus blob object reference
- implement deletion where the provider supports it

### Deliverables

- adapter toggle between in-memory and Walrus storage
- lifecycle-aware storage metadata available to the backend

### Acceptance Criteria

- Walrus never receives plaintext evidence JSON
- backend returns both blob reference fields
- failed mint cleanup can request blob deletion

## Phase 6: Frontend Owner Retrieval And Decryption

### Objective

Add the owner retrieval flow without changing the backend verification session model.

### Files To Change

- `apps/web` pages, hooks, and wallet integration modules
- `packages/shared/src/contracts.ts` if retrieval payload helpers are added

### Required Flow

1. Read proof metadata from Sui.
2. Fetch encrypted blob from Walrus using the stored blob reference.
3. Authorize a short-lived Seal session key with the owner wallet.
4. Evaluate or dry-run `seal_approve_owner`.
5. Decrypt evidence locally in the frontend.

### Deliverables

- proof result UI can show the richer proof metadata
- owner retrieval flow works independently of session creation

### Acceptance Criteria

- a successful proof can be located and inspected by its owner
- decrypted payload stays local to the frontend
- no raw biometric data is returned from backend APIs just for owner retrieval

## Phase 7: zkLogin

### Objective

Add zkLogin as a frontend-plus-chain capability after the wallet extension flow is stable.

### Files To Change

- `apps/web`
- `contracts/move` only if chain-side support needs explicit wiring
- shared types only if wallet session metadata changes

### Requirements

- session creation still only needs a wallet address
- backend contracts remain agnostic to wallet origin
- proof minting path works for both extension wallets and zkLogin-derived addresses

### Acceptance Criteria

- no verifier session API changes are required to support zkLogin
- zkLogin users can mint and later retrieve the same proof type

## Testing Backlog

### Verifier Tests

Add or update tests for:

- richer result payload fields
- full evidence package assembly
- cleanup behavior when minting fails after storage succeeds
- mock adapter parity with the new contract shape

Suggested target files:

- `services/verifier/tests/test_session_flows.py`
- new adapter-specific tests if needed

### Shared Contract Tests

Add or update tests for:

- fixture compatibility with the richer result shape
- any JSON schema or serialization expectations in `packages/shared`

### Move Tests

Add tests for:

- initial mint success
- duplicate active proof rejection
- expiry behavior
- renewal behavior
- revoke behavior
- owner-only Seal approval
- mismatched `seal_identity` rejection

### End-To-End Milestone Tests

The chain definition of done from the spec should become the final integration gate:

- `verify_and_mint` works on testnet through the backend adapter
- proof expiry is enforced
- `has_valid_proof` is usable by downstream dapps
- owner decryption policy works end to end
- adapters can toggle from mock to real without frontend contract churn

## Suggested PR Breakdown

To keep the work reviewable, split implementation into these PRs:

1. Shared/backend contract expansion and mock parity
2. Move package MVP
3. Real Sui testnet proof minter
4. Real Seal encryptor
5. Real Walrus store
6. Frontend owner retrieval flow
7. zkLogin integration

## Open Questions

These do not block Phase 1, but they should be answered before or during the later phases.

- What exact Sui client and signer flow should the backend use for testnet transactions?
- Will the frontend retrieve Walrus blobs directly, or through a thin relay in some environments?
- What exact Seal SDK or service surface should back `seal_identity` generation?
- Should `get_proof_details` return only one current proof per owner, or both proof id and registry lookup metadata?
- What operator workflow should exist for orphaned ciphertext when delete fails?

## Recommended Immediate Next Step

Start with Phase 1 only.

That phase gives the repo a stable final metadata shape and realistic mock behavior, which de-risks every later Sui, Walrus, and Seal integration step.
