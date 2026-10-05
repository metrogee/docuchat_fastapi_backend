from database.database import SessionLocal
from services.auth_service import AuthService


db = SessionLocal()

try:
    auth_service = AuthService()

    result = auth_service.login(
        db=db,
        email="test@example.com",
        password="password123",
    )

    print("User:", result["user"].email)
    print("Access token:", result["access_token"])
    print("Refresh token:", result["refresh_token"])

finally:
    db.close()