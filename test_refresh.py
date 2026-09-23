from database.database import SessionLocal
from services.auth_service import AuthService


db = SessionLocal()

try:
    auth_service = AuthService()

    login_result = auth_service.login(
        db=db,
        email="test@example.com",
        password="password123",
    )

    old_refresh_token = login_result["refresh_token"]

    result = auth_service.refresh(
        db=db,
        refresh_token=old_refresh_token,
    )

    print("New access token:", result["access_token"])
    print("New refresh token:", result["refresh_token"])

finally:
    db.close()