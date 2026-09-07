from datetime import datetime
from pydantic import BaseModel, ConfigDict


class MessageItem(BaseModel):
    role: str  # "user" | "assistant"
    content: str
    timestamp: datetime | None = None


class ConversationResponse(BaseModel):
    id: str
    title: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ConversationDetailResponse(BaseModel):
    id: str
    title: str
    created_at: datetime
    updated_at: datetime
    messages: list[MessageItem] = []

    model_config = ConfigDict(from_attributes=True)


class ChatRequest(BaseModel):
    message: str
    thread_id: str | None = None


class ChatResponse(BaseModel):
    response: str
    thread_id: str
    title: str
