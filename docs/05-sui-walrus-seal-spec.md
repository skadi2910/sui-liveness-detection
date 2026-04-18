# Sui, Walrus, And Seal Spec

## Goal

Define the Sui-native proof object and the storage/privacy integration path without blocking the first frontend and backend milestones.

## Sui Contract Model

Use a `ProofOfHuman` object with `key` but not `store` so the proof is owned yet not publicly transferable.

Important boundary:

- omitting `store` helps keep transfer control inside the package
- it does not make proof contents private
- all retained biometric or biometric-derived evidence must stay off-chain and encrypted before Walrus storage

Illustrative struct:

```move
public struct ProofOfHuman has key {
    id: UID,
    owner: address,
    walrus_blob_id: vector<u8>,
    walrus_blob_object_id: ID,
    seal_identity: vector<u8>,
    evidence_schema_version: u16,
    model_hash: vector<u8>,
    confidence_bps: u64,
    issued_at_ms: u64,
    expires_at_ms: u64,
    challenge_type: vector<u8>,
}
```

Recommended supporting objects:

- `ProofRegistry` shared object for configuration, uniqueness checks, and owner-to-proof lookup
- optional `VerifierCap` or equivalent package-controlled authority for mint paths

## Evidence Design

Seal should encrypt the retained evidence package, not just the final verdict fields.

Recommended retained evidence classes:

- `Class A`: public proof metadata on Sui
- `Class B`: encrypted audit evidence on Walrus
- `Class C`: raw or near-raw biometric artifacts only if explicitly approved later

### What Gets Encrypted In The MVP

Seal should encrypt the full retained evidence JSON payload produced after verification success.

That payload should include:

- session identifiers and timestamps
- wallet-linked verification context
- challenge sequence or challenge summary
- frame hashes
- landmark snapshot or landmark trace summary
- human-face summary
- per-frame or aggregate quality and anti-spoof summaries
- deepfake summary
- structured attack analysis
- model hashes
- final verdict context

This is intentionally more than the final verdict alone.

### What Does Not Go Into The Encrypted Payload By Default

- on-chain proof metadata
- Redis session state
- raw video stored in plaintext
- face embeddings or reusable biometric templates

### Optional Future Evidence Tiers

- `minimal`: summary evidence only
- `dispute_ready`: summary evidence plus landmark traces and per-frame diagnostics
- `high_assurance`: summary evidence plus selected face crops or short challenge clips

Full raw video should not be the default retention model.

## Required Entry Points

### `verify_and_mint`

- mints a new proof after verifier success
- rejects confidence below the configured threshold
- rejects minting when an unexpired proof already exists for the owner
- stores Walrus and Seal references for the encrypted evidence package

### `has_valid_proof`

- returns whether a wallet currently has an unexpired proof

### `renew`

- extends a proof after a new successful verification
- keeps the same proof lineage unless the implementation later chooses versioning

### `revoke`

- owner-driven burn path
- intended to support user deletion and consent withdrawal flows

### `get_proof_details`

- returns public audit metadata
- must not expose raw biometric material

### `seal_approve_owner`

- allows the proof owner to decrypt their own encrypted evidence package
- checks that the caller is the owner of the referenced proof
- checks that the requested Seal identity matches the proof record

### `seal_approve_dispute`

- optional later path for governed dispute access
- should be separate from the owner path
- should not require changing the backend encryption API surface

## Integration Order

1. Implement `ProofMinter` as a mock.
2. Replace mock with real Sui testnet minting.
3. Add Seal adapter for full evidence-package encryption.
4. Add Walrus adapter for ciphertext blob storage.
5. Add zkLogin for users without a traditional wallet.

## End-To-End Flow

### Verification And Storage Flow

1. The verifier completes liveness and anti-spoof evaluation.
2. The verifier assembles the retained evidence package as JSON.
3. `EvidenceEncryptor` Seal-encrypts the full evidence payload into opaque bytes.
4. `EvidenceStore` uploads those encrypted bytes to Walrus.
5. Walrus returns durable storage references such as `blob_id` and the blob object identifier.
6. `ProofMinter` calls `verify_and_mint` on Sui with:
   - wallet owner
   - Walrus references
   - Seal identity
   - schema version
   - public proof metadata such as confidence, model hash, challenge type, and expiry
7. The frontend receives the proof id, transaction digest, and blob reference fields from the backend result.

Current verifier note:

- the backend public API remains session-oriented even though verification internally uses multiple model heads
- face detection, quality gating, human-face scoring, anti-spoofing, and deepfake scoring remain backend concerns and should not leak as separate public minting APIs

### Owner Retrieval And Decryption Flow

1. The frontend reads proof metadata from Sui.
2. The frontend fetches the encrypted blob from Walrus using the stored blob reference.
3. The owner wallet authorizes a short-lived Seal session key.
4. The frontend submits or dry-runs the package policy function such as `seal_approve_owner`.
5. If approved, Seal key servers return the derived material needed for decryption.
6. The frontend decrypts the evidence locally.

This keeps Walrus public-storage friendly while leaving access control to Seal policy.

## Walrus Requirements

- store encrypted evidence payloads, not plaintext media
- accept the full ciphertext for the retained evidence package
- return a durable `blob_id`
- return or preserve the Walrus blob object reference needed for lifecycle management
- support deletion workflows where applicable
- keep storage interaction behind `EvidenceStore`

Walrus is the ciphertext storage layer, not the privacy layer.

## Seal Requirements

- encrypt the full retained evidence package, not only verdict fields
- support owner-controlled decryption through on-chain policy
- allow a later dispute-policy flow without changing the backend API surface
- generate or accept a stable `seal_identity` for the evidence item
- stay behind `EvidenceEncryptor`

Seal is the policy and decryption-control layer, not the durable storage layer.

## Encryption Shape

Initial design choice:

- serialize the retained evidence package to JSON bytes
- Seal-encrypt the whole payload as one blob
- upload the ciphertext blob to Walrus

Envelope encryption can be introduced later if the retained evidence package becomes large, such as when storing clips or selected face crops.

## zkLogin Requirements

- treated as a frontend-plus-chain capability, not a blocker for initial verifier work
- wallet address produced through zkLogin must still fit the same backend contracts
- session creation must not care whether the wallet comes from a browser extension or zkLogin

## Chain Definition Of Done

- `verify_and_mint` works on testnet through the backend adapter
- proof expiry is enforced
- `has_valid_proof` can be used by downstream dapps
- owner decryption policy works end to end for encrypted evidence retrieval
- storage and encryption adapters can be toggled from mock to real implementations without changing the frontend contracts
