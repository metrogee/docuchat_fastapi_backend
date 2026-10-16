
import logging

from celery import states
from sqlalchemy import delete, select

from database.database import SessionLocal
from database.models import Document, DocumentChunk
from queues.celery_app import celery_app
from queues.failure_handling import (
    get_retry_delay,
    send_to_dead_letter_queue,
)
from utils.chunker import split_into_chunks
from src.events import (
    event_emitter,
    EVENT_DOCUMENT_PROCESSED,
)


logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    name="queues.document_tasks.process_document",
    max_retries=2,
    acks_late=True,
)
def process_document(self, document_id: str, user_id: str):
    attempt = self.request.retries + 1

    logger.info(
        "Processing document %s, attempt %s",
        document_id,
        attempt,
    )

    try:
        # 1. Retrieve the document.
        with SessionLocal() as db:
            document = db.scalar(
                select(Document).where(
                    Document.id == document_id,
                    Document.user_id == user_id,
                    Document.deleted_at.is_(None),
                )
            )

            if document is None:
                logger.warning(
                    "Document %s not found or deleted",
                    document_id,
                )
                return {
                    "success": False,
                    "reason": "not_found",
                }

            # Avoid unnecessary duplicate processing.
            if document.status == "ready":
                return {
                    "success": True,
                    "already_processed": True,
                }

            document.status = "processing"
            document.processing_error = None
            content = document.content
            db.commit()

        # 2. Update processing progress.
        self.update_state(
            state=states.STARTED,
            meta={
                "progress": 10,
                "status": "processing",
            },
        )

        # 3. Split the content into chunks.
        chunks = split_into_chunks(
            content,
            max_words_per_chunk=500,
        )

        if not chunks:
            raise ValueError(
                "Document contains no processable text"
            )

        self.update_state(
            state=states.STARTED,
            meta={
                "progress": 40,
                "status": "processing",
            },
        )

        # 4. Save all chunks and update document status
        # in one database transaction.
        with SessionLocal() as db:
            try:
                document = db.scalar(
                    select(Document)
                    .where(
                        Document.id == document_id,
                        Document.user_id == user_id,
                        Document.deleted_at.is_(None),
                    )
                    .with_for_update()
                )

                if document is None:
                    db.rollback()
                    return {
                        "success": False,
                        "reason": "not_found",
                    }

                if document.status == "ready":
                    db.rollback()
                    return {
                        "success": True,
                        "already_processed": True,
                    }

                # Make retries idempotent.
                db.execute(
                    delete(DocumentChunk).where(
                        DocumentChunk.document_id == document_id
                    )
                )

                for index, chunk_text in enumerate(chunks):
                    db.add(
                        DocumentChunk(
                            document_id=document_id,
                            chunk_index=index,
                            content=chunk_text,
                        )
                    )

                document.status = "ready"
                document.processing_error = None
                db.commit()

            except Exception:
                db.rollback()
                raise

        # 5. Processing succeeded.
        self.update_state(
            state=states.STARTED,
            meta={
                "progress": 100,
                "status": "ready",
            },
        )

        event_emitter.emit(
            EVENT_DOCUMENT_PROCESSED,
            document_id=document_id,
            user_id=user_id,
            chunk_count=len(chunks),
        )

        logger.info(
            "Document %s processed successfully",
            document_id,
        )

        return {
            "success": True,
            "document_id": document_id,
            "chunks": len(chunks),
            "progress": 100,
        }

    except Exception as exc:
        logger.exception(
            "Document %s failed on attempt %s",
            document_id,
            attempt,
        )

        # 6. Retry while attempts remain.
        if self.request.retries < self.max_retries:
            retry_number = self.request.retries + 1
            countdown = get_retry_delay(retry_number)

            logger.warning(
                "Retrying document %s in %s seconds",
                document_id,
                countdown,
            )

            raise self.retry(
                exc=exc,
                countdown=countdown,
            )

        # 7. All attempts exhausted.
        logger.error(
            "Document %s permanently failed after %s attempts",
            document_id,
            attempt,
        )

        # Persist the failed status.
        with SessionLocal() as db:
            try:
                document = db.scalar(
                    select(Document)
                    .where(
                        Document.id == document_id,
                        Document.user_id == user_id,
                        Document.deleted_at.is_(None),
                    )
                    .with_for_update()
                )

                if document is not None:
                    if document.status != "ready":
                        document.status = "failed"
                        document.processing_error = str(exc)[:2000]
                        db.commit()
                    else:
                        db.rollback()

            except Exception:
                db.rollback()
                logger.exception(
                    "Could not update failed status for %s",
                    document_id,
                )

        # 8. Record the permanent failure in Redis.
        try:
            send_to_dead_letter_queue(
                document_id=document_id,
                user_id=user_id,
                error=str(exc),
                attempts=attempt,
            )

        except Exception:
            logger.exception(
                "Could not add document %s to dead-letter queue",
                document_id,
            )

        # Preserve Celery's FAILED task state.
        raise
