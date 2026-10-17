from sqlalchemy.orm import Session

from repositories.document_repository import DocumentRepository
from utils.errors import NotFoundError
from rbac.service import get_user_permissions
from src.events import (
    event_emitter,
    EVENT_DOCUMENT_CREATED,
    EVENT_DOCUMENT_DELETED,
)
from queues.document_tasks import process_document
from sqlalchemy import func, select
from database.models import DocumentChunk
from queues.celery_app import celery_app
import logging

from fastapi.encoders import jsonable_encoder
from redis.exceptions import RedisError

from cache.redis_cache import (
    CACHE_TTL,
    cache_get_or_set,
    cache_delete,
)
from utils.sanitizer import sanitize_text

logger = logging.getLogger(__name__)


class DocumentService:
    def __init__(self):
        self.document_repository = DocumentRepository()

    def create_document(
        self,
        db: Session,
        user_id: str,
        title: str,
        content: str,
    ):
        clean_title = sanitize_text(title).strip()

        if not clean_title:
            raise ValueError(
                "Document title cannot be empty after sanitization"
            )

        document = self.document_repository.create(
            db=db,
            user_id=user_id,
            title=clean_title,
            content=content,
        )

        try:
            job = process_document.apply_async(
                args=[document.id, user_id],
                queue="document-processing",
                task_id=document.id,
            )
        except Exception:
            # The document remains pending for recovery/requeueing.
            # Do not report that processing was successfully queued.
            raise

        event_emitter.emit(
            EVENT_DOCUMENT_CREATED,
            db=db,
            user_id=user_id,
            document_id=document.id,
            title=document.title,
            file_size_bytes=len(content.encode("utf-8")),
        )

        return {
            "document": document,
            "jobId": job.id,
        }

    
    @staticmethod
    def invalidate_document_cache(document_id: str):
        try:
            cache_delete(f"doc:{document_id}")
        except RedisError:
            logger.exception(
                "Document cache invalidation failed: %s",
                document_id,
            )

    def get_document_metadata(
        self,
        db: Session,
        document_id: str,
        user_id: str,
    ):
        """
        Cached read for the document GET endpoint.

        Cached records include ownership information.
        User permissions are checked on every request.
        """
        key = f"doc:{document_id}"

        def fetch():
            document = self.document_repository.find_by_id(
                db=db,
                document_id=document_id,
            )

            if document is None:
                raise NotFoundError("Document not found")

            return jsonable_encoder({
                column.key: getattr(document, column.key)
                for column in document.__mapper__.columns
            })

        try:
            metadata = cache_get_or_set(
                key=key,
                ttl=CACHE_TTL["DOCUMENT"],
                fetch_fn=fetch,
            )

        except RedisError:
            logger.exception(
                "Document cache unavailable: %s",
                document_id,
            )
            metadata = fetch()

        if metadata.get("deleted_at") is not None:
            raise NotFoundError("Document not found")

        if metadata["user_id"] != user_id:
            permissions = get_user_permissions(user_id, db)

            if "users:manage" not in permissions:
                raise NotFoundError("Document not found")

        return metadata


    def get_document(
        self,
        db: Session,
        document_id: str,
        user_id: str,
    ):
        document = self.document_repository.find_by_id(
            db=db,
            document_id=document_id,
        )

        if not document:
            raise NotFoundError("Document not found")

        if document.user_id != user_id:
            permissions = get_user_permissions(user_id, db)

            if "users:manage" not in permissions:
                raise NotFoundError("Document not found")

        return document

    def list_documents(
        self,
        db: Session,
        user_id: str,
        page: int = 1,
        limit: int = 20,
        status: str | None = None,
        search: str | None = None,
        sort_by: str = "createdAt",
        sort_order: str = "desc",
    ):
        documents, total = self.document_repository.find_by_user_id(
            db=db,
            user_id=user_id,
            skip=(page - 1) * limit,
            limit=limit,
            status=status,
            search=search,
            sort_by=sort_by,
            sort_order=sort_order,
        )

        return {
            "data": documents,
            "meta": {
                "page": page,
                "limit": limit,
                "total": total,
            },
        }
    
    def delete_document(
        self,
        db: Session,
        document_id: str,
        user_id: str,
    ):
        document = self.get_document(
            db=db,
            document_id=document_id,
            user_id=user_id,
        )

        deleted_document = self.document_repository.delete(
            db=db,
            document=document,
            deleted_by=user_id,
        )
        
        self.invalidate_document_cache(deleted_document.id)

        event_emitter.emit(
            EVENT_DOCUMENT_DELETED,
            db=db,
            deleted_by=user_id,
            document_id=deleted_document.id,
            title=deleted_document.title,
            deleted_at=deleted_document.deleted_at,
        )

        return deleted_document

    def get_processing_status(
        self,
        db: Session,
        document_id: str,
        user_id: str,
    ):
        # Reuse existing ownership and admin permission checks.
        document = self.get_document(
            db=db,
            document_id=document_id,
            user_id=user_id,
        )

        # Count chunks saved for this document.
        chunk_count = db.scalar(
            select(func.count(DocumentChunk.id)).where(
                DocumentChunk.document_id == document.id
            )
        ) or 0

        status = document.status

        # The Celery task ID is the document ID.
        job = celery_app.AsyncResult(document.id)

        if status == "ready":
            progress = 100

        elif status == "failed":
            progress = 0

        elif status == "pending":
            progress = 0

        elif status == "processing":
            # The worker publishes progress metadata to Redis.
            task_info = job.info

            if isinstance(task_info, dict):
                progress = task_info.get("progress", 10)
            else:
                progress = 10

        else:
            progress = 0

        progress = max(0, min(100, int(progress)))

        return {
            "documentId": document.id,
            "status": status,
            "progress": progress,
            "chunkCount": chunk_count,
            "error": (
                document.processing_error
                if status == "failed"
                else None
            ),
        }