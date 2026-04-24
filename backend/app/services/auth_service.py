from app.db import get_supabase
from app.models.auth_model import RegisterRequest, LoginRequest, RefreshRequest, AuthResponse


class AuthService:

    def __init__(self, db):
        self.db = db

    async def register(self, body: RegisterRequest) -> AuthResponse:
        response = await self.db.auth.sign_up({
            "email": body.email,
            "password": body.password,
        })
        if response.user is None:
            raise ValueError("registration_failed")

        user = response.user
        session = response.session

        # public.users row is created by DB trigger handle_new_user()
        return AuthResponse(
            access_token=session.access_token,
            refresh_token=session.refresh_token,
            user={
                "id": user.id,
                "email": user.email,
                "first_name": None,
                "last_name": None,
            },
        )

    async def login(self, body: LoginRequest) -> AuthResponse:
        response = await self.db.auth.sign_in_with_password({
            "email": body.email,
            "password": body.password,
        })
        if response.user is None:
            raise ValueError("invalid_credentials")

        user = response.user
        session = response.session

        # Fetch profile from public.users
        profile_result = await (
            self.db.table("users")
            .select("first_name,last_name")
            .eq("id", user.id)
            .single()
            .execute()
        )
        profile = profile_result.data or {}

        return AuthResponse(
            access_token=session.access_token,
            refresh_token=session.refresh_token,
            user={
                "id": user.id,
                "email": user.email,
                "first_name": profile.get("first_name"),
                "last_name": profile.get("last_name"),
            },
        )

    async def logout(self, access_token: str) -> None:
        await self.db.auth.sign_out()

    async def refresh(self, body: RefreshRequest) -> AuthResponse:
        response = await self.db.auth.refresh_session(body.refresh_token)
        if response.user is None:
            raise ValueError("invalid_refresh_token")

        user = response.user
        session = response.session

        return AuthResponse(
            access_token=session.access_token,
            refresh_token=session.refresh_token,
            user={
                "id": user.id,
                "email": user.email,
                "first_name": None,
                "last_name": None,
            },
        )
