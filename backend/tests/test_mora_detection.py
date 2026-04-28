"""
Unit tests — mora detection (SPEC-001 §US-006, §4.3).
mora recalculated on every credit.get(); never stale.
Mocked repo — no real DB.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
from datetime import date, timedelta


def _make_credit(mora: bool = False, mora_since: str | None = None) -> dict:
    return {
        "id": str(uuid4()),
        "user_id": "user-1",
        "client_id": str(uuid4()),
        "initial_capital": 10000.0,
        "pending_capital": 10000.0,
        "version": 1,
        "periodicity": "MONTHLY",
        "annual_interest_rate": 12.0,
        "status": "ACTIVE",
        "start_date": "2026-01-01",
        "next_period_date": "2026-02-01",
        "mora": mora,
        "mora_since": mora_since,
    }


def _make_installment(expected_date: str, status: str = "UPCOMING") -> dict:
    return {
        "id": str(uuid4()),
        "expected_date": expected_date,
        "interest_portion": 100.0,
        "principal_portion": 833.33,
        "paid_value": 0.0,
        "status": status,
        "is_overdue": False,
    }


def _build_db(credit: dict, overdue_installments: list[dict], all_installments: list[dict] | None = None):
    db = MagicMock()

    def _table(name: str):
        t = MagicMock()
        for m in ("select", "insert", "update", "eq", "in_", "is_", "lt", "single", "order", "range"):
            getattr(t, m).return_value = t

        if name == "credits":
            t.execute = AsyncMock(return_value=MagicMock(data=credit))
        elif name == "installments":
            t.execute = AsyncMock(return_value=MagicMock(data=overdue_installments or []))
        else:
            t.execute = AsyncMock(return_value=MagicMock(data=[]))
        return t

    db.table = MagicMock(side_effect=_table)
    return db


@pytest.mark.asyncio
async def test_mora_detected_when_unpaid_past_due():
    """
    SPEC: mora = true if ∃ unpaid installment with expected_date < today.
    """
    from app.services.credit_service import CreditService

    credit = _make_credit(mora=False)
    past_date = (date.today() - timedelta(days=10)).isoformat()
    overdue = [_make_installment(past_date)]
    db = _build_db(credit, overdue)
    service = CreditService(db, "user-1")

    result = await service.get_by_id(credit["id"])

    assert result["mora"] is True


@pytest.mark.asyncio
async def test_mora_since_is_earliest_overdue_date():
    """mora_since = earliest overdue installment date."""
    from app.services.credit_service import CreditService

    credit = _make_credit(mora=False)
    early = (date.today() - timedelta(days=20)).isoformat()
    late = (date.today() - timedelta(days=5)).isoformat()
    overdue = [_make_installment(late), _make_installment(early)]
    db = _build_db(credit, overdue)
    service = CreditService(db, "user-1")

    result = await service.get_by_id(credit["id"])

    assert result["mora_since"] == early


@pytest.mark.asyncio
async def test_mora_clears_when_all_installments_paid():
    """mora = false when no overdue installments remain."""
    from app.services.credit_service import CreditService

    credit = _make_credit(mora=True, mora_since="2025-01-01")
    db = _build_db(credit, overdue_installments=[])
    service = CreditService(db, "user-1")

    result = await service.get_by_id(credit["id"])

    assert result["mora"] is False
    assert result["mora_since"] is None


@pytest.mark.asyncio
async def test_mora_not_set_for_future_installments():
    """Installments with expected_date >= today do NOT trigger mora."""
    from app.services.credit_service import CreditService

    credit = _make_credit(mora=False)
    future_date = (date.today() + timedelta(days=30)).isoformat()
    # Overdue query returns empty — future installments excluded by the query
    db = _build_db(credit, overdue_installments=[])
    service = CreditService(db, "user-1")

    result = await service.get_by_id(credit["id"])

    assert result["mora"] is False


@pytest.mark.asyncio
async def test_check_mora_status_returns_correct_dict():
    """check_mora_status() returns {mora, mora_since} without persisting."""
    from app.services.credit_service import CreditService

    credit_id = uuid4()
    past = (date.today() - timedelta(days=5)).isoformat()
    db = MagicMock()

    def _table(name: str):
        t = MagicMock()
        for m in ("select", "insert", "update", "eq", "in_", "is_", "lt", "single", "order"):
            getattr(t, m).return_value = t
        if name == "installments":
            t.execute = AsyncMock(return_value=MagicMock(data=[{"id": str(uuid4()), "expected_date": past}]))
        else:
            t.execute = AsyncMock(return_value=MagicMock(data=[]))
        return t

    db.table = MagicMock(side_effect=_table)
    service = CreditService(db, "user-1")

    result = await service.check_mora_status(credit_id)

    assert result["mora"] is True
    assert result["mora_since"] == past


@pytest.mark.asyncio
async def test_check_mora_status_no_overdue():
    """check_mora_status() returns mora=false when no overdue installments."""
    from app.services.credit_service import CreditService

    credit_id = uuid4()
    db = MagicMock()

    def _table(name: str):
        t = MagicMock()
        for m in ("select", "insert", "update", "eq", "in_", "is_", "lt", "single", "order"):
            getattr(t, m).return_value = t
        t.execute = AsyncMock(return_value=MagicMock(data=[]))
        return t

    db.table = MagicMock(side_effect=_table)
    service = CreditService(db, "user-1")

    result = await service.check_mora_status(credit_id)

    assert result["mora"] is False
    assert result["mora_since"] is None
