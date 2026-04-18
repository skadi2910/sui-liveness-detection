"use client";

import type { ChallengeType, VerificationMode, VerificationResult } from "@sui-human/shared";

export type ManualAction =
  | "blink"
  | "turn_left"
  | "turn_right"
  | "nod_head"
  | "smile"
  | "spoof";

export type HarnessLogSection = "pipeline" | "detection" | "signals";

export type LogEntry = {
  id: string;
  summary: string;
  detail: string;
};

export type CalibrationLabel = "human" | "spoof";
export type SourceSplit = "train_calibration" | "dev" | "holdout";

export type AttackType =
  | "bona_fide"
  | "print"
  | "screen_replay"
  | "prerecorded_video"
  | "virtual_camera"
  | "ai_image"
  | "ai_video"
  | "face_swap_replay"
  | "unknown_spoof";

export type CalibrationRecord = {
  sample_id: string;
  label: CalibrationLabel;
  verification_mode: VerificationMode;
  failure_reason: string | null;
  attack_type: string;
  capture_medium: string;
  source_split: string;
  challenge_type: ChallengeType;
  challenge_sequence: ChallengeType[];
  total_challenges: number;
  status: VerificationResult["status"];
  human: boolean;
  spoof_score: number;
  max_spoof_score: number;
  confidence: number;
  challenge_progress: number;
  landmark_metrics: Record<string, number | null>;
  model_strategy: string;
  source: string;
  notes: string;
};

export type LandmarkEngineState = "idle" | "loading" | "ready" | "error";

export type BrowserLandmark = {
  x: number;
  y: number;
  z: number;
};

export type BrowserLandmarkResult = {
  faceLandmarks: BrowserLandmark[][];
};

export type LandmarkMetrics = {
  faceDetected: boolean;
  pointCount: number;
  yaw: number | null;
  pitch: number | null;
  pitchRatio: number | null;
  smileRatio: number | null;
  mouthRatio: number | null;
  leftEar: number | null;
  rightEar: number | null;
  averageEar: number | null;
  blinkDetected: boolean;
  mouthOpen: boolean;
  headTurn: "left" | "right" | "center" | null;
  timestamp: string | null;
};

export type LandmarkPacket = {
  landmarks: Record<string, number | string | boolean | null>;
  metadata: Record<string, unknown>;
  metrics: LandmarkMetrics;
};

export type PendingSignalState = {
  blinks: number;
  headTurn: "left" | "right" | null;
  pitchValues: number[];
};

export type SessionMetricSummary = {
  landmarksCaptured: number;
  pointCountMax: number;
  yawMin: number | null;
  yawMax: number | null;
  yawAbsPeak: number | null;
  pitchMin: number | null;
  pitchMax: number | null;
  smileRatioMax: number | null;
  mouthRatioMax: number | null;
  earMin: number | null;
  earMax: number | null;
  leftEarMin: number | null;
  rightEarMin: number | null;
};
