# Improvement Plan — Liveness & Anti-Spoofing Layer

**Date:** April 18, 2026
**Based on:** `10-progress-log.md` (updated), `11-liveness-anti-spoofing-review.md`, and model research session

---

## Current State Summary

The MVP stack is running end-to-end with real models and a hardened multi-step liveness sequence:

- YOLOv8 face detection (ONNX, `yolov8n-face-lindevs.onnx`)
- Heuristic face quality gate (OpenCV-based blur / size / angle / brightness checks)
- Human-face gate (CLIP zero-shot face-crop classifier, enforced by default in the current hackathon/demo build)
- Silent-Face passive anti-spoof (ONNX ensemble, official upstream weights)
- Finalize-time deepfake scorer (ONNX, enforced by default in the current hackathon/demo build)
- TensorFlow.js face landmarks (browser-side, landmark telemetry streamed to backend)
- Active challenge-response liveness — **server-authored randomized 2- or 3-step sequences**
  - Supported steps in the verifier: `blink_twice`, `turn_left`, `turn_right`, `nod_head`, `smile`, `open_mouth`
  - Current friendly default pool for new sessions: `turn_left`, `turn_right`, `nod_head`, `smile`, `open_mouth`
  - Ordered sequence enforcement with per-step frame windows and completion tracking
  - Configurable hold-window pacing for step completion
  - `blink_twice` remains available as a legacy QA challenge, but is no longer assigned in the default random pool
- Live webcam overlay with guide box, landmark wireframe, and backend face box
- Sequence timeline UI showing completed, current, and upcoming steps
- Browser-side `pitch` and `smile_ratio` metrics for nod/smile detection
- Faster browser-to-backend frame cadence for challenge responsiveness
- Split Pipeline / Detection / Signals logs with collapsed raw JSON for QA
- Tuning snapshot panel via `GET /api/health` exposing browser assist defaults and backend liveness thresholds
- Dedicated `Server Checks` panel showing live backend gate state, quality feedback, anti-spoof scores, and terminal failure reason
- Frontend split into a client-facing landing surface (`/`) and a dedicated admin/testing console (`/admin`)
- Admin/testing console refactored into reusable hooks, panel components, and shared utilities
- Admin/testing console supports QA finalize modes:
  - `full`
  - `liveness_only`
  - `antispoof_only`
  - `deepfake_only`
- Admin/testing console also supports fixed challenge sequences for repeatable manual QA instead of relying only on randomized friendly sequences
- Public verifier API remains session-oriented, with new admin-only evaluation endpoints for frame/session diagnostics
- Canonical verification stream route is now `/ws/sessions/{session_id}/stream` with the legacy `/ws/verify/{session_id}` alias kept for compatibility
- Finalize-time deepfake scoring is now wired into verifier results, health diagnostics, and terminal confidence as an optional second decision head
- Terminal verifier results now include structured `attack_analysis` so failed sessions can distinguish presentation-attack, deepfake, combined-attack, and non-attack failure families
- Local development / Docker now points at a real ONNX deepfake model (`onnx-community/Deep-Fake-Detector-v2-Model-ONNX`, `model_int8.onnx`) and the current hackathon/demo build enforces it by default
- The verifier currently runs as a gated sequential pipeline:
  - live path: face detect → quality → spot-check → human-face → liveness / anti-spoof preview
  - finalize path: accepted-frame filtering → liveness → anti-spoof → deepfake → decision fusion
- Production-parity local Docker assets now exist:
  - `docker-compose.prod.yml`
  - `proxy/nginx.conf`
  - `apps/web/Dockerfile.prod`
- Browser landmark runtime has been stabilized for the local in-app browser by replacing the brittle MediaPipe Tasks runtime with TensorFlow.js face-landmarks-detection
- Blink / nod defaults have been retuned so natural single actions register more reliably during manual QA
- Session lifecycle, WebSocket flow, calibration harness, and multi-step flow all validated in browser

What follows is a prioritized plan to harden the verifier before adding new layers (Walrus, Seal, SUI contract).

---

## Identified Gaps (from review + research)

### ~~Gap 1 — No enforced human face gate yet~~ ✅ RESOLVED FOR HACKATHON BUILD
The verifier now has a real CLIP-based human-face gate backed by a zero-shot classifier on the detected face crop. It exposes score/runtime diagnostics in health, admin evaluation endpoints, live debug payloads, and terminal results, and it is enforced by default in the current hackathon/demo build. The remaining work is deciding whether that strict default should remain in a production-cautious rollout after broader benchmarking.

### ~~Gap 2 — No enforced deepfake gate yet~~ ✅ RESOLVED FOR HACKATHON BUILD
The verifier now loads a real finalize-time ONNX deepfake detector, records sampled deepfake scores in results, and enforces the head by default in the current hackathon/demo build. The remaining work is deciding whether that strict default should remain enabled after broader attack-matrix validation.

### ~~Gap 3 — Single challenge per session~~ ✅ RESOLVED
The backend now authors randomized 2- or 3-step sequences server-side with ordered enforcement, per-step frame windows, and configurable hold-window pacing. The verifier still supports `blink_twice`, `turn_left`, `turn_right`, `nod_head`, `smile`, and `open_mouth`, but the default pool now favors friendlier actions for production-like manual testing. Remaining open items from this gap (motion continuity check, server-side landmark spot-check) are tracked under Priority 2 below.

### Gap 4 — Browser landmarks are trusted
The browser computes EAR, MAR, and yaw and sends them as telemetry. A tampered client or browser automation tool could send fabricated landmark values. The backend does not independently verify them.

### ~~Gap 5 — No face quality pre-filter~~ ✅ RESOLVED
The verifier now runs a heuristic face quality gate before liveness and anti-spoof frame acceptance. It checks blur, face size, yaw/pitch range, and brightness, exposes quality tuning through `GET /api/health`, and surfaces quality feedback in the browser testing harness.

### Gap 6 — No benchmark-style attack matrix
Threshold tuning exists, but the test suite does not report per-attack-type pass/fail rates (print, replay, deepfake, no-face, non-human). Without this it is hard to know which attack class is the current weakest point.

Note: the new admin QA modes make attack-matrix collection easier, but they do not replace the need for a structured benchmark/reporting layer.
The new fixed-sequence admin mode and terminal `attack_analysis` block now make that benchmark output much easier to interpret during manual QA, but they still need to be folded into a formal reporting suite.

---

## Improvement Priorities

Ordered by impact vs implementation cost. Do not start a new priority until the previous one is validated.

---

### Priority 1 — Human Face Gate (implemented, strict-demo enforced)

**Status:** Implemented as a face-crop classifier. The current local model path is a CLIP zero-shot scorer (`openai/clip-vit-base-patch32`) that compares the detected face crop against prompts such as real human face, animal face, cartoon face, and doll/mannequin face.

**Current implementation:**
- input: YOLOv8 detected face crop
- runtime: Transformers CLIP
- exposed through:
  - `GET /api/health`
  - live debug payloads / `Server Checks`
  - admin frame/session evaluation endpoints
  - terminal verifier results and exports
- current rollout mode:
  - `enabled=true`
  - `ready=true`
  - `enforced=true` in the current hackathon/demo build

**Current role in the pipeline:**
```
Frame → YOLOv8 face crop → Human Face Gate → Anti-Spoof → Liveness
```

**Remaining work after strict-demo enforcement:**
- benchmark obvious non-human inputs:
  - cat/dog face
  - cartoon/anime face
  - doll/mannequin
  - printed mask / costume face
- verify no meaningful false rejects on real human webcam sessions
- use the benchmark results to decide whether hard rejection should stay enabled outside the hackathon/demo build

**Acceptance criteria for keeping enforcement long-term:**
- obvious non-human face-like inputs score consistently below threshold
- real human sessions remain stable across lighting, glasses, hats, and facial hair
- latency remains acceptable on CPU

---

### Priority 2 — Finish Hardening the Challenge Protocol

**Status:** Completed for the current MVP hardening pass. The sequence infrastructure, motion continuity guard, and server-side landmark spot-check are all now in place.

**Already done (do not re-implement):**
- ✅ Randomized 2- or 3-step sequences server-authored and stored in Redis session
- ✅ Per-step frame windows with ordered completion tracking
- ✅ Configurable hold-window pacing for step completion
- ✅ Automatic session superseding when same wallet starts a new session
- ✅ `blink_twice`, `turn_left`, `turn_right`, `nod_head`, `smile`, and `open_mouth` all supported
- ✅ default random pool now favors friendlier actions and excludes `blink_twice`

**Completed sub-items:**

**2c. Motion continuity check** ✅ COMPLETED
- Require detectable natural face movement (micro-drift, head sway) both before and after each challenge event
- A perfectly still face that only moves during a challenge window is a replay signal
- Implement as frame-to-frame landmark displacement variance check in `services/verifier/app/pipeline/liveness.py`
- Threshold: flag if inter-frame landmark variance is below a minimum for more than 80% of frames in a step window

**Implemented behavior:**
- Configurable continuity thresholds added to verifier settings / health tuning snapshot
- Liveness evaluator now measures inter-frame landmark anchor displacement across consecutive frames
- Replay-like windows with too many near-static transitions no longer complete the step, even if the challenge signal itself appears valid
- Metadata-only / legacy tests remain supported: continuity enforcement activates only when sufficient landmark positions are present

**2d. Server-side landmark spot-check** ✅ COMPLETED
- The backend receives landmark-derived EAR/MAR/yaw telemetry from the browser but does not independently verify it
- Add a cross-check: compare the landmark-implied face center against the YOLOv8 bounding box from the same frame
- A tampered client sending fabricated landmark values will produce a spatial mismatch
- Implement in `services/verifier/app/pipeline/landmark_metrics.py` as a consistency scorer
- Reject the frame (not the session) if the mismatch exceeds a configurable pixel threshold

**Implemented behavior:**
- The verifier now computes a server-side landmark spot-check for each frame using the browser landmark anchor center against the server face box center
- Spot-check uses per-frame dimensions plus the detected face bounding box to calculate mismatch in pixels
- Frames with landmark telemetry that drifts too far from the detected face are excluded from liveness and anti-spoof acceptance instead of failing the whole session immediately
- Progress/debug payloads now expose spot-check status, mismatch amount, anchor count, and failure messaging for manual QA

**Acceptance criteria:**
- A pre-recorded blink clip fails > 95% of sessions (multi-step sequence already raises this bar significantly)
- Motion continuity check does not flag legitimate users under normal webcam conditions
- Fabricated landmark telemetry is rejected when face crop spatial position does not match

---

### Priority 3 — Add Face Quality Pre-Filter ✅ COMPLETED

**Status:** Completed. The verifier now has a fast OpenCV-based quality scorer, quality thresholds in config/health, and live frontend feedback through the testing harness.

**Implemented behavior:**
- A fast quality scorer that runs on the YOLOv8 face crop before it reaches Silent-Face
- Checks implemented:
  - **Blur score:** Laplacian variance
  - **Face size:** minimum crop size threshold
  - **Yaw/pitch range:** head angle bounds
  - **Brightness:** low-light / overexposure bounds
- These are all OpenCV operations — no additional model needed
- Return quality diagnostics in the progress/debug payload for frontend feedback

**UI feedback now exposed in the harness:**
- "Move closer to the camera"
- "Face the camera directly"
- "Find better lighting"

**Remaining validation work:**
- Confirm quality checks stay within the intended latency budget on real runs
- Confirm legitimate users see quality failures only in genuinely bad conditions
- Measure whether anti-spoof score variance decreases on the calibration dataset after filtering

---

### Priority 4 — Build an Attack Matrix Test Suite

**Why fourth:** Before adding heavier models, measure what the current stack actually misses. This is the practical recommendation from `11-liveness-anti-spoofing-review.md`.

**What to build:**
- A structured test dataset with labeled attack types:

| Attack Class | Example | Label |
|---|---|---|
| Live human | Real webcam sessions | `live` |
| Print attack | Printed A4 photo held to camera | `print` |
| Screen replay | Pre-recorded video played on phone/laptop | `replay` |
| Talking-head replay | AI talking-head video (e.g. D-ID, HeyGen output) | `talking_head` |
| Face-swap replay | Face-swap video played on screen | `face_swap` |
| Non-human | Cat video, plush toy, cartoon | `non_human` |
| Virtual camera injection | OBS virtual camera with static image | `injection` |

- Run each attack class through the full pipeline and report:
  - Pass rate (should be 0% for all attack classes except `live`)
  - Failure reason breakdown (which gate caught it)
  - Confidence score distribution per class

- Add this as a pytest fixture set so it runs on every release gate
- Use the admin/testing console modes intentionally:
  - `full` for realistic end-to-end attack outcomes
  - `liveness_only` to isolate challenge/gate regressions from spoof scoring
  - `antispoof_only` to isolate spoof classifier behavior without full sequence completion
  - `deepfake_only` to isolate finalize-time deepfake behavior without challenge completion obscuring the result
- Prefer fixed challenge sequences for benchmark runs so repeated attack samples are compared against the same action order

**Why this before a deepfake model:** If the current stack already catches talking-head and face-swap replay attacks via the challenge-response sequence, a dedicated deepfake model adds cost without adding protection. The attack matrix will answer this definitively.

**Acceptance criteria:**
- Report generated for all 7 attack classes
- Print and screen replay pass rate = 0%
- Non-human pass rate = 0% (after Priority 1 enforcement is enabled)
- Talking-head and face-swap pass rate measured and documented (expected to be the weak point)

---

### Priority 5 — Deepfake Detector Prototype (implemented, strict-demo enforced)

**Status:** The verifier now has a finalize-time deepfake scoring slot backed by a real ONNX model in local development / Docker, plus result/health telemetry. The current hackathon/demo build enforces it by default so the full stack is showcased end to end.

**Current target:** see `14-deepfake-detector-research.md`. The active local implementation target is an ONNX-ready image-level detector on accepted face crops (`onnx-community/Deep-Fake-Detector-v2-Model-ONNX`, quantized `model_int8.onnx`), with a heavier temporal video model reserved for a later hardening pass only if the attack matrix proves it is necessary.

**Integration as a second decision head, not a replacement:**
```
Frame → [existing] Silent-Face anti-spoof score
      → [new]      Deepfake detector score
      ↓
Fused verdict: reject if EITHER score exceeds threshold
```

**Do not replace Silent-Face.** Silent-Face catches print and replay attacks well. The deepfake detector catches AI-video attacks. They cover different threat classes.

**Implemented prototype shape:**
- sample a small number of accepted face crops per session (`4` to `8`, configurable)
- run deepfake inference only at finalize time
- load Hugging Face preprocessing metadata (`preprocessor_config.json`) for normalization and label mapping
- record:
  - `deepfake_score`
  - `max_deepfake_score`
  - `deepfake_frames_processed`
  - `deepfake_message`
  - `deepfake_enabled`
- expose terminal attack-family analysis alongside the raw deepfake scores so failed sessions clearly distinguish:
  - `presentation_attack`
  - `deepfake_attack`
  - `combined_attack_signals`
  - non-attack failures such as liveness/quality/no-face
- expose model/runtime state in `GET /api/health`
- include deepfake confidence contribution in the terminal verifier confidence when the head is active, while capping exported human-confidence using peak attack risk so failed attack sessions do not look like strong human passes

**Remaining acceptance criteria for keeping enforcement long-term:**
- Talking-head and face-swap pass rate drops below 5% when the head is enabled on local attack-matrix samples
- Live human pass rate does not decrease materially (no false-reject regression)
- Latency budget remains acceptable on CPU because the head samples only a small number of accepted face crops

---

### Priority 6 — Upgrade Face Detection to SCRFD-10GF

**Why:** SCRFD-10GF from InsightFace outputs face detection AND 5-point landmarks (eyes, nose, mouth corners) in a single model call. This means:
- One fewer model call per frame on the server side (currently YOLOv8 detection and browser landmark streaming are separate concerns)
- More accurate face crops for downstream models
- Server-side landmark availability for the spot-check in Priority 2d

**Migration path:**
- SCRFD-10GF is available as ONNX from the InsightFace model zoo
- Drop-in replacement for YOLOv8 in `services/verifier/app/pipeline/face.py`
- Keep the browser TensorFlow.js landmark layer in place for dense EAR / MAR / pitch-style signals (5-point landmarks are not enough for that role)
- Use SCRFD 5-point output only for the server-side spot-check (Priority 2d)

**Acceptance criteria:**
- Face detection accuracy equal or better than YOLOv8 on the calibration dataset
- Server-side 5-point landmarks available for spot-check validation
- No increase in per-frame latency

---

## What NOT to Do Yet

- **Do not integrate Walrus or Seal yet.** The verifier layer should be hardened first. Evidence worth storing is evidence from a hardened pipeline.
- **Do not fine-tune Silent-Face yet.** Calibration threshold tuning (already in the repo) is sufficient for MVP. Fine-tuning requires a labeled dataset that does not exist yet.
- **Do not add CDCN or MDFAS yet.** These are stronger anti-spoof models but require GPU for practical inference speed. They belong in Phase 2 after the CPU-based MVP is validated.
- **Do not add FaceShield (MLLM) yet.** This is a Phase 3 explainability layer, not an MVP requirement.

---

## Revised Four-Gate Pipeline (Target State After All Priorities)

```
Frame in
    ↓
Gate 0 — Human Face Gate        [Priority 1]
    Human-face classifier on YOLOv8 crop
    Current state: enforced by default in the current hackathon/demo build, visible in debug/result/health
    Long-term target: keep rejection enabled only if broader benchmarking supports it
    ↓
Gate 1 — Face Quality Gate      [Priority 3 ✅]
    Blur / size / angle / brightness checks (OpenCV, no model)
    Returns: quality_score + user guidance if failing
    ↓
Gate 2 — Anti-Spoof Gate        [current + Priority 5]
    Silent-Face ONNX (passive, print/replay)
    + Deepfake detector ONNX (currently enforced in the hackathon/demo build; subject to later benchmark review)
    Rejects: printed photos, screen replays, AI-generated video
    ↓
Gate 3 — Liveness Gate          [current ✅ + Priority 2 remaining]
    Randomized 2- or 3-step sequence (blink, turn, nod, smile) ✅
    Per-step frame windows and ordered completion tracking ✅
    Configurable hold-window pacing ✅
    Motion continuity check ✅
    Server-side landmark spot-check against face crop ✅
    Rejects: pre-recorded clips, virtual camera injection, bot automation
    ↓
Verdict: verified / failed + failure reason + confidence score
```

---

## Metrics to Track Per Release

| Metric | Target |
|---|---|
| Live human pass rate | > 95% |
| Print attack pass rate | 0% |
| Screen replay pass rate | 0% |
| Non-human face pass rate | 0% |
| Talking-head pass rate | < 5% (post Priority 5) |
| Virtual camera injection pass rate | < 10% (hard to fully block) |
| p95 full pipeline latency | < 120ms per frame |
| Two-step challenge completion time (p50) | < 6 seconds |

---

## Immediate Next Steps (This Sprint)

The multi-step challenge sequence is complete. The remaining sprint work in priority order:

1. **Collect real webcam samples and complete threshold calibration** — still pending per `10-progress-log.md`. Prefer fixed admin sequences for this pass so repeated human and attack runs are comparable across sessions.
2. **Validate the new face quality gate and human-face gate on real sessions** — use the live `Server Checks` panel plus saved NDJSON samples to confirm blur, size, angle, lighting, and human-face scores behave as intended on project-native devices.
3. **Build the attack matrix test fixture set (Priority 4 framework)** — even with a partial set of attack samples now, establish the reporting structure so every release gate produces a per-attack-class pass rate table, using the structured `attack_analysis` output instead of only raw `failure_reason`.
4. **Tune Priority 1, Priority 2, and Priority 5 thresholds using saved calibration rows** — human-face, motion continuity, landmark spot-check, and deepfake scoring are implemented; the remaining work is validating and tightening their thresholds against real captured sessions.
