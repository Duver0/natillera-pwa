"""
Unit tests for auth middleware — token validation, public paths.
SPEC-002 §US-AUTH-006.
"""
import pytest
import json
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from fastapi import FastAPI


def _make_app():
    """Minimal FastAPI app with auth middleware for testing."""
    from app.middleware.auth import auth_middleware
    from app.middleware.error_handler import register_error_handlers

    app = FastAPI()
    app.middleware("http")(auth_middleware)
    register_error_handlers(app)

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    @app.get("/api/v1/clients/")
    async def clients():
        return []

    @app.post("/api/v1/auth/login")
    async def login():
        return {"token": "ok"}

    return app


def test_health_endpoint_is_public():
    """Health endpoint bypasses auth middleware."""
    app = _make_app()
    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/health")
    assert response.status_code == 200


def test_login_endpoint_is_public():
    """Auth endpoints bypass middleware."""
    app = _make_app()
    client = TestClient(app, raise_server_exceptions=False)
    response = client.post("/api/v1/auth/login")
    assert response.status_code == 200


def test_protected_endpoint_missing_token_returns_401():
    """Missing Authorization header on protected endpoint → 401."""
    app = _make_app()
    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/api/v1/clients/")
    assert response.status_code == 401
    assert response.json()["detail"] == "missing_token"


def test_protected_endpoint_invalid_token_returns_401():
    """Malformed token → 401."""
    app = _make_app()
    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/api/v1/clients/", headers={"Authorization": "Bearer not_a_real_jwt"})
    assert response.status_code == 401


def test_bearer_prefix_required():
    """Token without 'Bearer ' prefix → 401 missing_token."""
    app = _make_app()
    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/api/v1/clients/", headers={"Authorization": "Token abc123"})
    assert response.status_code == 401
    assert response.json()["detail"] == "missing_token"
