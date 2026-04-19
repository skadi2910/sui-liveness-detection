# `apps/web`

This workspace will host the Next.js App Router frontend for the MVP demo.

Primary responsibilities:

- camera permission and webcam capture
- challenge UI states
- wallet and zkLogin entry points
- WebSocket integration with the verifier service
- success, failure, retry, and expiry views

Canonical product journey:

- start from `/app`
- connect wallet first
- launch into `/verify/[sessionId]` for the live challenge flow
- finalize and mint
- land on `/result/[sessionId]`
- return to `/app` for proof inspection and owner-side evidence decrypt

See [docs/03-frontend-spec.md](/Users/skadi2910/projects/sui-liveness-detection/docs/03-frontend-spec.md) for the implementation spec.

## Current Local Harness

The current app is a deliberately simple local verifier harness:

- opens the webcam
- creates verifier sessions against the FastAPI backend
- streams captured frames over WebSocket
- supports manual and auto-assisted challenge triggers
- surfaces verification result payloads and backend health

Environment variables:

- `NEXT_PUBLIC_VERIFIER_HTTP_URL` (optional; defaults to same-origin `/api`)
- `NEXT_PUBLIC_VERIFIER_WS_URL` (optional; defaults to same-origin `/ws`)
- `NEXT_PUBLIC_SUI_NETWORK` (optional; defaults to `testnet`)
- `NEXT_PUBLIC_SUI_RPC_URL` or `NEXT_PUBLIC_SUI_FULLNODE_URL` (optional fullnode override)
- `NEXT_PUBLIC_SUI_PACKAGE_ID` (required for owner-side proof lookup and Seal decrypt)
- `NEXT_PUBLIC_SEAL_SERVER_CONFIGS` (optional on testnet; JSON array of Seal key servers)
- `NEXT_PUBLIC_SEAL_THRESHOLD` (optional; defaults to `1`)
- `NEXT_PUBLIC_SEAL_VERIFY_KEY_SERVERS` (optional; defaults to `false`)
- `NEXT_PUBLIC_SEAL_SESSION_KEY_TTL_MINUTES` (optional; defaults to `10`)
- `NEXT_PUBLIC_WALRUS_AGGREGATOR_URL` (optional on testnet; defaults to the public testnet aggregator)
