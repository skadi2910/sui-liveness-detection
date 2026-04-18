# Test Plan

## Goal

Define the minimum automated, manual, and attack-driven checks required to move the verifier from a local MVP into a demo environment without guessing whether liveness and anti-spoofing actually hold up.

## Current Scope

The current stack is:

- active challenge-response liveness from browser landmarks
- passive RGB anti-spoofing with Silent-Face
- no standalone deepfake detector in the backend today

This means "deepfake testing" currently belongs inside the spoof / replay attack matrix unless a dedicated deepfake model is added later.

## Success Criteria

- bona fide users pass across normal device and lighting variation
- print, screen replay, and prerecorded challenge attacks fail reliably
- attack-specific error rates are reported, not just one aggregate threshold
- holdout attack samples remain separate from calibration samples
- demo deployment keeps the same operating point used in local validation

## Core Metrics

- face detection success rate on bona fide sessions
- challenge completion rate by challenge type
- BPCER for bona fide users rejected as attacks
- APCER by `attack_type`
- `APCER_max` across attack types as the main guardrail for demo readiness
- ACER-style summary for quick threshold comparison during calibration
- latency to first face lock, challenge completion, and final decision

## Attack Matrix

Every release candidate should be tested against a small but explicit matrix.

- bona fide baseline: indoor daylight, low light, backlight, glasses, facial hair, makeup, different distances, different webcams and phones
- print attack: high-quality face print on matte and glossy paper
- screen replay: phone screen, laptop screen, and tablet screen replaying a recorded challenge session
- prerecorded challenge video: attacker replays a video of the same user performing blink, turn, or mouth actions
- cropped-face replay: only the face region is replayed on a second screen to reduce background cues
- virtual camera injection: prerecorded or generated content fed through OBS / virtual webcam
- AI image spoof: a generated portrait or face-swapped still shown to camera
- AI video spoof: deepfake or talking-head video shown to camera
- mask attack: optional for MVP, but should be added if the target use case is high risk

## Test Layers

### 1. Unit and Contract

- liveness evaluator thresholds for blink, turn, and mouth signals
- anti-spoof threshold logic for pass, fail, and hard-fail paths
- session state transitions and terminal failure reasons
- shared payload parity between frontend and backend contracts

### 2. Integration

- `POST /api/sessions`, `GET /api/sessions/{session_id}`, and WebSocket flows
- reconnect behavior and Redis TTL expiry
- evidence assembly without raw-frame persistence
- model readiness checks on cold boot

### 3. Calibration

- collect project-native NDJSON rows for both `human` and `spoof`
- label every spoof row with `attack_type`
- keep `source_split=train_calibration` and `source_split=holdout` separate
- use the analyzer script to tune thresholds on calibration samples only
- verify the chosen threshold again on the holdout subset before shipping

### 4. Manual Device QA

- camera denied, camera unavailable, and low-frame-rate capture
- no face, multiple faces, extreme pose, and partial occlusion
- browser landmark failure while raw frames still stream
- finalization with too few usable frames

### 5. Demo / Hosting

- fresh Ubuntu deploy succeeds
- Nginx passes WebSocket upgrades correctly
- TLS termination does not break REST or WebSocket paths
- health checks fail loudly if Redis or model loading is broken

## External Benchmarks

Use public datasets to sanity-check generalization, but do not assume they match the product one-to-one.

- OULU-NPU is a strong fit for RGB mobile replay / print PAD testing because it emphasizes unseen environments, devices, and PAIs
- SiW-M is a strong fit once you want more attack diversity and stronger unseen-attack evaluation
- CASIA-SURF is useful mainly if the project later adds depth or IR; it is not a clean match for the current RGB-only MVP
- Celeb-DF, DFDC, DeeperForensics-1.0, and Deepfake-Eval-2024 matter only if a dedicated deepfake detector is introduced

## Recommended Release Gate

Before a shared demo:

- minimum 30 bona fide sessions across at least 3 devices
- minimum 10 samples for each primary attack type: `print`, `screen_replay`, `prerecorded_video`, `virtual_camera`, `ai_video`
- report `BPCER`, `APCER` by attack type, and `APCER_max` on holdout data
- do not change runtime thresholds after holdout evaluation without rerunning the holdout set
