"use client";

import { useEffect, useRef, useState } from "react";
import type {
  Face,
} from "@tensorflow-models/face-landmarks-detection/dist/types";
import type {
  FaceLandmarksDetector,
} from "@tensorflow-models/face-landmarks-detection/dist/face_landmarks_detector";
import {
  browserLandmarksEnabled,
} from "../_lib/constants";
import { processLandmarkResult } from "../_lib/landmarks";
import type {
  BrowserLandmark,
  BrowserLandmarkResult,
  LandmarkMetrics,
  LandmarkPacket,
  LandmarkEngineState,
  ManualAction,
  PendingSignalState,
} from "../_lib/types";
import { emptyLandmarkMetrics, roundMetric } from "../_lib/utils";

type AppendLog = (section: "pipeline" | "detection" | "signals", summary: string, detail?: unknown) => void;

export function useCameraLandmarks(params: {
  appendLog: AppendLog;
  onMetrics: (metrics: LandmarkMetrics) => void;
}) {
  type VideoWithFrameCallback = HTMLVideoElement & {
    requestVideoFrameCallback?: (
      callback: (now: number, metadata: { mediaTime?: number; presentedFrames?: number }) => void,
    ) => number;
    cancelVideoFrameCallback?: (handle: number) => void;
  };

  const videoRef = useRef<HTMLVideoElement | null>(null);
  const captureCanvasRef = useRef<HTMLCanvasElement | null>(null);
  const overlayCanvasRef = useRef<HTMLCanvasElement | null>(null);
  const landmarkSourceCanvasRef = useRef<HTMLCanvasElement | null>(null);
  const landmarkLoopRef = useRef<number | null>(null);
  const videoFrameCallbackRef = useRef<number | null>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const detectorRef = useRef<FaceLandmarksDetector | null>(null);
  const latestLandmarkPacketRef = useRef<LandmarkPacket | null>(null);
  const latestFaceRef = useRef<BrowserLandmark[] | null>(null);
  const lastProcessedVideoTimeRef = useRef(-1);
  const landmarkPassInFlightRef = useRef(false);
  const stabilizedFrameCountRef = useRef(0);
  const consecutiveNoFaceFramesRef = useRef(0);
  const pendingSignalsRef = useRef<PendingSignalState>({
    blinks: 0,
    headTurn: null,
    pitchValues: [],
  });
  const lastEyesClosedRef = useRef(false);
  const frameCounterRef = useRef(0);
  const queuedActionsRef = useRef<ManualAction[]>([]);

  const [cameraState, setCameraState] = useState<"idle" | "ready" | "error">("idle");
  const [cameraMessage, setCameraMessage] = useState("Requesting webcam access...");
  const [landmarkState, setLandmarkState] = useState<LandmarkEngineState>("loading");
  const [landmarkMessage, setLandmarkMessage] = useState("Loading browser face landmarks...");
  const [landmarkMetrics, setLandmarkMetrics] = useState<LandmarkMetrics>(
    emptyLandmarkMetrics,
  );
  const [queuedActions, setQueuedActions] = useState<ManualAction[]>([]);

  function queueManualAction(action: ManualAction) {
    queuedActionsRef.current = [...queuedActionsRef.current, action];
    setQueuedActions(queuedActionsRef.current);
  }

  function consumeManualAction(): ManualAction | null {
    const [selected, ...rest] = queuedActionsRef.current;
    queuedActionsRef.current = rest;
    setQueuedActions(rest);
    return selected ?? null;
  }

  function consumeLandmarkMetadata(
    includeTrackedSignals: boolean,
    forceSpoof: boolean,
  ): Record<string, unknown> {
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

    if (forceSpoof) {
      metadata.presentation_attack = true;
    }

    return metadata;
  }

  function manualMetadata(action: ManualAction | null): Record<string, unknown> {
    if (action === "open_mouth") return { mouth_open: true, mouth_ratio: 0.38 };
    if (action === "turn_left") return { head_turn: "left" };
    if (action === "turn_right") return { head_turn: "right" };
    if (action === "smile") return { smile: true, smile_ratio: 0.48 };
    if (action === "spoof") return { presentation_attack: true };
    return {};
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
      params.appendLog("detection", "Webcam stream attached");
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Could not open webcam.";
      setCameraState("error");
      setCameraMessage(message);
      params.appendLog("detection", "Camera error", { message });
    }
  }

  function processLandmarks(resultPayload: BrowserLandmarkResult) {
    const processed = processLandmarkResult({
      result: resultPayload,
      lastEyesClosed: lastEyesClosedRef.current,
      pendingSignals: pendingSignalsRef.current,
    });

    if (!processed.face || !processed.metrics || !processed.packet) {
      latestFaceRef.current = null;
      latestLandmarkPacketRef.current = null;
      lastEyesClosedRef.current = processed.lastEyesClosed;
      setLandmarkMetrics({
        ...emptyLandmarkMetrics(),
        timestamp: new Date().toISOString(),
      });
      setLandmarkMessage(processed.message);
      return;
    }

    latestFaceRef.current = processed.face;
    latestLandmarkPacketRef.current = processed.packet;
    lastEyesClosedRef.current = processed.lastEyesClosed;
    setLandmarkMetrics(processed.metrics);
    params.onMetrics(processed.metrics);
    setLandmarkMessage(processed.message);
  }

  function normalizeDetectedFace(face: Face, width: number, height: number): BrowserLandmark[] {
    const safeWidth = Math.max(width, 1);
    const safeHeight = Math.max(height, 1);
    return face.keypoints.map((point) => ({
      x: Math.min(Math.max(point.x / safeWidth, 0), 1),
      y: Math.min(Math.max(point.y / safeHeight, 0), 1),
      z: typeof point.z === "number" ? point.z / safeWidth : 0,
    }));
  }

  async function runLandmarkPass() {
    const detector = detectorRef.current;
    const video = videoRef.current;
    if (!detector || !video || video.readyState < HTMLMediaElement.HAVE_CURRENT_DATA) return;
    if (!video.videoWidth || !video.videoHeight) return;
    if (video.paused || video.ended || !Number.isFinite(video.currentTime) || video.currentTime <= 0) {
      return;
    }
    if (landmarkPassInFlightRef.current) {
      return;
    }
    if (video.currentTime === lastProcessedVideoTimeRef.current) {
      return;
    }
    if (stabilizedFrameCountRef.current < 3) {
      stabilizedFrameCountRef.current += 1;
      lastProcessedVideoTimeRef.current = video.currentTime;
      return;
    }

    landmarkPassInFlightRef.current = true;

    try {
      const sourceCanvas =
        landmarkSourceCanvasRef.current ?? document.createElement("canvas");
      landmarkSourceCanvasRef.current = sourceCanvas;
      sourceCanvas.width = video.videoWidth;
      sourceCanvas.height = video.videoHeight;

      const sourceContext = sourceCanvas.getContext("2d");
      if (!sourceContext) {
        return;
      }

      sourceContext.drawImage(video, 0, 0, sourceCanvas.width, sourceCanvas.height);

      const faces = await detector.estimateFaces(sourceCanvas, {
        flipHorizontal: false,
        staticImageMode: true,
      });
      if (detectorRef.current !== detector) {
        return;
      }

      if (faces.length === 0) {
        consecutiveNoFaceFramesRef.current += 1;
        if (consecutiveNoFaceFramesRef.current >= 12) {
          detector.reset();
          consecutiveNoFaceFramesRef.current = 0;
          params.appendLog("detection", "Landmark detector reset after repeated misses");
        }
      } else {
        consecutiveNoFaceFramesRef.current = 0;
      }

      const normalizedFaces =
        faces.length > 0
          ? [normalizeDetectedFace(faces[0], video.videoWidth, video.videoHeight)]
          : [];
      lastProcessedVideoTimeRef.current = video.currentTime;
      processLandmarks({ faceLandmarks: normalizedFaces });
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Landmark capture failed.";
      setLandmarkMessage(message);
      params.appendLog("detection", "Landmark error", { message });
    } finally {
      landmarkPassInFlightRef.current = false;
    }
  }

  function stopLandmarkLoop() {
    const video = videoRef.current as VideoWithFrameCallback | null;
    if (
      video &&
      videoFrameCallbackRef.current !== null &&
      typeof video.cancelVideoFrameCallback === "function"
    ) {
      video.cancelVideoFrameCallback(videoFrameCallbackRef.current);
      videoFrameCallbackRef.current = null;
    }
    if (landmarkLoopRef.current !== null) {
      window.cancelAnimationFrame(landmarkLoopRef.current);
      landmarkLoopRef.current = null;
    }
  }

  function scheduleLandmarkPass() {
    stopLandmarkLoop();

    const video = videoRef.current as VideoWithFrameCallback | null;
    if (video && typeof video.requestVideoFrameCallback === "function") {
      const loop = () => {
        runLandmarkPass();
        videoFrameCallbackRef.current = video.requestVideoFrameCallback?.(() => {
          loop();
        }) ?? null;
      };
      videoFrameCallbackRef.current = video.requestVideoFrameCallback(() => {
        loop();
      });
      return;
    }

    const loop = () => {
      runLandmarkPass();
      landmarkLoopRef.current = window.requestAnimationFrame(loop);
    };

    landmarkLoopRef.current = window.requestAnimationFrame(loop);
  }

  function captureFrame(
    socket: WebSocket | null,
    options: { includeTrackedSignals: boolean; forceSpoof: boolean },
  ) {
    const video = videoRef.current;
    const canvas = captureCanvasRef.current;
    if (!video || !canvas || socket?.readyState !== WebSocket.OPEN) return;

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
      ...consumeLandmarkMetadata(options.includeTrackedSignals, options.forceSpoof),
      ...manualMetadata(action),
      frame_number: frameNumber,
      frame_width: width,
      frame_height: height,
    };

    const imageBase64 = canvas.toDataURL("image/jpeg", 0.75).split(",")[1] ?? "";
    socket.send(
      JSON.stringify({
        type: "frame",
        timestamp: new Date().toISOString(),
        image_base64: imageBase64,
        metadata,
      }),
    );

    const packet = latestLandmarkPacketRef.current;
    if (packet) {
      socket.send(
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
      params.appendLog("pipeline", `Manual action queued: ${action.replace("_", " ")}`, metadata);
    }
  }

  function resetCaptureState() {
    frameCounterRef.current = 0;
    lastProcessedVideoTimeRef.current = -1;
    stabilizedFrameCountRef.current = 0;
    consecutiveNoFaceFramesRef.current = 0;
    queuedActionsRef.current = [];
    setQueuedActions([]);
  }

  useEffect(() => {
    void requestCamera();

    return () => {
      stopLandmarkLoop();
      landmarkPassInFlightRef.current = false;
      const activeDetector = detectorRef.current;
      detectorRef.current = null;
      if (activeDetector) {
        try {
          activeDetector.dispose();
        } catch (error) {
          params.appendLog("detection", "Landmark detector dispose skipped", {
            message: error instanceof Error ? error.message : "Unknown close error",
          });
        }
      }
      mediaStreamRef.current?.getTracks().forEach((track) => track.stop());
      mediaStreamRef.current = null;
    };
  }, []);

  useEffect(() => {
    if (!browserLandmarksEnabled) {
      setLandmarkState("idle");
      setLandmarkMessage("Browser landmarks disabled; backend-only mode.");
      return;
    }

    let cancelled = false;

    async function loadLandmarker() {
      try {
        setLandmarkState("loading");
        setLandmarkMessage("Loading TensorFlow.js face landmarks...");
        const [faceLandmarksDetectionTfjs, tf] = await Promise.all([
          import("@tensorflow-models/face-landmarks-detection/dist/tfjs/detector"),
          import("@tensorflow/tfjs-core"),
        ]);
        await Promise.all([
          import("@tensorflow/tfjs-backend-webgl"),
          import("@tensorflow/tfjs-backend-cpu"),
        ]);

        let backend: "webgl" | "cpu" | null = null;
        for (const candidate of ["webgl", "cpu"] as const) {
          try {
            const ready = await tf.setBackend(candidate);
            if (ready) {
              backend = candidate;
              break;
            }
          } catch {
            // Try the next registered backend.
          }
        }

        if (!backend) {
          throw new Error("Could not initialize a TensorFlow.js backend.");
        }

        await tf.ready();
        const detector = await faceLandmarksDetectionTfjs.load({
          runtime: "tfjs",
          maxFaces: 1,
          refineLandmarks: false,
        });

        if (cancelled) {
          detector.dispose();
          return;
        }

        detectorRef.current = detector;
        setLandmarkState("ready");
        setLandmarkMessage("TensorFlow.js face landmarks ready.");
        params.appendLog("detection", "Landmark detector ready", {
          model: "MediaPipeFaceMesh",
          runtime: "tfjs",
          backend,
        });
      } catch (error) {
        const message =
          error instanceof Error ? error.message : "Could not load TensorFlow.js face landmarks.";
        setLandmarkState("error");
        setLandmarkMessage(message);
        params.appendLog("detection", "Landmark detector error", { message });
      }
    }

    void loadLandmarker();
    return () => {
      cancelled = true;
    };
  }, [params.appendLog]);

  useEffect(() => {
    if (!browserLandmarksEnabled) {
      stopLandmarkLoop();
      return;
    }

    if (cameraState !== "ready" || landmarkState !== "ready") {
      stopLandmarkLoop();
      return;
    }

    const video = videoRef.current;
    if (!video) {
      return;
    }

    const handleLoadedData = () => {
      stabilizedFrameCountRef.current = 0;
      scheduleLandmarkPass();
    };

    video.addEventListener("loadeddata", handleLoadedData);
    video.addEventListener("playing", handleLoadedData);

    scheduleLandmarkPass();

    return () => {
      video.removeEventListener("loadeddata", handleLoadedData);
      video.removeEventListener("playing", handleLoadedData);
      stopLandmarkLoop();
    };
  }, [cameraState, landmarkState]);

  return {
    videoRef,
    captureCanvasRef,
    overlayCanvasRef,
    latestFaceRef,
    cameraState,
    cameraMessage,
    landmarkState,
    landmarkMessage,
    landmarkMetrics,
    queuedActions,
    queueManualAction,
    captureFrame,
    resetCaptureState,
  };
}
