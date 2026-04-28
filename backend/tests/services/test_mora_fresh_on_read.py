"""
RISK-003 Fix — Mora recalculation on credit read.
CreditService._refresh_mora() is invoked by get_by_id(); these tests verify
that mora/mora_since are recomputed from live installment data and persisted
only when the state has changed.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import date, timedelta

from app.services.credit_service import CreditService

USER_ID = "user-abc"
CREDIT_ID = "credit-111"
TODAY = date.today().isoformat()
PAST = (date.today() - timedelta(days=10)).isoformat()
PAST2 = (date.today() - timedelta(days=20)).isoformat()


def _make_db(overdue_rows: list, credit_row: dict) -> MagicMock:
    """Build a fluent Supabase mock that returns controlled data."""
    db = MagicMock()

    # credits.select().eq().eq().single().execute()  → credit
    credit_chain = MagicMock()
    credit_chain.execute = AsyncMock(return_value=MagicMock(data=credit_row))
    credit_chain.single = MagicMock(return_value=credit_chain)
    credit_chain.eq = MagicMock(return_value=credit_chain)
    credit_select = MagicMock(return_value=credit_chain)

    # installments overdue query (select id,expected_date ... lt)
    overdue_chain = MagicMock()
    overdue_chain.execute = AsyncMock(return_value=MagicMock(data=overdue_rows))
    overdue_chain.lt = MagicMock(return_value=overdue_chain)
    overdue_chain.in_ = MagicMock(return_value=overdue_chain)
    overdue_chain.eq = MagicMock(return_value=overdue_chain)
    overdue_select = MagicMock(return_value=overdue_chain)

    # installments aggregate query (select * ... in_ order)
    agg_chain = MagicMock()
    agg_chain.execute = AsyncMock(return_value=MagicMock(data=[]))
    agg_chain.order = MagicMock(return_value=agg_chain)
    agg_chain.in_ = MagicMock(return_value=agg_chain)
    agg_chain.eq = MagicMock(return_value=agg_chain)
    agg_select = MagicMock(return_value=agg_chain)

    def installments_select(fields):
        if "id,expected_date" in fields or "id" in fields:
            return overdue_chain
        return agg_chain

    installments_table = MagicMock()
    installments_table.select = MagicMock(side_effect=installments_select)

    # credits update chain
    update_chain = MagicMock()
    update_chain.execute = AsyncMock(return_value=MagicMock(data=[credit_row]))
    update_chain.eq = MagicMock(return_value=update_chain)
    credits_table = MagicMock()
    credits_table.select = credit_select
    credits_table.update = MagicMock(return_value=update_chain)

    # installments update chain (mark_overdue)
    inst_update_chain = MagicMock()
    inst_update_chain.execute = AsyncMock(return_value=MagicMock(data=[]))
    inst_update_chain.in_ = MagicMock(return_value=inst_update_chain)
    installments_table.update = MagicMock(return_value=inst_update_chain)

    def table_router(name):
        if name == "credits":
            return credits_table
        if name == "installments":
            return installments_table
        t = MagicMock()
        t.select = MagicMock(return_value=agg_chain)
        return t

    db.table = MagicMock(side_effect=table_router)
    return db, credits_table, installments_table


@pytest.mark.anyio
async def test_mora_false_when_no_overdue_installments():
    # GIVEN — credit stored with mora=True, but no overdue installments exist
    credit = {"id": CREDIT_ID, "user_id": USER_ID, "mora": True, "mora_since": PAST,
              "version": 1, "pending_capital": 5000, "annual_interest_rate": 12,
              "periodicity": "MONTHLY", "status": "ACTIVE"}
    db, credits_table, _ = _make_db(overdue_rows=[], credit_row=credit)
    svc = CreditService(db, USER_ID)

    # WHEN
    result = await svc._refresh_mora(credit.copy())

    # THEN — mora flag recalculated to False
    assert result["mora"] is False
    assert result["mora_since"] is None
    credits_table.update.assert_called_once()


@pytest.mark.anyio
async def test_mora_true_when_overdue_installment_exists():
    # GIVEN — credit without mora, one installment past expected_date
    credit = {"id": CREDIT_ID, "user_id": USER_ID, "mora": False, "mora_since": None,
              "version": 2, "pending_capital": 5000, "annual_interest_rate": 12,
              "periodicity": "MONTHLY", "status": "ACTIVE"}
    overdue = [{"id": "inst-1", "expected_date": PAST}]
    db, credits_table, _ = _make_db(overdue_rows=overdue, credit_row=credit)
    svc = CreditService(db, USER_ID)

    # WHEN
    result = await svc._refresh_mora(credit.copy())

    # THEN
    assert result["mora"] is True
    assert result["mora_since"] == PAST
    credits_table.update.assert_called_once()


@pytest.mark.anyio
async def test_mora_persists_if_changed_from_read():
    # GIVEN — credit mora=False in DB, overdue installment exists → state changed
    credit = {"id": CREDIT_ID, "user_id": USER_ID, "mora": False, "mora_since": None,
              "version": 3, "pending_capital": 8000, "annual_interest_rate": 10,
              "periodicity": "WEEKLY", "status": "ACTIVE"}
    overdue = [{"id": "inst-2", "expected_date": PAST}]
    db, credits_table, _ = _make_db(overdue_rows=overdue, credit_row=credit)
    svc = CreditService(db, USER_ID)

    # WHEN
    result = await svc._refresh_mora(credit.copy())

    # THEN — persisted with incremented version
    assert result["version"] == 4
    assert result["mora"] is True
    credits_table.update.assert_called_once()


@pytest.mark.anyio
async def test_installment_is_overdue_recalculated():
    # GIVEN — two overdue installments
    credit = {"id": CREDIT_ID, "user_id": USER_ID, "mora": False, "mora_since": None,
              "version": 1, "pending_capital": 3000, "annual_interest_rate": 12,
              "periodicity": "MONTHLY", "status": "ACTIVE"}
    overdue = [
        {"id": "inst-A", "expected_date": PAST},
        {"id": "inst-B", "expected_date": PAST2},
    ]
    db, _, installments_table = _make_db(overdue_rows=overdue, credit_row=credit)
    svc = CreditService(db, USER_ID)

    # WHEN
    await svc._refresh_mora(credit.copy())

    # THEN — is_overdue=True update called with both ids
    update_call_args = installments_table.update.call_args[0][0]
    assert update_call_args == {"is_overdue": True}
    in_call = installments_table.update.return_value.in_.call_args[0]
    assert set(in_call[1]) == {"inst-A", "inst-B"}


@pytest.mark.anyio
async def test_mora_since_earliest_overdue_date():
    # GIVEN — two overdue installments with different dates
    credit = {"id": CREDIT_ID, "user_id": USER_ID, "mora": False, "mora_since": None,
              "version": 1, "pending_capital": 6000, "annual_interest_rate": 15,
              "periodicity": "MONTHLY", "status": "ACTIVE"}
    overdue = [
        {"id": "inst-X", "expected_date": PAST},   # 10 days ago
        {"id": "inst-Y", "expected_date": PAST2},  # 20 days ago — earliest
    ]
    db, credits_table, _ = _make_db(overdue_rows=overdue, credit_row=credit)
    svc = CreditService(db, USER_ID)

    # WHEN
    result = await svc._refresh_mora(credit.copy())

    # THEN — mora_since = min(expected_date)
    assert result["mora_since"] == PAST2
