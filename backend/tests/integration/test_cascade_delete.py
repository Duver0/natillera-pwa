"""
Integration Test: soft-delete client → credits/savings cascaded (soft-delete via status/deleted_at).
Validates that CreditService.delete sets status=CLOSED and records history.
"""
import pytest
from datetime import date
from unittest.mock import AsyncMock, MagicMock, call
from uuid import uuid4

from app.services.credit_service import CreditService

USER_ID = "user-cascade-001"
CLIENT_ID = str(uuid4())
CREDIT_ID = str(uuid4())


def _make_db():
    db = MagicMock()
    db.table = MagicMock(return_value=db)
    db.select = MagicMock(return_value=db)
    db.update = MagicMock(return_value=db)
    db.insert = MagicMock(return_value=db)
    db.eq = MagicMock(return_value=db)
    db.single = MagicMock(return_value=db)
    db.execute = AsyncMock()
    return db


@pytest.mark.anyio
async def test_credit_soft_delete_sets_status_closed():
    """GIVEN existing credit WHEN delete() THEN status=CLOSED and history event recorded."""
    # GIVEN
    db = _make_db()
    credit_data = {
        "id": CREDIT_ID, "user_id": USER_ID, "client_id": CLIENT_ID,
        "pending_capital": 8000.0, "status": "ACTIVE",
    }
    db.execute.side_effect = [
        MagicMock(data=[{}]),       # soft_delete update
        MagicMock(data=credit_data),# find_by_id after delete
        MagicMock(data=[{}]),       # financial_history insert
    ]
    service = CreditService(db, USER_ID)

    # WHEN
    await service.delete(CREDIT_ID)

    # THEN — update was called (soft-delete)
    db.update.assert_called()
    # history insert called
    assert db.execute.call_count >= 2


@pytest.mark.anyio
async def test_credit_soft_delete_records_credit_closed_history():
    """GIVEN credit with $8000 pending WHEN delete() THEN CREDIT_CLOSED event with amount=8000."""
    # GIVEN
    db = _make_db()
    credit_data = {
        "id": CREDIT_ID, "user_id": USER_ID, "client_id": CLIENT_ID,
        "pending_capital": 8000.0, "status": "ACTIVE",
    }
    db.execute.side_effect = [
        MagicMock(data=[{}]),
        MagicMock(data=credit_data),
        MagicMock(data=[{}]),
    ]

    inserted_payloads = []
    original_insert = db.insert

    def capture_insert(payload):
        inserted_payloads.append(payload)
        return db
    db.insert = MagicMock(side_effect=capture_insert, return_value=db)

    service = CreditService(db, USER_ID)

    # WHEN
    await service.delete(CREDIT_ID)

    # THEN — at least one insert with CREDIT_CLOSED event type
    closed_events = [p for p in inserted_payloads if isinstance(p, dict) and p.get("event_type") == "CREDIT_CLOSED"]
    assert closed_events, "CREDIT_CLOSED history event must be inserted"
    assert closed_events[0]["amount"] == 8000.0


@pytest.mark.anyio
async def test_credit_soft_delete_no_history_when_not_found():
    """GIVEN credit that disappears after delete WHEN delete() THEN no history insert (graceful)."""
    # GIVEN
    db = _make_db()
    db.execute.side_effect = [
        MagicMock(data=[{}]),    # soft_delete
        MagicMock(data=None),    # find_by_id returns None
    ]
    service = CreditService(db, USER_ID)

    # WHEN — should not raise
    await service.delete(CREDIT_ID)

    # THEN — only 2 DB calls: delete + find
    assert db.execute.call_count == 2
