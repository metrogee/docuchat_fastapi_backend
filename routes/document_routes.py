from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from uuid import UUID

from database.database import get_db
from middleware.auth import require_auth
from schemas.document import (
    CreateDocumentRequest,
    DocumentResponse,
)
from services.document_service import DocumentService


router = APIRouter(prefix="/documents", tags=["Documents"])

document_service = DocumentService()


@router.post(
    "",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_document(
    request: CreateDocumentRequest,
    user=Depends(require_auth),
    db: Session = Depends(get_db),
):
    document = document_service.create_document(
        db=db,
        user_id=user.id,
        title=request.title,
        content=request.content,
    )

    return document


@router.get(
    "",
    response_model=list[DocumentResponse],
)
async def list_documents(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    status_filter: str | None = Query(
        default=None,
        alias="status",
        pattern="^(pending|processing|ready|failed)$",
    ),
    user=Depends(require_auth),
    db: Session = Depends(get_db),
):
    return document_service.list_documents(
        db=db,
        user_id=user.id,
        page=page,
        limit=limit,
        status=status_filter,
    )


@router.get(
    "/{document_id}",
    response_model=DocumentResponse,
)
async def get_document(
    document_id: UUID,
    user=Depends(require_auth),
    db: Session = Depends(get_db),
):
    try:
        return document_service.get_document(
            db=db,
            document_id=str(document_id),
            user_id=user.id,
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )


@router.delete(
    "/{document_id}",
)
async def delete_document(
    document_id: UUID,
    user=Depends(require_auth),
    db: Session = Depends(get_db),
):
    try:
        document_service.delete_document(
            db=db,
            document_id=str(document_id),
            user_id=user.id,
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    return {
        "success": True,
        "data": {
            "message": "Document deleted successfully",
        },
    }