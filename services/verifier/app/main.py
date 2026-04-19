from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.adapters.evidence_encryptor import MockEvidenceEncryptor, SealCommandEvidenceEncryptor
from app.adapters.evidence_store import InMemoryEvidenceStore, WalrusCliEvidenceStore
from app.adapters.proof_minter import MockProofMinter, SuiCliProofMinter
from app.api.routes import router as api_router
from app.api.websocket import router as websocket_router
from app.core.config import Settings, get_settings, resolve_data_path
from app.core.logging import configure_logging
from app.pipeline.antispoof import build_antispoof_evaluator
from app.pipeline.deepfake import build_deepfake_evaluator
from app.pipeline.evidence import EvidenceAssembler
from app.pipeline.face import build_face_detector
from app.pipeline.human_face import build_human_face_evaluator
from app.pipeline.liveness import MockLivenessEvaluator
from app.pipeline.quality import HeuristicFaceQualityEvaluator
from app.sessions.redis_store import RedisSessionStore
from app.sessions.service import VerificationSessionService


def _build_proof_minter(settings: Settings):
    if settings.effective_chain_adapter_mode == "sui_cli":
        package_id = settings.verifier_sui_package_id
        registry_object_id = settings.verifier_sui_registry_object_id
        verifier_cap_object_id = settings.verifier_sui_verifier_cap_object_id
        if not package_id or not registry_object_id or not verifier_cap_object_id:
            raise ValueError(
                "Sui CLI adapter requires VERIFIER_SUI_PACKAGE_ID, "
                "VERIFIER_SUI_REGISTRY_OBJECT_ID, and VERIFIER_SUI_VERIFIER_CAP_OBJECT_ID"
            )
        return SuiCliProofMinter(
            package_id=package_id,
            registry_object_id=registry_object_id,
            verifier_cap_object_id=verifier_cap_object_id,
            module_name=settings.verifier_sui_module_name,
            network=settings.verifier_sui_network,
            client_config_path=(
                str(resolve_data_path(settings.verifier_sui_client_config_path))
                if settings.verifier_sui_client_config_path
                else None
            ),
            env_alias=settings.verifier_sui_env_alias,
            expected_active_address=settings.verifier_sui_expected_active_address,
            gas_budget=settings.verifier_sui_gas_budget,
            proof_ttl_days=settings.verifier_sui_proof_ttl_days,
        )
    return MockProofMinter(
        proof_ttl_days=settings.verifier_sui_proof_ttl_days,
        minimum_confidence=settings.verifier_proof_minimum_confidence,
    )


def _build_evidence_store(settings: Settings):
    if settings.effective_storage_adapter_mode == "walrus_cli":
        return WalrusCliEvidenceStore(
            walrus_binary=settings.verifier_walrus_binary,
            config_path=(
                str(resolve_data_path(settings.verifier_walrus_config_path))
                if settings.verifier_walrus_config_path
                else None
            ),
            context=settings.verifier_walrus_context,
            wallet_path=(
                str(resolve_data_path(settings.verifier_walrus_wallet_path))
                if settings.verifier_walrus_wallet_path
                else None
            ),
            gas_budget=settings.verifier_walrus_gas_budget,
            storage_epochs=settings.verifier_walrus_storage_epochs,
            force_store=settings.verifier_walrus_force_store,
            deletable=settings.verifier_walrus_deletable,
        )
    return InMemoryEvidenceStore()


def _build_evidence_encryptor(settings: Settings):
    if settings.effective_encryption_adapter_mode == "seal_command":
        if not settings.verifier_seal_encrypt_command:
            raise ValueError(
                "Seal command adapter requires VERIFIER_SEAL_ENCRYPT_COMMAND"
            )
        helper_env = {
            "VERIFIER_SUI_PACKAGE_ID": settings.verifier_sui_package_id or "",
            "VERIFIER_SUI_NETWORK": settings.verifier_sui_network,
            "VERIFIER_SEAL_POLICY_VERSION": settings.verifier_seal_policy_version,
        }
        if getattr(settings, "verifier_seal_sui_base_url", None):
            helper_env["VERIFIER_SEAL_SUI_BASE_URL"] = settings.verifier_seal_sui_base_url
        if getattr(settings, "verifier_seal_sui_network", None):
            helper_env["VERIFIER_SEAL_SUI_NETWORK"] = settings.verifier_seal_sui_network
        if getattr(settings, "verifier_seal_server_configs", None):
            helper_env["VERIFIER_SEAL_SERVER_CONFIGS"] = settings.verifier_seal_server_configs
        if getattr(settings, "verifier_seal_threshold", None) is not None:
            helper_env["VERIFIER_SEAL_THRESHOLD"] = str(settings.verifier_seal_threshold)
        if getattr(settings, "verifier_seal_verify_key_servers", None) is not None:
            helper_env["VERIFIER_SEAL_VERIFY_KEY_SERVERS"] = (
                "true" if settings.verifier_seal_verify_key_servers else "false"
            )
        return SealCommandEvidenceEncryptor(
            encrypt_command=settings.verifier_seal_encrypt_command,
            decrypt_command=settings.verifier_seal_decrypt_command,
            command_cwd=(
                str(resolve_data_path(settings.verifier_seal_command_cwd))
                if settings.verifier_seal_command_cwd
                else None
            ),
            helper_env=helper_env,
            policy_version=settings.verifier_seal_policy_version,
        )
    return MockEvidenceEncryptor()


def build_lifespan(settings: Settings):
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        configure_logging(settings.verifier_log_level)
        store = RedisSessionStore(settings.verifier_redis_url)
        face_detector = build_face_detector(
            mode=settings.verifier_face_model_mode,
            model_path=settings.verifier_face_model_path,
            confidence_threshold=settings.verifier_face_detection_threshold,
            image_size=settings.verifier_face_image_size,
        )
        antispoof_evaluator = build_antispoof_evaluator(
            mode=settings.verifier_antispoof_model_mode,
            model_dir=settings.verifier_antispoof_model_dir,
            threshold=settings.verifier_antispoof_threshold,
            hard_fail_threshold=settings.verifier_antispoof_hard_fail_threshold,
        )
        deepfake_evaluator = build_deepfake_evaluator(
            mode=settings.verifier_deepfake_model_mode,
            enabled=settings.verifier_deepfake_enabled,
            model_path=settings.verifier_deepfake_model_path,
            threshold=settings.verifier_deepfake_threshold,
            enforce_decision=settings.verifier_deepfake_enforce_decision,
        )
        human_face_evaluator = build_human_face_evaluator(
            mode=settings.verifier_human_face_model_mode,
            enabled=settings.verifier_human_face_enabled,
            model_id=settings.verifier_human_face_model_id,
            threshold=settings.verifier_human_face_threshold,
            enforce_decision=settings.verifier_human_face_enforce_decision,
        )
        app.state.settings = settings
        app.state.session_store = store
        app.state.session_service = VerificationSessionService(
            store=store,
            settings=settings,
            face_detector=face_detector,
            face_quality_evaluator=HeuristicFaceQualityEvaluator(
                blur_threshold=settings.verifier_quality_blur_threshold,
                min_face_size=settings.verifier_quality_min_face_size,
                max_yaw_degrees=settings.verifier_quality_max_yaw_degrees,
                max_pitch_degrees=settings.verifier_quality_max_pitch_degrees,
                min_brightness=settings.verifier_quality_min_brightness,
                max_brightness=settings.verifier_quality_max_brightness,
            ),
            liveness_evaluator=MockLivenessEvaluator(
                blink_closed_threshold=settings.verifier_liveness_blink_closed_threshold,
                blink_open_threshold=settings.verifier_liveness_blink_open_threshold,
                blink_min_closed_frames=settings.verifier_liveness_blink_min_closed_frames,
                turn_yaw_threshold_degrees=settings.verifier_liveness_turn_yaw_threshold_degrees,
                turn_offset_threshold=settings.verifier_liveness_turn_offset_threshold,
                mouth_open_threshold=settings.verifier_liveness_mouth_open_threshold,
                nod_pitch_threshold=settings.verifier_liveness_nod_pitch_threshold,
                nod_pitch_ratio_threshold=settings.verifier_liveness_nod_pitch_ratio_threshold,
                smile_ratio_threshold=settings.verifier_liveness_smile_ratio_threshold,
                motion_min_displacement=settings.verifier_liveness_motion_min_displacement,
                motion_max_still_ratio=settings.verifier_liveness_motion_max_still_ratio,
                motion_min_transitions=settings.verifier_liveness_motion_min_transitions,
            ),
            antispoof_evaluator=antispoof_evaluator,
            deepfake_evaluator=deepfake_evaluator,
            human_face_evaluator=human_face_evaluator,
            evidence_assembler=EvidenceAssembler(),
            proof_minter=_build_proof_minter(settings),
            evidence_store=_build_evidence_store(settings),
            evidence_encryptor=_build_evidence_encryptor(settings),
        )
        yield

    return lifespan


def create_app(settings: Settings | None = None) -> FastAPI:
    active_settings = settings or get_settings()
    app = FastAPI(
        title="Sui Human Verifier",
        version="0.1.0",
        lifespan=build_lifespan(active_settings),
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=active_settings.verifier_allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(api_router)
    app.include_router(websocket_router)
    return app


app = create_app()
