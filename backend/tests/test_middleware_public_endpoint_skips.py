"""
SPEC-002 §US-AUTH-006 — public endpoints bypass JWT validation entirely.
"""
from fastapi import FastAPI
from fastapi.testclient import TestClient


def _make_app():
    from app.middleware.auth import auth_middleware

    app = FastAPI()
    app.middleware("http")(auth_middleware)

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    @app.post("/api/v1/auth/login")
    async def login():
        return {"result": "login"}

    @app.post("/api/v1/auth/register")
    async def register():
        return {"result": "register"}

    @app.post("/api/v1/auth/refresh")
    async def refresh():
        return {"result": "refresh"}

    @app.get("/api/v1/clients/")
    async def clients():
        return []

    return app


def test_health_skips_auth():
    """GIVEN no token WHEN hitting /health THEN 200."""
    client = TestClient(_make_app(), raise_server_exceptions=False)
    assert client.get("/health").status_code == 200


def test_auth_login_skips_auth():
    """GIVEN no token WHEN POST /auth/login THEN 200."""
    client = TestClient(_make_app(), raise_server_exceptions=False)
    assert client.post("/api/v1/auth/login").status_code == 200


def test_auth_register_skips_auth():
    """GIVEN no token WHEN POST /auth/register THEN 200."""
    client = TestClient(_make_app(), raise_server_exceptions=False)
    assert client.post("/api/v1/auth/register").status_code == 200


def test_auth_refresh_skips_auth():
    """GIVEN no token WHEN POST /auth/refresh THEN 200."""
    client = TestClient(_make_app(), raise_server_exceptions=False)
    assert client.post("/api/v1/auth/refresh").status_code == 200


def test_protected_endpoint_requires_token():
    """GIVEN no token WHEN hitting non-public endpoint THEN 401."""
    client = TestClient(_make_app(), raise_server_exceptions=False)
    assert client.get("/api/v1/clients/").status_code == 401
