"""
Integration Test: mora lifecycle.
create overdue installment → mora=true → payment clears → mora=false.
"""
import pytest
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from app.services.credit_service import CreditService
from app.services.payment_service import _compute_breakdown_3pool

USER_ID = "user-mora-001"
CREDIT_ID = str(uuid4())
INST_ID = str(uuid4())


def _make_db():
    db = MagicMock()
    db.table = MagicMock(return_value=db)
    db.select = MagicMock(return_value=db)
    db.update = MagicMock(return_value=db)
    db.eq = MagicMock(return_value=db)
    db.in_ = MagicMock(return_value=db)
    db.lt = MagicMock(return_value=db)
    db.single = MagicMock(return_value=db)
    db.order = MagicMock(return_value=db)
    db.execute = AsyncMock()
    return db


@pytest.mark.anyio
async def test_refresh_mora_sets_true_when_overdue_installment_exists():
    """GIVEN credit with overdue installment WHEN _refresh_mora THEN mora=True and mora_since set."""
    # GIVEN
    db = _make_db()
    overdue_date = (date.today() - timedelta(days=5)).isoformat()
    credit = {
        "id": CREDIT_ID, "mora": False, "mora_since": None, "version": 1,
    }
    db.execute.side_effect = [
        MagicMock(data=[{"id": INST_ID, "expected_date": overdue_date}]),  # overdue query
        MagicMock(data=[{}]),  # update credits
        MagicMock(data=[{}]),  # mark installments overdue
    ]
    service = CreditService(db, USER_ID)

    # WHEN
    result = await service._refresh_mora(credit)

    # THEN
    assert result["mora"] is True
    assert result["mora_since"] == overdue_date
    assert result["version"] == 2


@pytest.mark.anyio
async def test_refresh_mora_sets_false_when_no_overdue():
    """GIVEN credit with mora=True but no overdue installments WHEN _refresh_mora THEN mora=False."""
    # GIVEN
    db = _make_db()
    credit = {
        "id": CREDIT_ID, "mora": True,
        "mora_since": (date.today() - timedelta(days=10)).isoformat(),
        "version": 3,
    }
    db.execute.side_effect = [
        MagicMock(data=[]),   # no overdue installments
        MagicMock(data=[{}]), # update credits mora=False
    ]
    service = CreditService(db, USER_ID)

    # WHEN
    result = await service._refresh_mora(credit)

    # THEN
    assert result["mora"] is False
    assert result["mora_since"] is None


@pytest.mark.anyio
async def test_payment_preview_clears_mora_when_full_payment():
    """GIVEN single overdue installment WHEN payment covers full amount THEN mora_projected=False."""
    # GIVEN
    today = date.today()
    overdue_date = (today - timedelta(days=15)).isoformat()
    installments = [
        {
            "id": INST_ID,
            "expected_date": overdue_date,
            "expected_value": "500.00",
            "interest_portion": "100.00",
            "principal_portion": "400.00",
            "paid_value": "0.00",
            "status": "UPCOMING",
        }
    ]
    amount = Decimal("500.00")

    # WHEN
    applied, total_principal, remaining = _compute_breakdown_3pool(installments, amount, today)

    # THEN — installment fully paid, mora should clear
    total_applied = sum(e.amount for e in applied)
    assert total_applied == Decimal("500.00")
    assert remaining == Decimal("0.00")


@pytest.mark.anyio
async def test_payment_preview_mora_persists_when_partial_payment():
    """GIVEN overdue installment $500 WHEN payment $300 THEN mora_projected=True (not fully cleared)."""
    # GIVEN
    today = date.today()
    overdue_date = (today - timedelta(days=10)).isoformat()
    installments = [
        {
            "id": INST_ID,
            "expected_date": overdue_date,
            "expected_value": "500.00",
            "interest_portion": "100.00",
            "principal_portion": "400.00",
            "paid_value": "0.00",
            "status": "UPCOMING",
        }
    ]
    amount = Decimal("300.00")

    # WHEN
    applied, total_principal, remaining = _compute_breakdown_3pool(installments, amount, today)

    # THEN — payment did not cover full installment
    total_applied = sum(e.amount for e in applied)
    assert total_applied == Decimal("300.00")
    assert remaining == Decimal("0.00")
    # $200 still owed → mora stays
    assert total_applied < Decimal("500.00")
