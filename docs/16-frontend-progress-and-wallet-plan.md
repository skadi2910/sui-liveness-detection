# Frontend Progress And Wallet Login

Latest combined frontend + smart-contract integration status now lives in [17-frontend-smart-contract-integration-progress.md](/Users/skadi2910/projects/sui-liveness-detection/docs/17-frontend-smart-contract-integration-progress.md). This file remains a historical frontend checkpoint.

**Date:** April 19, 2026

## Summary

The frontend has moved out of the single-page harness phase and into a multi-route product shell.

We now have:

- a public landing page
- dedicated `overview`, `about`, and `app` routes
- a live verification route
- a result route
- a redesigned admin QA console that matches the same design system
- a wallet-gated app entry flow using the Sui dApp Kit React bindings

## Current Route Responsibilities

### Public Routes

- `/`
  - landing page and primary entry surface
- `/overview`
  - protocol and product explanation
- `/about`
  - mission, trust, and team-style editorial surface
- `/app`
  - wallet-gated client dashboard
  - restores last local session and decides whether to resume verification or hand off to result
- `/verify/[sessionId]`
  - active live verification flow
  - webcam, challenge guidance, progress, finalize
- `/result/[sessionId]`
  - terminal session outcome
  - verified, failed, spoof-oriented, expired

### Internal Route

- `/admin`
  - full QA console
  - diagnostics, attack simulation, calibration export, logs, and tuning visibility

## What Has Been Implemented

### Design System And Layout

- Tailwind-based app styling is now the primary UI system in `apps/web`
- light and dark themes are supported through semantic tokens
- the public routes share one shell language instead of mixing unrelated layouts
- the admin route now uses the same shell family as the public app instead of the previous isolated harness look

### New Frontend Structure

- shared page chrome for product routes
- shared app shell and left rail for terminal-like app surfaces
- modular page components for:
  - landing
  - overview
  - about
  - app dashboard
  - verify
  - result

### Verification Flow Improvements

- shared verifier-core extraction from admin work
- public verification flow remains separated from QA-only admin logic
- `/verify/[sessionId]` continues to be the focused live capture route
- `/result/[sessionId]` is server-safe and no longer trips the client/server formatter boundary

### App Dashboard Behavior

`/app` is no longer just a visual mock.

It now:

- restores the last saved local session id from browser storage
- fetches the saved session from the verifier backend
- decides whether the user should:
  - resume `/verify/[sessionId]`
  - move to `/result/[sessionId]`
  - stay in `/app` and restart because the session expired
- shares the same browser-side session creation path as the public start CTA

### Wallet Login

Wallet login is now active in the client-facing flow.

Implemented:

- Sui wallet provider integration through `@mysten/dapp-kit-react`
- client-side Sui RPC/network configuration with testnet as the default network
- shared wallet state hook for connected account, network, and disconnect actions
- wallet connect controls in the shared site header
- `/app` now requires a connected wallet before creating a fresh verification session
- public session creation now uses the connected wallet address instead of the demo placeholder
- landing CTA now routes disconnected users into `/app` instead of silently creating demo-wallet sessions

Current behavior:

- existing saved sessions can still be restored from `/app`
- a connected wallet is required only for starting a new session
- `/verify/[sessionId]` remains the focused live-capture route and does not own wallet connection UX

### Admin Redesign

The admin surface was redesigned without removing its QA functionality.

Preserved:

- live webcam overlay
- session controls
- QA mode selector
- fixed sequence controls
- spoof toggles
- server checks
- tuning snapshot
- calibration export
- logs

Changed:

- shell/layout now matches the current frontend design setup
- camera and controls are treated as the primary workspace
- diagnostics panels moved into a cleaner sidebar/content arrangement

## Key Files Added Or Updated

### New Public Route Pages

- `apps/web/app/overview/page.tsx`
- `apps/web/app/about/page.tsx`
- `apps/web/app/app/page.tsx`

### Shared Chrome And Page Modules

- `apps/web/components/chrome/app-shell.tsx`
- `apps/web/components/chrome/app-sidebar.tsx`
- `apps/web/components/chrome/console-panel.tsx`
- `apps/web/components/pages/overview-page.tsx`
- `apps/web/components/pages/about-page.tsx`
- `apps/web/components/pages/main-app-page.tsx`

### Session Routing And Restore Logic

- `apps/web/features/verifier-core/lib/app-session.ts`
- `apps/web/features/verifier-core/hooks/use-app-session.ts`
- `apps/web/components/verification/launch-verification-button.tsx`
- `apps/web/features/verifier-core/hooks/use-client-verification-flow.ts`

### Wallet Integration

- `apps/web/components/wallet/sui-wallet-provider.tsx`
- `apps/web/components/wallet/wallet-button.tsx`
- `apps/web/components/wallet/wallet-button-slot.tsx`
- `apps/web/components/wallet/wallet-summary-card.tsx`
- `apps/web/features/wallet/hooks/use-sui-wallet.ts`
- `apps/web/features/wallet/lib/config.ts`
- `apps/web/.env.example`

### Admin Redesign

- `apps/web/app/admin/page.tsx`
- `apps/web/app/admin/_components/panels.tsx`
- `apps/web/app/globals.css`

## Validation Completed

Validated during this frontend phase:

- `npm test` in `apps/web`
- `npm run build` in `apps/web`

Current web test count:

- `22` passing tests

Covered areas now include:

- client verification state mapping
- result outcome mapping
- verifier base URL resolution
- admin camera harness helpers
- app dashboard route-target derivation
- app dashboard session description logic
- wallet network / RPC config resolution
- wallet-aware entry helper coverage

Additional runtime validation completed:

- `GET /app` against the local dev server on `http://localhost:3000`
- `GET /about` and static route generation in the production build after wallet UI integration

## Current Constraints

- the wallet connection layer is client-side only, so the connect control is intentionally hydrated behind a browser-only boundary
- session restore is still based on the last local session id, not yet a wallet-keyed session registry
- `/result/[sessionId]` still handles result viewing independently of wallet proof claiming
- live browser validation from this environment can still require escalated localhost access, so build/test remains the most reliable automated gate

## Recommended Next Phase

Use the new connected-wallet state inside `/app` to implement proof claiming, wallet-bound result handoff, and any contract or SBT surfacing without moving wallet concerns into the live `/verify/[sessionId]` route.
