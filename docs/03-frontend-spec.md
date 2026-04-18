# Frontend Spec

## Goal

Build a Next.js App Router frontend with two clear surfaces:

1. a client-facing product experience that feels like the real application
2. an internal admin / testing surface for verifier QA, calibration, and attack simulation

The client-facing surface should represent the actual product direction. The admin/testing surface should optimize for observability, repeatability, and fast debugging.

---

## Product Direction

The frontend should no longer be treated as a single testing harness page.

For the current MVP phase, the app should have **two pages / surfaces**:

### 1. Client-Facing Surface

This is the user-facing product page.

It should be a full experience, not just a utility screen:

- landing-page style hero
- product explanation and trust copy
- clear primary CTA to begin verification
- sections for how it works, privacy, benefits, and status
- entry point into the verification flow

This page should feel like the actual product shell we would show to a real user.

### 2. Admin / Testing Surface

This is the internal verifier console.

It should remain explicitly QA-oriented and expose:

- webcam and overlay diagnostics
- sequence progress and current challenge state
- quality, spot-check, motion continuity, and anti-spoof telemetry
- raw/debug logs
- calibration export and auto-save feedback
- controls for testing modes and attack labeling

This page is not primarily for end users. It is for engineering, threshold tuning, manual QA, and attack-matrix collection.

---

## Stack

- Next.js App Router
- TypeScript
- Tailwind CSS
- browser webcam APIs
- MediaPipe Face Landmarker or equivalent browser landmark helper
- shared contracts from `packages/shared`
- wallet integration later in the same app surface

Styling direction should now diverge by surface:

- client-facing page: product-quality, polished, full-page marketing / application shell
- admin/testing page: dense, operational, information-rich, clearly diagnostic

---

## Information Architecture

### Client-Facing Routes

- `/`
  - product landing page
  - overview of proof-of-human verification
  - CTA into the verification experience

- `/verify/[sessionId]`
  - user-facing verification flow
  - webcam preview
  - current instruction
  - progress and status
  - finalize and result transition

- `/result/[sessionId]`
  - verification result
  - success / failure / spoof / expired outcomes
  - retry guidance

### Admin / Testing Routes

- `/admin` or `/testing`
  - internal verifier console
  - current harness functionality lives here instead of being the primary public page

The exact route name can be chosen during implementation, but it should be explicit that this is an internal QA surface.

---

## Primary Screens

### Client-Facing Landing

- hero explaining the product and value
- primary CTA to start verification
- wallet-ready framing, even if wallet connection lands later
- trust and privacy copy
- short explanation of how verification works
- sections for:
  - what it does
  - why it matters
  - privacy / retention posture
  - supported flow

### Client-Facing Verification

- webcam preview
- framing guide
- current challenge instruction
- progress and state text
- concise helper copy
- connection / camera state
- clean finalize flow

### Client-Facing Processing

- clear staged processing state
- verification running
- optional storage / encryption / proof minting stages depending on backend readiness

### Client-Facing Result

- verified state with confidence, proof identifier, and expiry when available
- failed state with retry guidance
- spoof / expired / timeout states with clear reasons

### Admin / Testing Console

- live webcam overlay
- sequence timeline
- server checks panel
- tuning snapshot
- pipeline / detection / signals logs
- calibration export / save status
- attack labeling controls
- manual QA controls

---

## Testing Modes

The admin/testing page should support **separate QA modes** even though production verification remains a fused decision pipeline.

### Production Rule

The real verifier result still depends on both:

- liveness passing
- anti-spoof passing

Do not split the production backend into two separate products.

### QA Modes

The testing surface should support these modes:

#### Full Verification

Use the full fused pipeline:

- face detection
- quality gate
- landmark spot-check
- motion continuity
- active liveness sequence
- anti-spoof

This is the closest match to real product behavior.

#### Liveness-Only QA

Used to test:

- challenge sequence flow
- quality gate
- landmark spot-check
- motion continuity
- frontend guidance and timing

This mode should make it easy to debug challenge failures without anti-spoof noise dominating the result.

#### Anti-Spoof-Only QA

Used to test:

- passive anti-spoof behavior
- frame acceptance
- replay / print / virtual-camera behavior
- live anti-spoof preview and terminal anti-spoof scoring

This mode should let engineering test spoof samples without needing full randomized challenge completion.

### Why Split QA Modes

The split is specifically for testability and interpretability:

- a failed session becomes easier to diagnose
- liveness tuning can be tested independently
- spoof testing can be repeated without challenge friction
- exported rows become easier to label and interpret

---

## Required UX States

### Client-Facing States

- initial load
- camera permission denied
- no face detected
- face detected and waiting
- challenge active
- processing
- success
- failure
- spoof detected
- session expired
- disconnected / reconnecting

### Admin / Testing States

- all client-facing states, plus:
- quality blocked
- landmark spot-check blocked
- motion continuity blocked
- anti-spoof preview active
- calibration auto-save success / failure
- QA mode active

---

## App Structure

```text
apps/web/
  app/
    page.tsx
    verify/[sessionId]/page.tsx
    result/[sessionId]/page.tsx
    admin/page.tsx
  components/
    marketing/
      hero.tsx
      trust-section.tsx
      how-it-works.tsx
    verification/
      camera-preview.tsx
      challenge-panel.tsx
      status-banner.tsx
      result-summary.tsx
    admin/
      server-checks.tsx
      tuning-panel.tsx
      debug-logs.tsx
      calibration-panel.tsx
      qa-mode-switcher.tsx
  lib/
    api.ts
    ws-client.ts
    media.ts
    challenges.ts
    qa-modes.ts
```

The current harness implementation can remain the starting point for `admin/page.tsx`, while the user-facing routes should be organized separately for cleaner long-term product structure.

---

## Browser Flow

### Client-Facing Flow

1. User opens `/`.
2. User reads landing content and starts verification.
3. Frontend creates a session with `POST /api/sessions`.
4. Frontend navigates to `/verify/{sessionId}`.
5. Frontend opens `/ws/sessions/{sessionId}/stream`.
6. Frontend captures frames and streams verification data.
7. Frontend renders progress and guidance.
8. Frontend finalizes the session.
9. Frontend routes to `/result/{sessionId}`.

### Admin / Testing Flow

1. QA user opens `/admin` or `/testing`.
2. QA user selects mode:
   - full verification
   - liveness-only QA
   - anti-spoof-only QA
3. QA user starts a session.
4. Frontend streams frames and landmarks.
5. Frontend surfaces all backend gates and live diagnostics.
6. QA user finalizes or records the session outcome.
7. Frontend auto-saves/export rows for calibration / attack-matrix collection.

---

## Data Contract Requirements

- Consume shared types from `packages/shared`.
- Do not define one-off frontend-only session enums for backend-owned states.
- Treat backend event payloads as authoritative.
- QA mode selection may introduce frontend-side control state, but terminal backend verdicts must remain explicit about what the backend actually evaluated.

If QA modes require backend contract additions later, those should be added to shared contracts rather than patched ad hoc in the frontend.

---

## UI Constraints

### Client-Facing Surface

- must feel like a real product, not a developer dashboard
- should support full-page storytelling and clear hierarchy
- should be mobile-aware and desktop-strong
- should not expose raw debug telemetry by default

### Admin / Testing Surface

- must prioritize scanability and diagnostics
- should expose verbose backend state without hiding critical details
- can be denser and less marketing-oriented
- should clearly distinguish QA controls from real user actions

---

## Frontend Definition Of Done

- The app has two clear surfaces:
  - a client-facing product flow
  - an internal admin/testing console
- The current harness is moved or structured as the admin/testing surface rather than being the default public product page.
- Session creation and WebSocket updates work in both the client-facing flow and the admin/testing flow where appropriate.
- The admin/testing surface supports separate QA modes:
  - full verification
  - liveness-only QA
  - anti-spoof-only QA
- The client-facing flow remains simpler and product-oriented, without exposing the full diagnostic surface.
- Result screens can render real verification outcomes cleanly without relying on the testing console.
