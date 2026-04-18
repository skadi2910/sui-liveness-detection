"use client";

import type { VerificationMode } from "@sui-human/shared";
import type { HarnessLogSection } from "./types";

function readNumberEnv(value: string | undefined, fallback: number): number {
  if (value === undefined) return fallback;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

function resolveHttpBase() {
  if (process.env.NEXT_PUBLIC_VERIFIER_HTTP_URL) {
    return process.env.NEXT_PUBLIC_VERIFIER_HTTP_URL;
  }
  return "";
}

function resolveWsBase() {
  if (process.env.NEXT_PUBLIC_VERIFIER_WS_URL) {
    return process.env.NEXT_PUBLIC_VERIFIER_WS_URL;
  }
  if (typeof window !== "undefined") {
    return `${window.location.protocol === "https:" ? "wss" : "ws"}://${window.location.host}`;
  }
  return "ws://localhost:3000";
}

export const httpBase = resolveHttpBase();
export const wsBase = resolveWsBase();
// Browser-side landmarks stay enabled for the admin harness. The hook uses the
// TensorFlow.js detector runtime so it stays independent from the brittle
// MediaPipe Tasks lifecycle that was failing in the local in-app browser.
export const browserLandmarksEnabled = true;

export const captureIntervalMs = readNumberEnv(
  process.env.NEXT_PUBLIC_CAPTURE_INTERVAL_MS,
  250,
);
export const landmarkIntervalMs = readNumberEnv(
  process.env.NEXT_PUBLIC_LANDMARK_INTERVAL_MS,
  120,
);
export const eyeClosedThreshold = 0.21;
export const eyeOpenThreshold = 0.26;
export const yawTurnThreshold = readNumberEnv(
  process.env.NEXT_PUBLIC_YAW_TURN_THRESHOLD,
  15,
);
export const smileRatioThreshold = readNumberEnv(
  process.env.NEXT_PUBLIC_SMILE_RATIO_THRESHOLD,
  0.36,
);
export const autoFinalizeDelayMs = readNumberEnv(
  process.env.NEXT_PUBLIC_AUTO_FINALIZE_DELAY_MS,
  900,
);
export const healthPollIntervalMs = readNumberEnv(
  process.env.NEXT_PUBLIC_HEALTH_POLL_INTERVAL_MS,
  3000,
);
export const maxLogEntries = 12;

export const verificationModeLabels: Record<VerificationMode, string> = {
  full: "Full verification",
  liveness_only: "Liveness-only QA",
  antispoof_only: "Anti-spoof-only QA",
  deepfake_only: "Deepfake-only QA",
};

export const verificationModeHints: Record<VerificationMode, string> = {
  full: "Requires both liveness and anti-spoof to pass.",
  liveness_only:
    "Finalize judges only the liveness path; anti-spoof stays informational.",
  antispoof_only:
    "Finalize judges only the anti-spoof path; incomplete challenges do not fail the session.",
  deepfake_only:
    "Finalize judges only the deepfake head; challenge and anti-spoof stay informational.",
};

export const sectionLabels: Record<HarnessLogSection, string> = {
  pipeline: "Pipeline",
  detection: "Detection",
  signals: "Signals",
};

export const landmarkIndices = {
  forehead: 10,
  chin: 152,
  faceLeft: 234,
  faceRight: 454,
  noseTip: 1,
  leftEyeOuter: 33,
  leftEyeInner: 133,
  rightEyeInner: 362,
  rightEyeOuter: 263,
  leftUpperEyeA: 159,
  leftUpperEyeB: 158,
  leftLowerEyeA: 145,
  leftLowerEyeB: 153,
  rightUpperEyeA: 386,
  rightUpperEyeB: 385,
  rightLowerEyeA: 374,
  rightLowerEyeB: 380,
  mouthLeft: 78,
  mouthRight: 308,
  upperLip: 13,
  lowerLip: 14,
};

export const overlayPointIndices = [
  landmarkIndices.forehead,
  landmarkIndices.faceLeft,
  landmarkIndices.leftEyeOuter,
  landmarkIndices.leftEyeInner,
  landmarkIndices.noseTip,
  landmarkIndices.rightEyeInner,
  landmarkIndices.rightEyeOuter,
  landmarkIndices.faceRight,
  landmarkIndices.mouthLeft,
  landmarkIndices.upperLip,
  landmarkIndices.lowerLip,
  landmarkIndices.mouthRight,
  landmarkIndices.chin,
] as const;

export const overlayConnections: Array<[number, number]> = [
  [landmarkIndices.faceLeft, landmarkIndices.forehead],
  [landmarkIndices.forehead, landmarkIndices.faceRight],
  [landmarkIndices.faceRight, landmarkIndices.chin],
  [landmarkIndices.chin, landmarkIndices.faceLeft],
  [landmarkIndices.leftEyeOuter, landmarkIndices.leftEyeInner],
  [landmarkIndices.rightEyeInner, landmarkIndices.rightEyeOuter],
  [landmarkIndices.noseTip, landmarkIndices.upperLip],
  [landmarkIndices.mouthLeft, landmarkIndices.upperLip],
  [landmarkIndices.upperLip, landmarkIndices.mouthRight],
  [landmarkIndices.mouthLeft, landmarkIndices.lowerLip],
  [landmarkIndices.lowerLip, landmarkIndices.mouthRight],
];

export const browserTuningDefaults = {
  capture_interval_ms: captureIntervalMs,
  landmark_interval_ms: landmarkIntervalMs,
  yaw_turn_threshold: yawTurnThreshold,
  smile_ratio_threshold: smileRatioThreshold,
  auto_finalize_delay_ms: autoFinalizeDelayMs,
};
