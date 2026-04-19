import { describe, expect, it } from "vitest";
import {
  deriveCanStartVerification,
  deriveCanFinalizeVerification,
  deriveCanMintProof,
  deriveClientVerificationState,
  deriveResultOutcome,
  humanizeFailureReason,
} from "./client-flow";
import { resolveVerifierHttpBase } from "../../../lib/verifier-base";
import { actionMetadata, nextPitchMetadata } from "../../../app/admin/_lib/camera-harness";

describe("deriveClientVerificationState", () => {
  it("requires full progress before allowing finalize-ready state", () => {
    expect(
      deriveClientVerificationState({
        sessionStatus: "streaming",
        resultStatus: undefined,
        proofId: undefined,
        finalizeRequested: false,
        mintRequested: false,
        finalizeReady: false,
        connectionState: "open",
        hasSession: true,
        cameraState: "ready",
        landmarkState: "ready",
        captureActive: true,
        busy: false,
        faceDetected: true,
        progress: 0.25,
        stepStatus: "active",
      }),
    ).toBe("challenge_active");
  });

  it("marks closed active sessions as disconnected", () => {
    expect(
      deriveClientVerificationState({
        sessionStatus: "streaming",
        resultStatus: undefined,
        proofId: undefined,
        finalizeRequested: false,
        mintRequested: false,
        finalizeReady: false,
        connectionState: "closed",
        hasSession: true,
        cameraState: "ready",
        landmarkState: "ready",
        captureActive: true,
        busy: false,
        faceDetected: true,
        progress: 0.8,
        stepStatus: "active",
      }),
    ).toBe("disconnected");
  });

  it("marks expired restored sessions as expired", () => {
    expect(
      deriveClientVerificationState({
        sessionStatus: "expired",
        resultStatus: undefined,
        proofId: undefined,
        finalizeRequested: false,
        mintRequested: false,
        finalizeReady: false,
        connectionState: "closed",
        hasSession: true,
        cameraState: "ready",
        landmarkState: "ready",
        captureActive: true,
        busy: false,
        faceDetected: true,
        progress: 1,
        stepStatus: "completed",
      }),
    ).toBe("expired");
  });

  it("shows a camera-idle state before the user opens the webcam", () => {
    expect(
      deriveClientVerificationState({
        sessionStatus: "streaming",
        resultStatus: undefined,
        proofId: undefined,
        finalizeRequested: false,
        mintRequested: false,
        finalizeReady: false,
        connectionState: "open",
        hasSession: true,
        cameraState: "idle",
        landmarkState: "ready",
        captureActive: false,
        busy: false,
        faceDetected: false,
        progress: 0,
        stepStatus: "pending",
      }),
    ).toBe("camera_idle");
  });

  it("shows camera-ready once framing is good but verification has not started", () => {
    expect(
      deriveClientVerificationState({
        sessionStatus: "streaming",
        resultStatus: undefined,
        proofId: undefined,
        finalizeRequested: false,
        mintRequested: false,
        finalizeReady: false,
        connectionState: "open",
        hasSession: true,
        cameraState: "ready",
        landmarkState: "ready",
        captureActive: false,
        busy: false,
        faceDetected: true,
        progress: 0,
        stepStatus: "pending",
      }),
    ).toBe("camera_ready");
  });
});

describe("deriveCanStartVerification", () => {
  it("allows verify after the webcam is open, tracking is ready, and the face is framed", () => {
    expect(
      deriveCanStartVerification({
        hasSession: true,
        connectionState: "open",
        cameraState: "ready",
        landmarkState: "ready",
        faceDetected: true,
        captureActive: false,
        finalizeReady: false,
        finalizeRequested: false,
        hasResult: false,
      }),
    ).toBe(true);
  });

  it("blocks verify before the webcam and face tracking are ready", () => {
    expect(
      deriveCanStartVerification({
        hasSession: true,
        connectionState: "open",
        cameraState: "idle",
        landmarkState: "ready",
        faceDetected: false,
        captureActive: false,
        finalizeReady: false,
        finalizeRequested: false,
        hasResult: false,
      }),
    ).toBe(false);
  });

  it("blocks verify once the backend has already marked the session ready to finalize", () => {
    expect(
      deriveCanStartVerification({
        hasSession: true,
        connectionState: "open",
        cameraState: "ready",
        landmarkState: "ready",
        faceDetected: true,
        captureActive: false,
        finalizeReady: true,
        finalizeRequested: false,
        hasResult: false,
      }),
    ).toBe(false);
  });
});

describe("deriveCanFinalizeVerification", () => {
  it("allows finalize only when the backend marks the session mint-ready and capture has stopped", () => {
    expect(
      deriveCanFinalizeVerification({
        modelsReady: true,
        hasSession: true,
        connectionState: "open",
        finalizeReady: true,
        captureActive: false,
        finalizeRequested: false,
        hasResult: false,
      }),
    ).toBe(true);
  });

  it("still blocks finalize while verification capture is still running", () => {
    expect(
      deriveCanFinalizeVerification({
        modelsReady: true,
        hasSession: true,
        connectionState: "open",
        finalizeReady: true,
        captureActive: true,
        finalizeRequested: false,
        hasResult: false,
      }),
    ).toBe(false);
  });
});

describe("deriveCanMintProof", () => {
  it("allows mint only after a verified verdict without a proof id", () => {
    expect(
      deriveCanMintProof({
        hasResult: true,
        resultStatus: "verified",
        proofId: undefined,
        mintRequested: false,
        walletConnected: true,
      }),
    ).toBe(true);
  });

  it("blocks mint after the proof has already been minted", () => {
    expect(
      deriveCanMintProof({
        hasResult: true,
        resultStatus: "verified",
        proofId: "0xproof",
        mintRequested: false,
        walletConnected: true,
      }),
    ).toBe(false);
  });
});

describe("deriveResultOutcome", () => {
  it("classifies spoof-oriented failures separately", () => {
    expect(
      deriveResultOutcome({
        session_id: "s1",
        status: "failed",
        challenge_type: "smile",
        challenge_sequence: ["smile"],
        current_challenge_index: 0,
        total_challenges: 1,
        completed_challenges: [],
        created_at: new Date().toISOString(),
        expires_at: new Date().toISOString(),
        result: {
          session_id: "s1",
          status: "failed",
          evaluation_mode: "full",
          human: false,
          challenge_type: "smile",
          challenge_sequence: ["smile"],
          current_challenge_index: 0,
          total_challenges: 1,
          completed_challenges: [],
          confidence: 0.2,
          spoof_score: 0.9,
          failure_reason: "spoof_detected",
          attack_analysis: {
            failure_category: "presentation_attack",
            suspected_attack_family: "screen_replay",
            presentation_attack_detected: true,
            presentation_attack_score: 0.9,
            deepfake_detected: false,
            note: "spoof",
          },
        },
      }),
    ).toBe("spoof");
  });
});

describe("humanizeFailureReason", () => {
  it("maps quality failures to user-facing copy", () => {
    expect(humanizeFailureReason("quality_gate_failed")).toContain("video quality");
  });
});

describe("resolveVerifierHttpBase", () => {
  it("prefers absolute verifier env values", () => {
    expect(
      resolveVerifierHttpBase({
        envValue: "http://127.0.0.1:8000",
        host: "localhost:3000",
        protocol: "http",
      }),
    ).toBe("http://127.0.0.1:8000");
  });

  it("resolves relative verifier env values against the app host", () => {
    expect(
      resolveVerifierHttpBase({
        envValue: "/proxy",
        host: "localhost:3000",
        protocol: "https",
      }),
    ).toBe("https://localhost:3000/proxy");
  });
});

describe("admin camera harness helpers", () => {
  it("builds spoof metadata from admin action", () => {
    expect(actionMetadata("spoof")).toEqual({ presentation_attack: true });
  });

  it("consumes queued nod pitch values in order", () => {
    const values = [14, -14];
    expect(nextPitchMetadata(values)).toEqual({ pitch: 14, pitch_ratio: 0.0778 });
    expect(nextPitchMetadata(values)).toEqual({ pitch: -14, pitch_ratio: -0.0778 });
    expect(nextPitchMetadata(values)).toEqual({});
  });
});
