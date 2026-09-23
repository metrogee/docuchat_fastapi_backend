from database.database import SessionLocal
from services.user_service import UserService


db = SessionLocal()

try:
    service = UserService()

    user = service.create_user(
        db=db,
        name="Test User",
        email="test3@example.com",
        password_hash="test-password-hash",
    )

    print("User created successfully!")
    print("ID:", user.id)
    print("Name:", user.name)
    print("Email:", user.email)

finally:
    db.close()