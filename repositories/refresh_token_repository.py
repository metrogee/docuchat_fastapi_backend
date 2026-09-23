from sqlalchemy.orm import Session

from database.models import RefreshToken


class RefreshTokenRepository:

    def create(
        self,
        db: Session,
        user_id: str,
        token_hash: str,
        expires_at,
    ):
        refresh_token = RefreshToken(
            user_id=user_id,
            token=token_hash,
            expires_at=expires_at,
        )

        db.add(refresh_token)
        db.commit()
        db.refresh(refresh_token)

        return refresh_token

    def find_by_token_hash(
        self,
        db: Session,
        token_hash: str,
    ):
        return (
            db.query(RefreshToken)
            .filter(RefreshToken.token == token_hash)
            .first()
        )

    def delete_by_token_hash(
        self,
        db: Session,
        token_hash: str,
    ):
        refresh_token = (
            db.query(RefreshToken)
            .filter(RefreshToken.token == token_hash)
            .first()
        )

        if not refresh_token:
            return None

        db.delete(refresh_token)
        db.commit()

        return refresh_token