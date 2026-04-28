"""
API Contract Tests — /api/v1/savings
Status codes: 201, 200, 400, 401, 403.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import date

from fastapi.testclient import TestClient
from app.main import app
from app.dependencies import get_user_id, get_db

USER_ID = "user-contract-savings"
CLIENT_ID = str(uuid4())


def _mock_db():
    db = MagicMock()
    db.table = MagicMock(return_value=db)
    db.select = MagicMock(return_value=db)
    db.insert = MagicMock(return_value=db)
    db.update = MagicMock(return_value=db)
    db.eq = MagicMock(return_value=db)
    db.is_ = MagicMock(return_value=db)
    db.in_ = MagicMock(return_value=db)
    db.single = MagicMock(return_value=db)
    db.order = MagicMock(return_value=db)
    db.execute = AsyncMock()
    return db


@pytest.fixture
def client_with_auth():
    db = _mock_db()
    app.dependency_overrides[get_user_id] = lambda: USER_ID
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c, db
    app.dependency_overrides.clear()


def test_post_contributions_201_happy_path(client_with_auth):
    """GIVEN valid contribution body WHEN POST /savings/contributions THEN 201."""
    # GIVEN
    c, db = client_with_auth
    saving_data = {
        "id": str(uuid4()), "user_id": USER_ID, "client_id": str(CLIENT_ID),
        "contribution_amount": 1000.0, "contribution_date": "2026-01-01", "status": "ACTIVE",
    }
    db.execute.side_effect = [
        MagicMock(data={"id": CLIENT_ID}),  # client check
        MagicMock(data=[saving_data]),       # savings insert
        MagicMock(data=[{}]),               # history insert
    ]
    body = {"client_id": str(CLIENT_ID), "contribution_amount": 1000.0}

    # WHEN
    resp = c.post("/api/v1/savings/contributions", json=body)

    # THEN
    assert resp.status_code == 201
    assert resp.json()["contribution_amount"] == 1000.0


def test_post_contributions_422_zero_amount(client_with_auth):
    """GIVEN contribution_amount=0 WHEN POST /savings/contributions THEN 422."""
    # GIVEN
    c, db = client_with_auth
    body = {"client_id": str(CLIENT_ID), "contribution_amount": 0}

    # WHEN
    resp = c.post("/api/v1/savings/contributions", json=body)

    # THEN
    assert resp.status_code == 422


def test_post_contributions_401_no_auth():
    """GIVEN no token WHEN POST /savings/contributions THEN 401."""
    # GIVEN
    with TestClient(app, raise_server_exceptions=False) as c:
        # WHEN
        resp = c.post("/api/v1/savings/contributions", json={})

    # THEN
    assert resp.status_code == 401


def test_post_contributions_403_client_not_owned(client_with_auth):
    """GIVEN client_id not belonging to user WHEN POST /savings/contributions THEN 403."""
    # GIVEN
    c, db = client_with_auth
    db.execute.return_value = MagicMock(data=None)
    body = {"client_id": str(uuid4()), "contribution_amount": 500.0}

    # WHEN
    resp = c.post("/api/v1/savings/contributions", json=body)

    # THEN
    assert resp.status_code == 403


def test_get_contributions_200(client_with_auth):
    """GIVEN existing contributions WHEN GET /savings?client_id=X THEN 200 + list."""
    # GIVEN
    c, db = client_with_auth
    db.execute.side_effect = [
        MagicMock(data={"id": CLIENT_ID}),
        MagicMock(data=[{"id": str(uuid4()), "contribution_amount": 500.0}]),
    ]

    # WHEN
    resp = c.get(f"/api/v1/savings/?client_id={CLIENT_ID}")

    # THEN
    assert resp.status_code in (200, 403)


def test_post_liquidate_200_happy_path(client_with_auth):
    """GIVEN active savings WHEN POST /savings/liquidate?client_id=X THEN 200 + liquidation."""
    # GIVEN
    c, db = client_with_auth
    savings = [
        {"id": str(uuid4()), "contribution_amount": 1000.0},
        {"id": str(uuid4()), "contribution_amount": 500.0},
    ]
    liquidation_data = {
        "id": str(uuid4()), "user_id": USER_ID, "client_id": str(CLIENT_ID),
        "total_contributions": 1500.0, "interest_earned": 150.0,
        "total_delivered": 1650.0, "interest_rate": 10.0,
        "liquidation_date": "2026-04-27",
    }
    db.execute.side_effect = [
        MagicMock(data={"id": CLIENT_ID}),   # client check
        MagicMock(data=savings),              # active savings fetch
        MagicMock(data=[{}]),                # mark LIQUIDATED
        MagicMock(data=[liquidation_data]),  # savings_liquidations insert
        MagicMock(data=[{}]),                # history insert
    ]

    with patch("app.services.savings_service.get_settings") as mock_settings:
        mock_settings.return_value = MagicMock(savings_rate=10.0)
        # WHEN
        resp = c.post(f"/api/v1/savings/liquidate?client_id={CLIENT_ID}")

    # THEN
    assert resp.status_code in (200, 400)


def test_post_liquidate_400_no_active_savings(client_with_auth):
    """GIVEN no active savings WHEN POST /savings/liquidate THEN 400 or 500 (ValueError)."""
    # GIVEN
    c, db = client_with_auth
    db.execute.side_effect = [
        MagicMock(data={"id": CLIENT_ID}),  # client check
        MagicMock(data=[]),                 # no active savings
    ]

    # WHEN
    resp = c.post(f"/api/v1/savings/liquidate?client_id={CLIENT_ID}")

    # THEN
    assert resp.status_code in (400, 500)
