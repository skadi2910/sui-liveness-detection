"use client";

import { startTransition, useEffect, useRef, useState } from "react";
import type {
  FaceLandmarker,
  FaceLandmarkerResult,
  NormalizedLandmark,
} from "@mediapipe/tasks-vision";
import type {
  ChallengeType,
  CreateSessionResponse,
  HealthResponse,
  StepStatus,
  VerificationDebugPayload,
  VerificationMode,
  VerificationResult,
  WsServerEvent,
} from "@sui-human/shared";

type ManualAction =
  | "blink"
  | "turn_left"
  | "turn_right"
  | "nod_head"
  | "smile"
  | "spoof";

type HarnessLogSection = "pipeline" | "detection" | "signals";

type LogEntry = {
  id: string;
  summary: string;
  detail: string;
};

type CalibrationLabel = "human" | "spoof";
type SourceSplit = "train_calibration" | "dev" | "holdout";
type AttackType =
  | "bona_fide"
  | "print"
  | "screen_replay"
  | "prerecorded_video"
  | "virtual_camera"
  | "ai_image"
  | "ai_video"
  | "face_swap_replay"
  | "unknown_spoof";

type CalibrationRecord = {
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

type LandmarkEngineState = "idle" | "loading" | "ready" | "error";

type LandmarkMetrics = {
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

type LandmarkPacket = {
  landmarks: Record<string, number | string | boolean | null>;
  metadata: Record<string, unknown>;
  metrics: LandmarkMetrics;
};

type PendingSignalState = {
  blinks: number;
  headTurn: "left" | "right" | null;
  pitchValues: number[];
};

type SessionMetricSummary = {
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

const verificationModeLabels: Record<VerificationMode, string> = {
  full: "Full verification",
  liveness_only: "Liveness-only QA",
  antispoof_only: "Anti-spoof-only QA",
};

function readNumberEnv(value: string | undefined, fallback: number): number {
  if (value === undefined) return fallback;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

const httpBase =
  process.env.NEXT_PUBLIC_VERIFIER_HTTP_URL ?? "http://localhost:8000";
const wsBase =
  process.env.NEXT_PUBLIC_VERIFIER_WS_URL ??
  httpBase.replace(/^http/, "ws");
const faceLandmarkerModelUrl =
  process.env.NEXT_PUBLIC_FACELANDMARKER_MODEL_URL ??
  "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task";
const mediapipeWasmUrl =
  process.env.NEXT_PUBLIC_MEDIAPIPE_WASM_URL ??
  "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@latest/wasm";

const captureIntervalMs = readNumberEnv(process.env.NEXT_PUBLIC_CAPTURE_INTERVAL_MS, 700);
const landmarkIntervalMs = readNumberEnv(process.env.NEXT_PUBLIC_LANDMARK_INTERVAL_MS, 120);
const eyeClosedThreshold = 0.19;
const eyeOpenThreshold = 0.24;
const yawTurnThreshold = readNumberEnv(process.env.NEXT_PUBLIC_YAW_TURN_THRESHOLD, 15);
const smileRatioThreshold = readNumberEnv(
  process.env.NEXT_PUBLIC_SMILE_RATIO_THRESHOLD,
  0.36,
);
const autoFinalizeDelayMs = readNumberEnv(
  process.env.NEXT_PUBLIC_AUTO_FINALIZE_DELAY_MS,
  900,
);
const maxLogEntries = 12;

const landmarkIndices = {
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

const overlayPointIndices = [
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

const overlayConnections: Array<[number, number]> = [
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

const sectionLabels: Record<HarnessLogSection, string> = {
  pipeline: "Pipeline",
  detection: "Detection",
  signals: "Signals",
};

function challengeLabel(challengeType: ChallengeType): string {
  if (challengeType === "blink_twice") return "Blink twice";
  if (challengeType === "turn_left") return "Turn left";
  if (challengeType === "turn_right") return "Turn right";
  if (challengeType === "nod_head") return "Nod head";
  if (challengeType === "smile") return "Smile";
  return "Open mouth";
}

function challengeHint(challengeType: ChallengeType | null): string {
  if (challengeType === "blink_twice") return "Blink twice to clear the current step.";
  if (challengeType === "turn_left") return "Turn your head left once.";
  if (challengeType === "turn_right") return "Turn your head right once.";
  if (challengeType === "nod_head") return "Nod down and back up.";
  if (challengeType === "smile") return "Hold a natural smile for a moment.";
  if (challengeType === "open_mouth") return "Open your mouth once.";
  return "Start a session to receive a challenge sequence.";
}

function normalizeChallengeSequence(
  sequence: ChallengeType[] | undefined,
  challengeType: ChallengeType | null | undefined,
): ChallengeType[] {
  if (Array.isArray(sequence)) {
    return sequence.filter(Boolean);
  }
  if (challengeType) {
    return [challengeType];
  }
  return [];
}

function normalizeCompletedChallenges(
  completed: ChallengeType[] | undefined,
): ChallengeType[] {
  return Array.isArray(completed) ? completed.filter(Boolean) : [];
}

function nextId() {
  return `${Date.now()}-${Math.random().toString(16).slice(2, 8)}`;
}

function roundMetric(value: number): number {
  return Math.round(value * 10000) / 10000;
}

function formatMetric(value: number | null | undefined): string {
  if (typeof value !== "number" || Number.isNaN(value)) return "n/a";
  return value.toFixed(2);
}

function formatPercent(value: number | null | undefined): string {
  if (typeof value !== "number" || Number.isNaN(value)) return "n/a";
  return `${Math.round(value * 100)}%`;
}

function distance(a: NormalizedLandmark, b: NormalizedLandmark): number {
  return Math.hypot(a.x - b.x, a.y - b.y);
}

function minNullable(current: number | null, next: number | null): number | null {
  if (next === null) return current;
  if (current === null) return next;
  return Math.min(current, next);
}

function maxNullable(current: number | null, next: number | null): number | null {
  if (next === null) return current;
  if (current === null) return next;
  return Math.max(current, next);
}

function emptyLandmarkMetrics(): LandmarkMetrics {
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

function emptySessionMetricSummary(): SessionMetricSummary {
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

function emptyLogs(): Record<HarnessLogSection, LogEntry[]> {
  return {
    pipeline: [],
    detection: [],
    signals: [],
  };
}

function calculateEar(
  p1: NormalizedLandmark,
  p2: NormalizedLandmark,
  p3: NormalizedLandmark,
  p4: NormalizedLandmark,
  p5: NormalizedLandmark,
  p6: NormalizedLandmark,
): number {
  const denominator = 2 * distance(p1, p4);
  if (denominator <= 0) return 0;
  return (distance(p2, p6) + distance(p3, p5)) / denominator;
}

function extractFaceMetrics(
  face: NormalizedLandmark[],
  blinkDetected: boolean,
): LandmarkMetrics {
  const forehead = face[landmarkIndices.forehead];
  const chin = face[landmarkIndices.chin];
  const faceLeft = face[landmarkIndices.faceLeft];
  const faceRight = face[landmarkIndices.faceRight];
  const noseTip = face[landmarkIndices.noseTip];
  const leftEyeOuter = face[landmarkIndices.leftEyeOuter];
  const leftEyeInner = face[landmarkIndices.leftEyeInner];
  const rightEyeInner = face[landmarkIndices.rightEyeInner];
  const rightEyeOuter = face[landmarkIndices.rightEyeOuter];
  const leftUpperEyeA = face[landmarkIndices.leftUpperEyeA];
  const leftUpperEyeB = face[landmarkIndices.leftUpperEyeB];
  const leftLowerEyeA = face[landmarkIndices.leftLowerEyeA];
  const leftLowerEyeB = face[landmarkIndices.leftLowerEyeB];
  const rightUpperEyeA = face[landmarkIndices.rightUpperEyeA];
  const rightUpperEyeB = face[landmarkIndices.rightUpperEyeB];
  const rightLowerEyeA = face[landmarkIndices.rightLowerEyeA];
  const rightLowerEyeB = face[landmarkIndices.rightLowerEyeB];
  const mouthLeft = face[landmarkIndices.mouthLeft];
  const mouthRight = face[landmarkIndices.mouthRight];
  const upperLip = face[landmarkIndices.upperLip];
  const lowerLip = face[landmarkIndices.lowerLip];

  const leftEar = calculateEar(
    leftEyeOuter,
    leftUpperEyeA,
    leftUpperEyeB,
    leftEyeInner,
    leftLowerEyeA,
    leftLowerEyeB,
  );
  const rightEar = calculateEar(
    rightEyeOuter,
    rightUpperEyeA,
    rightUpperEyeB,
    rightEyeInner,
    rightLowerEyeA,
    rightLowerEyeB,
  );
  const averageEar = (leftEar + rightEar) / 2;
  const mouthWidth = distance(mouthLeft, mouthRight);
  const mouthHeight = distance(upperLip, lowerLip);
  const mouthRatio = mouthWidth > 0 ? mouthHeight / mouthWidth : 0;
  const eyeMidX = (leftEyeOuter.x + rightEyeOuter.x) / 2;
  const eyeWidth = Math.max(Math.abs(rightEyeOuter.x - leftEyeOuter.x), 0.001);
  const yaw = -(((noseTip.x - eyeMidX) / eyeWidth) * 90);
  const faceHeight = Math.max(Math.abs(chin.y - forehead.y), 0.001);
  const centerY = (forehead.y + chin.y) / 2;
  const pitchRatio = (noseTip.y - centerY) / faceHeight;
  const pitch = pitchRatio * 180;
  const faceWidth = Math.max(Math.abs(faceRight.x - faceLeft.x), 0.001);
  const smileRatio = mouthWidth / faceWidth;

  let headTurn: LandmarkMetrics["headTurn"] = "center";
  if (yaw <= -yawTurnThreshold) headTurn = "left";
  if (yaw >= yawTurnThreshold) headTurn = "right";

  return {
    faceDetected: true,
    pointCount: face.length,
    yaw: roundMetric(yaw),
    pitch: roundMetric(pitch),
    pitchRatio: roundMetric(pitchRatio),
    smileRatio: roundMetric(smileRatio),
    mouthRatio: roundMetric(mouthRatio),
    leftEar: roundMetric(leftEar),
    rightEar: roundMetric(rightEar),
    averageEar: roundMetric(averageEar),
    blinkDetected,
    mouthOpen: mouthRatio >= 0.28,
    headTurn,
    timestamp: new Date().toISOString(),
  };
}

function buildLandmarkPacket(
  face: NormalizedLandmark[],
  metrics: LandmarkMetrics,
): LandmarkPacket {
  const noseTip = face[landmarkIndices.noseTip];
  const leftEyeOuter = face[landmarkIndices.leftEyeOuter];
  const rightEyeOuter = face[landmarkIndices.rightEyeOuter];
  const mouthLeft = face[landmarkIndices.mouthLeft];
  const mouthRight = face[landmarkIndices.mouthRight];
  const upperLip = face[landmarkIndices.upperLip];
  const lowerLip = face[landmarkIndices.lowerLip];
  const landmarks: LandmarkPacket["landmarks"] = {
    source: "mediapipe_face_landmarker",
    point_count: face.length,
    nose_tip_x: roundMetric(noseTip.x),
    nose_tip_y: roundMetric(noseTip.y),
    nose_tip_z: roundMetric(noseTip.z),
    left_eye_outer_x: roundMetric(leftEyeOuter.x),
    left_eye_outer_y: roundMetric(leftEyeOuter.y),
    right_eye_outer_x: roundMetric(rightEyeOuter.x),
    right_eye_outer_y: roundMetric(rightEyeOuter.y),
    mouth_left_x: roundMetric(mouthLeft.x),
    mouth_left_y: roundMetric(mouthLeft.y),
    mouth_right_x: roundMetric(mouthRight.x),
    mouth_right_y: roundMetric(mouthRight.y),
    upper_lip_y: roundMetric(upperLip.y),
    lower_lip_y: roundMetric(lowerLip.y),
    yaw: metrics.yaw,
    pitch: metrics.pitch,
    pitch_ratio: metrics.pitchRatio,
    smile_ratio: metrics.smileRatio,
    mouth_ratio: metrics.mouthRatio,
    left_ear: metrics.leftEar,
    right_ear: metrics.rightEar,
    average_ear: metrics.averageEar,
    blink_detected: metrics.blinkDetected,
    mouth_open: metrics.mouthOpen,
    head_turn: metrics.headTurn,
    smile: typeof metrics.smileRatio === "number" ? metrics.smileRatio >= smileRatioThreshold : false,
  };

  const metadata: LandmarkPacket["metadata"] = {
    yaw: metrics.yaw ?? 0,
    pitch: metrics.pitch ?? 0,
    pitch_ratio: metrics.pitchRatio ?? 0,
    smile_ratio: metrics.smileRatio ?? 0,
    mouth_ratio: metrics.mouthRatio ?? 0,
    eyes_closed:
      typeof metrics.averageEar === "number"
        ? metrics.averageEar < eyeClosedThreshold
        : false,
  };
  if (metrics.blinkDetected) metadata.blink = true;
  if (metrics.headTurn === "left" || metrics.headTurn === "right") {
    metadata.head_turn = metrics.headTurn;
  }
  if (typeof metrics.smileRatio === "number" && metrics.smileRatio >= smileRatioThreshold) {
    metadata.smile = true;
  }
  return { landmarks, metadata, metrics };
}

function summarizeProgressDebug(
  challengeType: ChallengeType,
  sequence: ChallengeType[],
  currentIndex: number,
  stepStatus: StepStatus,
  message: string,
): string {
  return `${currentIndex + 1}/${sequence.length} ${challengeLabel(challengeType)} ${stepStatus}: ${message}`;
}

function overlayTone(
  metrics: LandmarkMetrics,
  debug: VerificationDebugPayload | null,
  stepStatus: StepStatus,
): string {
  const backendDetected = Boolean(debug?.face_detection?.detected);
  const backendConfidence = debug?.face_detection?.confidence ?? 0;
  if (!metrics.faceDetected && !backendDetected) return "#d24b4b";
  if (stepStatus === "completed") return "#2878c8";
  if (!backendDetected || backendConfidence < 0.35) return "#d89a2b";
  return "#24966d";
}

export default function Page() {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const captureCanvasRef = useRef<HTMLCanvasElement | null>(null);
  const overlayCanvasRef = useRef<HTMLCanvasElement | null>(null);
  const socketRef = useRef<WebSocket | null>(null);
  const captureTimerRef = useRef<number | null>(null);
  const landmarkTimerRef = useRef<number | null>(null);
  const finalizeTimerRef = useRef<number | null>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const faceLandmarkerRef = useRef<FaceLandmarker | null>(null);
  const latestLandmarkPacketRef = useRef<LandmarkPacket | null>(null);
  const latestFaceRef = useRef<NormalizedLandmark[] | null>(null);
  const autoAssistRef = useRef(false);
  const forceSpoofRef = useRef(false);
  const pendingSignalsRef = useRef<PendingSignalState>({
    blinks: 0,
    headTurn: null,
    pitchValues: [],
  });
  const lastEyesClosedRef = useRef(false);
  const lastDebugSummariesRef = useRef<{ detection: string | null; signals: string | null }>({
    detection: null,
    signals: null,
  });
  const frameCounterRef = useRef(0);
  const finalizeRequestedRef = useRef(false);
  const lastAutoSavedSessionIdRef = useRef<string | null>(null);
  const sessionRef = useRef<CreateSessionResponse | null>(null);
  const resultRef = useRef<VerificationResult | null>(null);

  const [walletAddress, setWalletAddress] = useState("0xtesthuman");
  const [cameraState, setCameraState] = useState<"idle" | "ready" | "error">("idle");
  const [cameraMessage, setCameraMessage] = useState("Requesting webcam access...");
  const [landmarkState, setLandmarkState] = useState<LandmarkEngineState>("loading");
  const [landmarkMessage, setLandmarkMessage] = useState("Loading MediaPipe Face Landmarker...");
  const [landmarkMetrics, setLandmarkMetrics] = useState<LandmarkMetrics>(emptyLandmarkMetrics);
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [session, setSession] = useState<CreateSessionResponse | null>(null);
  const [challengeType, setChallengeType] = useState<ChallengeType | null>(null);
  const [challengeSequence, setChallengeSequence] = useState<ChallengeType[]>([]);
  const [currentChallengeIndex, setCurrentChallengeIndex] = useState(0);
  const [completedChallenges, setCompletedChallenges] = useState<ChallengeType[]>([]);
  const [stepStatus, setStepStatus] = useState<StepStatus>("pending");
  const [progress, setProgress] = useState(0);
  const [statusMessage, setStatusMessage] = useState("Waiting for backend.");
  const [backendDebug, setBackendDebug] = useState<VerificationDebugPayload | null>(null);
  const [result, setResult] = useState<VerificationResult | null>(null);
  const [sessionMetricSummary, setSessionMetricSummary] = useState<SessionMetricSummary>(
    emptySessionMetricSummary,
  );
  const [verificationMode, setVerificationMode] = useState<VerificationMode>("full");
  const [calibrationLabel, setCalibrationLabel] = useState<CalibrationLabel>("human");
  const [attackType, setAttackType] = useState<AttackType>("bona_fide");
  const [sourceSplit, setSourceSplit] = useState<SourceSplit>("train_calibration");
  const [calibrationNotes, setCalibrationNotes] = useState("");
  const [calibrationMessage, setCalibrationMessage] = useState("Complete a session to export a calibration row.");
  const [connectionState, setConnectionState] = useState("idle");
  const [autoAssist, setAutoAssist] = useState(false);
  const [forceSpoof, setForceSpoof] = useState(false);
  const [busy, setBusy] = useState(false);
  const [finalizeRequested, setFinalizeRequested] = useState(false);
  const [logs, setLogs] = useState<Record<HarnessLogSection, LogEntry[]>>(emptyLogs);
  const [queuedActions, setQueuedActions] = useState<ManualAction[]>([]);

  useEffect(() => {
    sessionRef.current = session;
  }, [session]);

  useEffect(() => {
    resultRef.current = result;
  }, [result]);

  function appendLog(section: HarnessLogSection, summary: string, detail: unknown = summary) {
    const entry: LogEntry = {
      id: nextId(),
      summary,
      detail:
        typeof detail === "string" ? detail : JSON.stringify(detail, null, 2),
    };
    startTransition(() => {
      setLogs((current) => ({
        ...current,
        [section]: [entry, ...current[section]].slice(0, maxLogEntries),
      }));
    });
  }

  function appendDebugLogs(debug: VerificationDebugPayload) {
    const detectionSummary = `Face ${debug.face_detection?.detected ? "detected" : "missing"} / quality ${debug.quality?.passed ? "ok" : "check"} / landmarks ${debug.landmarks?.point_count ?? 0}`;
    if (lastDebugSummariesRef.current.detection !== detectionSummary) {
      lastDebugSummariesRef.current.detection = detectionSummary;
      appendLog("detection", detectionSummary, debug);
    }

    const signalSummary = [
      `EAR ${formatMetric(debug.landmarks?.average_ear)}`,
      `yaw ${formatMetric(debug.landmarks?.yaw)}`,
      `pitch ${formatMetric(debug.landmarks?.pitch)}`,
      `smile ${formatMetric(debug.landmarks?.smile_ratio)}`,
      `quality ${formatMetric(debug.quality?.score)}`,
      `spotcheck ${debug.landmark_spotcheck?.passed === false ? "fail" : "ok"}`,
      `spoof ${formatMetric(debug.antispoof?.spoof_score)}`,
    ].join(" | ");
    if (lastDebugSummariesRef.current.signals !== signalSummary) {
      lastDebugSummariesRef.current.signals = signalSummary;
      appendLog("signals", signalSummary, debug);
    }
  }

  function queueManualAction(action: ManualAction) {
    setQueuedActions((current) => [...current, action]);
  }

  function consumeManualAction(): ManualAction | null {
    let selected: ManualAction | null = null;
    setQueuedActions((current) => {
      if (current.length === 0) return current;
      [selected] = current;
      return current.slice(1);
    });
    return selected;
  }

  function consumeLandmarkMetadata(includeTrackedSignals: boolean): Record<string, unknown> {
    const packet = latestLandmarkPacketRef.current;
    const metadata = includeTrackedSignals ? { ...(packet?.metadata ?? {}) } : {};
    const pendingSignals = pendingSignalsRef.current;

    if (pendingSignals.blinks > 0) {
      metadata.blink = true;
      pendingSignals.blinks -= 1;
    }

    if (pendingSignals.headTurn) {
      metadata.head_turn = pendingSignals.headTurn;
      pendingSignals.headTurn = null;
    }

    if (pendingSignals.pitchValues.length > 0) {
      const pitch = pendingSignals.pitchValues.shift();
      if (typeof pitch === "number") {
        metadata.pitch = pitch;
        metadata.pitch_ratio = roundMetric(pitch / 180);
      }
    }

    if (forceSpoofRef.current) {
      metadata.presentation_attack = true;
    }

    return metadata;
  }

  function manualMetadata(action: ManualAction | null): Record<string, unknown> {
    if (action === "blink") return { blink: true };
    if (action === "turn_left") return { head_turn: "left" };
    if (action === "turn_right") return { head_turn: "right" };
    if (action === "smile") return { smile: true, smile_ratio: 0.48 };
    if (action === "spoof") return { presentation_attack: true };
    return {};
  }

  function updateSessionMetricSummary(metrics: LandmarkMetrics) {
    if (!sessionRef.current || resultRef.current || !metrics.faceDetected) return;
    setSessionMetricSummary((current) => ({
      landmarksCaptured: current.landmarksCaptured + 1,
      pointCountMax: Math.max(current.pointCountMax, metrics.pointCount),
      yawMin: minNullable(current.yawMin, metrics.yaw),
      yawMax: maxNullable(current.yawMax, metrics.yaw),
      yawAbsPeak: maxNullable(
        current.yawAbsPeak,
        metrics.yaw === null ? null : Math.abs(metrics.yaw),
      ),
      pitchMin: minNullable(current.pitchMin, metrics.pitch),
      pitchMax: maxNullable(current.pitchMax, metrics.pitch),
      smileRatioMax: maxNullable(current.smileRatioMax, metrics.smileRatio),
      mouthRatioMax: maxNullable(current.mouthRatioMax, metrics.mouthRatio),
      earMin: minNullable(current.earMin, metrics.averageEar),
      earMax: maxNullable(current.earMax, metrics.averageEar),
      leftEarMin: minNullable(current.leftEarMin, metrics.leftEar),
      rightEarMin: minNullable(current.rightEarMin, metrics.rightEar),
    }));
  }

  function buildCalibrationRecord(
    terminalResult: VerificationResult | null = result,
    terminalChallengeType: ChallengeType | null = challengeType,
    terminalChallengeSequence: ChallengeType[] = challengeSequence,
    terminalProgress: number = progress,
    label: CalibrationLabel = calibrationLabel,
  ): CalibrationRecord | null {
    if (!session || !terminalResult || !terminalChallengeType) return null;
    return {
      sample_id: terminalResult.session_id,
      label,
      verification_mode: terminalResult.evaluation_mode ?? verificationMode,
      failure_reason: terminalResult.failure_reason ?? null,
      attack_type: label === "human" ? "bona_fide" : attackType,
      capture_medium: "camera",
      source_split: sourceSplit,
      challenge_type: terminalChallengeType,
      challenge_sequence: terminalChallengeSequence,
      total_challenges: terminalChallengeSequence.length,
      status: terminalResult.status,
      human: terminalResult.human,
      spoof_score: terminalResult.spoof_score,
      max_spoof_score: terminalResult.max_spoof_score ?? terminalResult.spoof_score,
      confidence: terminalResult.confidence,
      challenge_progress: terminalProgress,
      landmark_metrics: {
        point_count_max: sessionMetricSummary.pointCountMax,
        yaw_min: sessionMetricSummary.yawMin,
        yaw_max: sessionMetricSummary.yawMax,
        yaw_abs_peak: sessionMetricSummary.yawAbsPeak,
        pitch_min: sessionMetricSummary.pitchMin,
        pitch_max: sessionMetricSummary.pitchMax,
        smile_ratio_max: sessionMetricSummary.smileRatioMax,
        mouth_ratio_max: sessionMetricSummary.mouthRatioMax,
        ear_min: sessionMetricSummary.earMin,
        ear_max: sessionMetricSummary.earMax,
        left_ear_min: sessionMetricSummary.leftEarMin,
        right_ear_min: sessionMetricSummary.rightEarMin,
        landmarks_captured: sessionMetricSummary.landmarksCaptured,
      },
      model_strategy: "pretrained-calibration-only",
      source: "webcam-harness",
      notes: calibrationNotes,
    };
  }

  async function autoSaveSessionRecords(
    calibrationRecord: CalibrationRecord | null,
  ) {
    if (!calibrationRecord) {
      setCalibrationMessage("No completed session available to auto-save.");
      return;
    }

    const endpoints = [
      { key: "calibration", url: `${httpBase}/api/calibration/append` },
      { key: "attack_matrix", url: `${httpBase}/api/attack-matrix/append` },
    ] as const;

    const results = await Promise.allSettled(
      endpoints.map(async (endpoint) => {
        const response = await fetch(endpoint.url, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ record: calibrationRecord }),
        });

        if (!response.ok) {
          const payload = await response.json().catch(() => ({ detail: "Unknown error" }));
          throw new Error(payload.detail ?? `Could not auto-save ${endpoint.key} row.`);
        }

        const payload = (await response.json()) as {
          saved: boolean;
          sample_id?: string;
          output_path: string;
        };
        appendLog("pipeline", `${endpoint.key} row auto-saved`, payload);
        return { endpoint: endpoint.key, payload };
      }),
    );

    const successes = results.filter((item) => item.status === "fulfilled");
    const failures = results.filter((item) => item.status === "rejected");

    if (successes.length === endpoints.length) {
      const outputPaths = successes
        .map((item) => item.value.payload.output_path)
        .join(" and ");
      setCalibrationMessage(`Rows auto-saved to ${outputPaths}.`);
      return;
    }

    const messages = failures.map((item) =>
      item.status === "rejected" && item.reason instanceof Error
        ? item.reason.message
        : "Unknown auto-save error.",
    );
    setCalibrationMessage(messages.join(" | "));
    appendLog("pipeline", "Auto-save failed", { messages, calibrationRecord });
  }

  async function copyCalibrationRow() {
    const calibrationRecord = buildCalibrationRecord();
    if (!calibrationRecord) {
      setCalibrationMessage("No completed session available to export.");
      return;
    }
    const row = `${JSON.stringify(calibrationRecord)}\n`;
    try {
      await navigator.clipboard.writeText(row);
      setCalibrationMessage("Calibration NDJSON row copied to clipboard.");
      appendLog("pipeline", "Calibration row copied", calibrationRecord);
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Could not copy calibration row.";
      setCalibrationMessage(message);
      appendLog("pipeline", "Calibration copy failed", { message });
    }
  }

  function downloadCalibrationRow() {
    const calibrationRecord = buildCalibrationRecord();
    if (!calibrationRecord) {
      setCalibrationMessage("No completed session available to export.");
      return;
    }
    const row = `${JSON.stringify(calibrationRecord)}\n`;
    const blob = new Blob([row], { type: "application/x-ndjson;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `${calibrationRecord.sample_id}.ndjson`;
    anchor.click();
    URL.revokeObjectURL(url);
    setCalibrationMessage("Calibration NDJSON row downloaded.");
    appendLog("pipeline", "Calibration row downloaded", calibrationRecord);
  }

  async function requestCamera() {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          width: { ideal: 960 },
          height: { ideal: 720 },
          facingMode: "user",
        },
        audio: false,
      });
      mediaStreamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play();
      }
      setCameraState("ready");
      setCameraMessage("Webcam ready.");
      appendLog("detection", "Webcam stream attached");
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Could not open webcam.";
      setCameraState("error");
      setCameraMessage(message);
      appendLog("detection", "Camera error", { message });
    }
  }

  async function fetchHealth() {
    try {
      const response = await fetch(`${httpBase}/api/health`, {
        cache: "no-store",
      });
      const payload = (await response.json()) as HealthResponse;
      setHealth(payload);
      appendLog("pipeline", "Backend health fetched", payload);
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Health check failed.";
      appendLog("pipeline", "Health check failed", { message });
    }
  }

  function cleanupSocket() {
    if (captureTimerRef.current !== null) {
      window.clearInterval(captureTimerRef.current);
      captureTimerRef.current = null;
    }
    if (finalizeTimerRef.current !== null) {
      window.clearTimeout(finalizeTimerRef.current);
      finalizeTimerRef.current = null;
    }
    if (socketRef.current) {
      socketRef.current.close();
      socketRef.current = null;
    }
    finalizeRequestedRef.current = false;
    setFinalizeRequested(false);
    frameCounterRef.current = 0;
  }

  function processLandmarks(result: FaceLandmarkerResult) {
    const firstFace = result.faceLandmarks[0];
    if (!firstFace) {
      latestFaceRef.current = null;
      latestLandmarkPacketRef.current = null;
      lastEyesClosedRef.current = false;
      setLandmarkMetrics({
        ...emptyLandmarkMetrics(),
        timestamp: new Date().toISOString(),
      });
      setLandmarkMessage("No face landmarks detected yet.");
      return;
    }

    latestFaceRef.current = firstFace;
    const previewMetrics = extractFaceMetrics(firstFace, false);
    const eyesClosed =
      typeof previewMetrics.averageEar === "number" &&
      previewMetrics.averageEar < eyeClosedThreshold;
    let blinkDetected = false;

    if (!lastEyesClosedRef.current && eyesClosed) {
      pendingSignalsRef.current.blinks += 1;
      blinkDetected = true;
    }
    if (
      lastEyesClosedRef.current &&
      previewMetrics.averageEar !== null &&
      previewMetrics.averageEar > eyeOpenThreshold
    ) {
      lastEyesClosedRef.current = false;
    } else if (eyesClosed) {
      lastEyesClosedRef.current = true;
    }

    const metrics = extractFaceMetrics(firstFace, blinkDetected);
    if (metrics.headTurn === "left" || metrics.headTurn === "right") {
      pendingSignalsRef.current.headTurn = metrics.headTurn;
    }

    latestLandmarkPacketRef.current = buildLandmarkPacket(firstFace, metrics);
    setLandmarkMetrics(metrics);
    updateSessionMetricSummary(metrics);
    setLandmarkMessage(`Landmarks ready (${metrics.pointCount} points).`);
  }

  function runLandmarkPass() {
    const landmarker = faceLandmarkerRef.current;
    const video = videoRef.current;
    if (!landmarker || !video || video.readyState < HTMLMediaElement.HAVE_CURRENT_DATA) {
      return;
    }
    if (!video.videoWidth || !video.videoHeight) {
      return;
    }

    try {
      const result = landmarker.detectForVideo(video, performance.now());
      processLandmarks(result);
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Landmark capture failed.";
      if (
        message.includes("XNNPACK") ||
        message.includes("delegate") ||
        message.includes("ROI") ||
        message.includes("timestamp")
      ) {
        appendLog("detection", "Landmark pass skipped", { message });
        return;
      }
      setLandmarkMessage(message);
      appendLog("detection", "Landmark error", { message });
    }
  }

  function drawOverlay() {
    const video = videoRef.current;
    const canvas = overlayCanvasRef.current;
    if (!video || !canvas) return;

    const width = video.videoWidth || video.clientWidth || 640;
    const height = video.videoHeight || video.clientHeight || 480;
    canvas.width = width;
    canvas.height = height;

    const context = canvas.getContext("2d");
    if (!context) return;

    context.clearRect(0, 0, width, height);
    const tone = overlayTone(landmarkMetrics, backendDebug, stepStatus);

    const guideX = width * 0.18;
    const guideY = height * 0.12;
    const guideWidth = width * 0.64;
    const guideHeight = height * 0.76;

    context.strokeStyle = tone;
    context.lineWidth = 2;
    context.setLineDash([10, 6]);
    context.strokeRect(guideX, guideY, guideWidth, guideHeight);
    context.setLineDash([]);

    const face = latestFaceRef.current;
    if (face) {
      context.strokeStyle = tone;
      context.fillStyle = tone;
      context.lineWidth = 1.5;
      context.globalAlpha = 0.88;

      for (const [fromIndex, toIndex] of overlayConnections) {
        const from = face[fromIndex];
        const to = face[toIndex];
        if (!from || !to) continue;
        context.beginPath();
        context.moveTo(from.x * width, from.y * height);
        context.lineTo(to.x * width, to.y * height);
        context.stroke();
      }

      for (const pointIndex of overlayPointIndices) {
        const point = face[pointIndex];
        if (!point) continue;
        context.beginPath();
        context.arc(point.x * width, point.y * height, 2.2, 0, Math.PI * 2);
        context.fill();
      }
      context.globalAlpha = 1;
    }

    const backendBox = backendDebug?.face_detection?.bounding_box;
    if (backendBox) {
      const scaleX = backendBox.width <= 1 && backendBox.x <= 1 ? width : 1;
      const scaleY = backendBox.height <= 1 && backendBox.y <= 1 ? height : 1;
      context.strokeStyle = "#ffffff";
      context.lineWidth = 2;
      context.strokeRect(
        backendBox.x * scaleX,
        backendBox.y * scaleY,
        backendBox.width * scaleX,
        backendBox.height * scaleY,
      );
    }
  }

  function captureFrame() {
    const video = videoRef.current;
    const canvas = captureCanvasRef.current;
    if (!video || !canvas || socketRef.current?.readyState !== WebSocket.OPEN) {
      return;
    }

    const width = video.videoWidth || 640;
    const height = video.videoHeight || 480;
    canvas.width = width;
    canvas.height = height;

    const context = canvas.getContext("2d");
    if (!context) return;
    context.drawImage(video, 0, 0, width, height);

    frameCounterRef.current += 1;
    const frameNumber = frameCounterRef.current;
    const action = consumeManualAction();
    if (action === "nod_head") {
      pendingSignalsRef.current.pitchValues.push(14, -14);
    }

    const metadata = {
      ...consumeLandmarkMetadata(autoAssistRef.current),
      ...manualMetadata(action),
      frame_number: frameNumber,
      frame_width: width,
      frame_height: height,
    };

    const imageBase64 = canvas.toDataURL("image/jpeg", 0.75).split(",")[1] ?? "";
    socketRef.current.send(
      JSON.stringify({
        type: "frame",
        timestamp: new Date().toISOString(),
        image_base64: imageBase64,
        metadata,
      }),
    );

    const packet = latestLandmarkPacketRef.current;
    if (packet) {
      socketRef.current.send(
        JSON.stringify({
          type: "landmarks",
          timestamp: new Date().toISOString(),
          landmarks: packet.landmarks,
          metadata: {
            ...packet.metadata,
            ...metadata,
            frame_number: frameNumber,
            frame_width: width,
            frame_height: height,
          },
        }),
      );
    }

    if (action) {
      appendLog("pipeline", `Manual action queued: ${action.replace("_", " ")}`, metadata);
    }
  }

  function sendFinalize() {
    if (!socketRef.current || socketRef.current.readyState !== WebSocket.OPEN) {
      setStatusMessage("Finalize unavailable: session socket is not open.");
      appendLog("pipeline", "Finalize blocked", {
        connection_state: connectionState,
        has_socket: Boolean(socketRef.current),
      });
      return;
    }
    finalizeRequestedRef.current = true;
    setFinalizeRequested(true);
    socketRef.current.send(
      JSON.stringify({
        type: "finalize",
        timestamp: new Date().toISOString(),
        mode: verificationMode,
      }),
    );
    appendLog("pipeline", "Finalize requested", { mode: verificationMode });
  }

  function handleProgressLikePayload(
    payload: {
      challenge_type: ChallengeType;
      challenge_sequence: ChallengeType[];
      current_challenge_index?: number;
      completed_challenges?: ChallengeType[];
      step_status?: StepStatus;
      progress?: number;
      message?: string;
      debug?: VerificationDebugPayload | null;
    },
  ) {
    const normalizedSequence = normalizeChallengeSequence(
      payload.challenge_sequence,
      payload.challenge_type,
    );
    const normalizedCompleted = normalizeCompletedChallenges(
      payload.completed_challenges,
    );
    setChallengeType(payload.challenge_type);
    setChallengeSequence(normalizedSequence);
    setCurrentChallengeIndex(payload.current_challenge_index ?? 0);
    setCompletedChallenges(normalizedCompleted);
    if (payload.step_status) setStepStatus(payload.step_status);
    if ("progress" in payload && typeof payload.progress === "number") setProgress(payload.progress);
    if ("message" in payload && typeof payload.message === "string") setStatusMessage(payload.message);
    if ("debug" in payload) {
      setBackendDebug(payload.debug ?? null);
    }
  }

  async function startSession() {
    cleanupSocket();
    setBusy(true);
    setResult(null);
    setProgress(0);
    setBackendDebug(null);
    setChallengeSequence([]);
    setCompletedChallenges([]);
    setCurrentChallengeIndex(0);
    setStepStatus("pending");
    setFinalizeRequested(false);
    lastAutoSavedSessionIdRef.current = null;
    setSessionMetricSummary(emptySessionMetricSummary());
    setCalibrationMessage("Complete a session to export a calibration row.");
    setStatusMessage("Creating session...");
    setLogs(emptyLogs());
    lastDebugSummariesRef.current = { detection: null, signals: null };

    try {
      const response = await fetch(`${httpBase}/api/sessions`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          wallet_address: walletAddress,
          client: {
            platform: "web",
            user_agent: navigator.userAgent,
          },
        }),
      });

      if (!response.ok) {
        const payload = await response.json().catch(() => ({ detail: "Unknown error" }));
        throw new Error(payload.detail ?? "Could not create session");
      }

      const created = (await response.json()) as CreateSessionResponse;
      const normalizedSequence = normalizeChallengeSequence(
        created.challenge_sequence,
        created.challenge_type,
      );
      setSession(created);
      setChallengeType(created.challenge_type);
      setChallengeSequence(normalizedSequence);
      setCurrentChallengeIndex(created.current_challenge_index ?? 0);
      setCompletedChallenges(normalizeCompletedChallenges(created.completed_challenges));
      setStepStatus("pending");
      setStatusMessage(
        `Sequence ready: ${normalizedSequence.map(challengeLabel).join(" -> ") || challengeLabel(created.challenge_type)}`,
      );
      setConnectionState("connecting");
      appendLog("pipeline", "Session created", created);

      const websocket = new WebSocket(`${wsBase}/ws/verify/${created.session_id}`);
      socketRef.current = websocket;

      websocket.onopen = () => {
        setConnectionState("open");
        appendLog("pipeline", "WebSocket open", { session_id: created.session_id });
        captureTimerRef.current = window.setInterval(captureFrame, captureIntervalMs);
      };

      websocket.onmessage = (event) => {
        const message = JSON.parse(event.data) as WsServerEvent;

        if (message.type === "session_ready") {
          setStatusMessage(message.payload.message);
          appendLog("pipeline", "Session ready", message.payload);
          return;
        }

        if (message.type === "challenge_update" || message.type === "progress") {
          handleProgressLikePayload(message.payload);
          if (message.type === "challenge_update") {
            appendLog(
              "pipeline",
              summarizeProgressDebug(
                message.payload.challenge_type,
                normalizeChallengeSequence(
                  message.payload.challenge_sequence,
                  message.payload.challenge_type,
                ),
                message.payload.current_challenge_index,
                message.payload.step_status,
                message.payload.message,
              ),
              message.payload,
            );
          }

          if (message.payload.debug) {
            appendDebugLogs(message.payload.debug);
          }

          if (
            autoAssistRef.current &&
            message.payload.step_status === "completed" &&
            message.payload.progress >= 1 &&
            !finalizeRequestedRef.current
          ) {
            if (finalizeTimerRef.current !== null) {
              window.clearTimeout(finalizeTimerRef.current);
            }
            finalizeTimerRef.current = window.setTimeout(() => {
              finalizeTimerRef.current = null;
              sendFinalize();
            }, autoFinalizeDelayMs);
          }
          return;
        }

        if (message.type === "processing") {
          setStatusMessage(message.payload.message);
          appendLog("pipeline", "Processing", message.payload);
          return;
        }

        if (message.type === "verified" || message.type === "failed") {
          const terminalLabel: CalibrationLabel = message.payload.human ? "human" : "spoof";
          const terminalAttackType =
            terminalLabel === "human"
              ? "bona_fide"
              : attackType === "bona_fide"
              ? "unknown_spoof"
              : attackType;
          setResult(message.payload);
          setCalibrationLabel(terminalLabel);
          setAttackType(terminalAttackType);
          handleProgressLikePayload(message.payload);
          const resultMode = message.payload.evaluation_mode ?? verificationMode;
          setStatusMessage(
            message.type === "verified"
              ? `${verificationModeLabels[resultMode]} passed.`
              : `${verificationModeLabels[resultMode]} failed: ${message.payload.failure_reason ?? "unknown"}`,
          );
          appendLog(
            "pipeline",
            message.type === "verified" ? "Terminal result: verified" : "Terminal result: failed",
            message.payload,
          );
          appendLog(
            "signals",
            `Anti-spoof ${message.payload.spoof_score.toFixed(2)} / max ${message.payload.max_spoof_score?.toFixed(2) ?? "n/a"}`,
            message.payload,
          );
          cleanupSocket();
          return;
        }

        if (message.type === "error") {
          setStatusMessage(message.payload.message);
          appendLog("pipeline", "Socket error", message.payload);
          cleanupSocket();
        }
      };

      websocket.onerror = () => {
        setConnectionState("error");
        setStatusMessage("WebSocket error");
        appendLog("pipeline", "WebSocket error");
      };

      websocket.onclose = () => {
        setConnectionState("closed");
      };
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Session creation failed.";
      setStatusMessage(message);
      appendLog("pipeline", "Session creation failed", { message });
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    autoAssistRef.current = autoAssist;
  }, [autoAssist]);

  useEffect(() => {
    forceSpoofRef.current = forceSpoof;
  }, [forceSpoof]);

  useEffect(() => {
    void requestCamera();
    void fetchHealth();

    return () => {
      cleanupSocket();
      if (landmarkTimerRef.current !== null) {
        window.clearInterval(landmarkTimerRef.current);
        landmarkTimerRef.current = null;
      }
      faceLandmarkerRef.current?.close();
      faceLandmarkerRef.current = null;
      mediaStreamRef.current?.getTracks().forEach((track) => track.stop());
      mediaStreamRef.current = null;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;

    async function loadLandmarker() {
      try {
        setLandmarkState("loading");
        setLandmarkMessage("Loading MediaPipe Face Landmarker...");
        const vision = await import("@mediapipe/tasks-vision");
        const filesetResolver = await vision.FilesetResolver.forVisionTasks(
          mediapipeWasmUrl,
        );
        const faceLandmarker = await vision.FaceLandmarker.createFromOptions(
          filesetResolver,
          {
            baseOptions: {
              modelAssetPath: faceLandmarkerModelUrl,
            },
            runningMode: "VIDEO",
            numFaces: 1,
            outputFaceBlendshapes: false,
            outputFacialTransformationMatrixes: false,
          },
        );

        if (cancelled) {
          faceLandmarker.close();
          return;
        }

        faceLandmarkerRef.current = faceLandmarker;
        setLandmarkState("ready");
        setLandmarkMessage("MediaPipe Face Landmarker ready.");
        appendLog("detection", "Landmarker ready", { model: faceLandmarkerModelUrl });
      } catch (error) {
        const message =
          error instanceof Error ? error.message : "Could not load MediaPipe Face Landmarker.";
        setLandmarkState("error");
        setLandmarkMessage(message);
        appendLog("detection", "Landmarker error", { message });
      }
    }

    void loadLandmarker();

    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (cameraState !== "ready" || landmarkState !== "ready") {
      if (landmarkTimerRef.current !== null) {
        window.clearInterval(landmarkTimerRef.current);
        landmarkTimerRef.current = null;
      }
      return;
    }

    runLandmarkPass();
    landmarkTimerRef.current = window.setInterval(runLandmarkPass, landmarkIntervalMs);

    return () => {
      if (landmarkTimerRef.current !== null) {
        window.clearInterval(landmarkTimerRef.current);
        landmarkTimerRef.current = null;
      }
    };
  }, [cameraState, landmarkState]);

  useEffect(() => {
    if (!result || !session) return;
    if (lastAutoSavedSessionIdRef.current === result.session_id) return;

    const terminalLabel: CalibrationLabel = result.human ? "human" : "spoof";
    const terminalAttackType =
      terminalLabel === "human"
        ? "bona_fide"
        : attackType === "bona_fide"
        ? "unknown_spoof"
        : attackType;
    const terminalRecord = buildCalibrationRecord(
      result,
      result.challenge_type,
      normalizeChallengeSequence(result.challenge_sequence, result.challenge_type),
      result.status === "verified" ? 1 : progress,
      terminalLabel,
    );

    lastAutoSavedSessionIdRef.current = result.session_id;
    void autoSaveSessionRecords(
      terminalRecord
        ? {
            ...terminalRecord,
            attack_type: terminalAttackType,
          }
        : null,
    );
  }, [result, session, progress, attackType, sourceSplit, calibrationNotes, sessionMetricSummary]);

  useEffect(() => {
    drawOverlay();
  }, [landmarkMetrics, backendDebug, stepStatus]);

  const calibrationRecord = buildCalibrationRecord();
  const safeChallengeSequence = Array.isArray(challengeSequence) ? challengeSequence : [];
  const safeCompletedChallenges = Array.isArray(completedChallenges)
    ? completedChallenges
    : [];
  const backendTuning = health?.tuning;
  const canFinalize = Boolean(session) && !finalizeRequested && !result;
  const serverQualityFeedback =
    backendDebug?.quality?.feedback && backendDebug.quality.feedback.length > 0
      ? backendDebug.quality.feedback.join(" | ")
      : "No quality guidance yet.";
  const serverAntiSpoofScore = result?.spoof_score ?? backendDebug?.antispoof?.spoof_score;
  const serverAntiSpoofMax =
    result?.max_spoof_score ??
    result?.spoof_score ??
    backendDebug?.antispoof?.max_spoof_score ??
    backendDebug?.antispoof?.spoof_score;
  const serverAntiSpoofMessage = backendDebug?.antispoof?.message ?? "No anti-spoof guidance yet.";
  const serverSpotcheckStatus = backendDebug?.landmark_spotcheck?.enforced
    ? backendDebug?.landmark_spotcheck?.passed
      ? "passed"
      : "blocked"
    : "not_enforced";
  const serverSpotcheckMismatch = backendDebug?.landmark_spotcheck?.mismatch_pixels;
  const serverSpotcheckThreshold = backendDebug?.landmark_spotcheck?.threshold_pixels;
  const serverSpotcheckMessage =
    backendDebug?.landmark_spotcheck?.message ?? "Landmark spot-check unavailable.";
  const serverFailureReason =
    result?.status === "failed"
      ? result.failure_reason ?? "unknown_failure"
      : result?.status === "verified"
      ? "none"
      : "No terminal verdict yet.";
  const browserTuning = {
    capture_interval_ms: captureIntervalMs,
    landmark_interval_ms: landmarkIntervalMs,
    yaw_turn_threshold: yawTurnThreshold,
    smile_ratio_threshold: smileRatioThreshold,
    auto_finalize_delay_ms: autoFinalizeDelayMs,
  };

  return (
    <main className="page-shell">
      <section className="panel hero-panel">
        <div>
          <p className="eyebrow">SUI HUMAN / ADMIN CONSOLE</p>
          <h1>Verifier testing and QA console</h1>
          <p className="lede">
            Internal console for threshold tuning, attack simulation, and verifier
            QA. Use the mode selector to run the backend in full, liveness-only,
            or anti-spoof-only finalize behavior.
          </p>
        </div>
        <div className="meta-grid">
          <div>
            <span>backend</span>
            <strong>{httpBase}</strong>
          </div>
          <div>
            <span>camera</span>
            <strong>{cameraState}</strong>
          </div>
          <div>
            <span>landmarks</span>
            <strong>{landmarkState}</strong>
          </div>
          <div>
            <span>websocket</span>
            <strong>{connectionState}</strong>
          </div>
          <div>
            <span>current step</span>
            <strong>{challengeType ? challengeLabel(challengeType) : "pending"}</strong>
          </div>
          <div>
            <span>qa mode</span>
            <strong>{verificationModeLabels[verificationMode]}</strong>
          </div>
        </div>
      </section>

      <section className="grid">
        <div className="panel camera-panel">
          <div className="panel-header">
            <h2>Webcam Overlay</h2>
            <p>{cameraMessage}</p>
          </div>
          <div className="video-shell">
            <video ref={videoRef} className="video" playsInline muted />
            <canvas ref={overlayCanvasRef} className="overlay-canvas" />
          </div>
          <canvas ref={captureCanvasRef} className="hidden-canvas" />
          <div className="telemetry-card">
            <div>
              <span>landmark engine</span>
              <strong>{landmarkMessage}</strong>
            </div>
            <div className="signal-grid">
              <div>
                <span>points</span>
                <strong>{landmarkMetrics.pointCount}</strong>
              </div>
              <div>
                <span>yaw</span>
                <strong>{landmarkMetrics.yaw ?? "n/a"}</strong>
              </div>
              <div>
                <span>pitch</span>
                <strong>{landmarkMetrics.pitch ?? "n/a"}</strong>
              </div>
              <div>
                <span>smile</span>
                <strong>{landmarkMetrics.smileRatio ?? "n/a"}</strong>
              </div>
              <div>
                <span>avg ear</span>
                <strong>{landmarkMetrics.averageEar ?? "n/a"}</strong>
              </div>
              <div>
                <span>backend face</span>
                <strong>{backendDebug?.face_detection?.detected ? "locked" : "searching"}</strong>
              </div>
              <div>
                <span>quality</span>
                <strong>{backendDebug?.quality?.passed ? "ok" : backendDebug?.quality?.primary_issue ?? "n/a"}</strong>
              </div>
            </div>
          </div>
        </div>

        <div className="panel control-panel">
          <div className="panel-header">
            <h2>Session Controls</h2>
            <p>{challengeHint(challengeType)}</p>
          </div>

          <label className="field">
            <span>wallet address</span>
            <input
              value={walletAddress}
              onChange={(event) => setWalletAddress(event.target.value)}
            />
          </label>

          <label className="field">
            <span>qa mode</span>
            <select
              value={verificationMode}
              onChange={(event) => setVerificationMode(event.target.value as VerificationMode)}
            >
              <option value="full">full</option>
              <option value="liveness_only">liveness_only</option>
              <option value="antispoof_only">antispoof_only</option>
            </select>
            <small className="field-hint">
              {verificationMode === "full"
                ? "Requires both liveness and anti-spoof to pass."
                : verificationMode === "liveness_only"
                ? "Finalize judges only the liveness path; anti-spoof stays informational."
                : "Finalize judges only the anti-spoof path; incomplete challenges do not fail the session."}
            </small>
          </label>

          <div className="sequence-card">
            <span>challenge sequence</span>
            <ol className="sequence-list">
              {safeChallengeSequence.length === 0 ? (
                <li className="sequence-item is-upcoming">Start a session to load the sequence.</li>
              ) : (
                safeChallengeSequence.map((step, index) => {
                  const completed = safeCompletedChallenges.includes(step) && index < currentChallengeIndex + 1;
                  const current = index === currentChallengeIndex && stepStatus !== "completed";
                  const className = completed
                    ? "sequence-item is-completed"
                    : current
                    ? "sequence-item is-current"
                    : stepStatus === "completed" && index === currentChallengeIndex
                    ? "sequence-item is-completed"
                    : "sequence-item is-upcoming";
                  return (
                    <li className={className} key={`${step}-${index}`}>
                      <strong>{index + 1}.</strong> {challengeLabel(step)}
                    </li>
                  );
                })
              )}
            </ol>
          </div>

          <div className="toggle-row">
            <label>
              <input
                checked={autoAssist}
                onChange={(event) => setAutoAssist(event.target.checked)}
                type="checkbox"
              />
              landmark assist
            </label>
            <label>
              <input
                checked={forceSpoof}
                onChange={(event) => setForceSpoof(event.target.checked)}
                type="checkbox"
              />
              force spoof
            </label>
          </div>

          <div className="button-row">
            <button disabled={busy || cameraState !== "ready"} onClick={() => void startSession()}>
              {busy ? "Starting..." : "Start session"}
            </button>
            <button
              disabled={!canFinalize}
              onClick={sendFinalize}
              type="button"
            >
              {finalizeRequested ? "Finalizing..." : "Finalize"}
            </button>
          </div>

          <div className="button-grid">
            <button onClick={() => queueManualAction("blink")} type="button">
              Trigger blink
            </button>
            <button onClick={() => queueManualAction("turn_left")} type="button">
              Trigger left
            </button>
            <button onClick={() => queueManualAction("turn_right")} type="button">
              Trigger right
            </button>
            <button onClick={() => queueManualAction("nod_head")} type="button">
              Trigger nod
            </button>
            <button onClick={() => queueManualAction("smile")} type="button">
              Trigger smile
            </button>
            <button onClick={() => queueManualAction("spoof")} type="button">
              Trigger spoof
            </button>
          </div>

          <div className="status-box">
            <div>
              <span>status</span>
              <strong>{statusMessage}</strong>
            </div>
            <div>
              <span>step status</span>
              <strong>{stepStatus}</strong>
            </div>
            <div>
              <span>progress</span>
              <strong>{Math.round(progress * 100)}%</strong>
            </div>
            <div>
              <span>session</span>
              <strong>{session?.session_id ?? "none"}</strong>
            </div>
            <div>
              <span>result mode</span>
              <strong>{result?.evaluation_mode ?? verificationMode}</strong>
            </div>
          </div>
        </div>
      </section>

      <section className="grid">
        <div className="panel">
          <div className="panel-header">
            <h2>Backend Health</h2>
            <p>Quick view of the local verifier service.</p>
          </div>
          {health ? (
            <div className="status-box">
              <div>
                <span>status</span>
                <strong>{health.status}</strong>
              </div>
              <div>
                <span>redis</span>
                <strong>{health.redis}</strong>
              </div>
              <div>
                <span>models</span>
                <strong>{health.models}</strong>
              </div>
              <div>
                <span>chain</span>
                <strong>{health.chain_adapter}</strong>
              </div>
              <div>
                <span>storage</span>
                <strong>{health.storage_adapter}</strong>
              </div>
              <div>
                <span>encryption</span>
                <strong>{health.encryption_adapter}</strong>
              </div>
            </div>
          ) : (
            <p>Waiting for health response...</p>
          )}
        </div>

        <div className="panel">
          <div className="panel-header">
            <h2>Server Checks</h2>
            <p>Live backend decisions for face detection, quality, liveness, and the terminal verdict.</p>
          </div>
          <div className="status-box">
            <div>
              <span>face gate</span>
              <strong>{backendDebug?.face_detection?.detected ? "detected" : "missing"}</strong>
            </div>
            <div>
              <span>face confidence</span>
              <strong>{formatMetric(backendDebug?.face_detection?.confidence)}</strong>
            </div>
            <div>
              <span>quality gate</span>
              <strong>{backendDebug?.quality?.passed ? "passed" : "blocked"}</strong>
            </div>
            <div>
              <span>quality issue</span>
              <strong>{backendDebug?.quality?.primary_issue ?? "none"}</strong>
            </div>
            <div>
              <span>quality score</span>
              <strong>{formatMetric(backendDebug?.quality?.score)}</strong>
            </div>
            <div>
              <span>liveness step</span>
              <strong>{backendDebug?.liveness?.current_step ? challengeLabel(backendDebug.liveness.current_step) : "pending"}</strong>
            </div>
            <div>
              <span>step progress</span>
              <strong>{formatPercent(backendDebug?.liveness?.step_progress)}</strong>
            </div>
            <div>
              <span>spot-check</span>
              <strong>{serverSpotcheckStatus}</strong>
            </div>
            <div>
              <span>spot mismatch</span>
              <strong>{formatMetric(serverSpotcheckMismatch)}</strong>
            </div>
            <div>
              <span>anti-spoof</span>
              <strong>{formatMetric(serverAntiSpoofScore)}</strong>
            </div>
            <div>
              <span>anti-spoof max</span>
              <strong>{formatMetric(serverAntiSpoofMax)}</strong>
            </div>
            <div>
              <span>terminal verdict</span>
              <strong>{result?.status ?? "streaming"}</strong>
            </div>
          </div>
          <div className="server-note">
            <span>quality feedback</span>
            <strong>{serverQualityFeedback}</strong>
          </div>
          <div className="server-note">
            <span>failure reason</span>
            <strong>{serverFailureReason}</strong>
          </div>
          <div className="server-note">
            <span>spot-check note</span>
            <strong>
              {serverSpotcheckMessage}
              {typeof serverSpotcheckThreshold === "number"
                ? ` (threshold ${serverSpotcheckThreshold.toFixed(2)} px)`
                : ""}
            </strong>
          </div>
          <div className="server-note">
            <span>anti-spoof note</span>
            <strong>
              {serverAntiSpoofMessage}
              {backendDebug?.antispoof?.preview ? " (live preview)" : ""}
            </strong>
          </div>
        </div>

        <div className="panel">
          <div className="panel-header">
            <h2>Tuning Snapshot</h2>
            <p>Current browser assist defaults and backend liveness thresholds.</p>
          </div>
          <div className="tuning-grid">
            <div className="tuning-card">
              <span>browser assist</span>
              <pre className="json-block">{JSON.stringify(browserTuning, null, 2)}</pre>
            </div>
            <div className="tuning-card">
              <span>backend liveness</span>
              <pre className="json-block">
                {backendTuning
                  ? JSON.stringify(backendTuning, null, 2)
                  : "Waiting for health tuning..."}
              </pre>
            </div>
          </div>
        </div>

        <div className="panel">
          <div className="panel-header">
            <h2>Landmark Telemetry</h2>
            <p>Latest browser-side metrics and the backend debug payload.</p>
          </div>
          <pre className="json-block">
            {JSON.stringify(
              {
                browser: landmarkMetrics,
                backend: backendDebug,
              },
              null,
              2,
            )}
          </pre>
        </div>
      </section>

      <section className="grid">
        <div className="panel">
          <div className="panel-header">
            <h2>Latest Result</h2>
            <p>Terminal event from the verifier.</p>
          </div>
          <pre className="json-block">
            {result ? JSON.stringify(result, null, 2) : "No terminal result yet."}
          </pre>
        </div>

        <div className="panel">
          <div className="panel-header">
            <h2>Calibration Export</h2>
            <p>Save completed sessions as NDJSON rows for threshold tuning and QA.</p>
          </div>

          <label className="field">
            <span>label</span>
            <select
              value={calibrationLabel}
              onChange={(event) => {
                const nextLabel = event.target.value as CalibrationLabel;
                setCalibrationLabel(nextLabel);
                setAttackType(nextLabel === "human" ? "bona_fide" : "unknown_spoof");
              }}
            >
              <option value="human">human</option>
              <option value="spoof">spoof</option>
            </select>
          </label>

          <label className="field">
            <span>attack type</span>
            <select
              value={attackType}
              onChange={(event) => setAttackType(event.target.value as AttackType)}
            >
              <option value="bona_fide">bona_fide</option>
              <option value="print">print</option>
              <option value="screen_replay">screen_replay</option>
              <option value="prerecorded_video">prerecorded_video</option>
              <option value="virtual_camera">virtual_camera</option>
              <option value="ai_image">ai_image</option>
              <option value="ai_video">ai_video</option>
              <option value="face_swap_replay">face_swap_replay</option>
              <option value="unknown_spoof">unknown_spoof</option>
            </select>
          </label>

          <label className="field">
            <span>source split</span>
            <select
              value={sourceSplit}
              onChange={(event) => setSourceSplit(event.target.value as SourceSplit)}
            >
              <option value="train_calibration">train_calibration</option>
              <option value="dev">dev</option>
              <option value="holdout">holdout</option>
            </select>
          </label>

          <label className="field">
            <span>notes</span>
            <textarea
              value={calibrationNotes}
              onChange={(event) => setCalibrationNotes(event.target.value)}
              placeholder="lighting, webcam, attack type, environment"
            />
          </label>

          <div className="button-row">
            <button onClick={() => void copyCalibrationRow()} type="button">
              Copy NDJSON row
            </button>
            <button onClick={downloadCalibrationRow} type="button">
              Download NDJSON row
            </button>
          </div>

          <div className="status-box">
            <div>
              <span>export status</span>
              <strong>{calibrationMessage}</strong>
            </div>
            <div>
              <span>strategy</span>
              <strong>pretrained + calibration</strong>
            </div>
          </div>

          <pre className="json-block">
            {calibrationRecord
              ? JSON.stringify(calibrationRecord, null, 2)
              : "Complete a session to preview a calibration row."}
          </pre>
        </div>
      </section>

      <section className="grid">
        {(["pipeline", "detection", "signals"] as const).map((section) => (
          <div className="panel" key={section}>
            <div className="panel-header">
              <h2>{sectionLabels[section]}</h2>
              <p>Newest 20 entries. Summary first, raw JSON underneath.</p>
            </div>
            <ul className="log-list">
              {logs[section].length === 0 ? (
                <li>
                  <strong>No entries yet.</strong>
                  <span>Start a session to populate this panel.</span>
                </li>
              ) : (
                logs[section].map((entry) => (
                  <li key={entry.id}>
                    <strong>{entry.summary}</strong>
                    <details className="log-details">
                      <summary>Raw JSON</summary>
                      <pre className="log-json">{entry.detail}</pre>
                    </details>
                  </li>
                ))
              )}
            </ul>
          </div>
        ))}
      </section>
    </main>
  );
}
