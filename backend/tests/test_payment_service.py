"""
Unit tests for PaymentService — mandatory order, partial pay, overpayment.
SPEC-001 §US-005.
All DB calls mocked.
"""
import pytest
from decimal import Decimal
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4


# Helpers to build fake DB responses
def make_credit(pending=Decimal("1000"), mora=False, version=1):
    return {
        "id": str(uuid4()),
        "user_id": "user-1",
        "client_id": str(uuid4()),
        "pending_capital": float(pending),
        "mora": mora,
        "mora_since": None,
        "status": "ACTIVE",
        "version": version,
    }


def make_installment(
    credit_id,
    expected_value=Decimal("200"),
    principal=Decimal("100"),
    interest=Decimal("100"),
    paid=Decimal("0"),
    overdue=False,
    status="UPCOMING",
    expected_date=None,
):
    if expected_date is None:
        expected_date = date.today().isoformat() if not overdue else "2020-01-01"
    return {
        "id": str(uuid4()),
        "credit_id": credit_id,
        "user_id": "user-1",
        "expected_value": float(expected_value),
        "principal_portion": float(principal),
        "interest_portion": float(interest),
        "paid_value": float(paid),
        "is_overdue": overdue,
        "status": status,
        "expected_date": expected_date,
    }


@pytest.mark.asyncio
async def test_payment_applies_overdue_interest_first():
    """
    SPEC mandatory order: 1. overdue interest, 2. overdue principal, 3. future
    Payment of 100 should cover overdue interest only (100).
    """
    from app.services.payment_service import PaymentService
    from app.models.payment_model import PaymentRequest

    credit = make_credit()
    inst = make_installment(
        credit["id"],
        expected_value=Decimal("700"),
        principal=Decimal("500"),
        interest=Decimal("200"),
        overdue=True,
        expected_date="2020-01-01",
    )

    db = _build_db_mock(credit, [inst])
    service = PaymentService(db, "user-1")

    req = PaymentRequest(credit_id=credit["id"], amount=100)
    result = await service.process_payment(req)

    applied = result["applied_to"] if isinstance(result, dict) else result.applied_to
    types = [a["type"] for a in applied]
    assert "OVERDUE_INTEREST" in types
    # Should NOT have touched principal yet
    assert "OVERDUE_PRINCIPAL" not in types


@pytest.mark.asyncio
async def test_payment_covers_overdue_interest_then_principal():
    """SPEC: 700 = 200 interest + 500 principal"""
    from app.services.payment_service import PaymentService
    from app.models.payment_model import PaymentRequest

    credit = make_credit()
    inst = make_installment(
        credit["id"],
        expected_value=Decimal("700"),
        principal=Decimal("500"),
        interest=Decimal("200"),
        overdue=True,
        expected_date="2020-01-01",
    )
    db = _build_db_mock(credit, [inst])
    service = PaymentService(db, "user-1")

    req = PaymentRequest(credit_id=credit["id"], amount=700)
    result = await service.process_payment(req)

    applied = result["applied_to"]
    interest_entries = [a for a in applied if a["type"] == "OVERDUE_INTEREST"]
    principal_entries = [a for a in applied if a["type"] == "OVERDUE_PRINCIPAL"]
    assert sum(a["amount"] for a in interest_entries) == pytest.approx(200)
    assert sum(a["amount"] for a in principal_entries) == pytest.approx(500)


@pytest.mark.asyncio
async def test_partial_payment_leaves_remainder_in_installment():
    """SPEC: remainder stays in installment, status = PARTIALLY_PAID"""
    from app.services.payment_service import PaymentService
    from app.models.payment_model import PaymentRequest

    credit = make_credit()
    inst = make_installment(
        credit["id"],
        expected_value=Decimal("200"),
        principal=Decimal("100"),
        interest=Decimal("100"),
        overdue=True,
        expected_date="2020-01-01",
    )
    db = _build_db_mock(credit, [inst])
    service = PaymentService(db, "user-1")

    req = PaymentRequest(credit_id=credit["id"], amount=50)
    await service.process_payment(req)

    # Verify installment update called with PARTIALLY_PAID
    calls = db.table.return_value.update.call_args_list
    updated_statuses = [str(c) for c in calls]
    assert any("PARTIALLY_PAID" in s for s in updated_statuses)


@pytest.mark.asyncio
async def test_full_payment_marks_installment_paid():
    """SPEC: full payment → status = PAID"""
    from app.services.payment_service import PaymentService
    from app.models.payment_model import PaymentRequest

    credit = make_credit()
    inst = make_installment(
        credit["id"],
        expected_value=Decimal("200"),
        principal=Decimal("100"),
        interest=Decimal("100"),
        overdue=True,
        expected_date="2020-01-01",
    )
    db = _build_db_mock(credit, [inst])
    service = PaymentService(db, "user-1")

    req = PaymentRequest(credit_id=credit["id"], amount=200)
    await service.process_payment(req)

    calls = db.table.return_value.update.call_args_list
    updated_statuses = [str(c) for c in calls]
    assert any("PAID" in s for s in updated_statuses)


def _build_db_mock(credit, installments):
    """Build a minimal DB mock that returns provided data."""
    db = MagicMock()

    payment_id = str(uuid4())
    payment_record = {
        "id": payment_id,
        "user_id": "user-1",
        "credit_id": credit["id"],
        "amount": 0,
        "payment_date": date.today().isoformat(),
        "applied_to": [],
        "notes": None,
        "recorded_by": "user-1",
        "created_at": "2026-04-23T00:00:00",
    }

    def table_side_effect(name):
        t = MagicMock()
        t.select.return_value = t
        t.insert.return_value = t
        t.update.return_value = t
        t.delete.return_value = t
        t.eq.return_value = t
        t.in_.return_value = t
        t.lt.return_value = t
        t.order.return_value = t
        t.single.return_value = t
        t.range.return_value = t

        if name == "credits":
            t.execute = AsyncMock(return_value=MagicMock(data=credit))
        elif name == "installments":
            t.execute = AsyncMock(return_value=MagicMock(data=installments))
        elif name == "payments":
            t.execute = AsyncMock(return_value=MagicMock(data=[payment_record]))
        else:
            t.execute = AsyncMock(return_value=MagicMock(data=[]))

        return t

    db.table = MagicMock(side_effect=table_side_effect)
    return db
