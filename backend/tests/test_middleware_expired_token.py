"""
SPEC-002 §US-AUTH-006 — expired JWT → 401 token_expired.
"""
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from tests.helpers.jwt_helpers import (
    generate_rsa_key_pair,
    public_key_to_jwk,
    make_expired_token,
    TEST_SUPABASE_URL,
)


def _make_app():
    from app.middleware.auth import auth_middleware

    app = FastAPI()
    app.middleware("http")(auth_middleware)

    @app.get("/api/v1/clients/")
    async def clients():
        return []

    return app


def test_expired_token_returns_401_token_expired():
    """GIVEN an RS256 JWT with exp in the past WHEN hitting protected endpoint THEN 401 token_expired."""
    private_key, public_key = generate_rsa_key_pair()
    token = make_expired_token(private_key)
    jwk = public_key_to_jwk(public_key)
    jwks_response = {"keys": [jwk]}

    async def mock_get_jwks():
        return jwks_response

    app = _make_app()

    with patch("app.middleware.auth._get_jwks", new=mock_get_jwks), \
         patch("app.middleware.auth.SUPABASE_URL", TEST_SUPABASE_URL):
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get(
            "/api/v1/clients/",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 401
    assert response.json()["detail"] == "token_expired"
