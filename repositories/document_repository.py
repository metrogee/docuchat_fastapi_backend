from datetime import datetime, timezone

from sqlalchemy import func, or_, select
from database.models import Document, DocumentChunk
from sqlalchemy.orm import Session


class DocumentRepository:

    def create(
        self,
        db: Session,
        user_id: str,
        title: str,
        content: str,
    ):
        document = Document(
            user_id=user_id,
            title=title,
            content=content,
            status="pending",
        )

        db.add(document)

        try:
            db.commit()
        except Exception:
            db.rollback()
            raise

        db.refresh(document)
        return document

    def find_by_id(
        self,
        db: Session,
        document_id: str,
    ):
        return db.scalar(
            select(Document).where(
                Document.id == document_id,
                Document.deleted_at.is_(None),
            )
        )

    def find_by_user_id(
        self,
        db: Session,
        user_id: str,
        skip: int = 0,
        limit: int = 20,
        status: str | None = None,
        search: str | None = None,
        sort_by: str = "createdAt",
        sort_order: str = "desc",
    ):
        filters = [
            Document.user_id == user_id,
            Document.deleted_at.is_(None),
        ]

        if status:
            filters.append(Document.status == status)

        if search:
            filters.append(
                or_(
                    Document.title.ilike(f"%{search}%"),
                    Document.content.ilike(f"%{search}%"),
                )
            )

        chunk_count = (
            select(func.count(DocumentChunk.id))
            .where(DocumentChunk.document_id == Document.id)
            .correlate(Document)
            .scalar_subquery()
        )

        sort_columns = {
            "createdAt": Document.created_at,
            "title": Document.title,
            "chunkCount": chunk_count,
        }

        sort_column = sort_columns[sort_by]
        ordering = (
            sort_column.asc()
            if sort_order == "asc"
            else sort_column.desc()
        )

        total = db.scalar(
            select(func.count(Document.id)).where(*filters)
        ) or 0

        documents = db.scalars(
            select(Document)
            .where(*filters)
            .order_by(ordering, Document.id.asc())
            .offset(skip)
            .limit(limit)
        ).all()

        return documents, total

    def delete(
        self,
        db: Session,
        document: Document,
        deleted_by: str,
    ):
        document.deleted_at = datetime.now(timezone.utc)
        document.deleted_by = deleted_by

        try:
            db.commit()
        except Exception:
            db.rollback()
            raise

        db.refresh(document)
        return document