# `apps/web`

This workspace will host the Next.js App Router frontend for the MVP demo.

Primary responsibilities:

- camera permission and webcam capture
- challenge UI states
- wallet and zkLogin entry points
- WebSocket integration with the verifier service
- success, failure, retry, and expiry views

See [docs/03-frontend-spec.md](/Users/skadi2910/projects/sui-liveness-detection/docs/03-frontend-spec.md) for the implementation spec.

## Current Local Harness

The current app is a deliberately simple local verifier harness:

- opens the webcam
- creates verifier sessions against the FastAPI backend
- streams captured frames over WebSocket
- supports manual and auto-assisted challenge triggers
- surfaces verification result payloads and backend health

Environment variables:

- `NEXT_PUBLIC_VERIFIER_HTTP_URL`
- `NEXT_PUBLIC_VERIFIER_WS_URL`
