"""
Unit tests — CreditService.create()
SPEC-001 §US-002, §1.2 (version=1, mora=false, pending_capital=initial_capital).
Mocked repo — no real DB.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import date


def _build_db(client_data: dict | None = None, credit_data: dict | None = None):
    """Return a fully-mocked DatabaseInterface."""
    client_id = str(uuid4())
    default_client = {"id": client_id, "user_id": "user-1"}
    default_credit = {
        "id": str(uuid4()),
        "user_id": "user-1",
        "client_id": client_id,
        "initial_capital": 10000.0,
        "pending_capital": 10000.0,
        "version": 1,
        "periodicity": "MONTHLY",
        "annual_interest_rate": 12.0,
        "status": "ACTIVE",
        "start_date": date.today().isoformat(),
        "next_period_date": date.today().isoformat(),
        "mora": False,
        "mora_since": None,
    }

    db = MagicMock()

    def _table(name: str):
        t = MagicMock()
        for method in ("select", "insert", "update", "eq", "in_", "is_", "lt", "single", "order", "range"):
            getattr(t, method).return_value = t

        if name == "clients":
            t.execute = AsyncMock(return_value=MagicMock(data=client_data or default_client))
        elif name == "credits":
            t.execute = AsyncMock(return_value=MagicMock(data=[credit_data or default_credit]))
        else:
            t.execute = AsyncMock(return_value=MagicMock(data=[]))
        return t

    db.table = MagicMock(side_effect=_table)
    return db


@pytest.mark.asyncio
async def test_create_credit_sets_version_1():
    """SPEC: version = 1 on creation."""
    from app.services.credit_service import CreditService
    from app.models.credit_model import CreditCreate

    client_id = str(uuid4())
    credit_record = {
        "id": str(uuid4()), "user_id": "user-1", "client_id": client_id,
        "initial_capital": 5000.0, "pending_capital": 5000.0, "version": 1,
        "periodicity": "MONTHLY", "annual_interest_rate": 10.0, "status": "ACTIVE",
        "start_date": "2026-01-01", "next_period_date": "2026-02-01",
        "mora": False, "mora_since": None,
    }
    db = _build_db(credit_data=credit_record)
    service = CreditService(db, "user-1")
    body = CreditCreate(
        client_id=client_id,
        initial_capital=5000,
        periodicity="MONTHLY",
        annual_interest_rate=10,
        start_date=date(2026, 1, 1),
    )

    result = await service.create(body)

    assert result["version"] == 1


@pytest.mark.asyncio
async def test_create_credit_mora_false():
    """SPEC: mora = false at creation."""
    from app.services.credit_service import CreditService
    from app.models.credit_model import CreditCreate

    client_id = str(uuid4())
    credit_record = {
        "id": str(uuid4()), "user_id": "user-1", "client_id": client_id,
        "initial_capital": 10000.0, "pending_capital": 10000.0, "version": 1,
        "periodicity": "MONTHLY", "annual_interest_rate": 12.0, "status": "ACTIVE",
        "start_date": "2026-01-01", "next_period_date": "2026-02-01",
        "mora": False, "mora_since": None,
    }
    db = _build_db(credit_data=credit_record)
    service = CreditService(db, "user-1")
    body = CreditCreate(
        client_id=client_id,
        initial_capital=10000,
        periodicity="MONTHLY",
        annual_interest_rate=12,
        start_date=date(2026, 1, 1),
    )

    result = await service.create(body)

    assert result["mora"] is False
    assert result["mora_since"] is None


@pytest.mark.asyncio
async def test_create_credit_pending_capital_equals_initial():
    """SPEC: pending_capital = initial_capital at creation."""
    from app.services.credit_service import CreditService
    from app.models.credit_model import CreditCreate

    client_id = str(uuid4())
    initial = 7500.0
    credit_record = {
        "id": str(uuid4()), "user_id": "user-1", "client_id": client_id,
        "initial_capital": initial, "pending_capital": initial, "version": 1,
        "periodicity": "WEEKLY", "annual_interest_rate": 8.0, "status": "ACTIVE",
        "start_date": "2026-01-01", "next_period_date": "2026-01-08",
        "mora": False, "mora_since": None,
    }
    db = _build_db(credit_data=credit_record)
    service = CreditService(db, "user-1")
    body = CreditCreate(
        client_id=client_id,
        initial_capital=initial,
        periodicity="WEEKLY",
        annual_interest_rate=8,
        start_date=date(2026, 1, 1),
    )

    result = await service.create(body)

    assert result["pending_capital"] == result["initial_capital"]


@pytest.mark.asyncio
async def test_create_credit_status_active():
    """SPEC: status = ACTIVE at creation."""
    from app.services.credit_service import CreditService
    from app.models.credit_model import CreditCreate

    client_id = str(uuid4())
    credit_record = {
        "id": str(uuid4()), "user_id": "user-1", "client_id": client_id,
        "initial_capital": 3000.0, "pending_capital": 3000.0, "version": 1,
        "periodicity": "MONTHLY", "annual_interest_rate": 15.0, "status": "ACTIVE",
        "start_date": "2026-01-01", "next_period_date": "2026-02-01",
        "mora": False, "mora_since": None,
    }
    db = _build_db(credit_data=credit_record)
    service = CreditService(db, "user-1")
    body = CreditCreate(
        client_id=client_id,
        initial_capital=3000,
        periodicity="MONTHLY",
        annual_interest_rate=15,
        start_date=date(2026, 1, 1),
    )

    result = await service.create(body)

    assert result["status"] == "ACTIVE"


@pytest.mark.asyncio
async def test_create_credit_forbidden_when_client_not_found():
    """Unknown client → 403 forbidden."""
    from app.services.credit_service import CreditService
    from app.models.credit_model import CreditCreate
    from fastapi import HTTPException

    db = MagicMock()
    t = MagicMock()
    for m in ("select", "eq", "is_", "single"):
        getattr(t, m).return_value = t
    t.execute = AsyncMock(return_value=MagicMock(data=None))
    db.table = MagicMock(return_value=t)

    service = CreditService(db, "user-1")
    body = CreditCreate(
        client_id=uuid4(),
        initial_capital=1000,
        periodicity="MONTHLY",
        annual_interest_rate=10,
        start_date=date.today(),
    )

    with pytest.raises(HTTPException) as exc_info:
        await service.create(body)

    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_create_credit_records_history_event():
    """CREDIT_CREATED event must be written to financial_history."""
    from app.services.credit_service import CreditService
    from app.models.credit_model import CreditCreate

    client_id = str(uuid4())
    credit_record = {
        "id": str(uuid4()), "user_id": "user-1", "client_id": client_id,
        "initial_capital": 10000.0, "pending_capital": 10000.0, "version": 1,
        "periodicity": "MONTHLY", "annual_interest_rate": 12.0, "status": "ACTIVE",
        "start_date": "2026-01-01", "next_period_date": "2026-02-01",
        "mora": False, "mora_since": None,
    }
    inserted_tables: list[str] = []

    db = MagicMock()

    def _table(name: str):
        t = MagicMock()
        for method in ("select", "insert", "update", "eq", "in_", "is_", "lt", "single", "order"):
            getattr(t, method).return_value = t
        if name == "clients":
            t.execute = AsyncMock(return_value=MagicMock(data={"id": client_id, "user_id": "user-1"}))
        elif name == "credits":
            t.execute = AsyncMock(return_value=MagicMock(data=[credit_record]))
        else:
            t.execute = AsyncMock(return_value=MagicMock(data=[]))

        original_insert = t.insert

        def insert_track(payload):
            inserted_tables.append(name)
            return original_insert(payload)

        t.insert = insert_track
        return t

    db.table = MagicMock(side_effect=_table)
    service = CreditService(db, "user-1")
    body = CreditCreate(
        client_id=client_id,
        initial_capital=10000,
        periodicity="MONTHLY",
        annual_interest_rate=12,
        start_date=date(2026, 1, 1),
    )

    await service.create(body)

    assert "financial_history" in inserted_tables
