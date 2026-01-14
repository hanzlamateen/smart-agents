from sqlalchemy import Column, Integer, String, Boolean, Text, DateTime
from datetime import datetime
from ..infra.database import Base

from ..core.utils import generate_id

class AgentSettings(Base):
    __tablename__ = "agent_settings"

    id = Column(String(64), primary_key=True, default=generate_id)
    
    # Provider Config
    provider = Column(String(50), default="anthropic")
    model = Column(String(100), default="claude-sonnet-4-5-20250929")
    
    # Tool Config
    tool_version = Column(String(50), default="computer_use_20250124")
    
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    enable_token_efficient_tools = Column(Boolean, default=False)
    
    # Prompt Config
    system_prompt_suffix = Column(Text, default="")
    max_tokens = Column(Integer, default=4096)
    thinking_budget = Column(Integer, default=0)
    
    # Message Config
    only_n_most_recent_images = Column(Integer, default=3)
