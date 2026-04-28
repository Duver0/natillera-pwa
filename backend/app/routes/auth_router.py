from fastapi import APIRouter, Request
from app.db import get_database
from app.services.auth_service import AuthService
from app.models.auth_model import RegisterRequest, LoginRequest, RefreshRequest, AuthResponse

router = APIRouter()


@router.post("/register", response_model=AuthResponse)
async def register(body: RegisterRequest):
    if not is_supabase():
        from fastapi import HTTPException
        raise HTTPException(status_code=501, detail="auth_not_available_in_local_mode")
    db = get_database()
    service = AuthService(db)
    return await service.register(body)


@router.post("/login", response_model=AuthResponse)
async def login(body: LoginRequest):
    if not is_supabase():
        from fastapi import HTTPException
        raise HTTPException(status_code=501, detail="auth_not_available_in_local_mode")
    db = get_database()
    service = AuthService(db)
    return await service.login(body)


@router.post("/logout")
async def logout(request: Request):
    if not is_supabase():
        from fastapi import HTTPException
        raise HTTPException(status_code=501, detail="auth_not_available_in_local_mode")
    db = get_database()
    token = request.headers.get("Authorization", "").split(" ", 1)[-1]
    service = AuthService(db)
    await service.logout(token)
    return {"message": "logged_out"}


@router.post("/refresh", response_model=AuthResponse)
async def refresh(body: RefreshRequest):
    if not is_supabase():
        from fastapi import HTTPException
        raise HTTPException(status_code=501, detail="auth_not_available_in_local_mode")
    db = get_database()
    service = AuthService(db)
    return await service.refresh(body)