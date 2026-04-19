# Frontend + Smart Contract Integration Progress

**Date:** April 19, 2026

## Summary

The source of truth for combined frontend, verifier, shared-contract, and smart-contract integration status now lives in the `codex/frontend-smart-contract-integration` branch.

The project now has:

- a more productized multi-route frontend with wallet-gated entry flow
- richer mock Sui/Walrus/Seal backend contracts and retained-evidence metadata
- a passing Move package MVP in the separate smart-contract worktree/branch

What is still not integrated end to end:

- the Move package is not yet ported into this canonical integration branch
- the backend `ProofMinter` is still mock-backed
- Walrus and Seal are still mock-backed
- frontend proof claiming, retrieval, and proof-surfacing flows are not wired yet

## Current Branch State

- `codex/frontend-smart-contract-integration` is the canonical integration branch and current source of truth.
- `codex/smart-contract-mvp` is a separate contract implementation branch in its own worktree at `/Users/skadi2910/projects/sui-liveness-detection-smart-contract`.
- The Move package is implemented and validated in that separate worktree, but it is not yet wired into the backend adapter or frontend proof flow in the canonical branch.

## What Is Implemented Now

### Frontend

- multi-route product shell with public routes, wallet-gated `/app`, live `/verify/[sessionId]`, and terminal `/result/[sessionId]`
- redesigned `/admin` QA console aligned with the same design system
- Sui wallet integration through the dApp Kit React bindings
- wallet-aware session launch flow and app dashboard session-restore behavior

### Verifier / Backend

- Phase 1 Sui/Walrus/Seal mock contract expansion is implemented
- verifier results now carry richer proof metadata including:
  - `transaction_digest`
  - `walrus_blob_id`
  - `walrus_blob_object_id`
  - `seal_identity`
  - `evidence_schema_version`
  - `model_hash`
- retained evidence assembly now includes richer audit context for future Seal/Walrus integration
- `finalize_session` now cleans up stored ciphertext references when storage succeeds but minting fails
- `blob_id` is still preserved as a backward-compatible alias while the stack migrates

### Shared Contracts

- `packages/shared` types and fixtures now mirror the richer proof result shape
- the shared `VerificationResult` contract includes the Phase 1 Sui/Walrus/Seal fields
- fixtures now reflect the richer mock proof metadata used by the backend

### Smart Contract / Move Package

The separate `codex/smart-contract-mvp` worktree now contains a passing Move package MVP under `contracts/move` with:

- `ProofOfHuman`
- `ProofRegistry`
- `VerifierCap`
- `verify_and_mint`
- `has_valid_proof`
- `renew`
- `revoke`
- `get_proof_details`
- `seal_approve_owner`

The Move package currently enforces:

- minimum confidence threshold checks
- duplicate active-proof rejection
- same-lineage renewal for MVP
- owner-only revoke
- owner-only Seal approval with `seal_identity` matching

## Recent Validation

The following validations are known to have happened and are the current confirmed checkpoints:

- `npm test` in `apps/web`
- `npm run build` in `apps/web`
- `python3 -m py_compile services/verifier/app/adapters/evidence_encryptor.py services/verifier/app/adapters/evidence_store.py services/verifier/app/adapters/proof_minter.py services/verifier/app/pipeline/types.py services/verifier/app/pipeline/evidence.py services/verifier/app/sessions/models.py services/verifier/app/sessions/service.py services/verifier/tests/test_session_flows.py`
- `PYTHONPATH=services/verifier services/verifier/.venv/bin/pytest services/verifier/tests/test_session_flows.py`
- `sui move build` in `/Users/skadi2910/projects/sui-liveness-detection-smart-contract/contracts/move`
- `sui move test` in `/Users/skadi2910/projects/sui-liveness-detection-smart-contract/contracts/move` with `8` passing tests

## What Is Still Missing

Integration blockers still remaining:

- backend `ProofMinter` is still mock-backed in the canonical branch
- Walrus and Seal adapters are still mock-backed in the canonical branch
- frontend proof claiming, owner retrieval, and decrypted evidence flows are not wired
- zkLogin is not wired
- the Move package from `codex/smart-contract-mvp` has not yet been ported into `codex/frontend-smart-contract-integration`
- publish/package metadata and deployment configuration for real Sui testnet usage are not yet set up in the canonical branch

## Next Integration Plan

1. Port the Move package from `codex/smart-contract-mvp` into the canonical `codex/frontend-smart-contract-integration` branch.
2. Align the backend adapter call shape with the on-chain entry points already defined by the Move package.
3. Add package publishing metadata and environment/config needed for real Sui testnet usage.
4. Implement a real Sui testnet `ProofMinter` behind the existing backend adapter seam.
5. Surface proof metadata in frontend result and app flows so wallet-connected users can see proof status and references.
6. Replace the mock Walrus and Seal adapters with real integrations after the on-chain adapter path is stable.

## Current Assumptions

- the source of truth is the `codex/frontend-smart-contract-integration` branch
- renewal remains same-lineage for the MVP
- retained evidence stays encrypted off-chain rather than moving biometric payloads on-chain
- `blob_id` remains a backward-compatible alias in backend and shared contracts for now
