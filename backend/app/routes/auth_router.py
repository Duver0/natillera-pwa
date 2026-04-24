from fastapi import APIRouter, Depends, Request
from app.db import get_supabase
from app.services.auth_service import AuthService
from app.models.auth_model import RegisterRequest, LoginRequest, RefreshRequest, AuthResponse

router = APIRouter()


@router.post("/register", response_model=AuthResponse)
async def register(body: RegisterRequest, db=Depends(get_supabase)):
    service = AuthService(db)
    return await service.register(body)


@router.post("/login", response_model=AuthResponse)
async def login(body: LoginRequest, db=Depends(get_supabase)):
    service = AuthService(db)
    return await service.login(body)


@router.post("/logout")
async def logout(request: Request, db=Depends(get_supabase)):
    token = request.headers.get("Authorization", "").split(" ", 1)[-1]
    service = AuthService(db)
    await service.logout(token)
    return {"message": "logged_out"}


@router.post("/refresh", response_model=AuthResponse)
async def refresh(body: RefreshRequest, db=Depends(get_supabase)):
    service = AuthService(db)
    return await service.refresh(body)
