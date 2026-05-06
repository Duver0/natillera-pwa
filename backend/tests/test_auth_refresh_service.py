"""
Unit tests for AuthService.refresh() — mocking Supabase client directly.
"""
import pytest
from unittest.mock import MagicMock, patch
from app.services.auth_service import AuthService
from app.models.auth_model import RefreshRequest


def make_supabase_response(access_token="acc_new", refresh_token="ref_new", user_id="uid-99", email="svc@test.com"):
    user = MagicMock()
    user.id = user_id
    user.email = email
    session = MagicMock()
    session.access_token = access_token
    session.refresh_token = refresh_token
    resp = MagicMock()
    resp.user = user
    resp.session = session
    return resp


@pytest.fixture
def mock_db():
    return MagicMock()


@pytest.fixture
def auth_service(mock_db):
    return AuthService(mock_db)


@pytest.mark.asyncio
async def test_refresh_valid_token_returns_auth_response(auth_service):
    """GIVEN a valid refresh token WHEN refresh() is called THEN returns AuthResponse with new tokens."""
    # GIVEN
    supabase_resp = make_supabase_response()
    mock_supabase = MagicMock()
    mock_supabase.auth.refresh_session.return_value = supabase_resp
    auth_service._supabase = mock_supabase

    body = RefreshRequest(refresh_token="valid-token")

    # WHEN
    result = await auth_service.refresh(body)

    # THEN
    assert result.access_token == "acc_new"
    assert result.refresh_token == "ref_new"
    assert result.user.email == "svc@test.com"
    assert result.user.id == "uid-99"
    mock_supabase.auth.refresh_session.assert_called_once_with("valid-token")


@pytest.mark.asyncio
async def test_refresh_calls_supabase_with_exact_token(auth_service):
    """GIVEN a refresh token WHEN refresh() is called THEN supabase.auth.refresh_session receives that token."""
    # GIVEN
    supabase_resp = make_supabase_response()
    mock_supabase = MagicMock()
    mock_supabase.auth.refresh_session.return_value = supabase_resp
    auth_service._supabase = mock_supabase

    body = RefreshRequest(refresh_token="my-exact-token-xyz")

    # WHEN
    await auth_service.refresh(body)

    # THEN
    mock_supabase.auth.refresh_session.assert_called_once_with("my-exact-token-xyz")


@pytest.mark.asyncio
async def test_refresh_supabase_exception_raises_value_error(auth_service):
    """GIVEN supabase raises Exception WHEN refresh() is called THEN raises ValueError('invalid_refresh_token')."""
    # GIVEN
    mock_supabase = MagicMock()
    mock_supabase.auth.refresh_session.side_effect = Exception("Network error")
    auth_service._supabase = mock_supabase

    body = RefreshRequest(refresh_token="bad-token")

    # WHEN / THEN
    with pytest.raises(ValueError, match="invalid_refresh_token"):
        await auth_service.refresh(body)


@pytest.mark.asyncio
async def test_refresh_null_user_in_response_raises_value_error(auth_service):
    """GIVEN supabase returns user=None WHEN refresh() is called THEN raises ValueError('invalid_refresh_token')."""
    # GIVEN
    null_resp = MagicMock()
    null_resp.user = None
    mock_supabase = MagicMock()
    mock_supabase.auth.refresh_session.return_value = null_resp
    auth_service._supabase = mock_supabase

    body = RefreshRequest(refresh_token="token-no-user")

    # WHEN / THEN
    with pytest.raises(ValueError, match="invalid_refresh_token"):
        await auth_service.refresh(body)


@pytest.mark.asyncio
async def test_refresh_creates_supabase_client_lazily(mock_db):
    """GIVEN _supabase is None WHEN refresh() is called THEN creates client via create_client."""
    # GIVEN
    service = AuthService(mock_db)
    assert service._supabase is None

    supabase_resp = make_supabase_response()
    mock_supabase = MagicMock()
    mock_supabase.auth.refresh_session.return_value = supabase_resp

    with patch("app.services.auth_service.create_client", return_value=mock_supabase) as mock_factory:
        body = RefreshRequest(refresh_token="lazy-token")

        # WHEN
        result = await service.refresh(body)

        # THEN
        mock_factory.assert_called_once()
        assert result.access_token == "acc_new"
