import type {
  CreateSessionRequest,
  CreateSessionResponse,
  EvidenceBlob,
  HealthResponse,
  SessionRecordResponse,
  VerificationProgress,
  VerificationResult,
} from "./contracts.js";
import type { WsClientEvent, WsServerEvent } from "./websocket.js";

export const sampleCreateSessionRequest: CreateSessionRequest = {
  wallet_address: "0xabc123",
  client: {
    platform: "web",
    user_agent: "Mozilla/5.0",
  },
};

export const sampleCreateSessionResponse: CreateSessionResponse = {
  session_id: "sess_123",
  status: "created",
  challenge_type: "open_mouth",
  challenge_sequence: ["open_mouth", "turn_right"],
  current_challenge_index: 0,
  total_challenges: 2,
  completed_challenges: [],
  expires_at: "2026-04-17T14:00:00Z",
  ws_url: "/ws/sessions/sess_123/stream",
};

export const sampleVerificationProgress: VerificationProgress = {
  session_id: "sess_123",
  status: "streaming",
  challenge_type: "open_mouth",
  challenge_sequence: ["open_mouth", "turn_right"],
  current_challenge_index: 0,
  total_challenges: 2,
  completed_challenges: [],
  step_status: "active",
  progress: 0.6,
  finalize_ready: false,
  frames_processed: 18,
  message: "Open your mouth",
  debug: {
    face_detection: {
      detected: true,
      confidence: 0.92,
      bounding_box: {
        x: 0.2,
        y: 0.18,
        width: 0.45,
        height: 0.52,
      },
    },
    landmarks: {
      face_detected: true,
      point_count: 478,
      yaw: 4.2,
      pitch: -2.1,
      smile_ratio: 0.34,
      average_ear: 0.27,
    },
    liveness: {
      current_step: "open_mouth",
      step_progress: 0.6,
      message: "Open your mouth",
    },
  },
};

export const sampleVerificationResult: VerificationResult = {
  session_id: "sess_123",
  status: "verified",
  human: true,
  challenge_type: "turn_right",
  challenge_sequence: ["open_mouth", "turn_right"],
  current_challenge_index: 1,
  total_challenges: 2,
  completed_challenges: ["open_mouth", "turn_right"],
  confidence: 0.94,
  spoof_score: 0.03,
  max_spoof_score: 0.05,
  proof_id: "0xproof",
  transaction_digest: "0xtxn_123abc456def7890",
  proof_operation: "minted",
  chain_network: "sui-testnet",
  walrus_blob_id: "walrus_blob_123",
  walrus_blob_object_id: "0xwalrusobject123",
  seal_identity: "seal_identity_sess_123",
  evidence_schema_version: 1,
  model_hash: "sha256:verifier-bundle-123",
  blob_id: "walrus_blob_123",
  expires_at: "2026-07-16T14:00:00Z",
};

export const sampleEvidenceBlob: EvidenceBlob = {
  session_id: "sess_123",
  wallet_address: "0xabc123",
  challenge_type: "open_mouth",
  frame_hashes: ["sha256:frame-01", "sha256:frame-02"],
  landmark_snapshot: {
    source: "mediapipe",
    frame_index: 18,
  },
  spoof_score_summary: {
    max: 0.1,
    final: 0.03,
  },
  model_hashes: {
    antispoof: "sha256:antispoof-model",
    face_detector: "sha256:face-detector-model",
  },
  evidence_schema_version: 1,
  captured_at: "2026-04-17T14:00:00Z",
};

export const sampleSessionRecordResponse: SessionRecordResponse = {
  session_id: "sess_123",
  status: "verified",
  challenge_type: "turn_right",
  challenge_sequence: ["open_mouth", "turn_right"],
  current_challenge_index: 1,
  total_challenges: 2,
  completed_challenges: ["open_mouth", "turn_right"],
  created_at: "2026-04-17T13:55:00Z",
  expires_at: "2026-04-17T14:00:00Z",
  result: sampleVerificationResult,
};

export const sampleHealthResponse: HealthResponse = {
  status: "ready",
  redis: "ready",
  models: "ready",
  chain_adapter: "mock",
  storage_adapter: "mock",
  encryption_adapter: "mock",
  tuning: {
    minimum_step_frames: 4,
    blink_closed_threshold: 0.21,
    blink_open_threshold: 0.27,
    blink_min_closed_frames: 1,
    turn_yaw_threshold_degrees: 12,
    turn_offset_threshold: 0.085,
    nod_pitch_threshold: 6,
    nod_pitch_ratio_threshold: 0.045,
    smile_ratio_threshold: 0.36,
  },
};

export const sampleWsClientEvents: Record<string, WsClientEvent> = {
  frame: {
    type: "frame",
    timestamp: "2026-04-17T14:00:01Z",
    image_base64: "ZmFrZV9mcmFtZQ==",
  },
  heartbeat: {
    type: "heartbeat",
    timestamp: "2026-04-17T14:00:02Z",
  },
  finalize: {
    type: "finalize",
    timestamp: "2026-04-17T14:00:03Z",
  },
};

export const sampleWsServerEvents: Record<string, WsServerEvent> = {
  progress: {
    type: "progress",
    payload: {
      session_id: "sess_123",
      status: "streaming",
      challenge_type: "open_mouth",
      challenge_sequence: ["open_mouth", "turn_right"],
      current_challenge_index: 0,
      total_challenges: 2,
      completed_challenges: [],
      step_status: "active",
      progress: 0.5,
      finalize_ready: false,
      frames_processed: 10,
      message: "Keep your face centered",
      debug: {
        face_detection: {
          detected: true,
          confidence: 0.9,
        },
        liveness: {
          current_step: "open_mouth",
          step_progress: 0.5,
          message: "Open your mouth",
        },
      },
    },
  },
  verified: {
    type: "verified",
    payload: {
      session_id: "sess_123",
      status: "verified",
      human: true,
      challenge_type: "turn_right",
      challenge_sequence: ["open_mouth", "turn_right"],
      current_challenge_index: 1,
      total_challenges: 2,
      completed_challenges: ["open_mouth", "turn_right"],
      confidence: 0.94,
      spoof_score: 0.03,
      max_spoof_score: 0.05,
      proof_id: "0xproof",
      transaction_digest: "0xtxn_123abc456def7890",
      proof_operation: "minted",
      chain_network: "sui-testnet",
      walrus_blob_id: "walrus_blob_123",
      walrus_blob_object_id: "0xwalrusobject123",
      seal_identity: "seal_identity_sess_123",
      evidence_schema_version: 1,
      model_hash: "sha256:verifier-bundle-123",
      blob_id: "walrus_blob_123",
      expires_at: "2026-07-16T14:00:00Z",
    },
  },
  failed: {
    type: "failed",
    payload: {
      session_id: "sess_124",
      status: "failed",
      human: false,
      challenge_type: "open_mouth",
      challenge_sequence: ["open_mouth", "turn_right"],
      current_challenge_index: 0,
      total_challenges: 2,
      completed_challenges: [],
      confidence: 0.21,
      spoof_score: 0.86,
      max_spoof_score: 0.96,
      failure_reason: "spoof_detected",
    },
  },
};
