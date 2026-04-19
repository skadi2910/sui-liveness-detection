export interface SealServerConfig {
  objectId: string;
  weight: number;
  aggregatorUrl?: string;
  apiKeyName?: string;
  apiKey?: string;
}

export interface OwnerProofConfig {
  packageId: string | null;
  network: string;
  fullnodeUrl: string;
  walrusAggregatorUrl: string | null;
  sealServerConfigs: SealServerConfig[];
  sealThreshold: number;
  verifyKeyServers: boolean;
  sessionKeyTtlMinutes: number;
  proofType: string | null;
  missing: string[];
}

export interface OwnedProofMetadata {
  proofId: string;
  owner: string;
  walrusBlobId: string;
  walrusBlobObjectId: string;
  sealIdentity: string;
  evidenceSchemaVersion: number;
  modelHash: string;
  confidenceBps: number;
  issuedAtMs: number;
  expiresAtMs: number;
  challengeType: string;
  transactionDigest?: string | null;
}

export interface RetainedEvidenceBlob {
  evidence_schema_version: number;
  session_id: string;
  wallet_address: string;
  challenge_type: string;
  challenge_sequence: string[];
  session_started_at: string;
  session_completed_at: string;
  frame_hashes: string[];
  landmark_snapshot: Record<string, unknown>;
  spoof_score_summary: Record<string, unknown>;
  model_hashes: Record<string, string>;
  captured_at: string;
  landmark_trace_summary?: Record<string, unknown>;
  antispoof_summary?: Record<string, unknown>;
  human_face_summary?: Record<string, unknown>;
  quality_summary?: Record<string, unknown>;
  deepfake_summary?: Record<string, unknown>;
  verification_context?: Record<string, unknown>;
  challenge_summary?: Record<string, unknown>;
  attack_analysis?: Record<string, unknown>;
  verdict_context?: Record<string, unknown>;
}

export type ProofLoadState = "idle" | "loading" | "ready" | "empty" | "error" | "config_missing";

export type ProofDecryptState =
  | "idle"
  | "awaiting_wallet_approval"
  | "decrypting"
  | "success"
  | "error";

