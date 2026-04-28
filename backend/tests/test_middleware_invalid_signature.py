"""
SPEC-002 §US-AUTH-006 — JWT signed with wrong key → 401 invalid_signature / invalid_token.
"""
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from tests.helpers.jwt_helpers import (
    generate_rsa_key_pair,
    public_key_to_jwk,
    make_valid_token,
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


def test_token_signed_with_different_key_returns_401():
    """GIVEN JWT signed with key A but JWKS exposes key B WHEN validating THEN 401."""
    signer_private, _ = generate_rsa_key_pair()
    _, wrong_public = generate_rsa_key_pair()

    token = make_valid_token(signer_private)
    jwk = public_key_to_jwk(wrong_public)
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
    assert response.json()["detail"] in ("invalid_signature", "invalid_token")


def test_kid_not_in_jwks_returns_401():
    """GIVEN a valid JWT whose kid is not present in JWKS WHEN validating THEN 401 invalid_token."""
    private_key, public_key = generate_rsa_key_pair()
    token = make_valid_token(private_key, kid="test-key-id")
    jwk = public_key_to_jwk(public_key, kid="other-key-id")
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
    assert response.json()["detail"] == "invalid_token"
