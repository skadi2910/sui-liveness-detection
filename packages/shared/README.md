# `@sui-human/shared`

Shared TypeScript contracts for the Sui Human MVP.

This package is the source of truth for payload shapes used by:

- the Next.js frontend
- the FastAPI verifier service
- later contract/storage adapter integration layers

Contents:

- shared enum-like value sets
- request/response interfaces
- WebSocket event envelopes
- sample payload fixtures for contract tests

The interface source of truth is:

- [docs/06-api-and-shared-types.md](/Users/skadi2910/projects/sui-liveness-detection/docs/06-api-and-shared-types.md)

## Package Layout

```text
packages/shared/
  src/
    contracts.ts
    fixtures.ts
    index.ts
    values.ts
    websocket.ts
```

## Notes

- Contract values are exported as `as const` arrays plus string-literal types so they are easy to share with runtime validation later.
- Sample payloads are intentionally small and deterministic so frontend/backend tests can import the same examples.
