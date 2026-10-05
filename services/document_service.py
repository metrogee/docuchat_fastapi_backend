from sqlalchemy.orm import Session

from repositories.document_repository import DocumentRepository
from utils.errors import NotFoundError


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
        return self.document_repository.create(
            db=db,
            user_id=user_id,
            title=title,
            content=content,
        )

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

        if not document or document.user_id != user_id:
            raise NotFoundError("Document not found")

        return document

    def list_documents(
        self,
        db: Session,
        user_id: str,
        page: int = 1,
        limit: int = 20,
        status: str | None = None,
    ):
        skip = (page - 1) * limit

        return self.document_repository.find_by_user_id(
            db=db,
            user_id=user_id,
            skip=skip,
            limit=limit,
            status=status,
        )

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

        self.document_repository.delete(
            db=db,
            document=document,
        )