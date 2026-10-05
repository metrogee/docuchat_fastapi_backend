from fastapi import APIRouter

from routes.routes import router
from routes.auth_routes import router as auth_router
from routes.document_routes import router as document_router


api_router = APIRouter(prefix="/api/v1")

api_router.include_router(router)
api_router.include_router(auth_router)
api_router.include_router(document_router)