import os
from datetime import datetime, timedelta, timezone

import jwt
from dotenv import load_dotenv


load_dotenv()


JWT_ACCESS_SECRET = os.getenv("JWT_ACCESS_SECRET")
JWT_REFRESH_SECRET = os.getenv("JWT_REFRESH_SECRET")

if not JWT_ACCESS_SECRET:
    raise ValueError("JWT_ACCESS_SECRET is not set")

if not JWT_REFRESH_SECRET:
    raise ValueError("JWT_REFRESH_SECRET is not set")


ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 7


def create_access_token(user_id: str) -> str:
    expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=ACCESS_TOKEN_EXPIRE_MINUTES
    )

    payload = {
        "sub": user_id,
        "type": "access",
        "exp": expires_at,
    }

    return jwt.encode(
        payload,
        JWT_ACCESS_SECRET,
        algorithm="HS256",
    )


def create_refresh_token(user_id: str) -> str:
    expires_at = datetime.now(timezone.utc) + timedelta(
        days=REFRESH_TOKEN_EXPIRE_DAYS
    )

    payload = {
        "sub": user_id,
        "type": "refresh",
        "exp": expires_at,
    }

    return jwt.encode(
        payload,
        JWT_REFRESH_SECRET,
        algorithm="HS256",
    )

def verify_token(token: str, token_type: str) -> dict:
    secret = (
        JWT_ACCESS_SECRET
        if token_type == "access"
        else JWT_REFRESH_SECRET
    )

    payload = jwt.decode(
        token,
        secret,
        algorithms=["HS256"],
    )

    if payload.get("type") != token_type:
        raise ValueError("Invalid token type")

    return payload