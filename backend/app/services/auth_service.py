from app.models.auth_model import RegisterRequest, LoginRequest, RefreshRequest, AuthResponse, UserInfo
from app.config import get_settings
from supabase import create_client, Client


class AuthService:
    def __init__(self, db):
        self.db = db
        self._supabase: Client = None

    async def _get_supabase_client(self) -> Client:
        """Get or create Supabase client with anon key for auth"""
        if self._supabase is None:
            settings = get_settings()
            self._supabase = create_client(
                settings.supabase_url,
                settings.supabase_anon_key
            )
        return self._supabase

    async def register(self, body: RegisterRequest) -> AuthResponse:
        """Register using Supabase Auth API"""
        supabase = await self._get_supabase_client()
        
        try:
            response = supabase.auth.sign_up({
                "email": body.email,
                "password": body.password,
                "options": {
                    "email_redirect_to": f"{get_settings().supabase_url}/auth/callback"
                }
            })
            
            if response.user is None:
                raise ValueError("registration_failed")
            
            return AuthResponse(
                access_token=response.session.access_token if response.session else "",
                refresh_token=response.session.refresh_token if response.session else "",
                user=UserInfo(
                    id=response.user.id,
                    email=response.user.email
                )
            )
        except Exception as e:
            error_msg = str(e).lower()
            if "email_already_exists" in error_msg or "already been registered" in error_msg:
                raise ValueError("email_already_exists")
            raise ValueError(f"registration_failed: {e}")

    async def login(self, body: LoginRequest) -> AuthResponse:
        """Login using Supabase Auth API"""
        supabase = await self._get_supabase_client()
        
        try:
            response = supabase.auth.sign_in_with_password({
                "email": body.email,
                "password": body.password
            })
            
            if response.user is None:
                raise ValueError("invalid_credentials")
            
            return AuthResponse(
                access_token=response.session.access_token,
                refresh_token=response.session.refresh_token,
                user=UserInfo(
                    id=response.user.id,
                    email=response.user.email
                )
            )
        except Exception as e:
            raise ValueError("invalid_credentials")

    async def logout(self, access_token: str) -> None:
        """Logout using Supabase Auth API"""
        try:
            supabase = await self._get_supabase_client()
            supabase.auth.sign_out()
        except Exception:
            pass

    async def refresh(self, body: RefreshRequest) -> AuthResponse:
        """Refresh session using Supabase Auth API"""
        supabase = await self._get_supabase_client()
        
        try:
            response = supabase.auth.refresh_session(body.refresh_token)
            
            if response.user is None:
                raise ValueError("invalid_refresh_token")
            
            return AuthResponse(
                access_token=response.session.access_token,
                refresh_token=response.session.refresh_token,
                user=UserInfo(
                    id=response.user.id,
                    email=response.user.email
                )
            )
        except Exception as e:
            raise ValueError("invalid_refresh_token")
