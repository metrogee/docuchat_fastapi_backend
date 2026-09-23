from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from repositories.user_repository import UserRepository
from repositories.refresh_token_repository import RefreshTokenRepository
from utils.password import hash_password, verify_password
from utils.jwt import create_access_token, create_refresh_token, verify_token
from utils.token import hash_refresh_token


class AuthService:

    def __init__(self):
        self.user_repository = UserRepository()
        self.refresh_token_repository = RefreshTokenRepository()

    def register(
        self,
        db: Session,
        name: str,
        email: str,
        password: str,
    ):
        existing_user = self.user_repository.find_by_email(
            db,
            email,
        )

        if existing_user:
            raise ValueError("Email already registered")

        password_hash = hash_password(password)

        user = self.user_repository.create(
            db,
            name,
            email,
            password_hash,
        )

        access_token = create_access_token(user.id)
        refresh_token = create_refresh_token(user.id)

        refresh_token_hash = hash_refresh_token(
            refresh_token
        )

        expires_at = datetime.now(timezone.utc) + timedelta(days=7)

        refresh_token_record = self.refresh_token_repository.create(
            db,
            user.id,
            refresh_token_hash,
            expires_at,
        )

        return {
            "user": user,
            "access_token": access_token,
            "refresh_token": refresh_token,
        }

    def login(
    self,
    db: Session,
    email: str,
    password: str,
    ):
        user = self.user_repository.find_by_email(db, email)

        if not user or not verify_password(password, user.password_hash):
            raise ValueError("Invalid email or password")

        access_token = create_access_token(user.id)
        refresh_token = create_refresh_token(user.id)

        refresh_token_hash = hash_refresh_token(refresh_token)

        expires_at = datetime.now(timezone.utc) + timedelta(days=7)

        self.refresh_token_repository.create(
            db,
            user.id,
            refresh_token_hash,
            expires_at,
        )

        return {
            "user": user,
            "access_token": access_token,
            "refresh_token": refresh_token,
        }

    def refresh(
    self,
    db: Session,
    refresh_token: str,
    ):
        payload = verify_token(refresh_token, "refresh")

        user_id = payload.get("sub")

        if not user_id:
            raise ValueError("Invalid refresh token")

        refresh_token_hash = hash_refresh_token(refresh_token)

        stored_token = self.refresh_token_repository.find_by_token_hash(
            db,
            refresh_token_hash,
        )

        if not stored_token:
            raise ValueError("Invalid refresh token")

        if stored_token.expires_at <= datetime.now(timezone.utc):
            self.refresh_token_repository.delete_by_token_hash(
                db,
                refresh_token_hash,
            )
            raise ValueError("Refresh token expired")

        self.refresh_token_repository.delete_by_token_hash(
            db,
            refresh_token_hash,
        )

        new_access_token = create_access_token(user_id)
        new_refresh_token = create_refresh_token(user_id)

        new_refresh_token_hash = hash_refresh_token(new_refresh_token)

        new_expires_at = datetime.now(timezone.utc) + timedelta(days=7)

        self.refresh_token_repository.create(
            db,
            user_id,
            new_refresh_token_hash,
            new_expires_at,
        )

        return {
            "access_token": new_access_token,
            "refresh_token": new_refresh_token,
        }

    try:
        auth_service.refresh(
            db=db,
            refresh_token=old_refresh_token,
        )

        print("ERROR: Old refresh token was accepted!")

    except Exception as error:
        print("Old refresh token rejected:", error)   