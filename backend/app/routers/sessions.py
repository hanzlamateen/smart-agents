from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as sqlSession

from ..infra.database import get_db
from ..schemas import SessionCreate, SessionResponse, SessionUpdate, TitleGenerationRequest
from ..services.session import SessionService

router = APIRouter(prefix="/sessions", tags=["sessions"])

def get_session_service(db: sqlSession = Depends(get_db)) -> SessionService:
    return SessionService(db)

@router.post("", response_model=SessionResponse)
def create_session(session: SessionCreate, service: SessionService = Depends(get_session_service)):
    """
    Create a new chat session.
    
    Returns the created session with its assigned ID and default title.
    """
    return service.create_session(session)

@router.patch("/{session_id}", response_model=SessionResponse)
def update_session(session_id: str, updates: SessionUpdate, service: SessionService = Depends(get_session_service)):
    """
    Update an existing session.
    
    - **session_id**: The ID of the session to update.
    - **updates**: The fields to update (e.g., title).
    """
    session = service.update_session(session_id, updates)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session

@router.get("", response_model=List[SessionResponse])
def get_sessions(
    q: Optional[str] = None, 
    skip: int = 0, 
    limit: int = 20, 
    service: SessionService = Depends(get_session_service)
):
    """
    Retrieve a list of chat sessions.
    
    - **q**: Optional search query to filter sessions by title.
    - **skip**: Number of records to skip.
    - **limit**: Maximum number of records to return.
    """
    return service.get_sessions(search_query=q, skip=skip, limit=limit)

@router.post("/{session_id}/title", response_model=SessionResponse)
async def generate_session_title(
    session_id: str,
    request: TitleGenerationRequest,
    service: SessionService = Depends(get_session_service)
):
    """
    Generate a title for the session based on the first user message.
    """
    session = await service.generate_title(session_id, request.message)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return session
