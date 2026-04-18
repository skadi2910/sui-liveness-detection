# Agent Work Plan

## Goal

Enable multiple agents to build in parallel without conflicting write scopes or redefining interfaces.

## Track Ownership

### Agent 1: Frontend MVP

Owns:

- `apps/web`

Responsibilities:

- Next.js scaffold
- landing, verification, and result screens
- WebSocket client
- camera permission and basic media handling
- simple monospace visual system

Dependencies:

- `docs/03-frontend-spec.md`
- `docs/06-api-and-shared-types.md`

### Agent 2: Verifier Backend

Owns:

- `services/verifier`

Responsibilities:

- FastAPI bootstrap
- REST endpoints
- WebSocket session flow
- Redis session store
- placeholder or real pipeline wiring for anti-spoof and liveness logic

Dependencies:

- `docs/04-backend-spec.md`
- `docs/06-api-and-shared-types.md`

### Agent 3: Shared Contracts

Owns:

- `packages/shared`

Responsibilities:

- shared TypeScript types
- JSON schemas
- API fixtures
- contract test payloads

Dependencies:

- `docs/06-api-and-shared-types.md`

### Agent 4: Sui Contract And Adapters

Owns:

- `contracts/move`
- backend adapter interfaces touching chain integration

Responsibilities:

- Move package scaffold
- proof object design
- testnet mint adapter plan
- mock `ProofMinter` for early integration

Dependencies:

- `docs/05-sui-walrus-seal-spec.md`
- `docs/06-api-and-shared-types.md`

### Agent 5: Deployment And Ops

Owns:

- `infra`

Responsibilities:

- local Docker Compose
- Nginx reverse proxy
- VPS bootstrap notes
- environment templates

Dependencies:

- `docs/09-hosting-options.md`

## Coordination Rules

- No agent should invent a new payload shape outside `packages/shared`.
- Frontend and backend agents should integrate against the same session and result fixtures.
- Chain, Walrus, and Seal work must remain adapter-driven.
- Any file outside the owning area requires coordination before edit.

## Suggested Execution Order

1. Shared contracts
2. Frontend and backend in parallel
3. Infra bootstrap for local development
4. Sui contract and testnet mint adapter
5. Walrus, Seal, and zkLogin after the main verification path is stable

## Definition Of Done For This Phase

- every workstream has a clear ownership boundary
- shared contracts are treated as the interface source of truth
- no agent is blocked on ambiguous scope or missing folder structure
