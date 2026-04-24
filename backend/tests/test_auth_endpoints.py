"""
Tests for auth endpoints: register / login / logout / refresh
Uses mocked Supabase + mocked AuthService to avoid live DB.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient

from app.main import app

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

VALID_EMAIL = "user@example.com"
VALID_PASSWORD = "securepass123"
MOCK_USER_ID = "00000000-0000-0000-0000-000000000001"
MOCK_ACCESS_TOKEN = "mock.access.token"
MOCK_REFRESH_TOKEN = "mock.refresh.token"

MOCK_AUTH_RESPONSE = {
    "access_token": MOCK_ACCESS_TOKEN,
    "refresh_token": MOCK_REFRESH_TOKEN,
    "user": {
        "id": MOCK_USER_ID,
        "email": VALID_EMAIL,
        "first_name": None,
        "last_name": None,
    },
}


def _make_mock_db():
    mock_db = AsyncMock()
    return mock_db


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

@pytest.fixture()
def client():
    return TestClient(app, raise_server_exceptions=False)


# ---------------------------------------------------------------------------
# POST /api/v1/auth/register
# ---------------------------------------------------------------------------

class TestRegister:
    def test_register_happy_path(self, client):
        # GIVEN valid credentials
        with patch("app.services.auth_service.AuthService.register", new_callable=AsyncMock) as mock_reg, \
             patch("app.routes.auth_router.get_supabase", return_value=_make_mock_db()):
            mock_reg.return_value = MOCK_AUTH_RESPONSE

            # WHEN POST /register
            resp = client.post("/api/v1/auth/register", json={
                "email": VALID_EMAIL,
                "password": VALID_PASSWORD,
            })

        # THEN 200 with tokens
        assert resp.status_code == 200
        body = resp.json()
        assert body["access_token"] == MOCK_ACCESS_TOKEN
        assert body["user"]["email"] == VALID_EMAIL

    def test_register_missing_email_returns_422(self, client):
        # GIVEN missing email field
        resp = client.post("/api/v1/auth/register", json={"password": VALID_PASSWORD})

        # THEN validation error
        assert resp.status_code == 422

    def test_register_short_password_returns_422(self, client):
        # GIVEN password shorter than 8 chars
        resp = client.post("/api/v1/auth/register", json={
            "email": VALID_EMAIL,
            "password": "short",
        })

        # THEN validation error
        assert resp.status_code == 422

    def test_register_service_raises_returns_500(self, client):
        # GIVEN Supabase returns no user (registration_failed)
        with patch("app.services.auth_service.AuthService.register", new_callable=AsyncMock) as mock_reg, \
             patch("app.routes.auth_router.get_supabase", return_value=_make_mock_db()):
            mock_reg.side_effect = ValueError("registration_failed")

            resp = client.post("/api/v1/auth/register", json={
                "email": VALID_EMAIL,
                "password": VALID_PASSWORD,
            })

        # THEN error response
        assert resp.status_code in (400, 422, 500)


# ---------------------------------------------------------------------------
# POST /api/v1/auth/login
# ---------------------------------------------------------------------------

class TestLogin:
    def test_login_happy_path(self, client):
        # GIVEN valid credentials
        with patch("app.services.auth_service.AuthService.login", new_callable=AsyncMock) as mock_login, \
             patch("app.routes.auth_router.get_supabase", return_value=_make_mock_db()):
            mock_login.return_value = MOCK_AUTH_RESPONSE

            resp = client.post("/api/v1/auth/login", json={
                "email": VALID_EMAIL,
                "password": VALID_PASSWORD,
            })

        # THEN tokens returned
        assert resp.status_code == 200
        body = resp.json()
        assert "access_token" in body
        assert "refresh_token" in body

    def test_login_invalid_credentials_raises(self, client):
        # GIVEN wrong password
        with patch("app.services.auth_service.AuthService.login", new_callable=AsyncMock) as mock_login, \
             patch("app.routes.auth_router.get_supabase", return_value=_make_mock_db()):
            mock_login.side_effect = ValueError("invalid_credentials")

            resp = client.post("/api/v1/auth/login", json={
                "email": VALID_EMAIL,
                "password": "wrongpass",
            })

        # THEN error response (not 200)
        assert resp.status_code != 200

    def test_login_missing_password_returns_422(self, client):
        # GIVEN missing password field
        resp = client.post("/api/v1/auth/login", json={"email": VALID_EMAIL})

        # THEN validation error
        assert resp.status_code == 422

    def test_login_invalid_email_format_returns_422(self, client):
        # GIVEN non-email string
        resp = client.post("/api/v1/auth/login", json={
            "email": "not-an-email",
            "password": VALID_PASSWORD,
        })

        # THEN 422
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# POST /api/v1/auth/logout
# ---------------------------------------------------------------------------

class TestLogout:
    def test_logout_happy_path(self, client):
        # GIVEN a bearer token in header
        with patch("app.services.auth_service.AuthService.logout", new_callable=AsyncMock) as mock_logout, \
             patch("app.routes.auth_router.get_supabase", return_value=_make_mock_db()), \
             patch("app.middleware.auth.auth_middleware", side_effect=lambda request, call_next: call_next(request)):
            mock_logout.return_value = None

            resp = client.post(
                "/api/v1/auth/logout",
                headers={"Authorization": f"Bearer {MOCK_ACCESS_TOKEN}"},
            )

        # THEN 200 with logged_out message
        assert resp.status_code == 200
        assert resp.json().get("message") == "logged_out"

    def test_logout_no_token_still_accepted(self, client):
        # GIVEN no Authorization header — logout is best-effort
        with patch("app.services.auth_service.AuthService.logout", new_callable=AsyncMock) as mock_logout, \
             patch("app.routes.auth_router.get_supabase", return_value=_make_mock_db()), \
             patch("app.middleware.auth.auth_middleware", side_effect=lambda request, call_next: call_next(request)):
            mock_logout.return_value = None

            resp = client.post("/api/v1/auth/logout")

        # THEN accepted (no crash)
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# POST /api/v1/auth/refresh
# ---------------------------------------------------------------------------

class TestRefresh:
    def test_refresh_happy_path(self, client):
        # GIVEN valid refresh token
        with patch("app.services.auth_service.AuthService.refresh", new_callable=AsyncMock) as mock_refresh, \
             patch("app.routes.auth_router.get_supabase", return_value=_make_mock_db()), \
             patch("app.middleware.auth.auth_middleware", side_effect=lambda request, call_next: call_next(request)):
            mock_refresh.return_value = MOCK_AUTH_RESPONSE

            resp = client.post("/api/v1/auth/refresh", json={"refresh_token": MOCK_REFRESH_TOKEN})

        # THEN new tokens returned
        assert resp.status_code == 200
        body = resp.json()
        assert "access_token" in body

    def test_refresh_invalid_token_raises(self, client):
        # GIVEN expired/invalid refresh token
        with patch("app.services.auth_service.AuthService.refresh", new_callable=AsyncMock) as mock_refresh, \
             patch("app.routes.auth_router.get_supabase", return_value=_make_mock_db()), \
             patch("app.middleware.auth.auth_middleware", side_effect=lambda request, call_next: call_next(request)):
            mock_refresh.side_effect = ValueError("invalid_refresh_token")

            resp = client.post("/api/v1/auth/refresh", json={"refresh_token": "expired.token"})

        # THEN error response
        assert resp.status_code != 200

    def test_refresh_missing_body_returns_422(self, client):
        # GIVEN empty body
        with patch("app.middleware.auth.auth_middleware", side_effect=lambda request, call_next: call_next(request)):
            resp = client.post("/api/v1/auth/refresh", json={})

        # THEN 422
        assert resp.status_code == 422
