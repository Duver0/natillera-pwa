"""
Unit tests for InstallmentService daily cron methods.
SPEC-001 §US-004 Phase 3.

Covers:
  - should_generate_installment() — eligibility logic
  - run_daily_installment_job() — batch processing, partial failures

All DB calls mocked. No live Supabase required.
"""
import pytest
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_credit(
    status="ACTIVE",
    mora=False,
    pending_capital=1000.0,
    next_period_date=None,
):
    if next_period_date is None:
        next_period_date = date.today().isoformat()
    return {
        "id": str(uuid4()),
        "user_id": "user-1",
        "client_id": str(uuid4()),
        "status": status,
        "mora": mora,
        "pending_capital": pending_capital,
        "next_period_date": next_period_date,
        "annual_interest_rate": 12.0,
        "periodicity": "MONTHLY",
        "version": 1,
    }


def _build_minimal_db_mock():
    """Minimal mock — overridden per test."""
    db = MagicMock()
    t = MagicMock()
    t.select.return_value = t
    t.insert.return_value = t
    t.update.return_value = t
    t.eq.return_value = t
    t.lte.return_value = t
    t.single.return_value = t
    t.order.return_value = t
    t.execute = AsyncMock(return_value=MagicMock(data=[], count=0))
    db.table = MagicMock(return_value=t)
    return db


def _make_service(db=None):
    from app.services.installment_service import InstallmentService
    return InstallmentService(db=db or _build_minimal_db_mock(), user_id="user-1")


# ---------------------------------------------------------------------------
# should_generate_installment — eligibility
# ---------------------------------------------------------------------------

def test_should_generate_installment_true():
    """GIVEN ACTIVE credit, mora=False, capital>0, next_period_date=today THEN True."""
    credit = make_credit(next_period_date=date.today().isoformat())
    service = _make_service()
    assert service.should_generate_installment(credit) is True


def test_should_generate_installment_false_if_suspended():
    """GIVEN SUSPENDED credit THEN False regardless of other fields."""
    credit = make_credit(status="SUSPENDED")
    service = _make_service()
    assert service.should_generate_installment(credit) is False


def test_should_generate_installment_false_if_closed():
    """GIVEN CLOSED credit THEN False."""
    credit = make_credit(status="CLOSED")
    service = _make_service()
    assert service.should_generate_installment(credit) is False


def test_should_generate_installment_false_if_mora():
    """GIVEN mora=True THEN False (interest stops in mora per spec)."""
    credit = make_credit(mora=True)
    service = _make_service()
    assert service.should_generate_installment(credit) is False


def test_should_generate_installment_false_if_no_capital():
    """GIVEN pending_capital=0 THEN False."""
    credit = make_credit(pending_capital=0.0)
    service = _make_service()
    assert service.should_generate_installment(credit) is False


def test_should_generate_installment_false_if_future_date():
    """GIVEN next_period_date=tomorrow THEN False."""
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    credit = make_credit(next_period_date=tomorrow)
    service = _make_service()
    assert service.should_generate_installment(credit) is False


def test_should_generate_installment_true_if_past_date():
    """GIVEN next_period_date=yesterday THEN True (overdue trigger)."""
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    credit = make_credit(next_period_date=yesterday)
    service = _make_service()
    assert service.should_generate_installment(credit) is True


def test_should_generate_installment_false_if_missing_next_period_date():
    """GIVEN next_period_date=None THEN False (cannot determine eligibility)."""
    credit = make_credit()
    credit["next_period_date"] = None
    service = _make_service()
    assert service.should_generate_installment(credit) is False


# ---------------------------------------------------------------------------
# run_daily_installment_job
# ---------------------------------------------------------------------------

def _build_batch_db_mock(credits_to_return):
    """
    Build DB mock whose 'credits' table returns credits_to_return for the
    lte() query, and installments table supports generate_next() flow.
    """
    db = MagicMock()

    def table_side_effect(name):
        t = MagicMock()
        t.select.return_value = t
        t.insert.return_value = t
        t.update.return_value = t
        t.eq.return_value = t
        t.in_.return_value = t
        t.lte.return_value = t
        t.lt.return_value = t
        t.order.return_value = t
        t.single.return_value = t
        t.is_.return_value = t

        if name == "credits":
            # First call: batch query (returns list)
            # Subsequent calls (per credit): single-row query for generate_next
            call_count = [0]
            async def credits_execute():
                call_count[0] += 1
                if call_count[0] == 1:
                    return MagicMock(data=credits_to_return)
                # Per-credit ownership check
                return MagicMock(data=credits_to_return[0] if credits_to_return else None)
            t.execute = AsyncMock(side_effect=credits_execute)
        elif name == "installments":
            t.execute = AsyncMock(return_value=MagicMock(data=[{"id": str(uuid4()), **_fake_installment_fields()}], count=0))
        elif name == "financial_history":
            t.execute = AsyncMock(return_value=MagicMock(data=[]))
        else:
            t.execute = AsyncMock(return_value=MagicMock(data=[]))

        return t

    db.table = MagicMock(side_effect=table_side_effect)
    return db


def _fake_installment_fields():
    return {
        "credit_id": str(uuid4()),
        "period_number": 1,
        "expected_date": date.today().isoformat(),
        "expected_value": 950.0,
        "principal_portion": 833.33,
        "interest_portion": 100.0,
        "paid_value": 0.0,
        "is_overdue": False,
        "status": "UPCOMING",
    }


@pytest.mark.asyncio
async def test_run_daily_job_no_eligible_credits():
    """GIVEN no credits returned by query THEN processed=0, errors=[]."""
    db = _build_batch_db_mock([])
    service = _make_service(db)
    result = await service.run_daily_installment_job()
    assert result["processed"] == 0
    assert result["errors"] == []


@pytest.mark.asyncio
async def test_run_daily_job_processes_eligible_credits():
    """GIVEN 2 eligible credits THEN generate_next called for each, processed=2."""
    credit_a = make_credit()
    credit_b = make_credit()
    credits = [credit_a, credit_b]

    db = _build_minimal_db_mock()

    generate_next_calls = []

    async def fake_generate_next(credit_id):
        generate_next_calls.append(str(credit_id))
        return {"id": str(uuid4()), **_fake_installment_fields()}

    # Batch query returns two credits
    batch_t = MagicMock()
    batch_t.select.return_value = batch_t
    batch_t.eq.return_value = batch_t
    batch_t.lte.return_value = batch_t
    batch_t.execute = AsyncMock(return_value=MagicMock(data=credits))

    db.table = MagicMock(return_value=batch_t)

    service = _make_service(db)
    service.generate_next = fake_generate_next  # type: ignore[method-assign]

    result = await service.run_daily_installment_job()

    assert result["processed"] == 2
    assert result["errors"] == []
    assert len(generate_next_calls) == 2


@pytest.mark.asyncio
async def test_run_daily_job_handles_individual_error():
    """GIVEN 1 credit that raises ValueError THEN errors=[...], processed=0."""
    credit = make_credit()

    db = _build_minimal_db_mock()
    batch_t = MagicMock()
    batch_t.select.return_value = batch_t
    batch_t.eq.return_value = batch_t
    batch_t.lte.return_value = batch_t
    batch_t.execute = AsyncMock(return_value=MagicMock(data=[credit]))
    db.table = MagicMock(return_value=batch_t)

    service = _make_service(db)

    async def failing_generate_next(credit_id):
        raise ValueError("credit is in mora")

    service.generate_next = failing_generate_next  # type: ignore[method-assign]

    result = await service.run_daily_installment_job()

    assert result["processed"] == 0
    assert len(result["errors"]) == 1
    assert str(credit["id"]) in result["errors"][0]["credit_id"]


@pytest.mark.asyncio
async def test_run_daily_job_partial_success():
    """GIVEN 2 credits, 1 succeeds + 1 fails THEN processed=1, errors=[1]."""
    credit_ok = make_credit()
    credit_fail = make_credit()
    credits = [credit_ok, credit_fail]

    db = _build_minimal_db_mock()
    batch_t = MagicMock()
    batch_t.select.return_value = batch_t
    batch_t.eq.return_value = batch_t
    batch_t.lte.return_value = batch_t
    batch_t.execute = AsyncMock(return_value=MagicMock(data=credits))
    db.table = MagicMock(return_value=batch_t)

    service = _make_service(db)

    fail_id = str(credit_fail["id"])

    async def maybe_fail(credit_id):
        if str(credit_id) == fail_id:
            raise ValueError("suspended credit")
        return {"id": str(uuid4()), **_fake_installment_fields()}

    service.generate_next = maybe_fail  # type: ignore[method-assign]

    result = await service.run_daily_installment_job()

    assert result["processed"] == 1
    assert len(result["errors"]) == 1
    assert fail_id in result["errors"][0]["credit_id"]
