from fastapi import APIRouter, Depends
from controllers.health_controller import health_check
from middleware.auth import require_auth, require_role

router = APIRouter()

router.add_api_route("/", health_check, methods=["GET"])


@router.get("/protected")
async def protected_route(user=Depends(require_auth)):
    return {
        "message": "You are authenticated",
        "user_id": str(user.id),
        "email": user.email,
    }

@router.get("/admin-only")
async def admin_only_route(
    user=Depends(require_role("admin")),
):
    return {
        "message": "You are an admin",
        "user_id": str(user.id),
        "email": user.email,
    }