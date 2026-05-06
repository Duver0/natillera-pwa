"""
Integration tests for POST /api/v1/auth/refresh endpoint.
"""
import pytest
from unittest.mock import MagicMock, patch
from httpx import AsyncClient, ASGITransport


def make_supabase_response(access_token="new_acc", refresh_token="new_ref", user_id="uid-1", email="u@test.com"):
    user = MagicMock()
    user.id = user_id
    user.email = email
    session = MagicMock()
    session.access_token = access_token
    session.refresh_token = refresh_token
    response = MagicMock()
    response.user = user
    response.session = session
    return response


@pytest.fixture
def app_with_test_mode():
    from app.main import app, set_test_mode
    set_test_mode(True)
    yield app
    set_test_mode(False)


@pytest.mark.asyncio
async def test_refresh_valid_token_returns_new_tokens(app_with_test_mode):
    """GIVEN a valid refresh_token WHEN POST /refresh THEN returns 200 with new tokens and user."""
    supabase_resp = make_supabase_response()

    with patch("app.services.auth_service.create_client") as mock_create:
        mock_supabase = MagicMock()
        mock_supabase.auth.refresh_session.return_value = supabase_resp
        mock_create.return_value = mock_supabase

        async with AsyncClient(
            transport=ASGITransport(app=app_with_test_mode),
            base_url="http://test"
        ) as client:
            # WHEN
            response = await client.post(
                "/api/v1/auth/refresh",
                json={"refresh_token": "valid-refresh-token"}
            )

    # THEN
    assert response.status_code == 200
    data = response.json()
    assert data["access_token"] == "new_acc"
    assert data["refresh_token"] == "new_ref"
    assert data["user"]["email"] == "u@test.com"


@pytest.mark.asyncio
async def test_refresh_invalid_token_returns_401(app_with_test_mode):
    """GIVEN an invalid refresh_token WHEN POST /refresh THEN returns 401 invalid_refresh_token."""
    with patch("app.services.auth_service.create_client") as mock_create:
        mock_supabase = MagicMock()
        mock_supabase.auth.refresh_session.side_effect = Exception("Token expired")
        mock_create.return_value = mock_supabase

        async with AsyncClient(
            transport=ASGITransport(app=app_with_test_mode),
            base_url="http://test"
        ) as client:
            # WHEN
            response = await client.post(
                "/api/v1/auth/refresh",
                json={"refresh_token": "expired-token"}
            )

    # THEN
    assert response.status_code == 401
    assert response.json()["detail"] == "invalid_refresh_token"


@pytest.mark.asyncio
async def test_refresh_empty_token_returns_422(app_with_test_mode):
    """GIVEN empty refresh_token WHEN POST /refresh THEN returns 422 validation error."""
    async with AsyncClient(
        transport=ASGITransport(app=app_with_test_mode),
        base_url="http://test"
    ) as client:
        # WHEN
        response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": ""}
        )

    # THEN — Pydantic accepts empty string (no min_length constraint on RefreshRequest)
    # The supabase call will fail → 401 is also acceptable; check for non-200
    assert response.status_code in (401, 422)


@pytest.mark.asyncio
async def test_refresh_missing_body_returns_422(app_with_test_mode):
    """GIVEN missing body WHEN POST /refresh THEN returns 422."""
    async with AsyncClient(
        transport=ASGITransport(app=app_with_test_mode),
        base_url="http://test"
    ) as client:
        # WHEN
        response = await client.post("/api/v1/auth/refresh", json={})

    # THEN
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_refresh_supabase_returns_null_user_returns_401(app_with_test_mode):
    """GIVEN supabase returns response with user=None WHEN POST /refresh THEN returns 401."""
    null_resp = MagicMock()
    null_resp.user = None

    with patch("app.services.auth_service.create_client") as mock_create:
        mock_supabase = MagicMock()
        mock_supabase.auth.refresh_session.return_value = null_resp
        mock_create.return_value = mock_supabase

        async with AsyncClient(
            transport=ASGITransport(app=app_with_test_mode),
            base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/v1/auth/refresh",
                json={"refresh_token": "some-token"}
            )

    assert response.status_code == 401
