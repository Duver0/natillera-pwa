"""
Tests for auth endpoints: register / login / logout / refresh
Tests the auth endpoints with mocked AuthService.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient

from app.main import app, set_test_mode
import app.db as _db_module

VALID_EMAIL = "user@example.com"
VALID_PASSWORD = "securepass123"
MOCK_USER_ID = "00000000-0000-0000-0000-000000000001"
MOCK_ACCESS_TOKEN = "mock.access.token"
MOCK_REFRESH_TOKEN = "mock.refresh.token"


@pytest.fixture(autouse=True)
def setup_auth_test(monkeypatch):
    set_test_mode(True)
    mock_db = MagicMock()
    mock_db.table.return_value = mock_db
    mock_db.select.return_value = mock_db
    mock_db.execute.return_value = MagicMock(data=[])
    monkeypatch.setattr(_db_module, "get_database", lambda: mock_db)
    yield
    set_test_mode(False)


@pytest.fixture()
def client():
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


class TestRegister:
    def test_register_happy_path(self, client, monkeypatch):
        mock_resp = MagicMock()
        mock_resp.user = MagicMock(id=MOCK_USER_ID, email=VALID_EMAIL)
        mock_resp.session = MagicMock(access_token=MOCK_ACCESS_TOKEN, refresh_token=MOCK_REFRESH_TOKEN)
        
        async def mock_register(self, body):
            return mock_resp
        
        from app import services
        monkeypatch.setattr(services.auth_service.AuthService, "register", mock_register)
        
        resp = client.post("/api/v1/auth/register", json={
            "email": VALID_EMAIL,
            "password": VALID_PASSWORD,
        })

        assert resp.status_code == 200
        assert resp.json()["access_token"] == MOCK_ACCESS_TOKEN

    def test_register_missing_email_returns_422(self, client):
        resp = client.post("/api/v1/auth/register", json={"password": VALID_PASSWORD})
        assert resp.status_code == 422


class TestLogin:
    def test_login_invalid_credentials_returns_401(self, client, monkeypatch):
        async def mock_login(self, body):
            raise ValueError("invalid_credentials")
        
        from app import services
        monkeypatch.setattr(services.auth_service.AuthService, "login", mock_login)
        
        resp = client.post("/api/v1/auth/login", json={
            "email": VALID_EMAIL,
            "password": "wrongpass",
        })

        assert resp.status_code == 401

    def test_login_missing_password_returns_422(self, client):
        resp = client.post("/api/v1/auth/login", json={"email": VALID_EMAIL})
        assert resp.status_code == 422


class TestLogout:
    def test_logout_returns_200(self, client, monkeypatch):
        async def mock_logout(self, token):
            pass
        
        from app import services
        monkeypatch.setattr(services.auth_service.AuthService, "logout", mock_logout)
        
        resp = client.post("/api/v1/auth/logout", headers={"Authorization": f"Bearer {MOCK_ACCESS_TOKEN}"})

        assert resp.status_code == 200


class TestRefresh:
    def test_refresh_invalid_token_returns_401(self, client, monkeypatch):
        async def mock_refresh(self, body):
            raise ValueError("invalid_refresh_token")
        
        from app import services
        monkeypatch.setattr(services.auth_service.AuthService, "refresh", mock_refresh)
        
        resp = client.post("/api/v1/auth/refresh", json={"refresh_token": "invalid"})

        assert resp.status_code == 401