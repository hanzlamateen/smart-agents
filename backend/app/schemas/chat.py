from pydantic import BaseModel

class ChatRequest(BaseModel):
    message: str # The new user message
    session_id: str
