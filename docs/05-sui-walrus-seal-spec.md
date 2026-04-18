# Sui, Walrus, And Seal Spec

## Goal

Define the Sui-native proof object and the storage/privacy integration path without blocking the first frontend and backend milestones.

## Sui Contract Model

Use a `ProofOfHuman` object with `key` but not `store` so the proof is owned yet not publicly transferable.

Illustrative struct:

```move
public struct ProofOfHuman has key {
    id: UID,
    owner: address,
    walrus_blob_id: vector<u8>,
    model_hash: vector<u8>,
    confidence_bps: u64,
    issued_at_ms: u64,
    expires_at_ms: u64,
    challenge_type: vector<u8>,
}
```

## Required Entry Points

### `verify_and_mint`

- mints a new proof after verifier success
- rejects confidence below the configured threshold
- rejects minting when an unexpired proof already exists for the owner

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

## Integration Order

1. Implement `ProofMinter` as a mock.
2. Replace mock with real Sui testnet minting.
3. Add Walrus adapter for encrypted evidence blob storage.
4. Add Seal adapter for wallet-scoped encryption.
5. Add zkLogin for users without a traditional wallet.

## Walrus Requirements

- store encrypted evidence payloads, not plaintext media
- return a durable `blob_id`
- support deletion workflows where applicable
- keep storage interaction behind `EvidenceStore`

## Seal Requirements

- encrypt evidence against the user wallet identity
- allow a later dispute-policy flow without changing the backend API surface
- stay behind `EvidenceEncryptor`

## zkLogin Requirements

- treated as a frontend-plus-chain capability, not a blocker for initial verifier work
- wallet address produced through zkLogin must still fit the same backend contracts
- session creation must not care whether the wallet comes from a browser extension or zkLogin

## Chain Definition Of Done

- `verify_and_mint` works on testnet through the backend adapter
- proof expiry is enforced
- `has_valid_proof` can be used by downstream dapps
- storage and encryption adapters can be toggled from mock to real implementations without changing the frontend contracts
