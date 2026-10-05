from sqlalchemy.orm import Session

from database.models import Document


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
        db.commit()
        db.refresh(document)

        return document

    def find_by_id(
        self,
        db: Session,
        document_id: str,
    ):
        return (
            db.query(Document)
            .filter(Document.id == document_id)
            .first()
        )

    def find_by_user_id(
        self,
        db: Session,
        user_id: str,
        skip: int = 0,
        limit: int = 20,
        status: str | None = None,
    ):
        query = (
            db.query(Document)
            .filter(Document.user_id == user_id)
        )

        if status:
            query = query.filter(Document.status == status)

        return (
            query
            .order_by(Document.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def delete(
        self,
        db: Session,
        document: Document,
    ):
        db.delete(document)
        db.commit()