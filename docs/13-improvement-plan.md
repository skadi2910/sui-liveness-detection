# Improvement Plan — Liveness & Anti-Spoofing Layer

**Date:** April 18, 2026
**Based on:** `10-progress-log.md` (updated), `11-liveness-anti-spoofing-review.md`, and model research session

---

## Current State Summary

The MVP stack is running end-to-end with real models and a hardened multi-step liveness sequence:

- YOLOv8 face detection (ONNX, `yolov8n-face-lindevs.onnx`)
- Heuristic face quality gate (OpenCV-based blur / size / angle / brightness checks)
- Silent-Face passive anti-spoof (ONNX ensemble, official upstream weights)
- TensorFlow.js face landmarks (browser-side, landmark telemetry streamed to backend)
- Active challenge-response liveness — **server-authored randomized 2- or 3-step sequences**
  - Supported steps: `blink_twice`, `turn_left`, `turn_right`, `nod_head`, `smile`
  - Ordered sequence enforcement with per-step frame windows and completion tracking
  - Configurable hold-window pacing for step completion
  - `open_mouth` removed from active pool and replaced with `smile`
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
- Browser landmark runtime has been stabilized for the local in-app browser by moving away from the brittle MediaPipe Tasks runtime
- Blink / nod defaults have been retuned so natural single actions register more reliably during manual QA
- Session lifecycle, WebSocket flow, calibration harness, and multi-step flow all validated in browser

What follows is a prioritized plan to harden the verifier before adding new layers (Walrus, Seal, SUI contract).

---

## Identified Gaps (from review + research)

### Gap 1 — No human face gate
The current pipeline assumes the incoming face is human. It does not explicitly reject non-human faces (animal masks, cartoon faces, plush toys). YOLOv8-face is trained on human face data and will usually skip non-human faces, but this is implicit behavior, not an explicit gate.

### Gap 2 — No dedicated deepfake detector
Silent-Face and the challenge-response sequence catch many AI-video attacks incidentally, but there is no model that specifically asks "is this stream synthetically generated?" Virtual-camera injection in particular is not blocked.

### ~~Gap 3 — Single challenge per session~~ ✅ RESOLVED
The backend now authors randomized 2- or 3-step sequences server-side with ordered enforcement, per-step frame windows, and configurable hold-window pacing. Supported steps: `blink_twice`, `turn_left`, `turn_right`, `nod_head`, `smile`. Remaining open items from this gap (motion continuity check, server-side landmark spot-check) are tracked under Priority 2 below.

### Gap 4 — Browser landmarks are trusted
The browser computes EAR, MAR, and yaw and sends them as telemetry. A tampered client or browser automation tool could send fabricated landmark values. The backend does not independently verify them.

### ~~Gap 5 — No face quality pre-filter~~ ✅ RESOLVED
The verifier now runs a heuristic face quality gate before liveness and anti-spoof frame acceptance. It checks blur, face size, yaw/pitch range, and brightness, exposes quality tuning through `GET /api/health`, and surfaces quality feedback in the browser testing harness.

### Gap 6 — No benchmark-style attack matrix
Threshold tuning exists, but the test suite does not report per-attack-type pass/fail rates (print, replay, deepfake, no-face, non-human). Without this it is hard to know which attack class is the current weakest point.

Note: the new admin QA modes make attack-matrix collection easier, but they do not replace the need for a structured benchmark/reporting layer.

---

## Improvement Priorities

Ordered by impact vs implementation cost. Do not start a new priority until the previous one is validated.

---

### Priority 1 — Add Gate 0: Human Face Classifier

**Why first:** This is the most direct fix for the non-human face problem identified above. It is also a lightweight pre-filter that reduces load on the more expensive models downstream.

**What to build:**
- A binary classifier: `human_face` vs `not_human_face`
- Input: the face crop output from YOLOv8 (not the full frame)
- Model options ranked by effort:
  1. **MobileNetV3-Small fine-tuned** — smallest, CPU-friendly, fine-tune on a mixed dataset of human faces + animal faces + masks + cartoons
  2. **EfficientNet-B0 fine-tuned** — slightly heavier but more accurate, same training approach
  3. **Rule-based skin tone + facial symmetry check** — very fast heuristic fallback, not robust against edge cases but adds a cheap first filter

**Training data sources:**
- Human faces: FFHQ, CelebA, LFW
- Non-human: ImageNet animal classes, iNaturalist (animal faces), cartoon face datasets
- Masks and props: collect from open spoof datasets (WMCA includes 3D mask samples)

**Integration point:**
```
Frame → YOLOv8 face crop → [NEW] Human Face Gate → Anti-Spoof → Liveness
                                  ↓ FAIL
                           Reject: "No human face detected"
```

**Acceptance criteria:**
- Rejects a cat face video with > 99% reliability
- Does not reject real human faces with hats, glasses, or facial hair
- Adds < 10ms latency on CPU

---

### Priority 2 — Finish Hardening the Challenge Protocol

**Status:** Completed for the current MVP hardening pass. The sequence infrastructure, motion continuity guard, and server-side landmark spot-check are all now in place.

**Already done (do not re-implement):**
- ✅ Randomized 2- or 3-step sequences server-authored and stored in Redis session
- ✅ Per-step frame windows with ordered completion tracking
- ✅ Configurable hold-window pacing for step completion
- ✅ Automatic session superseding when same wallet starts a new session
- ✅ `blink_twice`, `turn_left`, `turn_right`, `nod_head`, `smile` all supported

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

**Why this before a deepfake model:** If the current stack already catches talking-head and face-swap replay attacks via the challenge-response sequence, a dedicated deepfake model adds cost without adding protection. The attack matrix will answer this definitively.

**Acceptance criteria:**
- Report generated for all 7 attack classes
- Print and screen replay pass rate = 0%
- Non-human pass rate = 0% (after Priority 1 is done)
- Talking-head and face-swap pass rate measured and documented (expected to be the weak point)

---

### Priority 5 — Add Deepfake Detector (conditional on Priority 4 results)

**Only proceed if:** The attack matrix from Priority 4 shows that talking-head or face-swap replay attacks pass the current stack at a rate above 5%.

**Recommended model:** ViT-based deepfake detector (ONNX) available on HuggingFace (`onnx-community/Deep-Fake-Detector-v2-Model-ONNX`) — 92% accuracy, drop-in ONNX, no GPU required for inference.

**Integration as a second decision head, not a replacement:**
```
Frame → [existing] Silent-Face anti-spoof score
      → [new]      Deepfake detector score
      ↓
Fused verdict: reject if EITHER score exceeds threshold
```

**Do not replace Silent-Face.** Silent-Face catches print and replay attacks well. The deepfake detector catches AI-video attacks. They cover different threat classes.

**Acceptance criteria:**
- Talking-head and face-swap pass rate drops below 5%
- Live human pass rate does not decrease (no regression on false rejection)
- Latency budget: deepfake inference must complete in < 80ms on CPU

---

### Priority 6 — Upgrade Face Detection to SCRFD-10GF

**Why:** SCRFD-10GF from InsightFace outputs face detection AND 5-point landmarks (eyes, nose, mouth corners) in a single model call. This means:
- One fewer model call per frame (currently YOLOv8 + MediaPipe landmark streaming are separate)
- More accurate face crops for downstream models
- Server-side landmark availability for the spot-check in Priority 2d

**Migration path:**
- SCRFD-10GF is available as ONNX from the InsightFace model zoo
- Drop-in replacement for YOLOv8 in `services/verifier/app/pipeline/face.py`
- Keep MediaPipe in the browser for the 468-point landmark mesh (5-point is not enough for EAR/MAR)
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
    Human face classifier on YOLOv8 crop
    Rejects: non-human faces, cartoon faces, masks with non-human features
    ↓
Gate 1 — Face Quality Gate      [Priority 3 ✅]
    Blur / size / angle / brightness checks (OpenCV, no model)
    Returns: quality_score + user guidance if failing
    ↓
Gate 2 — Anti-Spoof Gate        [current + Priority 5]
    Silent-Face ONNX (passive, print/replay)
    + Deepfake detector ONNX (conditional on Priority 4 results)
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

1. **Collect real webcam samples and complete threshold calibration** — still pending per `10-progress-log.md`. Run all supported challenge combinations (`turn_left`, `turn_right`, `nod_head`, `smile`) manually, save labeled NDJSON calibration rows, and run the analyzer script. This unblocks reliable threshold values for everything downstream.
2. **Validate the new face quality gate on real sessions** — use the live `Server Checks` panel plus saved NDJSON samples to confirm blur, size, angle, and lighting checks behave as intended on project-native devices.
3. **Build the attack matrix test fixture set (Priority 4 framework)** — even with a partial set of attack samples now, establish the reporting structure so every release gate produces a per-attack-class pass rate table.
4. **Finish Priority 2 remaining items** — motion continuity check (2c) and landmark spot-check (2d) once calibration data is available to tune thresholds.

Start the human face classifier (Priority 1) only after the above are stable, since it requires a training or fine-tuning run against an assembled dataset.
