from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from database.database import get_db
from middleware.auth import require_permission
from schemas.conversation import (
    CreateConversationRequest,
    ConversationResponse,
    ConversationListResponse,
)
from services.conversation_service import ConversationService
from uuid import UUID
from schemas.conversation import (
    SendMessageRequest,
    SendMessageResponse,
)
from fastapi import Request
from utils.http_cache import conditional_json_response



router = APIRouter(
    prefix="/conversations",
    tags=["Conversations"],
)

conversation_service = ConversationService()


@router.post(
    "",
    response_model=ConversationResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_conversation(
    request: CreateConversationRequest,
    user=Depends(require_permission("conversations:create")),
    db: Session = Depends(get_db),
):
    return conversation_service.create_conversation(
        db=db,
        user_id=user.id,
        title=request.title,
    )



@router.get("")
def list_conversations(
    request: Request,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    user=Depends(require_permission("conversations:read")),
    db: Session = Depends(get_db),
):
    result = conversation_service.list_conversations(
        db=db,
        user_id=user.id,
        page=page,
        limit=limit,
    )

    return conditional_json_response(
        request=request,
        data=result,
        cache_control="private, no-cache",
    )


@router.post(
    "/{conversation_id}/messages",
    response_model=SendMessageResponse,
    status_code=status.HTTP_201_CREATED,
)
def send_message(
    conversation_id: UUID,
    request: SendMessageRequest,
    user=Depends(require_permission("conversations:create")),
    db: Session = Depends(get_db),
):
    return conversation_service.send_message(
        db=db,
        conversation_id=str(conversation_id),
        user_id=user.id,
        content=request.content,
        document_id=request.document_id,
    )