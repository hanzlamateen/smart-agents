from pydantic import BaseModel
from typing import Any
from datetime import datetime

class MessageResponse(BaseModel):
    id: str
    role: str
    content: Any # Content is dynamic (list of dicts or string)
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
