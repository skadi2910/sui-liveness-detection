export const challengeTypes = [
  "blink_twice",
  "turn_left",
  "turn_right",
  "open_mouth",
  "nod_head",
  "smile",
] as const;

export type ChallengeType = (typeof challengeTypes)[number];

export const sessionStatuses = [
  "created",
  "ready",
  "streaming",
  "processing",
  "verified",
  "failed",
  "expired",
] as const;

export type SessionStatus = (typeof sessionStatuses)[number];

export const verificationModes = [
  "full",
  "liveness_only",
  "antispoof_only",
] as const;

export type VerificationMode = (typeof verificationModes)[number];

export const healthComponentStatuses = [
  "ready",
  "degraded",
  "unavailable",
  "not_configured",
] as const;

export type HealthComponentStatus = (typeof healthComponentStatuses)[number];

export const wsClientEventTypes = [
  "frame",
  "heartbeat",
  "landmarks",
  "finalize",
] as const;

export type WsClientEventType = (typeof wsClientEventTypes)[number];

export const wsServerEventTypes = [
  "session_ready",
  "challenge_update",
  "progress",
  "processing",
  "verified",
  "failed",
  "error",
] as const;

export type WsServerEventType = (typeof wsServerEventTypes)[number];
