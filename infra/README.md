# `infra`

This workspace will hold local and VPS deployment assets.

Planned contents:

- local Docker Compose stack
- Nginx reverse proxy config
- VPS bootstrap notes
- environment templates
- future CI and deployment manifests

See [docs/09-hosting-options.md](/Users/skadi2910/projects/sui-liveness-detection/docs/09-hosting-options.md) for the hosting strategy.

## Local MVP Run Path

Current local options:

1. Docker Compose from the repo root:
   - `docker compose up --build`
2. Split local development:
   - backend: `cd services/verifier && python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt && uvicorn app.main:app --reload`
   - frontend: `cd apps/web && npm install && npm run dev`

The current stack is intended for webcam flow testing and backend integration testing, not production deployment.
