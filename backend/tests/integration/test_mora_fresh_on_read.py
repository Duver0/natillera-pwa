"""
Integration Tests — RISK-001: Mora staleness fix.
Validates that mora is recalculated on every credit.get() — never stale.
Mocked DB (no real Supabase). Uses CreditService._refresh_mora().

SPEC-001 §US-006, §1.2 rule "Mora Detection".
"""
import pytest
from datetime import date, timedelta
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from app.services.credit_service import CreditService

USER_ID = "user-mora-read-001"


def _make_db():
    db = MagicMock()
    db.table = MagicMock(return_value=db)
    db.select = MagicMock(return_value=db)
    db.update = MagicMock(return_value=db)
    db.insert = MagicMock(return_value=db)
    db.eq = MagicMock(return_value=db)
    db.in_ = MagicMock(return_value=db)
    db.lt = MagicMock(return_value=db)
    db.is_ = MagicMock(return_value=db)
    db.single = MagicMock(return_value=db)
    db.order = MagicMock(return_value=db)
    db.execute = AsyncMock()
    return db


@pytest.mark.anyio
async def test_mora_false_on_read_when_no_overdue_installments():
    """
    GIVEN credit with mora=False and no overdue installments
    WHEN _refresh_mora() is called
    THEN mora remains False, mora_since remains None, no DB update.
    """
    # GIVEN
    db = _make_db()
    credit = {
        "id": str(uuid4()), "mora": False, "mora_since": None, "version": 1,
    }
    db.execute.side_effect = [
        MagicMock(data=[]),  # no overdue installments found
    ]
    service = CreditService(db, USER_ID)

    # WHEN
    result = await service._refresh_mora(credit)

    # THEN
    assert result["mora"] is False
    assert result["mora_since"] is None


@pytest.mark.anyio
async def test_mora_true_when_overdue_installment_exists():
    """
    GIVEN credit with mora=False and one overdue installment (expected_date < today)
    WHEN _refresh_mora() is called
    THEN mora=True, mora_since set to that installment's expected_date.
    """
    # GIVEN
    db = _make_db()
    overdue_date = (date.today() - timedelta(days=3)).isoformat()
    credit = {
        "id": str(uuid4()), "mora": False, "mora_since": None, "version": 1,
    }
    db.execute.side_effect = [
        MagicMock(data=[{"id": str(uuid4()), "expected_date": overdue_date}]),  # overdue query
        MagicMock(data=[{}]),  # update credits
        MagicMock(data=[{}]),  # mark installments overdue
    ]
    service = CreditService(db, USER_ID)

    # WHEN
    result = await service._refresh_mora(credit)

    # THEN
    assert result["mora"] is True
    assert result["mora_since"] == overdue_date


@pytest.mark.anyio
async def test_mora_status_change_is_persisted():
    """
    GIVEN credit with mora=False that now has an overdue installment
    WHEN _refresh_mora() detects the change
    THEN DB update is called to persist the new mora state.
    """
    # GIVEN
    db = _make_db()
    credit_id = str(uuid4())
    overdue_date = (date.today() - timedelta(days=10)).isoformat()
    credit = {"id": credit_id, "mora": False, "mora_since": None, "version": 2}

    update_calls: list = []

    original_update = db.update

    def track_update(payload):
        update_calls.append(payload)
        return original_update(payload)

    db.update = MagicMock(side_effect=track_update, return_value=db)

    db.execute.side_effect = [
        MagicMock(data=[{"id": str(uuid4()), "expected_date": overdue_date}]),
        MagicMock(data=[{}]),
        MagicMock(data=[{}]),
    ]
    service = CreditService(db, USER_ID)

    # WHEN
    result = await service._refresh_mora(credit)

    # THEN
    assert result["mora"] is True
    assert any(
        isinstance(c, dict) and c.get("mora") is True
        for c in update_calls
    ), "mora=True update must be persisted"


@pytest.mark.anyio
async def test_mora_cleared_when_overdue_installments_disappear():
    """
    GIVEN credit currently in mora (mora=True)
    WHEN no overdue installments remain (all paid)
    THEN mora=False and mora_since=None are persisted.
    """
    # GIVEN
    db = _make_db()
    credit = {
        "id": str(uuid4()),
        "mora": True,
        "mora_since": (date.today() - timedelta(days=7)).isoformat(),
        "version": 5,
    }
    db.execute.side_effect = [
        MagicMock(data=[]),   # no overdue installments remain
        MagicMock(data=[{}]), # update credit mora=False
    ]
    service = CreditService(db, USER_ID)

    # WHEN
    result = await service._refresh_mora(credit)

    # THEN
    assert result["mora"] is False
    assert result["mora_since"] is None


@pytest.mark.anyio
async def test_is_overdue_flag_set_per_installment():
    """
    GIVEN overdue installments with is_overdue=False
    WHEN _refresh_mora() detects them as overdue
    THEN installment records are updated with is_overdue=True.

    Verifies per-installment flag alignment with credit-level mora.
    """
    # GIVEN
    db = _make_db()
    inst_id = str(uuid4())
    overdue_date = (date.today() - timedelta(days=2)).isoformat()
    credit = {"id": str(uuid4()), "mora": False, "mora_since": None, "version": 1}

    update_payloads: list = []

    original_update = db.update

    def track_update(payload):
        update_payloads.append(payload)
        return original_update(payload)

    db.update = MagicMock(side_effect=track_update, return_value=db)

    db.execute.side_effect = [
        MagicMock(data=[{"id": inst_id, "expected_date": overdue_date}]),  # overdue query
        MagicMock(data=[{}]),   # update credit
        MagicMock(data=[{}]),   # update installments is_overdue=True
    ]
    service = CreditService(db, USER_ID)

    # WHEN
    await service._refresh_mora(credit)

    # THEN — at least one update with is_overdue=True was issued
    assert any(
        isinstance(p, dict) and p.get("is_overdue") is True
        for p in update_payloads
    ), "installments must be updated with is_overdue=True"
