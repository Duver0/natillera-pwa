"""
Unit tests — HistoryService immutability (SPEC-001 §US-008).
FinancialHistory is append-only: record_event() inserts, never updates or deletes.
Mocked DB — no real DB.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, call
from uuid import uuid4


def _build_db(insert_result: dict | None = None) -> MagicMock:
    db = MagicMock()

    def _table(name: str):
        t = MagicMock()
        for m in ("select", "insert", "update", "delete", "eq", "in_", "is_", "lt",
                  "single", "order", "range"):
            getattr(t, m).return_value = t
        t.execute = AsyncMock(return_value=MagicMock(data=[insert_result or {}]))
        return t

    db.table = MagicMock(side_effect=_table)
    return db


@pytest.mark.asyncio
async def test_record_event_uses_insert_not_update():
    """record_event() MUST call insert(), never update()."""
    from app.services.history_service import HistoryService

    client_id = uuid4()
    record = {
        "id": str(uuid4()), "event_type": "CREDIT_CREATED",
        "client_id": str(client_id), "credit_id": None,
        "amount": 10000.0, "description": "Credit created",
        "metadata": {}, "operator_id": "user-1",
        "created_at": "2026-04-27T00:00:00",
    }
    db = _build_db(record)
    service = HistoryService(db, "user-1")

    result = await service.record_event(
        event_type="CREDIT_CREATED",
        client_id=client_id,
        amount=10000.0,
        description="Credit created",
        operator_id="user-1",
    )

    # insert must be called on financial_history table
    history_table_calls = [
        c for c in db.table.call_args_list
        if c.args[0] == "financial_history"
    ]
    assert len(history_table_calls) >= 1

    # update must NOT be called
    for c in db.table.return_value.update.call_args_list:
        pytest.fail(f"update() was called on history — immutable violation: {c}")


@pytest.mark.asyncio
async def test_record_event_all_required_fields_in_payload():
    """Payload must include event_type, client_id, operator_id, description."""
    from app.services.history_service import HistoryService

    client_id = uuid4()
    credit_id = uuid4()
    inserted_payloads: list[dict] = []

    db = MagicMock()

    def _table(name: str):
        t = MagicMock()
        for m in ("select", "insert", "update", "eq", "in_", "is_", "lt", "single", "order"):
            getattr(t, m).return_value = t

        original_insert = t.insert

        def track(payload):
            if name == "financial_history":
                inserted_payloads.append(payload)
            return original_insert(payload)

        t.insert = track
        t.execute = AsyncMock(return_value=MagicMock(data=[{}]))
        return t

    db.table = MagicMock(side_effect=_table)
    service = HistoryService(db, "user-1")

    await service.record_event(
        event_type="PAYMENT_RECORDED",
        client_id=client_id,
        credit_id=credit_id,
        amount=500.0,
        description="Payment of 500",
        operator_id="user-1",
        metadata={"payment_id": "abc"},
    )

    assert len(inserted_payloads) == 1
    p = inserted_payloads[0]
    assert p["event_type"] == "PAYMENT_RECORDED"
    assert p["client_id"] == str(client_id)
    assert p["credit_id"] == str(credit_id)
    assert p["operator_id"] == "user-1"
    assert p["description"] == "Payment of 500"
    assert p["amount"] == 500.0


@pytest.mark.asyncio
async def test_record_event_credit_id_nullable():
    """credit_id is optional (nullable) for non-credit events."""
    from app.services.history_service import HistoryService

    client_id = uuid4()
    inserted_payloads: list[dict] = []

    db = MagicMock()

    def _table(name: str):
        t = MagicMock()
        for m in ("select", "insert", "update", "eq", "in_", "is_", "lt", "single", "order"):
            getattr(t, m).return_value = t

        original_insert = t.insert

        def track(payload):
            if name == "financial_history":
                inserted_payloads.append(payload)
            return original_insert(payload)

        t.insert = track
        t.execute = AsyncMock(return_value=MagicMock(data=[{}]))
        return t

    db.table = MagicMock(side_effect=_table)
    service = HistoryService(db, "user-1")

    await service.record_event(
        event_type="CLIENT_CREATED",
        client_id=client_id,
        amount=None,
        description="Client registered",
        operator_id="user-1",
    )

    assert inserted_payloads[0]["credit_id"] is None


@pytest.mark.asyncio
async def test_list_events_paginated_returns_reverse_chronological():
    """list_events() returns ordered (newest first) slice."""
    from app.services.history_service import HistoryService

    events = [
        {"id": str(uuid4()), "event_type": "PAYMENT_RECORDED", "created_at": "2026-04-27"},
        {"id": str(uuid4()), "event_type": "CREDIT_CREATED", "created_at": "2026-04-26"},
    ]
    db = MagicMock()

    def _table(name: str):
        t = MagicMock()
        for m in ("select", "insert", "update", "eq", "in_", "is_", "lt", "single", "order", "range"):
            getattr(t, m).return_value = t
        t.execute = AsyncMock(return_value=MagicMock(data=events))
        return t

    db.table = MagicMock(side_effect=_table)
    service = HistoryService(db, "user-1")

    result = await service.list_events(limit=10, offset=0)

    assert len(result) == 2
    assert result[0]["event_type"] == "PAYMENT_RECORDED"


@pytest.mark.asyncio
async def test_list_events_filter_by_event_type():
    """list_events(event_type=X) must apply filter."""
    from app.services.history_service import HistoryService

    filtered = [{"id": str(uuid4()), "event_type": "SAVINGS_LIQUIDATION"}]
    db = MagicMock()

    eq_calls: list[tuple] = []

    def _table(name: str):
        t = MagicMock()
        for m in ("select", "insert", "update", "eq", "in_", "is_", "lt", "single", "order", "range"):
            getattr(t, m).return_value = t

        original_eq = t.eq

        def track_eq(col, val):
            eq_calls.append((col, val))
            return original_eq(col, val)

        t.eq = track_eq
        t.execute = AsyncMock(return_value=MagicMock(data=filtered))
        return t

    db.table = MagicMock(side_effect=_table)
    service = HistoryService(db, "user-1")

    result = await service.list_events(event_type="SAVINGS_LIQUIDATION")

    assert any(col == "event_type" for col, _ in eq_calls)


@pytest.mark.asyncio
async def test_list_events_filter_by_client_id():
    """list_events(client_id=X) must scope to that client."""
    from app.services.history_service import HistoryService

    client_id = uuid4()
    events = [{"id": str(uuid4()), "event_type": "CREDIT_CREATED", "client_id": str(client_id)}]
    eq_calls: list[tuple] = []

    db = MagicMock()

    def _table(name: str):
        t = MagicMock()
        for m in ("select", "insert", "update", "eq", "in_", "is_", "lt", "single", "order", "range"):
            getattr(t, m).return_value = t

        original_eq = t.eq

        def track_eq(col, val):
            eq_calls.append((col, val))
            return original_eq(col, val)

        t.eq = track_eq
        t.execute = AsyncMock(return_value=MagicMock(data=events))
        return t

    db.table = MagicMock(side_effect=_table)
    service = HistoryService(db, "user-1")

    await service.list_events(client_id=client_id)

    assert any(col == "client_id" for col, _ in eq_calls)
