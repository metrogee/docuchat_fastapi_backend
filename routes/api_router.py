from fastapi import APIRouter

from routes.routes import router
from routes.auth_routes import router as auth_router
from routes.document_routes import router as document_router
from routes.admin_routes import router as admin_router
from routes.conversation_routes import router as conversation_router
from routes.webhook_routes import router as webhook_router

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(router)
api_router.include_router(auth_router)
api_router.include_router(document_router)
api_router.include_router(admin_router)
api_router.include_router(conversation_router)
api_router.include_router(webhook_router)