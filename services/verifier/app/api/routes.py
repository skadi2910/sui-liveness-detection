from fastapi import APIRouter, Depends, Request, status

from app.sessions.models import (
    AdminEvaluateFrameRequest,
    AdminEvaluateFrameResponse,
    AdminEvaluateSessionRequest,
    AdminEvaluateSessionResponse,
    CalibrationAppendRequest,
    CalibrationAppendResponse,
    CancelProofClaimRequest,
    CompleteProofClaimRequest,
    HealthResponse,
    PreparedProofClaim,
    SessionCreateRequest,
    SessionCreateResponse,
    SessionResponse,
    VerificationResult,
)
from app.sessions.service import VerificationSessionService

router = APIRouter(prefix="/api", tags=["verifier"])


def get_service(request: Request) -> VerificationSessionService:
    return request.app.state.session_service


@router.get("/health", response_model=HealthResponse)
async def health(service: VerificationSessionService = Depends(get_service)) -> HealthResponse:
    return await service.get_health()


@router.post(
    "/sessions",
    response_model=SessionCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_session(
    payload: SessionCreateRequest,
    service: VerificationSessionService = Depends(get_service),
) -> SessionCreateResponse:
    return await service.create_session(payload)


@router.get("/sessions/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: str,
    service: VerificationSessionService = Depends(get_service),
) -> SessionResponse:
    return await service.get_session(session_id)


@router.post("/sessions/{session_id}/mint", response_model=VerificationResult)
async def mint_session(
    session_id: str,
    service: VerificationSessionService = Depends(get_service),
) -> VerificationResult:
    return await service.mint_verified_session(session_id)


@router.post("/sessions/{session_id}/claim", response_model=PreparedProofClaim)
async def prepare_wallet_claim(
    session_id: str,
    service: VerificationSessionService = Depends(get_service),
) -> PreparedProofClaim:
    return await service.prepare_wallet_claim(session_id)


@router.post("/sessions/{session_id}/claim/complete", response_model=VerificationResult)
async def complete_wallet_claim(
    session_id: str,
    payload: CompleteProofClaimRequest,
    service: VerificationSessionService = Depends(get_service),
) -> VerificationResult:
    return await service.complete_wallet_claim(session_id, payload)


@router.post("/sessions/{session_id}/claim/cancel", response_model=VerificationResult)
async def cancel_wallet_claim(
    session_id: str,
    payload: CancelProofClaimRequest,
    service: VerificationSessionService = Depends(get_service),
) -> VerificationResult:
    return await service.cancel_wallet_claim(session_id, payload.reason)


@router.post("/calibration/append", response_model=CalibrationAppendResponse)
async def append_calibration_record(
    payload: CalibrationAppendRequest,
    service: VerificationSessionService = Depends(get_service),
) -> CalibrationAppendResponse:
    return await service.append_calibration_record(payload.record)


@router.post("/attack-matrix/append", response_model=CalibrationAppendResponse)
async def append_attack_matrix_record(
    payload: CalibrationAppendRequest,
    service: VerificationSessionService = Depends(get_service),
) -> CalibrationAppendResponse:
    return await service.append_attack_matrix_record(payload.record)


@router.post("/admin/calibration/append", response_model=CalibrationAppendResponse)
async def append_calibration_record_admin(
    payload: CalibrationAppendRequest,
    service: VerificationSessionService = Depends(get_service),
) -> CalibrationAppendResponse:
    return await service.append_calibration_record(payload.record)


@router.post("/admin/attack-matrix/append", response_model=CalibrationAppendResponse)
async def append_attack_matrix_record_admin(
    payload: CalibrationAppendRequest,
    service: VerificationSessionService = Depends(get_service),
) -> CalibrationAppendResponse:
    return await service.append_attack_matrix_record(payload.record)


@router.post("/admin/evaluate/frame", response_model=AdminEvaluateFrameResponse)
async def evaluate_frame(
    payload: AdminEvaluateFrameRequest,
    service: VerificationSessionService = Depends(get_service),
) -> AdminEvaluateFrameResponse:
    return await service.evaluate_frame(payload)


@router.post("/admin/evaluate/session", response_model=AdminEvaluateSessionResponse)
async def evaluate_session(
    payload: AdminEvaluateSessionRequest,
    service: VerificationSessionService = Depends(get_service),
) -> AdminEvaluateSessionResponse:
    return await service.evaluate_session(payload)
