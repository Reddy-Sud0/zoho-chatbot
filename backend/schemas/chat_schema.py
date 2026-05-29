from pydantic import BaseModel
from typing import Optional

class ChatRequest(BaseModel):
    session_id: str
    message: str
    confirmed: Optional[bool] = None

class ChatResponse(BaseModel):
    reply: str
    awaiting_confirmation: bool = False
    pending_action: Optional[dict] = None