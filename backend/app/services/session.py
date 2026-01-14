import logging
from typing import List, Optional, Any
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from ..models import Session as DBSession, Message as DBMessage
from ..schemas import SessionCreate, SessionUpdate

logger = logging.getLogger(__name__)

class SessionService:
    def __init__(self, db: Session):
        self.db = db

    def create_session(self, session_in: SessionCreate) -> DBSession:
        try:
            db_session = DBSession(title=session_in.title)
            self.db.add(db_session)
            self.db.commit()
            self.db.refresh(db_session)
            logger.info(f"Created new session with ID: {db_session.id}")
            return db_session
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Failed to create session: {e}", exc_info=True)
            raise

    def update_session(self, session_id: str, updates: SessionUpdate) -> Optional[DBSession]:
        try:
            db_session = self.get_session(session_id)
            if not db_session:
                logger.warning(f"Attempted to update non-existent session: {session_id}")
                return None
                
            db_session.title = updates.title
            self.db.add(db_session)
            self.db.commit()
            self.db.refresh(db_session)
            logger.info(f"Updated session {session_id} title to: {updates.title}")
            return db_session
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Failed to update session {session_id}: {e}", exc_info=True)
            raise

    def get_sessions(self, search_query: Optional[str] = None, skip: int = 0, limit: int = 20) -> List[DBSession]:
        try:
            query = self.db.query(DBSession)
            if search_query:
                # Secure filtering using SQLAlchemy's ilike which handles parameterization
                query = query.filter(DBSession.title.ilike(f"%{search_query}%"))
            return query.order_by(DBSession.created_at.desc()).offset(skip).limit(limit).all()
        except SQLAlchemyError as e:
            logger.error(f"Failed to retrieve sessions: {e}", exc_info=True)
            raise

    def get_session(self, session_id: str) -> Optional[DBSession]:
        try:
            return self.db.query(DBSession).filter(DBSession.id == session_id).first()
        except SQLAlchemyError as e:
            logger.error(f"Failed to retrieve session {session_id}: {e}", exc_info=True)
            raise

    async def generate_title(self, session_id: str, user_message: str) -> Optional[DBSession]:
        """Generate a short title and update the session using LLM."""
        from ..loop import sampling_loop
        from ..core.config import settings as app_settings
        from ..services.agent_settings import AgentSettingsService
        
        # Load Settings internally
        settings_service = AgentSettingsService(self.db)
        settings = settings_service.get_settings()
        
        logger.info(f"Generating title for session {session_id}")
        try:
            # Simple prompt for title
            messages = [{
                "role": "user", 
                "content": f"Generate a concise 3-4 word title for this chat based on the message: '{user_message}'. Do not use quotes."
            }]
            
            title = "New Session"
            # Logic to skip if no API key?
            if not settings.api_key and not app_settings.api_key:
                logger.warning("No API key available for title generation.")
                return self.get_session(session_id)

            logger.info(f"Using model: {settings.model}, provider: {settings.provider} for title generation")
            async for event in sampling_loop(
                model=settings.model,
                provider=settings.provider,
                system_prompt_suffix="",
                messages=messages,
                api_key=settings.api_key or app_settings.api_key,
                max_tokens=20, # Short title
                tool_version=settings.tool_version,
                session_id=session_id,
                # Explicitly disable images/pdfs for title gen to save tokens/bandwidth
                only_n_most_recent_images=0 
            ):
                if event["type"] == "text":
                    title = event["content"]
                    logger.info(f"Received title chunk: {title}")
                elif event["type"] == "error":
                    logger.error(f"Title generation error event: {event['message']}")
                    return self.get_session(session_id)
            
            clean_title = title.strip()
            updated_session = self.update_session(session_id, SessionUpdate(title=clean_title))
            logger.info(f"Generated and saved title for {session_id}: {clean_title}")
            return updated_session
                
        except Exception as e:
            logger.error(f"Failed to generate title for {session_id}: {e}", exc_info=True)
            return self.get_session(session_id)

