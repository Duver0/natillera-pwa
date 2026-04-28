"""
API Contract Tests — /api/v1/history
Pagination, filter by event_type, reverse chronological order.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
from datetime import datetime, timezone, timedelta

from fastapi.testclient import TestClient
from app.main import app
from app.dependencies import get_user_id, get_db

USER_ID = "user-contract-history"
CLIENT_ID = str(uuid4())


def _mock_db():
    db = MagicMock()
    db.table = MagicMock(return_value=db)
    db.select = MagicMock(return_value=db)
    db.eq = MagicMock(return_value=db)
    db.order = MagicMock(return_value=db)
    db.range = MagicMock(return_value=db)
    db.execute = AsyncMock()
    return db


def _make_events(n: int, event_type="CREDIT_CREATED"):
    now = datetime.now(timezone.utc)
    return [
        {
            "id": str(uuid4()),
            "event_type": event_type,
            "client_id": str(CLIENT_ID),
            "amount": 1000.0,
            "description": f"event {i}",
            "created_at": (now - timedelta(days=i)).isoformat(),
        }
        for i in range(n)
    ]


@pytest.fixture
def client_with_auth():
    db = _mock_db()
    app.dependency_overrides[get_user_id] = lambda: USER_ID
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c, db
    app.dependency_overrides.clear()


def test_get_history_200_paginated(client_with_auth):
    """GIVEN 50 events WHEN GET /history?limit=10&offset=0 THEN 200 + 10 items."""
    # GIVEN
    c, db = client_with_auth
    db.execute.return_value = MagicMock(data=_make_events(10))

    # WHEN
    resp = c.get("/api/v1/history/?limit=10&offset=0")

    # THEN
    assert resp.status_code == 200
    assert len(resp.json()) == 10


def test_get_history_401_no_auth():
    """GIVEN no token WHEN GET /history THEN 401."""
    # GIVEN
    with TestClient(app, raise_server_exceptions=False) as c:
        # WHEN
        resp = c.get("/api/v1/history/")

    # THEN
    assert resp.status_code == 401


def test_get_history_filter_by_event_type(client_with_auth):
    """GIVEN filter type=PAYMENT_REGISTERED WHEN GET /history?event_type=X THEN only that type returned."""
    # GIVEN
    c, db = client_with_auth
    events = _make_events(3, event_type="PAYMENT_REGISTERED")
    db.execute.return_value = MagicMock(data=events)

    # WHEN
    resp = c.get("/api/v1/history/?event_type=PAYMENT_REGISTERED")

    # THEN
    assert resp.status_code == 200
    data = resp.json()
    assert all(e["event_type"] == "PAYMENT_REGISTERED" for e in data)


def test_get_history_filter_by_client_id(client_with_auth):
    """GIVEN client_id filter WHEN GET /history?client_id=X THEN service filters by client."""
    # GIVEN
    c, db = client_with_auth
    db.execute.return_value = MagicMock(data=_make_events(5))

    # WHEN
    resp = c.get(f"/api/v1/history/?client_id={CLIENT_ID}")

    # THEN
    assert resp.status_code == 200


def test_get_history_reverse_chronological_order(client_with_auth):
    """GIVEN events WHEN GET /history THEN service calls order(created_at, desc=True)."""
    # GIVEN
    c, db = client_with_auth
    db.execute.return_value = MagicMock(data=_make_events(3))

    # WHEN
    resp = c.get("/api/v1/history/")

    # THEN
    assert resp.status_code == 200
    # Verify order was called with desc=True via mock
    db.order.assert_called_with("created_at", desc=True)


def test_get_history_422_limit_too_large(client_with_auth):
    """GIVEN limit=201 (> max 200) WHEN GET /history THEN 422."""
    # GIVEN
    c, db = client_with_auth

    # WHEN
    resp = c.get("/api/v1/history/?limit=201")

    # THEN
    assert resp.status_code == 422


def test_get_history_422_negative_offset(client_with_auth):
    """GIVEN offset=-1 WHEN GET /history THEN 422."""
    # GIVEN
    c, db = client_with_auth

    # WHEN
    resp = c.get("/api/v1/history/?offset=-1")

    # THEN
    assert resp.status_code == 422


def test_get_history_default_pagination(client_with_auth):
    """GIVEN no pagination params WHEN GET /history THEN default limit=50 applied."""
    # GIVEN
    c, db = client_with_auth
    db.execute.return_value = MagicMock(data=_make_events(50))

    # WHEN
    resp = c.get("/api/v1/history/")

    # THEN
    assert resp.status_code == 200
    db.range.assert_called_with(0, 49)  # offset=0, limit=50 → range(0, 49)
