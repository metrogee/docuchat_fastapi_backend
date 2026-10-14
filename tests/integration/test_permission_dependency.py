from fastapi import FastAPI, Depends
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from database.database import get_db
from middleware.auth import require_permission
from tests.conftest import TestSessionLocal
from utils.errors import ForbiddenError

def test_multiple_required_permissions(client, test_db):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from middleware.auth import require_permission
    from database.database import get_db
    from tests.conftest import TestSessionLocal

    response = client.post(
        "/api/v1/auth/register",
        json={
            "name": "Permission Test",
            "email": "multi_permission@example.com",
            "password": "TestPassword123!",
        },
    )

    assert response.status_code == 201
    token = response.json()["access_token"]

    test_app = FastAPI()
    @test_app.exception_handler(ForbiddenError)
    async def forbidden_handler(request, exc):
        from fastapi.responses import JSONResponse

        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                },
            },
        )

    def override_get_db():
        db = TestSessionLocal()
        try:
            yield db
        finally:
            db.close()

    test_app.dependency_overrides[get_db] = override_get_db

    @test_app.get("/test-multiple-permissions")
    async def protected_route(
        user=Depends(
            require_permission(
                "documents:read",
                "roles:manage",
            )
        ),
    ):
        return {"success": True}

    with TestClient(test_app) as test_client:
        response = test_client.get(
            "/test-multiple-permissions",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 403