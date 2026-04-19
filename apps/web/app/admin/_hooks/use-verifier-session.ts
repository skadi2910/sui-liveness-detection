"use client";

import type {
  ChallengeType,
  VerificationDebugPayload,
  VerificationMode,
} from "@sui-human/shared";
import { useVerifierSession as useBaseVerifierSession } from "../../../features/verifier-core/hooks/use-verifier-session";

type AppendLog = (section: "pipeline" | "detection" | "signals", summary: string, detail?: unknown) => void;

export function useVerifierSession(params: {
  walletAddress: string;
  verificationMode: VerificationMode;
  challengeSequenceOverride?: ChallengeType[] | null;
  autoAssist: boolean;
  appendLog: AppendLog;
  appendDebugLogs: (debug: VerificationDebugPayload) => void;
  resetLogs: () => void;
  resetSummary: () => void;
  captureFrame: (
    socket: WebSocket | null,
    options: { includeTrackedSignals: boolean; forceSpoof: boolean },
  ) => void;
  resetCaptureState: () => void;
  forceSpoof: boolean;
}) {
  return useBaseVerifierSession({
    walletAddress: params.walletAddress,
    verificationMode: params.verificationMode,
    challengeSequenceOverride: params.challengeSequenceOverride,
    autoFinalizeOnComplete: params.autoAssist,
    appendLog: params.appendLog,
    appendDebugLogs: params.appendDebugLogs,
    resetLogs: params.resetLogs,
    resetSummary: params.resetSummary,
    captureFrame: (socket) =>
      params.captureFrame(socket, {
        includeTrackedSignals: params.autoAssist,
        forceSpoof: params.forceSpoof,
      }),
    resetCaptureState: params.resetCaptureState,
  });
}
