import type { SessionRecordResponse, VerificationResult } from "@sui-human/shared";
import type { ClientVerificationState } from "../hooks/use-client-verification-flow";

export function deriveClientVerificationState(params: {
  sessionStatus?: string;
  resultStatus?: string;
  proofId?: string;
  finalizeRequested: boolean;
  mintRequested: boolean;
  finalizeReady: boolean;
  connectionState: string;
  hasSession: boolean;
  cameraState: "idle" | "ready" | "error";
  landmarkState: "idle" | "loading" | "ready" | "error";
  captureActive: boolean;
  busy: boolean;
  faceDetected: boolean;
  progress: number;
  stepStatus: string;
}): ClientVerificationState {
  if (params.mintRequested) return "minting";
  if (params.resultStatus === "verified" && !params.proofId) return "ready_to_mint";
  if (params.resultStatus === "verified") return "verified";
  if (params.resultStatus === "expired") return "expired";
  if (params.resultStatus === "failed") return "failed";
  if (params.sessionStatus === "expired") return "expired";
  if (params.finalizeRequested) return "processing";
  if (
    (params.connectionState === "error" || params.connectionState === "closed") &&
    params.hasSession
  ) {
    return "disconnected";
  }
  if (params.cameraState === "error") return "camera_blocked";
  if (params.cameraState === "idle") return "camera_idle";
  if (
    params.landmarkState === "loading" ||
    params.busy
  ) {
    return "warming";
  }
  if (!params.captureActive && params.faceDetected) return "camera_ready";
  if (!params.faceDetected) return "framing";
  if (params.finalizeReady) {
    return "ready_to_finalize";
  }
  if (!params.captureActive) return "camera_ready";
  return "challenge_active";
}

export function deriveCanStartVerification(params: {
  hasSession: boolean;
  connectionState: string;
  cameraState: "idle" | "ready" | "error";
  landmarkState: "idle" | "loading" | "ready" | "error";
  faceDetected: boolean;
  captureActive: boolean;
  finalizeReady: boolean;
  finalizeRequested: boolean;
  hasResult: boolean;
}) {
  return (
    params.hasSession &&
    params.connectionState === "open" &&
    params.cameraState === "ready" &&
    params.landmarkState === "ready" &&
    params.faceDetected &&
    !params.captureActive &&
    !params.finalizeReady &&
    !params.finalizeRequested &&
    !params.hasResult
  );
}

export function deriveCanMintProof(params: {
  hasResult: boolean;
  resultStatus?: string;
  proofId?: string;
  mintRequested: boolean;
  walletConnected: boolean;
}) {
  return (
    params.hasResult &&
    params.resultStatus === "verified" &&
    !params.proofId &&
    !params.mintRequested &&
    params.walletConnected
  );
}

export function deriveCanFinalizeVerification(params: {
  modelsReady: boolean;
  hasSession: boolean;
  connectionState: string;
  finalizeReady: boolean;
  captureActive: boolean;
  finalizeRequested: boolean;
  hasResult: boolean;
}) {
  return (
    params.modelsReady &&
    params.hasSession &&
    params.connectionState === "open" &&
    params.finalizeReady &&
    !params.captureActive &&
    !params.finalizeRequested &&
    !params.hasResult
  );
}

export function humanizeFailureReason(value: string | undefined) {
  if (!value) return "The verifier could not confirm this session.";
  if (value.includes("expired")) return "This session expired before verification completed.";
  if (value.includes("spoof")) {
    return "The verifier detected a presentation pattern that did not look trustworthy.";
  }
  if (value.includes("deepfake")) {
    return "The verifier detected a synthetic or manipulated presentation pattern.";
  }
  if (value.includes("quality")) {
    return "The captured video quality was not strong enough to verify safely.";
  }
  if (value.includes("challenge")) {
    return "The live challenge sequence was not completed successfully.";
  }
  return "The verifier could not confirm this session.";
}

export type ResultOutcome = "verified" | "expired" | "spoof" | "failed" | "missing";

export function detectSpoofFailure(result: VerificationResult | undefined) {
  return Boolean(
    result?.attack_analysis?.presentation_attack_detected ||
      result?.attack_analysis?.deepfake_detected ||
      result?.failure_reason?.includes("spoof") ||
      result?.failure_reason?.includes("deepfake"),
  );
}

export function deriveResultOutcome(session: SessionRecordResponse | null): ResultOutcome {
  const result = session?.result;

  if (result?.status === "verified") return "verified";
  if (result?.status === "expired" || session?.status === "expired") return "expired";
  if (result?.status === "failed") {
    return detectSpoofFailure(result) ? "spoof" : "failed";
  }
  return "missing";
}
