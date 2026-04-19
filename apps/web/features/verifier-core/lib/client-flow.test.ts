import { describe, expect, it } from "vitest";
import {
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
        finalizeRequested: false,
        connectionState: "open",
        hasSession: true,
        cameraState: "ready",
        landmarkState: "ready",
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
        finalizeRequested: false,
        connectionState: "closed",
        hasSession: true,
        cameraState: "ready",
        landmarkState: "ready",
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
        finalizeRequested: false,
        connectionState: "closed",
        hasSession: true,
        cameraState: "ready",
        landmarkState: "ready",
        busy: false,
        faceDetected: true,
        progress: 1,
        stepStatus: "completed",
      }),
    ).toBe("expired");
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
