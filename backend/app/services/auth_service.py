from app.db import get_database
from app.models.auth_model import RegisterRequest, LoginRequest, RefreshRequest, AuthResponse


class AuthService:
    def __init__(self, db):
        self.db = db

    async def register(self, body: RegisterRequest) -> AuthResponse:
        response = await self.db.table("auth.users").insert({
            "email": body.email,
            "password": body.password,
        }).execute()
        if not response.data:
            raise ValueError("registration_failed")

    async def login(self, body: LoginRequest) -> AuthResponse:
        response = await self.db.table("auth.users").select("*").eq("email", body.email).single().execute()
        if not response.data:
            raise ValueError("invalid_credentials")

    async def logout(self, access_token: str) -> None:
        pass

    async def refresh(self, body: RefreshRequest) -> AuthResponse:
        raise ValueError("invalid_refresh_token")