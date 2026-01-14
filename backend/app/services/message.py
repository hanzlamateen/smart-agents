import logging
from typing import List
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from ..models import Message as DBMessage

logger = logging.getLogger(__name__)

class MessageService:
    def __init__(self, db: Session):
        self.db = db

    def get_messages(self, session_id: str, skip: int = 0, limit: int = 100) -> List[DBMessage]:
        try:
            # Fetch newest messages first (Limit 100)
            # Use secondary sort on ID for stability
            messages = self.db.query(DBMessage).filter(DBMessage.session_id == session_id).order_by(DBMessage.created_at.desc()).offset(skip).limit(limit).all()
            
            # Reverse to chronological order (Oldest -> Newest) for display
            messages = messages[::-1]
            
            # Hydrate S3 URLs for frontend display
            from ..infra.storage import storage
            for msg in messages:
                if isinstance(msg.content, list):
                    for block in msg.content:
                        if isinstance(block, dict) and block.get("type") == "tool_result":
                            if block.get("s3_key") and not block.get("image_url"):
                                block["image_url"] = storage.get_public_url(block["s3_key"])
            return messages
        except SQLAlchemyError as e:
            logger.error(f"Failed to retrieve messages for session {session_id}: {e}", exc_info=True)
            raise
