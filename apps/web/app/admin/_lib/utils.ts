"use client";

import type { ChallengeType } from "@sui-human/shared";
import type {
  CalibrationRecord,
  LandmarkMetrics,
  LogEntry,
  SessionMetricSummary,
} from "./types";

export function challengeLabel(challengeType: ChallengeType): string {
  if (challengeType === "blink_twice") return "Blink twice (legacy)";
  if (challengeType === "turn_left") return "Turn left";
  if (challengeType === "turn_right") return "Turn right";
  if (challengeType === "nod_head") return "Nod head";
  if (challengeType === "smile") return "Smile";
  return "Open mouth";
}

export function challengeHint(challengeType: ChallengeType | null): string {
  if (challengeType === "blink_twice") return "Blink twice to clear the current step. This is a legacy QA challenge.";
  if (challengeType === "turn_left") return "Turn your head left once, then return to center.";
  if (challengeType === "turn_right") return "Turn your head right once, then return to center.";
  if (challengeType === "nod_head") return "Give one natural down-and-up nod.";
  if (challengeType === "smile") return "Hold a natural smile for a moment.";
  if (challengeType === "open_mouth") return "Open your mouth once in a natural way.";
  return "Start a session to receive a challenge sequence.";
}

export function normalizeChallengeSequence(
  sequence: ChallengeType[] | undefined,
  challengeType: ChallengeType | null | undefined,
): ChallengeType[] {
  if (Array.isArray(sequence)) {
    return sequence.filter(Boolean);
  }
  if (challengeType) return [challengeType];
  return [];
}

export function normalizeCompletedChallenges(
  completed: ChallengeType[] | undefined,
): ChallengeType[] {
  return Array.isArray(completed) ? completed.filter(Boolean) : [];
}

export function nextId() {
  return `${Date.now()}-${Math.random().toString(16).slice(2, 8)}`;
}

export function roundMetric(value: number): number {
  return Math.round(value * 10000) / 10000;
}

export function formatMetric(value: number | null | undefined): string {
  if (typeof value !== "number" || Number.isNaN(value)) return "n/a";
  return value.toFixed(2);
}

export function formatPercent(value: number | null | undefined): string {
  if (typeof value !== "number" || Number.isNaN(value)) return "n/a";
  return `${Math.round(value * 100)}%`;
}

export function minNullable(current: number | null, next: number | null): number | null {
  if (next === null) return current;
  if (current === null) return next;
  return Math.min(current, next);
}

export function maxNullable(current: number | null, next: number | null): number | null {
  if (next === null) return current;
  if (current === null) return next;
  return Math.max(current, next);
}

export function emptyLandmarkMetrics(): LandmarkMetrics {
  return {
    faceDetected: false,
    pointCount: 0,
    yaw: null,
    pitch: null,
    pitchRatio: null,
    smileRatio: null,
    mouthRatio: null,
    leftEar: null,
    rightEar: null,
    averageEar: null,
    blinkDetected: false,
    mouthOpen: false,
    headTurn: null,
    timestamp: null,
  };
}

export function emptySessionMetricSummary(): SessionMetricSummary {
  return {
    landmarksCaptured: 0,
    pointCountMax: 0,
    yawMin: null,
    yawMax: null,
    yawAbsPeak: null,
    pitchMin: null,
    pitchMax: null,
    smileRatioMax: null,
    mouthRatioMax: null,
    earMin: null,
    earMax: null,
    leftEarMin: null,
    rightEarMin: null,
  };
}

export function emptyLogs(): Record<"pipeline" | "detection" | "signals", LogEntry[]> {
  return {
    pipeline: [],
    detection: [],
    signals: [],
  };
}

export function summarizeProgressDebug(
  challengeType: ChallengeType,
  sequence: ChallengeType[],
  currentIndex: number,
  stepStatus: string,
  message: string,
): string {
  return `${currentIndex + 1}/${sequence.length} ${challengeLabel(challengeType)} ${stepStatus}: ${message}`;
}

export function deriveAttackTypeForLabel(
  label: "human" | "spoof",
  attackType: string,
): string {
  if (label === "human") return "bona_fide";
  return attackType === "bona_fide" ? "unknown_spoof" : attackType;
}

export function buildCalibrationRecord(params: {
  sessionId: string | null;
  verificationMode: string;
  label: "human" | "spoof";
  attackType: string;
  sourceSplit: string;
  challengeType: ChallengeType | null;
  challengeSequence: ChallengeType[];
  result: {
    session_id: string;
    evaluation_mode?: string;
    failure_reason?: string | null;
    status: CalibrationRecord["status"];
    human: boolean;
    spoof_score: number;
    max_spoof_score?: number | null;
    deepfake_score?: number | null;
    max_deepfake_score?: number | null;
    deepfake_frames_processed?: number;
    deepfake_enabled?: boolean;
    attack_analysis?: CalibrationRecord["attack_analysis"];
    confidence: number;
  } | null;
  progress: number;
  summary: SessionMetricSummary;
  notes: string;
}): CalibrationRecord | null {
  const {
    sessionId,
    verificationMode,
    label,
    attackType,
    sourceSplit,
    challengeType,
    challengeSequence,
    result,
    progress,
    summary,
    notes,
  } = params;

  if (!sessionId || !result || !challengeType) return null;

  return {
    sample_id: result.session_id,
    label,
    verification_mode: (result.evaluation_mode ?? verificationMode) as CalibrationRecord["verification_mode"],
    failure_reason: result.failure_reason ?? null,
    attack_type: label === "human" ? "bona_fide" : attackType,
    capture_medium: "camera",
    source_split: sourceSplit,
    challenge_type: challengeType,
    challenge_sequence: challengeSequence,
    total_challenges: challengeSequence.length,
    status: result.status,
    human: result.human,
    spoof_score: result.spoof_score,
    max_spoof_score: result.max_spoof_score ?? result.spoof_score,
    deepfake_score: result.deepfake_score ?? null,
    max_deepfake_score: result.max_deepfake_score ?? result.deepfake_score ?? null,
    deepfake_frames_processed: result.deepfake_frames_processed ?? 0,
    deepfake_enabled: result.deepfake_enabled ?? false,
    attack_analysis: result.attack_analysis ?? null,
    confidence: result.confidence,
    challenge_progress: progress,
    landmark_metrics: {
      point_count_max: summary.pointCountMax,
      yaw_min: summary.yawMin,
      yaw_max: summary.yawMax,
      yaw_abs_peak: summary.yawAbsPeak,
      pitch_min: summary.pitchMin,
      pitch_max: summary.pitchMax,
      smile_ratio_max: summary.smileRatioMax,
      mouth_ratio_max: summary.mouthRatioMax,
      ear_min: summary.earMin,
      ear_max: summary.earMax,
      left_ear_min: summary.leftEarMin,
      right_ear_min: summary.rightEarMin,
      landmarks_captured: summary.landmarksCaptured,
    },
    model_strategy: "pretrained-calibration-only",
    source: "webcam-harness",
    notes,
  };
}
