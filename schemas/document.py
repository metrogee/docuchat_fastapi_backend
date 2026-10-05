from pydantic import BaseModel, Field
from datetime import datetime
from typing import Literal


class CreateDocumentRequest(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    content: str = Field(min_length=1)


class DocumentResponse(BaseModel):
    id: str
    user_id: str
    title: str
    content: str
    status: str
    created_at: datetime
    updated_at: datetime


class DocumentListQuery(BaseModel):
    page: int = Field(default=1, ge=1)
    limit: int = Field(default=20, ge=1, le=100)
    status: Literal["pending", "processing", "ready", "failed"] | None = None