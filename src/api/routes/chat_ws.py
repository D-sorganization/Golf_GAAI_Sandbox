"""WebSocket and REST routes for AI chat streaming."""

from __future__ import annotations

import contextlib
from typing import Any

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect

from src.api.dependencies import get_chat_service
from src.api.services.chat_service import ChatService
from src.shared.python.core.contracts import precondition
from src.shared.python.logging_pkg.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter()


def _resolve_session_id(chat_service: ChatService, session_id: str) -> str:
    """Return an existing or newly-created chat session id."""
    requested_session = None if session_id == "new" else session_id
    return chat_service.get_or_create_session(requested_session).session_id


async def _send_chat_message(
    websocket: WebSocket,
    chat_service: ChatService,
    session_id: str,
    msg: dict[str, Any],
) -> None:
    """Validate, persist, and stream a chat message response."""
    user_message = msg.get("message", "").strip()
    if not user_message:
        await websocket.send_json({"type": "error", "detail": "Empty message"})
        return

    try:
        chat_service.add_user_message(
            session_id, user_message, msg.get("engine_context")
        )
    except ValueError as exc:
        await websocket.send_json({"type": "error", "detail": str(exc)})
        return

    async for chunk in chat_service.stream_response(session_id):
        await websocket.send_json({"type": "chunk", "content": chunk})
    await websocket.send_json({"type": "complete", "session_id": session_id})


async def _send_history(
    websocket: WebSocket,
    chat_service: ChatService,
    session_id: str,
) -> None:
    """Send chat history for *session_id*."""
    messages = chat_service.get_session_history(session_id)
    await websocket.send_json({"type": "history", "messages": messages})


async def _create_new_session(
    websocket: WebSocket,
    chat_service: ChatService,
) -> str:
    """Create a fresh session and notify the WebSocket client."""
    session_id = chat_service.get_or_create_session(None).session_id
    await websocket.send_json({"type": "session_created", "session_id": session_id})
    return session_id


async def _handle_chat_action(
    websocket: WebSocket,
    chat_service: ChatService,
    session_id: str,
    msg: dict[str, Any],
) -> str:
    """Handle one inbound chat action and return the active session id."""
    action = msg.get("action")
    if action == "send":
        await _send_chat_message(websocket, chat_service, session_id, msg)
    elif action == "history":
        await _send_history(websocket, chat_service, session_id)
    elif action == "new_session":
        session_id = await _create_new_session(websocket, chat_service)
    else:
        await websocket.send_json(
            {"type": "error", "detail": f"Unknown action: {action}"}
        )
    return session_id


async def _chat_receive_loop(
    websocket: WebSocket,
    chat_service: ChatService,
    session_id: str,
) -> None:
    """Receive and dispatch chat actions until the client disconnects."""
    while True:
        msg = await websocket.receive_json()
        session_id = await _handle_chat_action(
            websocket, chat_service, session_id, msg
        )


@router.websocket("/ws/chat/{session_id}")
async def chat_stream(
    websocket: WebSocket,
    session_id: str = "new",
    chat_service: ChatService = Depends(get_chat_service),
) -> None:
    """Stream AI chat over WebSocket.

    Protocol:
        Client -> Server:
            {"action": "send", "message": "...", "engine_context": "mujoco"}
            {"action": "history"}
            {"action": "new_session"}

        Server -> Client:
            {"type": "session_info", "session_id": "..."}
            {"type": "chunk", "content": "..."}
            {"type": "complete", "session_id": "..."}
            {"type": "history", "messages": [...]}
            {"type": "error", "detail": "..."}
    """
    if not (websocket is not None):
        raise ValueError("websocket must be provided")
    await websocket.accept()
    session_id = _resolve_session_id(chat_service, session_id)
    await websocket.send_json({"type": "session_info", "session_id": session_id})

    try:
        await _chat_receive_loop(websocket, chat_service, session_id)
    except WebSocketDisconnect:
        logger.debug("Chat WebSocket disconnected: session=%s", session_id)
    except (ConnectionError, TimeoutError, OSError) as e:
        logger.error("Chat WebSocket error: %s", e)
        with contextlib.suppress(ConnectionError, TimeoutError, OSError):
            await websocket.send_json({"type": "error", "detail": str(e)})


# ── REST fallback endpoints ──────────────────────────────────────────


@router.get("/chat/sessions")
async def list_sessions(
    chat_service: ChatService = Depends(get_chat_service),
) -> list[dict]:
    """List all active chat sessions."""
    return chat_service.list_sessions()


@router.get("/chat/sessions/{session_id}/history")
@precondition(
    lambda session_id, **_kwargs: session_id is not None
    and len(session_id.strip()) > 0,
    "Session ID must be a non-empty string",
)
async def get_history(
    session_id: str,
    chat_service: ChatService = Depends(get_chat_service),
) -> dict:
    """Get message history for a session."""
    messages = chat_service.get_session_history(session_id)
    return {"session_id": session_id, "messages": messages}
