"""
E2E Integration Test: create credit → generate installments → register payment → verify pending_capital reduced.
Uses mocked DB — no real Supabase connection.
"""
import pytest
from decimal import Decimal
from datetime import date, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from app.services.credit_service import CreditService
from app.services.payment_service import PaymentService, _compute_breakdown_3pool
from app.models.credit_model import CreditCreate, Periodicity
from app.models.payment_model import PaymentRequest


USER_ID = "user-e2e-001"
CLIENT_ID = str(uuid4())
CREDIT_ID = str(uuid4())
INST_ID = str(uuid4())


def _make_db():
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
    db.lt = MagicMock(return_value=db)
    db.rpc = MagicMock(return_value=db)
    db.execute = AsyncMock()
    return db


@pytest.mark.anyio
async def test_create_credit_generates_installments_and_records_history():
    """GIVEN valid credit body WHEN create() THEN installments inserted + history recorded."""
    # GIVEN
    db = _make_db()
    client_resp = MagicMock(data={"id": CLIENT_ID, "user_id": USER_ID})
    credit_data = {
        "id": CREDIT_ID, "user_id": USER_ID, "client_id": CLIENT_ID,
        "initial_capital": 10000.0, "pending_capital": 10000.0,
        "version": 1, "periodicity": "MONTHLY", "annual_interest_rate": 12.0,
        "status": "ACTIVE", "mora": False, "mora_since": None,
    }
    db.execute.side_effect = [
        MagicMock(data=client_resp),    # client ownership check
        MagicMock(data=[credit_data]),  # credits.insert
        MagicMock(data=[]),             # installments.insert
        MagicMock(data=[{}]),           # financial_history.insert
    ]

    service = CreditService(db, USER_ID)
    body = CreditCreate(
        client_id=CLIENT_ID,
        initial_capital=10000.0,
        periodicity=Periodicity.MONTHLY,
        annual_interest_rate=12.0,
        start_date=date(2026, 1, 1),
    )

    # WHEN
    result = await service.create(body)

    # THEN
    assert result["id"] == CREDIT_ID
    assert result["pending_capital"] == 10000.0
    assert result["status"] == "ACTIVE"
    # installments and history inserts were called
    assert db.execute.call_count >= 3


@pytest.mark.anyio
async def test_payment_reduces_pending_capital_via_rpc():
    """GIVEN active credit WHEN process_payment RPC called THEN pending_capital reduced in snapshot."""
    # GIVEN
    db = _make_db()
    new_capital = "9583.33"
    rpc_response = {
        "payment_id": str(uuid4()),
        "credit_id": CREDIT_ID,
        "total_amount": "416.67",
        "applied_to": [
            {"installment_id": INST_ID, "type": "OVERDUE_INTEREST", "amount": "100.00"},
            {"installment_id": INST_ID, "type": "OVERDUE_PRINCIPAL", "amount": "316.67"},
        ],
        "updated_credit_snapshot": {
            "pending_capital": new_capital,
            "mora": False,
            "version": 2,
        },
        "idempotent": False,
    }
    db.execute.return_value = MagicMock(data=rpc_response)

    service = PaymentService(db, USER_ID)
    body = PaymentRequest(
        credit_id=CREDIT_ID,
        amount=Decimal("416.67"),
        operator_id=USER_ID,
    )

    # WHEN
    result = await service.process_payment(body)

    # THEN
    assert result["updated_credit_snapshot"]["pending_capital"] == new_capital
    assert result["updated_credit_snapshot"]["mora"] is False
    assert result["updated_credit_snapshot"]["version"] == 2
    db.rpc.assert_called_once_with("process_payment_atomic", {
        "p_credit_id": str(body.credit_id),
        "p_amount": "416.67",
        "p_operator_id": USER_ID,
        "p_idempotency_key": None,
    })


@pytest.mark.anyio
async def test_full_flow_capital_math():
    """GIVEN $10k credit with 12% annual WHEN installment payment applied THEN interest=100, principal reduces capital."""
    # GIVEN
    today = date.today()
    overdue_date = (today - timedelta(days=30)).isoformat()
    installments = [
        {
            "id": INST_ID,
            "expected_date": overdue_date,
            "expected_value": "933.33",
            "interest_portion": "100.00",
            "principal_portion": "833.33",
            "paid_value": "0.00",
            "status": "UPCOMING",
        }
    ]

    # WHEN — preview allocation
    applied, total_principal, remaining = _compute_breakdown_3pool(
        installments, Decimal("416.67"), today
    )

    # THEN — interest pool covered first, remainder to principal
    applied_types = {e.type for e in applied}
    assert "OVERDUE_INTEREST" in applied_types
    interest_applied = sum(e.amount for e in applied if e.type == "OVERDUE_INTEREST")
    assert interest_applied == Decimal("100.00")
    assert total_principal <= Decimal("316.67")
