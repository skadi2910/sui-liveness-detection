# `contracts/move`

This workspace will host the Sui Move package for the `ProofOfHuman` soulbound proof object.

Primary responsibilities:

- minting a non-transferable proof object
- enforcing expiry and renewal rules
- supporting owner revocation
- exposing verification and audit query helpers
- storing Walrus blob references and model integrity metadata

See [docs/05-sui-walrus-seal-spec.md](/Users/skadi2910/projects/sui-liveness-detection/docs/05-sui-walrus-seal-spec.md) for the contract and integration spec.
