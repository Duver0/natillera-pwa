"""
SPEC-002 §US-AUTH-006 — missing Authorization header on protected endpoint → 401.
"""
from fastapi import FastAPI
from fastapi.testclient import TestClient


def _make_app():
    from app.middleware.auth import auth_middleware

    app = FastAPI()
    app.middleware("http")(auth_middleware)

    @app.get("/api/v1/clients/")
    async def clients():
        return []

    return app


def test_missing_token_returns_401():
    """GIVEN no Authorization header WHEN hitting protected endpoint THEN 401 missing_token."""
    app = _make_app()
    client = TestClient(app, raise_server_exceptions=False)

    response = client.get("/api/v1/clients/")

    assert response.status_code == 401
    assert response.json()["detail"] == "missing_token"


def test_wrong_scheme_returns_401_missing_token():
    """GIVEN Authorization header without Bearer prefix WHEN hitting protected endpoint THEN 401 missing_token."""
    app = _make_app()
    client = TestClient(app, raise_server_exceptions=False)

    response = client.get("/api/v1/clients/", headers={"Authorization": "Basic abc123"})

    assert response.status_code == 401
    assert response.json()["detail"] == "missing_token"
