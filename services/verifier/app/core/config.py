from functools import lru_cache
import json
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    verifier_env: str = Field(default="development", alias="VERIFIER_ENV")
    verifier_host: str = Field(default="0.0.0.0", alias="VERIFIER_HOST")
    verifier_port: int = Field(default=8000, alias="VERIFIER_PORT")
    verifier_log_level: str = Field(default="INFO", alias="VERIFIER_LOG_LEVEL")
    verifier_face_model_mode: str = Field(default="auto", alias="VERIFIER_FACE_MODEL_MODE")
    verifier_face_model_path: str | None = Field(default=None, alias="VERIFIER_FACE_MODEL_PATH")
    verifier_face_detection_threshold: float = Field(
        default=0.35,
        alias="VERIFIER_FACE_DETECTION_THRESHOLD",
    )
    verifier_face_image_size: int = Field(default=640, alias="VERIFIER_FACE_IMAGE_SIZE")
    verifier_quality_blur_threshold: float = Field(
        default=45.0,
        alias="VERIFIER_QUALITY_BLUR_THRESHOLD",
    )
    verifier_quality_min_face_size: int = Field(
        default=80,
        alias="VERIFIER_QUALITY_MIN_FACE_SIZE",
    )
    verifier_quality_max_yaw_degrees: float = Field(
        default=40.0,
        alias="VERIFIER_QUALITY_MAX_YAW_DEGREES",
    )
    verifier_quality_max_pitch_degrees: float = Field(
        default=30.0,
        alias="VERIFIER_QUALITY_MAX_PITCH_DEGREES",
    )
    verifier_quality_min_brightness: float = Field(
        default=40.0,
        alias="VERIFIER_QUALITY_MIN_BRIGHTNESS",
    )
    verifier_quality_max_brightness: float = Field(
        default=220.0,
        alias="VERIFIER_QUALITY_MAX_BRIGHTNESS",
    )
    verifier_human_face_enabled: bool = Field(
        default=True,
        alias="VERIFIER_HUMAN_FACE_ENABLED",
    )
    verifier_human_face_model_mode: str = Field(
        default="auto",
        alias="VERIFIER_HUMAN_FACE_MODEL_MODE",
    )
    verifier_human_face_model_id: str | None = Field(
        default="openai/clip-vit-base-patch32",
        alias="VERIFIER_HUMAN_FACE_MODEL_ID",
    )
    verifier_human_face_threshold: float = Field(
        default=0.55,
        alias="VERIFIER_HUMAN_FACE_THRESHOLD",
    )
    verifier_human_face_enforce_decision: bool = Field(
        default=True,
        alias="VERIFIER_HUMAN_FACE_ENFORCE_DECISION",
    )
    verifier_landmark_spotcheck_max_center_mismatch_px: float = Field(
        default=96.0,
        alias="VERIFIER_LANDMARK_SPOTCHECK_MAX_CENTER_MISMATCH_PX",
    )
    verifier_antispoof_model_mode: str = Field(
        default="auto",
        alias="VERIFIER_ANTISPOOF_MODEL_MODE",
    )
    verifier_antispoof_model_dir: str | None = Field(
        default=None,
        alias="VERIFIER_ANTISPOOF_MODEL_DIR",
    )
    verifier_antispoof_threshold: float = Field(
        default=0.35,
        alias="VERIFIER_ANTISPOOF_THRESHOLD",
    )
    verifier_antispoof_hard_fail_threshold: float = Field(
        default=0.75,
        alias="VERIFIER_ANTISPOOF_HARD_FAIL_THRESHOLD",
    )
    verifier_deepfake_enabled: bool = Field(
        default=True,
        alias="VERIFIER_DEEPFAKE_ENABLED",
    )
    verifier_deepfake_model_mode: str = Field(
        default="auto",
        alias="VERIFIER_DEEPFAKE_MODEL_MODE",
    )
    verifier_deepfake_model_path: str | None = Field(
        default="models/deepfake/model_int8.onnx",
        alias="VERIFIER_DEEPFAKE_MODEL_PATH",
    )
    verifier_deepfake_threshold: float = Field(
        default=0.80,
        alias="VERIFIER_DEEPFAKE_THRESHOLD",
    )
    verifier_deepfake_sample_frames: int = Field(
        default=6,
        alias="VERIFIER_DEEPFAKE_SAMPLE_FRAMES",
    )
    verifier_deepfake_enforce_decision: bool = Field(
        default=True,
        alias="VERIFIER_DEEPFAKE_ENFORCE_DECISION",
    )
    verifier_proof_minimum_confidence: float = Field(
        default=0.35,
        alias="VERIFIER_PROOF_MINIMUM_CONFIDENCE",
    )
    verifier_liveness_blink_closed_threshold: float = Field(
        default=0.23,
        alias="VERIFIER_LIVENESS_BLINK_CLOSED_THRESHOLD",
    )
    verifier_liveness_blink_open_threshold: float = Field(
        default=0.27,
        alias="VERIFIER_LIVENESS_BLINK_OPEN_THRESHOLD",
    )
    verifier_liveness_blink_min_closed_frames: int = Field(
        default=1,
        alias="VERIFIER_LIVENESS_BLINK_MIN_CLOSED_FRAMES",
    )
    verifier_liveness_turn_yaw_threshold_degrees: float = Field(
        default=12.0,
        alias="VERIFIER_LIVENESS_TURN_YAW_THRESHOLD_DEGREES",
    )
    verifier_liveness_turn_offset_threshold: float = Field(
        default=0.065,
        alias="VERIFIER_LIVENESS_TURN_OFFSET_THRESHOLD",
    )
    verifier_liveness_mouth_open_threshold: float = Field(
        default=0.28,
        alias="VERIFIER_LIVENESS_MOUTH_OPEN_THRESHOLD",
    )
    verifier_liveness_nod_pitch_threshold: float = Field(
        default=6.0,
        alias="VERIFIER_LIVENESS_NOD_PITCH_THRESHOLD",
    )
    verifier_liveness_nod_pitch_ratio_threshold: float = Field(
        default=0.045,
        alias="VERIFIER_LIVENESS_NOD_PITCH_RATIO_THRESHOLD",
    )
    verifier_liveness_smile_ratio_threshold: float = Field(
        default=0.36,
        alias="VERIFIER_LIVENESS_SMILE_RATIO_THRESHOLD",
    )
    verifier_liveness_motion_min_displacement: float = Field(
        default=0.0015,
        alias="VERIFIER_LIVENESS_MOTION_MIN_DISPLACEMENT",
    )
    verifier_liveness_motion_max_still_ratio: float = Field(
        default=0.8,
        alias="VERIFIER_LIVENESS_MOTION_MAX_STILL_RATIO",
    )
    verifier_liveness_motion_min_transitions: int = Field(
        default=2,
        alias="VERIFIER_LIVENESS_MOTION_MIN_TRANSITIONS",
    )
    verifier_liveness_minimum_step_frames: int = Field(
        default=2,
        alias="VERIFIER_LIVENESS_MINIMUM_STEP_FRAMES",
    )
    verifier_session_ttl_seconds: int = Field(
        default=600,
        alias="VERIFIER_SESSION_TTL_SECONDS",
    )
    verifier_result_ttl_seconds: int = Field(
        default=600,
        alias="VERIFIER_RESULT_TTL_SECONDS",
    )
    verifier_calibration_output_path: str = Field(
        default="sample-data/calibration/local-dev.ndjson",
        alias="VERIFIER_CALIBRATION_OUTPUT_PATH",
    )
    verifier_attack_matrix_output_path: str = Field(
        default="sample-data/attack-matrix/local-dev.ndjson",
        alias="VERIFIER_ATTACK_MATRIX_OUTPUT_PATH",
    )
    verifier_allowed_origins: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:3001",
            "http://127.0.0.1:3001",
        ],
        alias="VERIFIER_ALLOWED_ORIGINS",
    )
    verifier_redis_url: str | None = Field(default=None, alias="VERIFIER_REDIS_URL")
    verifier_chain_adapter_mode: str | None = Field(
        default=None,
        alias="VERIFIER_CHAIN_ADAPTER_MODE",
    )
    verifier_chain_adapter_enabled: bool = Field(
        default=False,
        alias="VERIFIER_CHAIN_ADAPTER_ENABLED",
    )
    verifier_storage_adapter_mode: str | None = Field(
        default=None,
        alias="VERIFIER_STORAGE_ADAPTER_MODE",
    )
    verifier_storage_adapter_enabled: bool = Field(
        default=False,
        alias="VERIFIER_STORAGE_ADAPTER_ENABLED",
    )
    verifier_encryption_adapter_mode: str | None = Field(
        default=None,
        alias="VERIFIER_ENCRYPTION_ADAPTER_MODE",
    )
    verifier_encryption_adapter_enabled: bool = Field(
        default=False,
        alias="VERIFIER_ENCRYPTION_ADAPTER_ENABLED",
    )
    verifier_sui_client_config_path: str | None = Field(
        default=None,
        alias="VERIFIER_SUI_CLIENT_CONFIG_PATH",
    )
    verifier_sui_env_alias: str | None = Field(
        default=None,
        alias="VERIFIER_SUI_ENV_ALIAS",
    )
    verifier_sui_expected_active_address: str | None = Field(
        default=None,
        alias="VERIFIER_SUI_EXPECTED_ACTIVE_ADDRESS",
    )
    verifier_sui_package_id: str | None = Field(
        default=None,
        alias="VERIFIER_SUI_PACKAGE_ID",
    )
    verifier_sui_registry_object_id: str | None = Field(
        default=None,
        alias="VERIFIER_SUI_REGISTRY_OBJECT_ID",
    )
    verifier_sui_verifier_cap_object_id: str | None = Field(
        default=None,
        alias="VERIFIER_SUI_VERIFIER_CAP_OBJECT_ID",
    )
    verifier_sui_module_name: str = Field(
        default="proof_of_human",
        alias="VERIFIER_SUI_MODULE_NAME",
    )
    verifier_sui_network: str = Field(
        default="sui-testnet",
        alias="VERIFIER_SUI_NETWORK",
    )
    verifier_sui_gas_budget: int | None = Field(
        default=None,
        alias="VERIFIER_SUI_GAS_BUDGET",
    )
    verifier_sui_proof_ttl_days: int = Field(
        default=90,
        alias="VERIFIER_SUI_PROOF_TTL_DAYS",
    )
    verifier_sui_claim_ttl_seconds: int = Field(
        default=300,
        alias="VERIFIER_SUI_CLAIM_TTL_SECONDS",
    )
    verifier_walrus_binary: str = Field(default="walrus", alias="VERIFIER_WALRUS_BINARY")
    verifier_walrus_config_path: str | None = Field(
        default=None,
        alias="VERIFIER_WALRUS_CONFIG_PATH",
    )
    verifier_walrus_context: str | None = Field(
        default=None,
        alias="VERIFIER_WALRUS_CONTEXT",
    )
    verifier_walrus_wallet_path: str | None = Field(
        default=None,
        alias="VERIFIER_WALRUS_WALLET_PATH",
    )
    verifier_walrus_gas_budget: int | None = Field(
        default=None,
        alias="VERIFIER_WALRUS_GAS_BUDGET",
    )
    verifier_walrus_storage_epochs: int = Field(
        default=5,
        alias="VERIFIER_WALRUS_STORAGE_EPOCHS",
    )
    verifier_walrus_force_store: bool = Field(
        default=True,
        alias="VERIFIER_WALRUS_FORCE_STORE",
    )
    verifier_walrus_deletable: bool = Field(
        default=True,
        alias="VERIFIER_WALRUS_DELETABLE",
    )
    verifier_seal_encrypt_command: str | None = Field(
        default=None,
        alias="VERIFIER_SEAL_ENCRYPT_COMMAND",
    )
    verifier_seal_decrypt_command: str | None = Field(
        default=None,
        alias="VERIFIER_SEAL_DECRYPT_COMMAND",
    )
    verifier_seal_command_cwd: str | None = Field(
        default=None,
        alias="VERIFIER_SEAL_COMMAND_CWD",
    )
    verifier_seal_policy_version: str = Field(
        default="seal-v1",
        alias="VERIFIER_SEAL_POLICY_VERSION",
    )
    verifier_seal_server_configs: str | None = Field(
        default=None,
        alias="VERIFIER_SEAL_SERVER_CONFIGS",
    )
    verifier_seal_threshold: int | None = Field(
        default=None,
        alias="VERIFIER_SEAL_THRESHOLD",
    )
    verifier_seal_sui_network: str | None = Field(
        default=None,
        alias="VERIFIER_SEAL_SUI_NETWORK",
    )
    verifier_seal_sui_base_url: str | None = Field(
        default=None,
        alias="VERIFIER_SEAL_SUI_BASE_URL",
    )
    verifier_seal_verify_key_servers: bool | None = Field(
        default=None,
        alias="VERIFIER_SEAL_VERIFY_KEY_SERVERS",
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @field_validator("verifier_allowed_origins", mode="before")
    @classmethod
    def split_allowed_origins(cls, value: object) -> object:
        if isinstance(value, str):
            stripped = value.strip()
            if stripped.startswith("["):
                try:
                    parsed = json.loads(stripped)
                except json.JSONDecodeError:
                    parsed = None
                if isinstance(parsed, list):
                    return [str(item).strip() for item in parsed if str(item).strip()]
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @property
    def effective_chain_adapter_mode(self) -> str:
        if self.verifier_chain_adapter_mode:
            return self.verifier_chain_adapter_mode
        return "sui_cli" if self.verifier_chain_adapter_enabled else "mock"

    @property
    def effective_storage_adapter_mode(self) -> str:
        if self.verifier_storage_adapter_mode:
            return self.verifier_storage_adapter_mode
        return "walrus_cli" if self.verifier_storage_adapter_enabled else "memory"

    @property
    def effective_encryption_adapter_mode(self) -> str:
        if self.verifier_encryption_adapter_mode:
            return self.verifier_encryption_adapter_mode
        return "seal_command" if self.verifier_encryption_adapter_enabled else "mock"


@lru_cache
def get_settings() -> Settings:
    return Settings()


def resolve_data_path(path: str) -> Path:
    candidate = Path(path).expanduser()
    if candidate.is_absolute():
        return candidate
    return (Path.cwd() / candidate).resolve()
