from datetime import datetime
from typing import Optional
from pydantic import BaseModel

class InstanceResponse(BaseModel):
    id: Optional[str]
    session_id: str
    status: str
    vnc_port: Optional[int]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True
