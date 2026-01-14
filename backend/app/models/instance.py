from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from ..infra.database import Base
from ..core.utils import generate_id

class Instance(Base):
    __tablename__ = "instances"

    id = Column(String(64), primary_key=True, default=generate_id)
    session_id = Column(String(64), ForeignKey("sessions.id"), unique=True, nullable=False)
    
    # container_id for Docker management
    container_id = Column(String(255), nullable=False)
    
    # Internal IP
    host = Column(String(255), nullable=True) # E.g., "172.18.0.3" or hostname

    # SSH Access
    ssh_port = Column(Integer, default=22)
    ssh_username = Column(String(50), nullable=True) # e.g. "smart-agents"
    ssh_private_key_enc = Column(String(4096), nullable=True) # Encrypted Fernet token (base64 string)

    # External Port for VNC (mapped to host)
    vnc_port = Column(Integer, nullable=True)
    
    # Status
    # starting, running, stopped, error
    status = Column(String(50), default="starting")
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship
    session = relationship("Session")
