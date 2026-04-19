# Progress Log

Latest combined frontend + smart-contract integration status now lives in [17-frontend-smart-contract-integration-progress.md](/Users/skadi2910/projects/sui-liveness-detection/docs/17-frontend-smart-contract-integration-progress.md). This file remains a historical verifier/harness checkpoint.

## Current Status

The repository now has a documented MVP structure plus a runnable local verifier/testing harness with a sequence-based liveness flow, live overlay diagnostics, modularized frontend/backend code, and QA-oriented calibration tooling.

For the latest frontend route/status checkpoint and wallet-login implementation status, see:

- `docs/16-frontend-progress-and-wallet-plan.md`

Validated on April 18, 2026:

- `docker compose config`
- `python3 -m compileall services/verifier/app`
- `python3 -m compileall services/verifier/tests services/verifier/scripts/analyze_calibration_samples.py`
- `npm install` in `apps/web`
- `npm run build` in `apps/web`
- live health check against `GET /api/health`
- live REST + WebSocket smoke test ending in a `verified` terminal event
- live landmark-aware REST + WebSocket smoke test ending in a `verified` terminal event
- `PYTHONPATH=services/verifier services/verifier/.venv/bin/pytest services/verifier/tests/test_session_flows.py services/verifier/tests/test_logging.py`
- `PYTHONPATH=services/verifier services/verifier/.venv/bin/pytest services/verifier/tests/test_session_flows.py services/verifier/tests/test_face_quality.py services/verifier/tests/test_calibration_analysis.py`
- `PYTHONPATH=services/verifier services/verifier/.venv/bin/pytest services/verifier/tests/test_session_flows.py services/verifier/tests/test_liveness_motion_continuity.py`
- `PYTHONPATH=services/verifier services/verifier/.venv/bin/pytest services/verifier/tests/test_session_flows.py`
- real YOLOv8 face model download and SHA-256 verification
- official Silent-Face weights copied locally and exported to ONNX
- real-model sample validation against upstream Silent-Face sample images
- real CLIP human-face model load validation (`openai/clip-vit-base-patch32`)
- browser manual flow validation for mirrored preview, session start, multi-step progress, successful finalize, and tuned blink/nod responsiveness

## What Is Implemented

### Documentation

- core product, architecture, backend, frontend, test, and hosting spec pack
- this progress log as the current implementation checkpoint

### Shared Contracts

- TypeScript package under `packages/shared`
- shared enums, REST payloads, WebSocket event types, and sample fixtures

### Backend

- FastAPI application scaffold
- Redis-ready session store with in-memory fallback
- REST endpoints for health and session lifecycle
- WebSocket verification endpoint
- landmark-aware liveness pipeline with configurable thresholds
- heuristic face quality gate before liveness and anti-spoof frame acceptance
- motion continuity check inside the liveness gate when sufficient landmark positions are available
- server-side landmark spot-check that cross-checks landmark-implied face position against the detected face box
- human-face gate using a CLIP zero-shot classifier on the detected face crop, enforced by default in the current hackathon/demo build
- stateful blink counting across frames
- metadata fallback path when landmarks are absent
- server-authored randomized 2- or 3-step challenge sequences
- supported sequence steps: `blink_twice`, `turn_left`, `turn_right`, `nod_head`, `smile`
- ordered sequence enforcement with per-step frame windows and completion tracking
- compact debug payloads attached to progress events
- per-frame cached server debug annotations for face detection and quality decisions
- health payload exposes face quality tuning thresholds
- health payload also exposes motion continuity tuning thresholds
- health payload also exposes the landmark spot-check mismatch threshold
- health payload now also exposes human-face model readiness, runtime, threshold, and enforcement mode
- health payload now also exposes the current proof-mint minimum confidence threshold used by the local/demo adapter
- tuned blink / nod thresholds and lower step-frame floor for more natural challenge completion during browser QA
- backend session/service logic refactored into smaller session modules with clearer responsibilities
- configurable hold-window pacing for step completion
- automatic superseding of older active sessions when the same wallet starts a new test session
- real YOLOv8 face detection model loaded from disk
- real Silent-Face ONNX anti-spoof ensemble loaded from disk
- real CLIP human-face classifier loaded from Hugging Face
- mock evidence encryptor, store, and proof minter
- Dockerfile for local containerized backend runs
- lightweight backend tests around session lifecycle and terminal events
- calibration analyzer script for project-native threshold tuning

### Frontend

- Next.js App Router scaffold under `apps/web`
- client-facing landing page at `/`
- internal verifier / QA console at `/admin`
- webcam-based local verifier harness moved into the admin surface
- admin console refactored into reusable hooks, panel components, and shared admin utilities instead of a monolithic page implementation
- session creation against the backend
- WebSocket-driven progress and result rendering
- manual and auto-assisted challenge triggers for testing
- QA mode selector with backend finalize modes:
  - `full`
  - `liveness_only`
  - `antispoof_only`
  - `deepfake_only`
- fixed-sequence admin test mode for repeatable manual QA, with configurable 1-, 2-, or 3-step challenge order
- browser-side TensorFlow.js face landmarks integration with Turbopack-safe shims around the face-detection runtime
- landmark telemetry streaming to the verifier
- on-screen landmark readiness and signal metrics for manual testing
- mirrored webcam preview so left/right actions match user expectation
- live webcam overlay with guide box, landmark wireframe, and backend face box
- sequence timeline showing completed, current, and upcoming steps
- browser-side `pitch` and `smile_ratio` metrics for nod/smile testing
- faster browser-to-backend frame shipping for challenge responsiveness
- split `Pipeline`, `Detection`, and `Signals` logs with collapsed raw JSON detail
- dedicated `Server Checks` panel for live backend gate visibility during manual QA
- terminal result display with structured attack analysis:
  - failure category
  - suspected attack family
  - presentation-attack metrics
  - deepfake metrics
  - attack note
- live `Server Checks` now also surfaces the human-face gate state, score, and note
- tuning snapshot panel showing browser assist defaults and backend liveness thresholds
- slower end-of-sequence pacing with delayed auto-finalize for better QA UX
- calibration-row export from completed sessions for NDJSON-based threshold tuning
- completed exports now include the verification evaluation mode used for the session
- completed exports now include structured attack analysis from the terminal verifier result
- Dockerfile for local containerized frontend runs

### Local Run Path

- root `docker-compose.yml` for `redis`, `verifier`, and `web`
- template calibration dataset under `services/verifier/sample-data/calibration/`

## What Is Not Implemented Yet

- Walrus integration
- Seal integration
- Sui contract adapter beyond mock minting
- zkLogin
- production auth, observability, and deployment hardening

## Important Current Constraint

The backend is runnable today with real face detection, real anti-spoofing, and landmark-aware liveness. The current admin harness is suitable for local flow validation, payload validation, attack-matrix collection, and real model integration testing, while `/` now serves as the client-facing product shell.

The testing-harness phase described in `12-testing-phase-plan.md` is now effectively complete: multi-step sequences, overlay diagnostics, structured logs, shared-contract updates, and terminal verification flows are all implemented. Current work has moved from harness construction into verifier hardening.

The current health response may still show `degraded` for Redis when Redis is not running locally, but the model layer should now report ready when the verifier starts with the checked-in `.env`.

Wallet cooldown after terminal sessions has been removed to support heavy repeated testing, and repeated `Start session` actions now supersede any older active session for the same wallet instead of returning a blocking `409`.

The one milestone that is still only partially complete is project-native threshold tuning: the repo now has the collection/analyzer workflow, but actual real webcam sample capture still requires a human to perform and label sessions. This is calibration work for the pretrained stack, not model retraining.

The verifier now also has a model-backed human-face gate, and the current hackathon/demo build enforces it by default in `full`, `antispoof_only`, and `deepfake_only` modes.

The current hackathon/demo build also enforces the deepfake head by default so the demo showcases the full multi-model verifier stack. A more production-cautious enforcement posture can still be restored later after broader benchmarking.

## Real Model Notes

- YOLOv8 face detection is using `yolov8n-face-lindevs.onnx`.
- Silent-Face is using the official upstream `.pth` weights exported locally to ONNX.
- The anti-spoof runtime had to be aligned with upstream preprocessing: Silent-Face expects float tensors in the `0..255` value range, not normalized `0..1`.
- Browser-side landmarks are now produced by TensorFlow.js face landmarks and sent to the backend over the existing WebSocket flow.
- The backend now also runs a CLIP-based human-face scorer on the detected face crop and exposes it in live debug, health, admin evaluation endpoints, and terminal result exports.
- The current hackathon/demo build now enforces both the human-face gate and the deepfake head by default, while still exposing their scores and notes in terminal/admin results.
- Backend liveness now consumes landmark-derived EAR, MAR, and yaw-style signals, while preserving metadata overrides for synthetic or manual testing.
- The testing harness now uses backend-authored multi-step sequences instead of a single randomized challenge.
- `open_mouth` has been removed from the active testing sequence pool for this phase and replaced with `smile`.
- Current liveness tuning values are exposed through `GET /api/health` to support browser-based QA and threshold calibration.
- Current face quality tuning values are also exposed through `GET /api/health`, and the verifier now gates liveness/anti-spoof frame usage on those checks.
- The current MVP strategy is pretrained-model-first; local sample capture exists to justify thresholds on project-native devices and conditions.
- The browser harness can now export completed sessions as NDJSON calibration rows, reducing manual bookkeeping during QA.
- The browser harness now has a live `Server Checks` panel so manual QA can see the backend face gate, quality gate, liveness step state, anti-spoof scores, and terminal failure reason without inspecting raw JSON.
- The `Server Checks` panel now also shows human-face telemetry.
- The frontend is now split into a client-facing landing page and a separate admin/testing console.
- The admin console now supports four finalize modes for QA:
  - `full`: fused verifier path
  - `liveness_only`: challenge / gate debugging without anti-spoof verdict blocking the result
  - `antispoof_only`: spoof testing without full challenge completion blocking the result
  - `deepfake_only`: deepfake-head QA without liveness or Silent-Face verdict blocking the result
- Only `full` mode is eligible for proof minting; QA-only modes are test surfaces, not production proof flows.
- The admin console can now run fixed challenge sequences for repeatable testing instead of relying only on randomized friendly sequences.
- Failed terminal results now carry structured attack-family semantics such as `presentation_attack`, `deepfake_attack`, or `combined_attack_signals` instead of exposing only a raw failure reason.
- Terminal verifier confidence is now peak-aware, so strong spoof/deepfake peaks cap the exported human-confidence score on failed attack sessions.
- Proof minting now uses an explicit configurable minimum confidence threshold instead of a hidden hardcoded cutoff, which keeps clean hackathon-demo `full` sessions from failing unexpectedly after the verifier already passed them.
- The backend now blocks replay-like step windows that are too static across consecutive landmark anchor positions, reducing the chance that a still or near-still clip can satisfy a challenge step.
- The backend now excludes frames whose browser landmark telemetry does not spatially line up with the detected face crop, reducing trust in tampered landmark streams.
- The browser landmark runtime had to be swapped away from `@mediapipe/tasks-vision` because the local in-app browser repeatedly crashed inside the Tasks runtime; TensorFlow.js now provides the browser landmark layer more reliably in this environment.
- Manual QA tuning now favors natural single blinks and normal down-and-up nods instead of requiring exaggerated repeated motion.
- On the upstream sample set, the current real pipeline now behaves as expected:
  - `image_F1.jpg`: fake, failed
  - `image_F2.jpg`: fake, failed
  - `image_T1.jpg`: real, passed
- On the live local stack, a landmark-aware smoke test against the restarted verifier completed with a terminal `verified` event.

## Recommended Next Steps Status

1. Install local dependencies and boot the verifier plus harness: completed.
2. Validate the webcam flow end to end: completed for local boot/build, landmark-aware live API smoke, and manual browser verification of the multi-step harness.
3. Replace mock liveness with real browser landmark analysis: completed.
4. Add lightweight backend tests around session flows and terminal events: completed and expanded for sequence progression, health tuning visibility, hold-window pacing, and session restart behavior.
5. Implement face-quality pre-filtering and surface server-side QA diagnostics in the harness: completed.
6. Refactor the admin harness and verifier session orchestration into smaller reusable modules: completed.
7. Replace the brittle browser landmark runtime and retune quick challenge actions for manual QA: completed.
8. Capture a few real webcam samples and tune thresholds using project-native data: partially completed.
   - completed: sample collection format, calibration folder, analyzer script, and live server-side quality visibility
   - completed in this session: first-pass blink / nod threshold tuning and faster frame capture cadence for manual QA
   - pending: broader human-recorded sample collection and threshold tuning pass across devices and lighting conditions
9. Add human-face gate and validate the real model path: completed.
   - completed: backend pipeline wiring, health/debug/result exposure, admin panel visibility, export support, real CLIP model load, and strict-demo enforcement defaults
   - pending: broader non-human benchmark pass before deciding whether production defaults should remain this strict
10. Promote deepfake from telemetry-first prototype to strict-demo enforcement in the hackathon build: completed.
   - completed: finalize-time ONNX scoring, result/health exposure, strict-demo enforcement defaults, and proof-mint flow alignment for clean `full` passes
   - pending: broader attack-matrix review before deciding on long-term production enforcement defaults

## New Assets

- frontend surfaces:
  - `apps/web/app/page.tsx`
  - `apps/web/app/admin/page.tsx`
  - `apps/web/app/globals.css`
  - `apps/web/package.json`
- frontend modularization and browser landmark runtime:
  - `apps/web/app/admin/_components/`
  - `apps/web/app/admin/_hooks/`
  - `apps/web/app/admin/_lib/`
  - `apps/web/shims/tfjs-face-detection.ts`
  - `apps/web/next.config.ts`
- backend landmark-aware liveness:
 - backend landmark-aware liveness and human-face gate:
  - `services/verifier/app/pipeline/liveness.py`
  - `services/verifier/app/pipeline/landmark_metrics.py`
  - `services/verifier/app/pipeline/human_face.py`
  - `services/verifier/app/pipeline/quality.py`
  - `services/verifier/app/sessions/service.py`
  - `services/verifier/app/sessions/frame_pipeline.py`
  - `services/verifier/app/sessions/debug.py`
  - `services/verifier/app/sessions/finalize.py`
  - `services/verifier/app/core/config.py`
- tests and calibration:
  - `services/verifier/tests/conftest.py`
  - `services/verifier/tests/test_session_flows.py`
  - `services/verifier/tests/test_face_quality.py`
  - `services/verifier/scripts/analyze_calibration_samples.py`
  - `services/verifier/sample-data/calibration/README.md`

## Recommended Next Steps

`12-testing-phase-plan.md` is complete enough that the next steps now come from verifier hardening rather than testing-harness construction.

1. Run one more focused manual QA pass from `/admin` using the fixed-sequence controls, all four finalize modes, and the `Server Checks` panel, specifically validating:
   - `full` for end-to-end fused verification
   - `liveness_only` for challenge and gate tuning
   - `antispoof_only` for spoof-sample evaluation
   - `deepfake_only` for deepfake-head evaluation
   - live human-face telemetry on real human inputs and obvious non-human face-like inputs
   - the new same-origin API/WebSocket path when running through the production-parity proxy stack
   - finalize-time deepfake telemetry in `full`, `antispoof_only`, and `deepfake_only`
   - structured attack-analysis output and peak-aware confidence on failed attack sessions
2. Save labeled calibration rows from real browser webcam sessions in `services/verifier/sample-data/calibration/`.
3. Expand attack-matrix rows with real labeled spoof attempts so release checks measure pass/fail by attack class against project-native samples.
4. Use the new admin evaluation endpoints plus the analyzer scripts to tune liveness, anti-spoof, face-quality, motion continuity, spot-check, deepfake, and human-face thresholds.
5. Continue manual QA and attack-matrix collection on the production-parity Docker stack through `/`, `/admin`, `/api/health`, session creation, WebSocket streaming, and finalize through the proxy.
6. Start the next engineering phase from `13-improvement-plan.md`, with the likely next implementation target being structured attack-matrix benchmarking and threshold review now that the human-face gate is live in telemetry mode.
