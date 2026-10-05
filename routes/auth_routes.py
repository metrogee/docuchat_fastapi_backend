from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database.database import get_db
from schemas.auth import (
    RegisterRequest,
    LoginRequest,
    RefreshRequest,
    LogoutRequest,
    AuthResponse,
    UserResponse,
    TokenResponse,
)
from services.auth_service import AuthService


router = APIRouter(
    prefix="/auth",
    tags=["auth"],
)

auth_service = AuthService()


@router.post(
    "/register",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register(
    data: RegisterRequest,
    db: Session = Depends(get_db),
):
    try:
        result = auth_service.register(
            db=db,
            name=data.name,
            email=data.email,
            password=data.password,
        )

        user = result["user"]

        return {
            "user": UserResponse(
                id=user.id,
                name=user.name,
                email=user.email,
                role=user.role,
                tier=user.tier,
                is_active=user.is_active,
            ),
            "access_token": result["access_token"],
            "refresh_token": result["refresh_token"],
        }

    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

@router.post("/login", response_model=AuthResponse)
async def login(data: LoginRequest, db: Session = Depends(get_db)):
    try:
        result = auth_service.login(
            db=db,
            email=data.email,
            password=data.password,
        )

        user = result["user"]

        return {
            "user": UserResponse(
                id=user.id,
                name=user.name,
                email=user.email,
                role=user.role,
                tier=user.tier,
                is_active=user.is_active,
            ),
            "access_token": result["access_token"],
            "refresh_token": result["refresh_token"],
        }

    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    data: RefreshRequest,
    db: Session = Depends(get_db),
):
    try:
        return auth_service.refresh(
            db=db,
            refresh_token=data.refresh_token,
        )

    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

@router.post("/logout")
async def logout(
    data: LogoutRequest,
    db: Session = Depends(get_db),
):
    return auth_service.logout(
        db=db,
        refresh_token=data.refresh_token,
    )