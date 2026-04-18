import type {
  VerificationProgress,
  VerificationResult,
} from "./contracts.js";
import type { VerificationMode } from "./values.js";

export interface WsFrameEvent {
  type: "frame";
  timestamp: string;
  image_base64: string;
  metadata?: Record<string, unknown>;
}

export interface WsHeartbeatEvent {
  type: "heartbeat";
  timestamp: string;
}

export interface WsLandmarksEvent {
  type: "landmarks";
  timestamp: string;
  landmarks: Record<string, number | string | boolean | null>;
  metadata?: Record<string, unknown>;
}

export interface WsFinalizeEvent {
  type: "finalize";
  timestamp: string;
  mode?: VerificationMode;
}

export type WsClientEvent =
  | WsFrameEvent
  | WsHeartbeatEvent
  | WsLandmarksEvent
  | WsFinalizeEvent;

export interface WsSessionReadyEvent {
  type: "session_ready";
  payload: {
    session_id: string;
    message: string;
  };
}

export interface WsChallengeUpdateEvent {
  type: "challenge_update";
  payload: VerificationProgress;
}

export interface WsProgressEvent {
  type: "progress";
  payload: VerificationProgress;
}

export interface WsProcessingEvent {
  type: "processing";
  payload: {
    session_id: string;
    status: "processing";
    message: string;
  };
}

export interface WsVerifiedEvent {
  type: "verified";
  payload: VerificationResult & {
    status: "verified";
  };
}

export interface WsFailedEvent {
  type: "failed";
  payload: VerificationResult & {
    status: "failed" | "expired";
  };
}

export interface WsErrorEvent {
  type: "error";
  payload: {
    session_id: string;
    code: string;
    message: string;
    retryable: boolean;
  };
}

export type WsServerEvent =
  | WsSessionReadyEvent
  | WsChallengeUpdateEvent
  | WsProgressEvent
  | WsProcessingEvent
  | WsVerifiedEvent
  | WsFailedEvent
  | WsErrorEvent;
