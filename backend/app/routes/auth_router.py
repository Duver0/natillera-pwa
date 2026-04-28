from fastapi import APIRouter, Request, HTTPException
from app.db import get_database, is_supabase
from app.services.auth_service import AuthService
from app.models.auth_model import RegisterRequest, LoginRequest, RefreshRequest, AuthResponse

router = APIRouter()


@router.post("/register", response_model=AuthResponse)
async def register(body: RegisterRequest):
    if not is_supabase():
        raise HTTPException(status_code=501, detail="auth_not_available_in_local_mode")
    db = get_database()
    service = AuthService(db)
    try:
        return await service.register(body)
    except ValueError as e:
        error_msg = str(e)
        if "email_already_exists" in error_msg:
            raise HTTPException(status_code=400, detail="email_already_exists")
        raise HTTPException(status_code=400, detail=error_msg)


@router.post("/login", response_model=AuthResponse)
async def login(body: LoginRequest):
    if not is_supabase():
        raise HTTPException(status_code=501, detail="auth_not_available_in_local_mode")
    db = get_database()
    service = AuthService(db)
    try:
        return await service.login(body)
    except ValueError:
        raise HTTPException(status_code=401, detail="invalid_credentials")


@router.post("/logout")
async def logout(request: Request):
    if not is_supabase():
        raise HTTPException(status_code=501, detail="auth_not_available_in_local_mode")
    db = get_database()
    token = request.headers.get("Authorization", "").split(" ", 1)[-1]
    service = AuthService(db)
    await service.logout(token)
    return {"message": "logged_out"}


@router.post("/refresh", response_model=AuthResponse)
async def refresh(body: RefreshRequest):
    if not is_supabase():
        raise HTTPException(status_code=501, detail="auth_not_available_in_local_mode")
    db = get_database()
    service = AuthService(db)
    try:
        return await service.refresh(body)
    except ValueError:
        raise HTTPException(status_code=401, detail="invalid_refresh_token")