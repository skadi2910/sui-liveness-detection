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
    verifier_liveness_blink_closed_threshold: float = Field(
        default=0.21,
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
        default=18.0,
        alias="VERIFIER_LIVENESS_TURN_YAW_THRESHOLD_DEGREES",
    )
    verifier_liveness_turn_offset_threshold: float = Field(
        default=0.085,
        alias="VERIFIER_LIVENESS_TURN_OFFSET_THRESHOLD",
    )
    verifier_liveness_mouth_open_threshold: float = Field(
        default=0.28,
        alias="VERIFIER_LIVENESS_MOUTH_OPEN_THRESHOLD",
    )
    verifier_liveness_nod_pitch_threshold: float = Field(
        default=10.0,
        alias="VERIFIER_LIVENESS_NOD_PITCH_THRESHOLD",
    )
    verifier_liveness_nod_pitch_ratio_threshold: float = Field(
        default=0.08,
        alias="VERIFIER_LIVENESS_NOD_PITCH_RATIO_THRESHOLD",
    )
    verifier_liveness_smile_ratio_threshold: float = Field(
        default=0.36,
        alias="VERIFIER_LIVENESS_SMILE_RATIO_THRESHOLD",
    )
    verifier_liveness_motion_min_displacement: float = Field(
        default=0.002,
        alias="VERIFIER_LIVENESS_MOTION_MIN_DISPLACEMENT",
    )
    verifier_liveness_motion_max_still_ratio: float = Field(
        default=0.8,
        alias="VERIFIER_LIVENESS_MOTION_MAX_STILL_RATIO",
    )
    verifier_liveness_motion_min_transitions: int = Field(
        default=4,
        alias="VERIFIER_LIVENESS_MOTION_MIN_TRANSITIONS",
    )
    verifier_liveness_minimum_step_frames: int = Field(
        default=4,
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
    verifier_chain_adapter_enabled: bool = Field(
        default=False,
        alias="VERIFIER_CHAIN_ADAPTER_ENABLED",
    )
    verifier_storage_adapter_enabled: bool = Field(
        default=False,
        alias="VERIFIER_STORAGE_ADAPTER_ENABLED",
    )
    verifier_encryption_adapter_enabled: bool = Field(
        default=False,
        alias="VERIFIER_ENCRYPTION_ADAPTER_ENABLED",
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


@lru_cache
def get_settings() -> Settings:
    return Settings()


def resolve_data_path(path: str) -> Path:
    candidate = Path(path).expanduser()
    if candidate.is_absolute():
        return candidate
    return (Path.cwd() / candidate).resolve()
