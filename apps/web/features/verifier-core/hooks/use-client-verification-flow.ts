"use client";

import { useEffect, useMemo, useRef } from "react";
import { useDAppKit } from "@mysten/dapp-kit-react";
import { storeSessionId } from "../lib/app-session";
import {
  deriveCanStartVerification,
  deriveCanFinalizeVerification,
  deriveCanMintProof,
  deriveClientVerificationState,
} from "../lib/client-flow";
import { signAndExecuteMintClaim } from "../lib/wallet-mint";
import { challengeHint } from "../lib/utils";
import { useCameraLandmarks } from "./use-camera-landmarks";
import { useSessionMetricSummary } from "./use-session-metric-summary";
import { useVerifierSession } from "./use-verifier-session";
import { useSuiWallet } from "@/features/wallet/hooks/use-sui-wallet";

const noop = () => {};

export type ClientVerificationState =
  | "warming"
  | "camera_idle"
  | "camera_ready"
  | "camera_blocked"
  | "framing"
  | "challenge_active"
  | "ready_to_finalize"
  | "ready_to_mint"
  | "processing"
  | "minting"
  | "disconnected"
  | "verified"
  | "failed"
  | "expired";

export function useClientVerificationFlow(sessionId: string) {
  const attemptedSessionRef = useRef<string | null>(null);
  const reconnectAttemptedRef = useRef(false);
  const { updateSummary, resetSummary } = useSessionMetricSummary();
  const dAppKit = useDAppKit();
  const wallet = useSuiWallet();

  const media = useCameraLandmarks({
    appendLog: noop,
    onMetrics: updateSummary,
    autoRequestCamera: false,
  });

  const verifier = useVerifierSession({
    walletAddress: wallet.address,
    verificationMode: "full",
    autoFinalizeOnComplete: false,
    autoCaptureOnSocketOpen: false,
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

  useEffect(() => {
    if (!verifier.finalizeReady || !verifier.captureActive) return;
    verifier.stopCapture();
  }, [verifier.captureActive, verifier.finalizeReady, verifier.stopCapture]);

  function reconnectSession() {
    attemptedSessionRef.current = null;
    reconnectAttemptedRef.current = true;
    void verifier.connectToSession(sessionId);
  }

  const uiState = useMemo<ClientVerificationState>(() => {
    return deriveClientVerificationState({
      sessionStatus: verifier.session?.status,
      resultStatus: verifier.result?.status,
      proofId: verifier.result?.proof_id,
      finalizeRequested: verifier.finalizeRequested,
      mintRequested: verifier.mintRequested,
      finalizeReady: verifier.finalizeReady,
      connectionState: verifier.connectionState,
      hasSession: Boolean(verifier.session),
      cameraState: media.cameraState,
      landmarkState: media.landmarkState,
      captureActive: verifier.captureActive,
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
    verifier.mintRequested,
    verifier.finalizeRequested,
    verifier.finalizeReady,
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
    if (uiState === "camera_idle") return "Open your webcam when you are ready to begin.";
    if (uiState === "camera_ready") return "Webcam is ready. Press Verify to start live liveness and anti-spoof checks.";
    if (uiState === "framing") return media.landmarkMessage;
    if (uiState === "disconnected") return "Connection dropped. Hold still while the session reconnects.";
    if (uiState === "processing") {
      return "Submitting your session for the server's final verdict.";
    }
    if (uiState === "minting") {
      return "Preparing the claim and waiting for your wallet to approve the proof transaction.";
    }
    if (uiState === "ready_to_finalize") {
      return "All live checks are complete. Finalize verification to receive the server verdict.";
    }
    if (uiState === "ready_to_mint") {
      return "The server accepted your verification. Minting now requires a wallet signature.";
    }
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
    openCamera: media.requestCamera,
    closeCamera: () => {
      verifier.stopCapture();
      media.closeCamera();
    },
    startVerification: verifier.startCapture,
    stopVerification: verifier.stopCapture,
    mintProof: async () => {
      let transactionSubmitted = false;
      try {
        const claim = await verifier.prepareMintClaim();
        if (!claim) {
          return;
        }
        const executed = await signAndExecuteMintClaim({
          claim,
          dAppKit,
        });
        transactionSubmitted = true;
        await verifier.completeMintClaim(executed.digest, executed.proofId);
      } catch (error) {
        if (!transactionSubmitted) {
          const reason =
            error instanceof Error ? error.message : "Wallet approval was cancelled.";
          await verifier.cancelMintClaim(reason);
          return;
        }
        return;
      }
    },
    canOpenCamera: media.cameraState !== "ready",
    canCloseCamera: media.cameraState === "ready",
    canStartVerification: deriveCanStartVerification({
      hasSession: Boolean(verifier.session),
      connectionState: verifier.connectionState,
      cameraState: media.cameraState,
      landmarkState: media.landmarkState,
      faceDetected: media.landmarkMetrics.faceDetected,
      captureActive: verifier.captureActive,
      finalizeReady: verifier.finalizeReady,
      finalizeRequested: verifier.finalizeRequested,
      hasResult: Boolean(verifier.result),
    }),
    canFinalize: deriveCanFinalizeVerification({
      modelsReady: verifier.modelsReady,
      hasSession: Boolean(verifier.session),
      connectionState: verifier.connectionState,
      finalizeReady: verifier.finalizeReady,
      captureActive: verifier.captureActive,
      finalizeRequested: verifier.finalizeRequested,
      hasResult: Boolean(verifier.result),
    }),
    canMint: deriveCanMintProof({
      hasResult: Boolean(verifier.result),
      resultStatus: verifier.result?.status,
      proofId: verifier.result?.proof_id,
      mintRequested: verifier.mintRequested,
      walletConnected: wallet.isConnected,
    }),
  };
}
