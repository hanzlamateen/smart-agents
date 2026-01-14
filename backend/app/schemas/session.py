from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class SessionCreate(BaseModel):
    title: Optional[str] = "New Session"

class SessionUpdate(BaseModel):
    title: str = Field(..., min_length=3, description="Title cannot be empty")

class SessionResponse(BaseModel):
    id: str
    title: Optional[str]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class TitleGenerationRequest(BaseModel):
    message: str = Field(..., description="The user's first message to base the title on")
