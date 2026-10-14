from datetime import datetime

from pydantic import BaseModel, Field


class CreateConversationRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)


class ConversationResponse(BaseModel):
    id: str
    title: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class LastMessageResponse(BaseModel):
    content: str
    role: str
    createdAt: datetime


class ConversationListItem(BaseModel):
    id: str
    title: str
    messageCount: int
    lastMessage: LastMessageResponse | None
    updatedAt: datetime


class PaginationMeta(BaseModel):
    page: int
    limit: int
    total: int


class ConversationListResponse(BaseModel):
    data: list[ConversationListItem]
    meta: PaginationMeta

class SendMessageRequest(BaseModel):
    content: str = Field(min_length=1)
    document_id: str | None = None


class MessageResponse(BaseModel):
    id: str
    conversation_id: str
    document_id: str | None
    role: str
    content: str
    prompt_tokens: int
    completion_tokens: int
    cost_usd: float
    created_at: datetime

    model_config = {"from_attributes": True}


class SendMessageResponse(BaseModel):
    userMessage: MessageResponse
    assistantMessage: MessageResponse