from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session as sqlSession
from sse_starlette.sse import EventSourceResponse
import logging

from ..infra.database import get_db
from ..schemas.chat import ChatRequest
from ..services.chat import ChatService

router = APIRouter(prefix="/sessions/{session_id}/chat", tags=["chat"])
logger = logging.getLogger(__name__)

def get_chat_service(db: sqlSession = Depends(get_db)) -> ChatService:
    return ChatService(db)

@router.post("")
async def chat_message(
    session_id: str,
    request: ChatRequest,
    service: ChatService = Depends(get_chat_service)
):
    """
    Stream a chat response from the agent.

    This endpoint:
    1. Validates the session exists.
    2. Checks if a worker instance is running for this session; spawns one if not.
    3. Persists the user message to the database.
    4. Proxies the message to the worker agent.
    5. Streams the agent's response (text, tool use, thinking) via Server-Sent Events (SSE).
    """
    event_generator = await service.run_chat(session_id, request)
    return EventSourceResponse(event_generator)
