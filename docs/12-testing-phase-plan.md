# Testing Phase Plan

This document defines the next implementation phase for the verifier testing experience.

It is a direct follow-on from [11-liveness-anti-spoofing-review.md](/Users/skadi2910/projects/sui-liveness-detection/docs/11-liveness-anti-spoofing-review.md) and is intended to be agent-ready for implementation in a new chat.

## Goal

Upgrade the current single-step liveness test into a richer testing harness that:

1. runs a randomized multi-step challenge sequence instead of a single step
2. shows visual landmark and face-detection clues directly on the webcam feed
3. exposes clear stage-by-stage logs so testing behavior is easy to understand

This phase is for testing and protocol hardening, not for model retraining.

## Current State

The current stack already has:

- backend YOLOv8 face detection
- backend Silent-Face anti-spoofing
- browser-side MediaPipe Face Landmarker
- one randomized challenge per session from:
  - `blink_twice`
  - `turn_left`
  - `turn_right`
  - `open_mouth`
- browser telemetry and a simple event log in the testing harness

## Target Experience

### New challenge flow

Replace the current one-step session flow with a randomized sequence of 2 or 3 ordered steps.

Supported step pool after this phase:

- `blink_twice`
- `turn_left`
- `turn_right`
- `nod_head`
- `smile`

Explicitly remove `open_mouth` from the active testing sequence pool for this phase and replace it with `smile`.

### Sequence rules

Use these exact rules:

- sequence length is randomized server-side between `2` and `3`
- selection is unique within a sequence; no repeated step in the same session
- sequence order matters
- the user must complete steps in order
- a later step does not count early
- the backend owns the authoritative step order and completion state
- the frontend only renders and assists

Default randomization policy:

- 50% chance of a 2-step sequence
- 50% chance of a 3-step sequence

Step generation constraints:

- allow both `turn_left` and `turn_right` in the same sequence
- do not generate both `blink_twice` and `smile` as the only two steps in a 2-step sequence
  because that produces low head-motion entropy
- for 3-step sequences, require at least one head-motion step from:
  - `turn_left`
  - `turn_right`
  - `nod_head`

Example valid sequences:

- `blink_twice -> turn_right`
- `nod_head -> smile -> blink_twice`
- `turn_left -> blink_twice -> turn_right`

## Backend Changes

### Challenge model

Replace the single `challenge_type` session model with a sequence model.

Required session fields:

- `challenge_sequence: ChallengeType[]`
- `current_challenge_index: number`
- `completed_challenges: ChallengeType[]`
- `total_challenges: number`

Keep `challenge_type` in progress/result payloads only as a compatibility alias for the current active step during this phase.

Compatibility rule:

- `challenge_type` in `VerificationProgress` should equal `challenge_sequence[current_challenge_index]`
- once all steps are complete, `challenge_type` should remain the final completed step for terminal payload compatibility

### New challenge types

Extend the shared/backend `ChallengeType` enum with:

- `nod_head`
- `smile`

### Liveness evaluation behavior

Change the liveness evaluator from “evaluate one challenge over all frames” to “evaluate current sequence step over all frames, advance step when satisfied.”

Rules:

- evaluate only the current step at a time
- when a step passes, increment `current_challenge_index`
- clear per-step transient state that should not leak between steps
  especially blink closed/open tracking
- do not discard the full frame history; keep it for evidence and debugging
- but compute step completion from the frame window since the current step became active

Required per-step windows:

- store `step_started_frame_index`
- evaluate the current step only on frames with `frame_index >= step_started_frame_index`

### Step completion logic

Use these exact criteria for the new steps:

- `blink_twice`
  - keep the current stateful blink logic
  - requires 2 blink events in the current step window
- `turn_left`
  - keep current yaw-driven logic
- `turn_right`
  - keep current yaw-driven logic
- `nod_head`
  - add pitch-style or vertical nose-motion logic from MediaPipe landmarks
  - accept either:
    - a direct `pitch` metric if computed, or
    - a normalized vertical nose displacement ratio derived from landmarks
  - require a down-then-up or up-then-down motion pattern, not a single static pose
- `smile`
  - use a smile-related landmark ratio from mouth corners and lip geometry
  - if MediaPipe blendshapes are available in-browser later, they may be added, but this phase should not require them
  - backend accepts a smile based on landmark-derived metadata sent by the browser

### Progress and debug payloads

Extend `VerificationProgress` with:

- `challenge_sequence: ChallengeType[]`
- `current_challenge_index: number`
- `total_challenges: number`
- `completed_challenges: ChallengeType[]`
- `step_status: "pending" | "active" | "completed"`

Add optional `debug` payload to progress events:

- `debug.face_detection.detected`
- `debug.face_detection.confidence`
- `debug.face_detection.bounding_box`
- `debug.landmarks.face_detected`
- `debug.landmarks.point_count`
- `debug.landmarks.yaw`
- `debug.landmarks.pitch`
- `debug.landmarks.smile_ratio`
- `debug.landmarks.average_ear`
- `debug.liveness.current_step`
- `debug.liveness.step_progress`
- `debug.liveness.message`

Do not add a separate WebSocket event type for debug in this phase.
Keep debug attached to `progress` and `challenge_update`.

### Logs

Backend logs should clearly report:

- session created with selected challenge sequence
- step advanced
- step failed to match yet
- finalize requested
- anti-spoof verdict
- terminal result

Log structure should be compact key-value style, not huge raw frame dumps.

## Frontend Changes

### Webcam overlay

Add an overlay canvas on top of the video element.

Render these testing visuals:

- landmark points for the tracked face
- a face hull or reduced-face wireframe using selected landmark connections
- a face-center guide box for alignment
- backend face detection box when available from progress debug payload

Color rules:

- red: no face lock
- amber: landmarks available but backend face detection weak or challenge not satisfied
- green: face locked and current step actively trackable
- blue: current step completed

### Sequence UI

Replace the single challenge label with a sequence timeline:

- show all steps in order
- clearly mark:
  - completed
  - current
  - upcoming

Example UI line:

- `1. Blink twice`
- `2. Turn right`
- `3. Turn left`

### New browser-side metrics

Extend the MediaPipe processing path to compute:

- `pitch`
- `smile_ratio`

Keep existing:

- `yaw`
- `mouth_ratio`
- `average_ear`

Browser sends these metrics through the existing `landmarks` event and frame metadata path.

### Clear logs panel

Split the current generic event log into three sections:

- `Pipeline`
  - session created
  - current step
  - step completed
  - finalize
  - verified/failed
- `Detection`
  - backend face detector state
  - landmark engine state
  - point count
- `Signals`
  - EAR
  - yaw
  - pitch
  - smile ratio
  - anti-spoof score when available at terminal state

Rules:

- keep the newest 20 entries per section
- each entry should be human-readable first, JSON second
- preserve the raw JSON blocks below the summarized logs for debugging

## Shared Types And API

Update shared contracts in `packages/shared` and backend models together.

Required additions:

- `ChallengeType`:
  - add `nod_head`
  - add `smile`
- `VerificationProgress`:
  - add sequence fields described above
  - add optional `debug`
- `CreateSessionResponse`:
  - add `challenge_sequence`
  - add `total_challenges`
- `WsServerEvent` progress payload typing:
  - include the new sequence/debug fields

Do not remove existing fields during this phase.
Additive changes only.

## Testing Requirements

Implementation is not done until these are verified:

### Functional

- a 2-step sequence can complete successfully
- a 3-step sequence can complete successfully
- `blink_twice -> turn_right`
- `nod_head -> smile -> blink_twice`
- order enforcement works; completing step 2 before step 1 does not advance

### Overlay and debug

- landmarks render over the live face
- alignment guide renders even before full face lock
- backend face box appears when progress debug payload includes it
- log sections update while the session is running

### Regression

- `npm run build` in `apps/web`
- `python3 -m compileall services/verifier/app`
- `pytest tests/test_session_flows.py`
- existing spoof-fail terminal path still works

## Agent Work Split

Recommended split for the next chat:

### Agent 1: Backend sequence protocol

- session models
- challenge sequence selection
- progress payload changes
- liveness step advancement
- new `nod_head` and `smile` backend handling

### Agent 2: Frontend overlay and sequence UI

- webcam overlay canvas
- sequence timeline
- current-step rendering
- face box and landmark drawing

### Agent 3: Logging and verification

- structured browser log panels
- backend log cleanup
- tests for 2-step and 3-step flows
- regression verification

## Defaults Chosen

- this phase is for testing harness quality, not production UX polish
- sequence length randomization is `2` or `3` only
- `open_mouth` is replaced by `smile` in the active pool
- debug data remains visible in the testing harness
- backend remains authoritative for challenge sequence state
