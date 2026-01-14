from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from ..infra.database import Base

from ..core.utils import generate_id

class Message(Base):
    __tablename__ = "messages"

    id = Column(String(64), primary_key=True, default=generate_id)
    session_id = Column(String(64), ForeignKey("sessions.id"))
    role = Column(String(50))  # user, assistant, tool
    content = Column(JSON)      # Store the full content block logic (text, tool_use, etc)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    session = relationship("Session", back_populates="messages")
