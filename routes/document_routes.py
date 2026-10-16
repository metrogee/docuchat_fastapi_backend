from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from uuid import UUID

from database.database import get_db
from middleware.auth import require_permission
from schemas.document import (
    CreateDocumentRequest,
    DocumentResponse,
)
from services.document_service import DocumentService
from schemas.document import DocumentListResponse
from schemas.document import CreateDocumentResponse
from schemas.document import DocumentProcessingStatusResponse


router = APIRouter(prefix="/documents", tags=["Documents"])

document_service = DocumentService()


@router.post(
    "",
    response_model=CreateDocumentResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_document(
    request: CreateDocumentRequest,
    user=Depends(require_permission("documents:create")),
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
    response_model=DocumentListResponse,
)
async def list_documents(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    status_filter: str | None = Query(
        default=None,
        alias="status",
        pattern="^(pending|processing|ready|failed)$",
    ),
    search: str | None = Query(default=None, max_length=200),
    sort_by: str = Query(
        default="createdAt",
        alias="sortBy",
        pattern="^(createdAt|title|chunkCount)$",
    ),
    sort_order: str = Query(
        default="desc",
        alias="sortOrder",
        pattern="^(asc|desc)$",
    ),
    user=Depends(require_permission("documents:read")),
    db: Session = Depends(get_db),
):
    return document_service.list_documents(
        db=db,
        user_id=user.id,
        page=page,
        limit=limit,
        status=status_filter,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
    )

@router.get(
    "/{document_id}/processing-status",
    response_model=DocumentProcessingStatusResponse,
)
async def get_document_processing_status(
    document_id: UUID,
    user=Depends(require_permission("documents:read")),
    db: Session = Depends(get_db),
):
    return document_service.get_processing_status(
        db=db,
        document_id=str(document_id),
        user_id=user.id,
    )

@router.get(
    "/{document_id}",
    response_model=DocumentResponse,
)
async def get_document(
    document_id: UUID,
    user=Depends(require_permission("documents:read")),
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
    user=Depends(require_permission("documents:delete")),
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

