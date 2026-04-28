"""
SPEC-002 §US-AUTH-006 — valid JWT allows request and injects user_id into request.state.
"""
from unittest.mock import patch, AsyncMock

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from tests.helpers.jwt_helpers import (
    generate_rsa_key_pair,
    public_key_to_jwk,
    make_valid_token,
    TEST_USER_ID,
    TEST_SUPABASE_URL,
)


def _make_app_with_state_echo():
    from app.middleware.auth import auth_middleware

    app = FastAPI()
    app.middleware("http")(auth_middleware)

    @app.get("/api/v1/protected")
    async def protected(request: Request):
        return {"user_id": getattr(request.state, "user_id", None)}

    return app


@pytest.fixture()
def rsa_keys():
    private_key, public_key = generate_rsa_key_pair()
    return private_key, public_key


def test_valid_token_returns_200_and_injects_user_id(rsa_keys):
    """GIVEN a valid RS256 JWT signed by Supabase WHEN hitting a protected endpoint THEN 200 + user_id injected."""
    private_key, public_key = rsa_keys
    token = make_valid_token(private_key)
    jwk = public_key_to_jwk(public_key)
    jwks_response = {"keys": [jwk]}

    async def mock_get_jwks():
        return jwks_response

    app = _make_app_with_state_echo()

    with patch("app.middleware.auth._get_jwks", new=mock_get_jwks), \
         patch("app.middleware.auth.SUPABASE_URL", TEST_SUPABASE_URL):
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get(
            "/api/v1/protected",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 200
    assert response.json()["user_id"] == TEST_USER_ID
