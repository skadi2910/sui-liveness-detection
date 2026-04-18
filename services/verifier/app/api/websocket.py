from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, status

from app.sessions.models import ClientEventType, VerificationMode, WebSocketClientEvent
from app.sessions.service import VerificationSessionService

router = APIRouter(tags=["websocket"])


@router.websocket("/ws/sessions/{session_id}/stream")
@router.websocket("/ws/verify/{session_id}")
async def verify_session(websocket: WebSocket, session_id: str) -> None:
    service: VerificationSessionService = websocket.app.state.session_service
    await websocket.accept()

    try:
        session = await service.mark_ready(session_id)
        await websocket.send_json(service.session_ready_event(session))

        while True:
            raw_payload = await websocket.receive_json()
            event = WebSocketClientEvent.model_validate(raw_payload)

            if event.type == ClientEventType.FRAME:
                session = await service.record_frame(session_id, event)
                await websocket.send_json(service.challenge_update_event(session))
                await websocket.send_json(service.progress_event(session))
                continue

            if event.type == ClientEventType.LANDMARKS:
                session = await service.record_landmarks(session_id, event)
                await websocket.send_json(service.progress_event(session))
                continue

            if event.type == ClientEventType.HEARTBEAT:
                session = await service.record_heartbeat(session_id)
                await websocket.send_json(service.progress_event(session))
                continue

            if event.type == ClientEventType.FINALIZE:
                await websocket.send_json(service.processing_event(session_id))
                result = await service.finalize_session(
                    session_id,
                    mode=event.mode or VerificationMode.FULL,
                )
                await websocket.send_json(service.terminal_event(result))
                break
    except WebSocketDisconnect:
        return
    except HTTPException as exc:
        await websocket.send_json(
            service.error_event(
                str(exc.detail),
                session_id=session_id,
            )
        )
        await websocket.close(code=1013)
    except Exception as exc:
        await websocket.send_json(service.error_event(str(exc), session_id=session_id))
        await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
