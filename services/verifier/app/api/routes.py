from fastapi import APIRouter, Depends, Request, status

from app.sessions.models import (
    CalibrationAppendRequest,
    CalibrationAppendResponse,
    HealthResponse,
    SessionCreateRequest,
    SessionCreateResponse,
    SessionResponse,
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
