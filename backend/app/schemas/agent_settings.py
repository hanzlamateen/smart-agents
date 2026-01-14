from pydantic import BaseModel
from typing import Optional

from datetime import datetime

class AgentSettingsBase(BaseModel):
    provider: str = "anthropic"
    model: str = "claude-sonnet-4-5-20250929"
    tool_version: str = "computer_use_20250124"
    enable_token_efficient_tools: bool = False
    system_prompt_suffix: str = ""
    max_tokens: int = 4096
    thinking_budget: int = 0
    only_n_most_recent_images: int = 3

class AgentSettingsUpdate(AgentSettingsBase):
    id: str
    api_key: Optional[str] = None # Handling API key in the update payload

class AgentSettingsResponse(AgentSettingsBase):
    id: str
    api_key: Optional[str] = None # Returning API key (masked or full? usually full for local tools)

    updated_at: datetime
    
    class Config:
        from_attributes = True
