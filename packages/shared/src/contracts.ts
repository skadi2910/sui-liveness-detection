import type {
  ChallengeType,
  HealthComponentStatus,
  SessionStatus,
  VerificationMode,
} from "./values.js";

export type StepStatus = "pending" | "active" | "completed";

export interface DebugFaceBoundingBox {
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface VerificationDebugPayload {
  face_detection?: {
    detected?: boolean;
    confidence?: number;
    bounding_box?: DebugFaceBoundingBox | null;
  };
  quality?: {
    passed?: boolean;
    score?: number;
    primary_issue?: string | null;
    feedback?: string[];
    checks?: Record<string, boolean>;
    metrics?: Record<string, number | string | boolean | null>;
  };
  landmark_spotcheck?: {
    enforced?: boolean;
    passed?: boolean;
    message?: string;
    mismatch_pixels?: number | null;
    threshold_pixels?: number | null;
    anchors_used?: number;
    landmark_center?: Record<string, number> | null;
    face_center?: Record<string, number> | null;
  };
  landmarks?: {
    face_detected?: boolean;
    point_count?: number;
    yaw?: number | null;
    pitch?: number | null;
    smile_ratio?: number | null;
    average_ear?: number | null;
  };
  liveness?: {
    current_step?: ChallengeType | null;
    step_progress?: number;
    message?: string;
  };
  antispoof?: {
    passed?: boolean | null;
    spoof_score?: number | null;
    max_spoof_score?: number | null;
    frames_processed?: number;
    message?: string;
    preview?: boolean;
  };
  deepfake?: {
    enabled?: boolean;
    enforced?: boolean;
    score?: number | null;
    max_score?: number | null;
    frames_processed?: number;
    message?: string;
    preview?: boolean;
  };
}

export interface ClientInfo {
  platform: string;
  user_agent: string;
}

export interface AttackAnalysis {
  failure_category: string;
  suspected_attack_family: string;
  presentation_attack_detected: boolean;
  presentation_attack_score: number;
  presentation_attack_peak?: number | null;
  deepfake_detected: boolean;
  deepfake_score?: number | null;
  deepfake_peak?: number | null;
  note: string;
}

export interface CreateSessionRequest {
  wallet_address: string;
  client: ClientInfo;
  challenge_sequence?: ChallengeType[];
}

export interface CreateSessionResponse {
  session_id: string;
  status: SessionStatus;
  challenge_type: ChallengeType;
  challenge_sequence: ChallengeType[];
  current_challenge_index: number;
  total_challenges: number;
  completed_challenges: ChallengeType[];
  expires_at: string;
  ws_url: string;
}

export interface LandmarkSnapshot {
  source: string;
  frame_index: number;
}

export interface SpoofScoreSummary {
  max: number;
  final: number;
}

export interface ModelHashes {
  antispoof: string;
  face_detector: string;
}

export interface EvidenceBlob {
  session_id: string;
  wallet_address: string;
  challenge_type: ChallengeType;
  frame_hashes: string[];
  landmark_snapshot: LandmarkSnapshot;
  spoof_score_summary: SpoofScoreSummary;
  model_hashes: ModelHashes;
  captured_at: string;
}

export interface VerificationProgress {
  session_id: string;
  status: SessionStatus;
  challenge_type: ChallengeType;
  challenge_sequence: ChallengeType[];
  current_challenge_index: number;
  total_challenges: number;
  completed_challenges: ChallengeType[];
  step_status: StepStatus;
  progress: number;
  frames_processed: number;
  message: string;
  debug?: VerificationDebugPayload;
}

export interface VerificationResult {
  session_id: string;
  status: Extract<SessionStatus, "verified" | "failed" | "expired">;
  evaluation_mode?: VerificationMode;
  human: boolean;
  challenge_type: ChallengeType;
  challenge_sequence: ChallengeType[];
  current_challenge_index: number;
  total_challenges: number;
  completed_challenges: ChallengeType[];
  confidence: number;
  spoof_score: number;
  max_spoof_score?: number;
  deepfake_score?: number | null;
  max_deepfake_score?: number | null;
  deepfake_frames_processed?: number;
  deepfake_message?: string | null;
  deepfake_enabled?: boolean;
  attack_analysis?: AttackAnalysis | null;
  proof_id?: string;
  blob_id?: string;
  expires_at?: string;
  failure_reason?: string;
}

export interface SessionRecordResponse {
  session_id: string;
  status: SessionStatus;
  challenge_type: ChallengeType;
  challenge_sequence: ChallengeType[];
  current_challenge_index: number;
  total_challenges: number;
  completed_challenges: ChallengeType[];
  created_at: string;
  expires_at: string;
  result?: VerificationResult;
}

export interface HealthResponse {
  status: HealthComponentStatus;
  redis: HealthComponentStatus;
  models: HealthComponentStatus;
  chain_adapter: HealthComponentStatus;
  storage_adapter: HealthComponentStatus;
  encryption_adapter: HealthComponentStatus;
  model_details?: {
    face_detector?: {
      ready?: boolean;
      runtime?: string;
    };
    antispoof?: {
      ready?: boolean;
      runtime?: string;
      threshold?: number;
      hard_fail_threshold?: number;
    };
    deepfake?: {
      enabled?: boolean;
      ready?: boolean;
      runtime?: string;
      threshold?: number;
      enforced?: boolean;
      sample_frames?: number;
      model_hash?: string | null;
    };
  };
  tuning?: {
    minimum_step_frames?: number;
    blink_closed_threshold?: number;
    blink_open_threshold?: number;
    blink_min_closed_frames?: number;
    quality_blur_threshold?: number;
    quality_min_face_size?: number;
    quality_max_yaw_degrees?: number;
    quality_max_pitch_degrees?: number;
    quality_min_brightness?: number;
    quality_max_brightness?: number;
    turn_yaw_threshold_degrees?: number;
    turn_offset_threshold?: number;
    nod_pitch_threshold?: number;
    nod_pitch_ratio_threshold?: number;
    smile_ratio_threshold?: number;
    deepfake_threshold?: number;
    deepfake_sample_frames?: number;
    deepfake_enforced?: boolean;
  };
}

export interface AdminFramePayload {
  frame_index?: number;
  timestamp?: string;
  image_base64?: string | null;
  landmarks?: Record<string, unknown>;
  metadata?: Record<string, unknown>;
}

export interface AdminEvaluateFrameRequest {
  frame: AdminFramePayload;
  challenge_type?: ChallengeType;
  mode?: VerificationMode;
}

export interface AdminEvaluateFrameResponse {
  challenge_type: ChallengeType;
  evaluation_mode: VerificationMode;
  accepted_for_liveness: boolean;
  accepted_for_spoof: boolean;
  face_detection: Record<string, unknown>;
  quality: Record<string, unknown>;
  landmark_spotcheck: Record<string, unknown>;
  liveness: Record<string, unknown>;
  antispoof: Record<string, unknown>;
  deepfake: Record<string, unknown>;
}

export interface AdminEvaluateSessionRequest {
  frames: AdminFramePayload[];
  challenge_type?: ChallengeType;
  mode?: VerificationMode;
}

export interface AdminEvaluateSessionResponse {
  challenge_type: ChallengeType;
  evaluation_mode: VerificationMode;
  frames_processed: number;
  accepted_frame_indices: number[];
  face_detected: boolean;
  quality_frames_available: boolean;
  face_detection: Record<string, unknown>;
  quality: Record<string, unknown>;
  landmark_spotcheck: Record<string, unknown>;
  liveness: Record<string, unknown>;
  antispoof: Record<string, unknown>;
  deepfake: Record<string, unknown>;
  verdict_preview: {
    human: boolean;
    failure_reason: string | null;
    mode: VerificationMode;
    attack_analysis?: AttackAnalysis | null;
  };
}
