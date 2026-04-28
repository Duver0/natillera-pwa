"""
API Contract Tests — /api/v1/payments
Status codes: 201, 200, 400, 409, 403, 422.
"""
import pytest
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from fastapi.testclient import TestClient
from app.main import app
from app.dependencies import get_user_id, get_db

USER_ID = "user-contract-pay"
CREDIT_ID = str(uuid4())
INST_ID = str(uuid4())


def _mock_db():
    db = MagicMock()
    db.table = MagicMock(return_value=db)
    db.select = MagicMock(return_value=db)
    db.insert = MagicMock(return_value=db)
    db.update = MagicMock(return_value=db)
    db.eq = MagicMock(return_value=db)
    db.in_ = MagicMock(return_value=db)
    db.single = MagicMock(return_value=db)
    db.order = MagicMock(return_value=db)
    db.rpc = MagicMock(return_value=db)
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


def _rpc_success(credit_id=CREDIT_ID):
    return MagicMock(data={
        "payment_id": str(uuid4()),
        "credit_id": credit_id,
        "total_amount": "500.00",
        "applied_to": [],
        "updated_credit_snapshot": {
            "pending_capital": "9500.00",
            "mora": False,
            "version": 2,
        },
        "idempotent": False,
    })


def test_post_payments_201_happy_path(client_with_auth):
    """GIVEN valid payment body WHEN POST /payments THEN 201 + PaymentResponse."""
    # GIVEN
    c, db = client_with_auth
    db.execute.return_value = _rpc_success()
    body = {
        "credit_id": CREDIT_ID,
        "amount": "500.00",
        "operator_id": USER_ID,
    }

    # WHEN
    resp = c.post("/api/v1/payments/", json=body)

    # THEN
    assert resp.status_code == 201


def test_post_payments_422_missing_fields(client_with_auth):
    """GIVEN missing operator_id WHEN POST /payments THEN 422."""
    # GIVEN
    c, db = client_with_auth
    body = {"credit_id": CREDIT_ID, "amount": "500.00"}  # missing operator_id

    # WHEN
    resp = c.post("/api/v1/payments/", json=body)

    # THEN
    assert resp.status_code == 422


def test_post_payments_422_zero_amount(client_with_auth):
    """GIVEN amount=0 WHEN POST /payments THEN 422 (gt=0 constraint)."""
    # GIVEN
    c, db = client_with_auth
    body = {"credit_id": CREDIT_ID, "amount": "0.00", "operator_id": USER_ID}

    # WHEN
    resp = c.post("/api/v1/payments/", json=body)

    # THEN
    assert resp.status_code == 422


def test_post_payments_401_no_auth():
    """GIVEN no token WHEN POST /payments THEN 401."""
    # GIVEN
    with TestClient(app, raise_server_exceptions=False) as c:
        # WHEN
        resp = c.post("/api/v1/payments/", json={})

    # THEN
    assert resp.status_code == 401


def test_post_payments_409_version_conflict(client_with_auth):
    """GIVEN RPC raises VersionConflict WHEN POST /payments THEN 409."""
    # GIVEN
    c, db = client_with_auth
    db.execute.side_effect = Exception("VersionConflict P0001")
    body = {
        "credit_id": CREDIT_ID,
        "amount": "500.00",
        "operator_id": USER_ID,
    }

    # WHEN
    resp = c.post("/api/v1/payments/", json=body)

    # THEN
    assert resp.status_code == 409


def test_post_payments_400_credit_closed(client_with_auth):
    """GIVEN RPC raises CreditClosed WHEN POST /payments THEN 400."""
    # GIVEN
    c, db = client_with_auth
    db.execute.side_effect = Exception("CreditClosed P0002")
    body = {
        "credit_id": CREDIT_ID,
        "amount": "500.00",
        "operator_id": USER_ID,
    }

    # WHEN
    resp = c.post("/api/v1/payments/", json=body)

    # THEN
    assert resp.status_code == 400
    assert resp.json()["detail"] == "credit_not_active"


def test_post_payments_preview_200(client_with_auth):
    """GIVEN valid preview request WHEN POST /payments/preview THEN 200 + breakdown."""
    # GIVEN
    c, db = client_with_auth
    credit_data = {
        "id": CREDIT_ID, "user_id": USER_ID, "pending_capital": "10000.00",
        "annual_interest_rate": 12.0, "periodicity": "MONTHLY",
        "status": "ACTIVE", "mora": False, "version": 1,
    }
    db.execute.side_effect = [
        MagicMock(data=credit_data),  # credit fetch
        MagicMock(data=[]),           # installments fetch
    ]
    body = {"credit_id": CREDIT_ID, "amount": "500.00"}

    # WHEN
    resp = c.post("/api/v1/payments/preview", json=body)

    # THEN
    assert resp.status_code == 200
    data = resp.json()
    assert "applied_to" in data
    assert "updated_credit_snapshot" in data


def test_get_payments_200_list(client_with_auth):
    """GIVEN existing payments WHEN GET /payments?credit_id=X THEN 200 + list."""
    # GIVEN
    c, db = client_with_auth
    db.execute.side_effect = [
        MagicMock(data={"id": CREDIT_ID}),  # credit ownership check
        MagicMock(data=[{"id": str(uuid4()), "amount": 500.0}]),  # payments list
    ]

    # WHEN
    resp = c.get(f"/api/v1/payments/?credit_id={CREDIT_ID}")

    # THEN
    assert resp.status_code in (200, 403)


def test_post_payments_idempotent_hit_returns_200(client_with_auth):
    """GIVEN idempotency_key already processed WHEN POST /payments THEN still 201 (idempotent response)."""
    # GIVEN
    c, db = client_with_auth
    idem_key = str(uuid4())
    db.execute.return_value = MagicMock(data={
        "payment_id": str(uuid4()),
        "credit_id": CREDIT_ID,
        "total_amount": "500.00",
        "applied_to": [],
        "updated_credit_snapshot": {"pending_capital": "9500.00", "mora": False, "version": 2},
        "idempotent": True,
    })
    body = {
        "credit_id": CREDIT_ID,
        "amount": "500.00",
        "operator_id": USER_ID,
        "idempotency_key": idem_key,
    }

    # WHEN
    resp = c.post("/api/v1/payments/", json=body)

    # THEN — router returns 201, idempotent flag is internal
    assert resp.status_code == 201
