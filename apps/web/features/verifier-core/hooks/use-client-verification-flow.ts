"use client";

import { useEffect, useMemo, useRef } from "react";
import { demoWalletAddress } from "../lib/constants";
import { storeSessionId } from "../lib/app-session";
import { deriveClientVerificationState } from "../lib/client-flow";
import { challengeHint } from "../lib/utils";
import { useCameraLandmarks } from "./use-camera-landmarks";
import { useSessionMetricSummary } from "./use-session-metric-summary";
import { useVerifierSession } from "./use-verifier-session";

const noop = () => {};

export type ClientVerificationState =
  | "warming"
  | "camera_blocked"
  | "framing"
  | "challenge_active"
  | "ready_to_finalize"
  | "processing"
  | "disconnected"
  | "verified"
  | "failed"
  | "expired";

export function useClientVerificationFlow(sessionId: string) {
  const attemptedSessionRef = useRef<string | null>(null);
  const reconnectAttemptedRef = useRef(false);
  const { updateSummary, resetSummary } = useSessionMetricSummary();

  const media = useCameraLandmarks({
    appendLog: noop,
    onMetrics: updateSummary,
  });

  const verifier = useVerifierSession({
    walletAddress: demoWalletAddress,
    verificationMode: "full",
    autoFinalizeOnComplete: false,
    appendLog: noop,
    appendDebugLogs: noop,
    resetLogs: noop,
    resetSummary,
    captureFrame: media.captureFrame,
    resetCaptureState: media.resetCaptureState,
  });

  useEffect(() => {
    if (!sessionId) return;
    storeSessionId(sessionId);
  }, [sessionId]);

  useEffect(() => {
    if (!sessionId) return;
    if (attemptedSessionRef.current === sessionId) return;
    attemptedSessionRef.current = sessionId;
    void verifier.connectToSession(sessionId);
  }, [sessionId, verifier]);

  function reconnectSession() {
    attemptedSessionRef.current = null;
    reconnectAttemptedRef.current = true;
    void verifier.connectToSession(sessionId);
  }

  const uiState = useMemo<ClientVerificationState>(() => {
    return deriveClientVerificationState({
      sessionStatus: verifier.session?.status,
      resultStatus: verifier.result?.status,
      finalizeRequested: verifier.finalizeRequested,
      connectionState: verifier.connectionState,
      hasSession: Boolean(verifier.session),
      cameraState: media.cameraState,
      landmarkState: media.landmarkState,
      busy: verifier.busy,
      faceDetected: media.landmarkMetrics.faceDetected,
      progress: verifier.progress,
      stepStatus: verifier.stepStatus,
    });
  }, [
    media.cameraState,
    media.landmarkMetrics.faceDetected,
    media.landmarkState,
    verifier.busy,
    verifier.connectionState,
    verifier.finalizeRequested,
    verifier.progress,
    verifier.result,
    verifier.stepStatus,
  ]);

  useEffect(() => {
    if (uiState !== "disconnected") {
      reconnectAttemptedRef.current = false;
      return;
    }
    if (reconnectAttemptedRef.current) return;

    reconnectAttemptedRef.current = true;
    const timeoutId = window.setTimeout(() => {
      attemptedSessionRef.current = null;
      void verifier.connectToSession(sessionId);
    }, 1500);

    return () => {
      window.clearTimeout(timeoutId);
    };
  }, [sessionId, uiState, verifier]);

  const helperText = useMemo(() => {
    if (uiState === "camera_blocked") return media.cameraMessage;
    if (uiState === "framing") return media.landmarkMessage;
    if (uiState === "disconnected") return "Connection dropped. Hold still while the session reconnects.";
    if (uiState === "processing") return "We have enough motion evidence. Finalizing your attestation now.";
    if (uiState === "ready_to_finalize") return "All challenge steps are complete. Finalize to receive the verifier decision.";
    if (verifier.statusMessage) return verifier.statusMessage;
    return challengeHint(verifier.challengeType);
  }, [
    media.cameraMessage,
    media.landmarkMessage,
    uiState,
    verifier.challengeType,
    verifier.statusMessage,
  ]);

  return {
    media,
    verifier,
    uiState,
    helperText,
    currentInstruction: challengeHint(verifier.challengeType),
    reconnectSession,
    canFinalize:
      verifier.modelsReady &&
      Boolean(verifier.session) &&
      verifier.connectionState === "open" &&
      verifier.progress >= 1 &&
      !verifier.finalizeRequested &&
      !verifier.result,
  };
}
