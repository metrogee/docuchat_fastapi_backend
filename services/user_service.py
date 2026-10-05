from sqlalchemy.orm import Session

from repositories.user_repository import UserRepository
from utils.errors import ConflictError

class UserService:

    def __init__(self):
        self.repository = UserRepository()

    def get_user_by_email(
        self,
        db: Session,
        email: str,
    ):
        return self.repository.find_by_email(
            db,
            email,
        )
    
    def create_user(
    self,
    db: Session,
    name: str,
    email: str,
    password_hash: str,
    ):
        existing_user = self.repository.find_by_email(
            db,
            email,
        )

        if existing_user:
            raise ConflictError("Email already registered")

        return self.repository.create(
            db,
            name,
            email,
            password_hash,
        )