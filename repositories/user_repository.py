from datetime import datetime
from sqlalchemy.orm import Session

from database.models import User


class UserRepository:

    def find_by_id(
        self,
        db: Session,
        user_id: str,
    ):
        return (
            db.query(User)
            .filter(
                User.id == user_id,
                User.deleted_at.is_(None),
            )
            .first()
        )

    def find_by_email(
        self,
        db: Session,
        email: str,
    ):
        return (
            db.query(User)
            .filter(
                User.email == email,
                User.deleted_at.is_(None),
            )
            .first()
        )

    def create(
        self,
        db: Session,
        name: str,
        email: str,
        password_hash: str,
    ):
        user = User(
            name=name,
            email=email,
            password_hash=password_hash,
        )

        db.add(user)
        db.commit()
        db.refresh(user)

        return user

    def update_by_id(
        self,
        db: Session,
        user_id: str,
        name: str | None = None,
        email: str | None = None,
        is_active: bool | None = None,
    ):
        user = (
            db.query(User)
            .filter(
                User.id == user_id,
                User.deleted_at.is_(None),
            )
            .first()
        )

        if not user:
            return None

        if name is not None:
            user.name = name

        if email is not None:
            user.email = email

        if is_active is not None:
            user.is_active = is_active

        db.commit()
        db.refresh(user)

        return user

    def soft_delete(
        self,
        db: Session,
        user_id: str,
    ):
        user = (
            db.query(User)
            .filter(
                User.id == user_id,
                User.deleted_at.is_(None),
            )
            .first()
        )

        if not user:
            return None

        user.deleted_at = datetime.utcnow()

        db.commit()
        db.refresh(user)

        return user