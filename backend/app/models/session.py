from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import relationship
from ..infra.database import Base

from ..core.utils import generate_id

class Session(Base):
    __tablename__ = "sessions"

    id = Column(String(64), primary_key=True, default=generate_id)
    title = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    messages = relationship("Message", back_populates="session", cascade="all, delete-orphan")
