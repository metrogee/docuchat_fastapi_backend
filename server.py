import src.document_events  # Registers document event listeners
from fastapi import FastAPI, Depends
from utils.errors import AppError
from middleware.error_handler import (
    app_error_handler,
    unexpected_error_handler,
)
from routes.routes import router    
from routes.auth_routes import router as auth_router
from routes.api_router import api_router

from sqlalchemy import text
from sqlalchemy.orm import Session

from database.database import get_db
import rbac.cache_invalidation  # Register RBAC cache listeners
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from middleware.rate_limit import APIRateLimitMiddleware
from middleware.security_headers import SecurityHeadersMiddleware
import os
from fastapi.middleware.cors import CORSMiddleware


class AuthNoStoreMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        if request.url.path.startswith("/api/v1/auth"):
            response.headers["Cache-Control"] = "no-store"

        return response


app = FastAPI(title="Docuchat Backend", version="1.0.0")


# Read permitted frontend origins from environment.
# Multiple origins can be separated by commas.
allowed_origins = [
    origin.strip()
    for origin in os.getenv(
        "FRONTEND_URL",
        "http://localhost:3001",
    ).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Content-Type", "Authorization"],
    max_age=86400,
)

app.add_middleware(AuthNoStoreMiddleware)
app.add_middleware(APIRateLimitMiddleware)

app.add_exception_handler(
    AppError,
    app_error_handler,
)

app.add_exception_handler(
    Exception,
    unexpected_error_handler,
)
app.add_middleware(SecurityHeadersMiddleware)


# CORS must be the outermost registered middleware.
allowed_origins = [
    origin.strip()
    for origin in os.getenv(
        "FRONTEND_URL",
        "http://localhost:3001",
    ).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Content-Type", "Authorization"],
    max_age=86400,
)


# Register all application routes
app.include_router(api_router)

@app.get("/")
def home():
    return {
        "message": "FastAPI server is working"
    }


@app.get("/database-test")
def database_test(
    db: Session = Depends(get_db)
):
    result = db.execute(
        text("SELECT 1")
    )

    return {
        "database": result.scalar()
    }



@app.get("/users/{user_id}")
def get_user(
    user_id: str,
    db: Session = Depends(get_db),
):
    user = user_repository.find_by_id(
        db,
        user_id,
    )

    if not user:
        return {
            "message": "User not found"
        }

    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=3000, reload=True)
