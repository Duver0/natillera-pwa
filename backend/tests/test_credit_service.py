"""
Unit tests for CreditService — mora detection, creation.
SPEC-001 §US-002, §US-006, §4.3.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
from datetime import date, timedelta


def _make_db(credit=None, overdue_installments=None):
    db = MagicMock()

    def table_se(name):
        t = MagicMock()
        t.select.return_value = t
        t.insert.return_value = t
        t.update.return_value = t
        t.eq.return_value = t
        t.in_.return_value = t
        t.lt.return_value = t
        t.is_.return_value = t
        t.single.return_value = t
        t.order.return_value = t

        if name == "credits":
            t.execute = AsyncMock(return_value=MagicMock(data=credit))
        elif name == "installments":
            t.execute = AsyncMock(return_value=MagicMock(data=overdue_installments or []))
        elif name == "clients":
            t.execute = AsyncMock(return_value=MagicMock(data={"id": str(uuid4()), "user_id": "user-1"}))
        else:
            t.execute = AsyncMock(return_value=MagicMock(data=[]))
        return t

    db.table = MagicMock(side_effect=table_se)
    return db


@pytest.mark.asyncio
async def test_get_credit_sets_mora_when_overdue_exists():
    """
    SPEC: mora recalculated on every credit.get().
    If unpaid installment expected_date < today → mora = true.
    """
    from app.services.credit_service import CreditService

    credit_id = str(uuid4())
    credit = {
        "id": credit_id,
        "user_id": "user-1",
        "client_id": str(uuid4()),
        "mora": False,
        "mora_since": None,
        "version": 1,
        "pending_capital": 5000.0,
        "status": "ACTIVE",
    }
    overdue = [{"id": str(uuid4()), "expected_date": "2020-01-01"}]
    db = _make_db(credit=credit, overdue_installments=overdue)
    service = CreditService(db, "user-1")

    result = await service.get_by_id(credit_id)

    assert result["mora"] is True
    assert result["mora_since"] == "2020-01-01"


@pytest.mark.asyncio
async def test_get_credit_clears_mora_when_no_overdue():
    """mora = false when no overdue installments exist."""
    from app.services.credit_service import CreditService

    credit_id = str(uuid4())
    credit = {
        "id": credit_id,
        "user_id": "user-1",
        "client_id": str(uuid4()),
        "mora": True,
        "mora_since": "2020-01-01",
        "version": 2,
        "pending_capital": 5000.0,
        "status": "ACTIVE",
    }
    db = _make_db(credit=credit, overdue_installments=[])
    service = CreditService(db, "user-1")

    result = await service.get_by_id(credit_id)

    assert result["mora"] is False
    assert result["mora_since"] is None


@pytest.mark.asyncio
async def test_create_credit_injects_user_id():
    """user_id must be injected from service context, not from client input."""
    from app.services.credit_service import CreditService
    from app.models.credit_model import CreditCreate

    client_id = str(uuid4())
    credit_record = {
        "id": str(uuid4()),
        "user_id": "user-1",
        "client_id": client_id,
        "initial_capital": 10000.0,
        "pending_capital": 10000.0,
        "status": "ACTIVE",
        "version": 1,
        "mora": False,
        "mora_since": None,
    }

    db = MagicMock()
    t = MagicMock()
    t.select.return_value = t
    t.insert.return_value = t
    t.update.return_value = t
    t.eq.return_value = t
    t.is_.return_value = t
    t.single.return_value = t
    t.execute = AsyncMock(return_value=MagicMock(data=credit_record))
    db.table = MagicMock(return_value=t)

    service = CreditService(db, "user-1")
    body = CreditCreate(
        client_id=client_id,
        initial_capital=10000,
        periodicity="MONTHLY",
        annual_interest_rate=12,
        start_date=date.today(),
    )
    result = await service.create(body)

    insert_calls = [str(c) for c in db.table.return_value.insert.call_args_list]
    assert any("user-1" in c for c in insert_calls)
