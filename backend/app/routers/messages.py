from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..infra.database import get_db
from ..schemas import MessageResponse
from ..services.session import SessionService
from ..services.message import MessageService

router = APIRouter(prefix="/sessions/{session_id}/messages", tags=["messages"])

def get_message_service(db: Session = Depends(get_db)) -> MessageService:
    return MessageService(db)

def get_session_service(db: Session = Depends(get_db)) -> SessionService:
    return SessionService(db)

@router.get("", response_model=List[MessageResponse])
def get_session_messages(
    session_id: str, 
    skip: int = 0, 
    limit: int = 100, 
    service: MessageService = Depends(get_message_service),
    session_service: SessionService = Depends(get_session_service)
):
    """
    Retrieve messages for a specific session.
    
    - **session_id**: The ID of the session.
    - **skip**: Number of messages to skip.
    - **limit**: Maximum number of messages to return.
    """
    session = session_service.get_session(session_id)

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return service.get_messages(session_id, skip=skip, limit=limit)
