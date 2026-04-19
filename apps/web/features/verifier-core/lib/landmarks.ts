"use client";

import type { StepStatus, VerificationDebugPayload } from "@sui-human/shared";
import {
  eyeClosedThreshold,
  landmarkIndices,
  overlayConnections,
  overlayPointIndices,
  smileRatioThreshold,
  yawTurnThreshold,
} from "./constants";
import type {
  BrowserLandmark,
  BrowserLandmarkResult,
  LandmarkMetrics,
  LandmarkPacket,
  PendingSignalState,
} from "./types";
import { roundMetric } from "./utils";

function distance(a: BrowserLandmark, b: BrowserLandmark): number {
  return Math.hypot(a.x - b.x, a.y - b.y);
}

function calculateEar(
  p1: BrowserLandmark,
  p2: BrowserLandmark,
  p3: BrowserLandmark,
  p4: BrowserLandmark,
  p5: BrowserLandmark,
  p6: BrowserLandmark,
): number {
  const denominator = 2 * distance(p1, p4);
  if (denominator <= 0) return 0;
  return (distance(p2, p6) + distance(p3, p5)) / denominator;
}

export function extractFaceMetrics(
  face: BrowserLandmark[],
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

export function buildLandmarkPacket(
  face: BrowserLandmark[],
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
    source: "tfjs_face_landmarks",
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
    smile:
      typeof metrics.smileRatio === "number"
        ? metrics.smileRatio >= smileRatioThreshold
        : false,
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
  if (
    typeof metrics.smileRatio === "number" &&
    metrics.smileRatio >= smileRatioThreshold
  ) {
    metadata.smile = true;
  }

  return { landmarks, metadata, metrics };
}

export function overlayTone(
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

export function processLandmarkResult(params: {
  result: BrowserLandmarkResult;
  lastEyesClosed: boolean;
  pendingSignals: PendingSignalState;
}): {
  face: BrowserLandmark[] | null;
  packet: LandmarkPacket | null;
  metrics: LandmarkMetrics | null;
  lastEyesClosed: boolean;
  message: string;
} {
  const firstFace = params.result.faceLandmarks[0];
  if (!firstFace) {
    return {
      face: null,
      packet: null,
      metrics: null,
      lastEyesClosed: false,
      message: "No face landmarks detected yet. Center your face and hold still for a moment.",
    };
  }

  const previewMetrics = extractFaceMetrics(firstFace, false);
  const eyesClosed =
    typeof previewMetrics.averageEar === "number" &&
    previewMetrics.averageEar < eyeClosedThreshold;
  let blinkDetected = false;

  if (!params.lastEyesClosed && eyesClosed) {
    params.pendingSignals.blinks += 1;
    blinkDetected = true;
  }

  let nextLastEyesClosed = params.lastEyesClosed;
  if (
    params.lastEyesClosed &&
    previewMetrics.averageEar !== null &&
    previewMetrics.averageEar > 0.24
  ) {
    nextLastEyesClosed = false;
  } else if (eyesClosed) {
    nextLastEyesClosed = true;
  }

  const metrics = extractFaceMetrics(firstFace, blinkDetected);
  if (metrics.headTurn === "left" || metrics.headTurn === "right") {
    params.pendingSignals.headTurn = metrics.headTurn;
  }

  return {
    face: firstFace,
    packet: buildLandmarkPacket(firstFace, metrics),
    metrics,
    lastEyesClosed: nextLastEyesClosed,
    message: `Landmarks ready (${metrics.pointCount} points).`,
  };
}

export function drawOverlay(params: {
  video: HTMLVideoElement | null;
  canvas: HTMLCanvasElement | null;
  face: BrowserLandmark[] | null;
  metrics: LandmarkMetrics;
  debug: VerificationDebugPayload | null;
  stepStatus: StepStatus;
}) {
  const { video, canvas, face, metrics, debug, stepStatus } = params;
  if (!video || !canvas) return;

  const width = video.videoWidth || video.clientWidth || 640;
  const height = video.videoHeight || video.clientHeight || 480;
  canvas.width = width;
  canvas.height = height;

  const context = canvas.getContext("2d");
  if (!context) return;

  context.clearRect(0, 0, width, height);
  const tone = overlayTone(metrics, debug, stepStatus);

  const guideX = width * 0.18;
  const guideY = height * 0.12;
  const guideWidth = width * 0.64;
  const guideHeight = height * 0.76;

  context.strokeStyle = tone;
  context.lineWidth = 2;
  context.setLineDash([10, 6]);
  context.strokeRect(guideX, guideY, guideWidth, guideHeight);
  context.setLineDash([]);

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

  const backendBox = debug?.face_detection?.bounding_box;
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
