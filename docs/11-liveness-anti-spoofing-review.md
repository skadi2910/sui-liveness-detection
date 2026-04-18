# Liveness And Anti-Spoofing Review

## Current Approach

The current verifier combines:

- YOLOv8 face detection on backend frames
- MediaPipe Face Landmarker metrics from the browser
- active challenge-response liveness using blink, turn, and mouth actions
- Silent-Face RGB passive anti-spoof scoring on backend frames

This is a sensible CPU-friendly MVP stack for camera-based proof-of-human checks.

## What It Does Well

- combines active and passive checks instead of relying on only one
- keeps the liveness logic interpretable through EAR, MAR, and yaw-style thresholds
- uses a lightweight anti-spoof ensemble that is practical on CPU
- already has a calibration workflow for project-native data

## Main Gaps

### No dedicated deepfake detector

The backend currently does not run a separate deepfake model. Deepfake or talking-head attacks are only caught if they look spoof-like enough to Silent-Face or if they fail the challenge sequence.

### Limited challenge entropy

Each session uses one challenge type only. That is easier to replay than a short randomized sequence such as blink plus turn with timing constraints.

### Browser landmarks are trusted as telemetry

The browser computes the liveness cues and sends them to the backend. That is fine for MVP speed, but it leaves room for browser automation, virtual camera injection, or tampered clients unless server-side checks are made stricter.

### Testing is currently calibration-heavy, not benchmark-heavy

The repo had threshold tuning support, but not PAD-style attack reporting by attack type. That made it hard to answer whether the system is strong against replay, print, or deepfake-style attacks specifically.

## Recommended Improvements

### Keep the current stack for MVP, but harden the protocol

- move from one challenge to a randomized 2-step sequence
- enforce challenge timing windows instead of accepting any matching frame eventually
- require enough motion before and after a challenge event so prerecorded replays are less effective
- add explicit virtual-camera and replay testing to every release gate

### Treat deepfakes as an attack class first

Before adding a dedicated deepfake model, test whether the current active-plus-passive stack rejects:

- talking-head replay videos
- face-swapped videos replayed on screen
- AI-generated still portraits shown to camera
- virtual-camera injected synthetic video

If that attack subset remains weak, then add a separate deepfake detector.

### Add a dedicated deepfake detector only if the threat model needs it

A deepfake detector is worth adding when:

- virtual-camera or injected media is in scope
- high-value onboarding or fraud prevention is the goal
- holdout testing shows silent-face plus challenge-response misses AI video attacks

If added, evaluate it separately with deepfake datasets because PAD benchmarks and deepfake benchmarks are not interchangeable.

## Research Notes

- ISO/IEC 30107-3:2023 is the current testing and reporting standard for biometric presentation attack detection.
- NIST FATE PAD (NISTIR 8491, published September 19, 2023) evaluated passive software-only face PAD algorithms on conventional 2D imagery.
- OULU-NPU emphasizes generalization across unseen environments, devices, and PAIs in mobile RGB settings.
- CASIA-SURF is large and multi-modal, but it aligns better with RGB + depth + IR systems than with the current RGB-only MVP.
- Recent deepfake benchmarks show a serious generalization problem. Deepfake-Eval-2024 reports that open-source model AUC drops sharply on real in-the-wild 2024 content.

## Practical Recommendation

Do not jump straight to a heavier model because "deepfake" sounds more advanced. First tighten the protocol, collect a labeled attack matrix, and measure PAD-style metrics by attack type. If AI-video attacks remain a holdout weakness after that, add a dedicated deepfake detector as a second decision head rather than replacing the current liveness and anti-spoof stack.
