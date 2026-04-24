"""
Tests for installment schedule generation on credit create.
"""
import pytest
from unittest.mock import AsyncMock, call
from datetime import date, timedelta
from decimal import Decimal

CLIENT_ID = "dddddddd-0000-0000-0000-000000000004"
USER_ID = "user-004"


def _make_credit_create(
    initial_capital=10000.0,
    annual_interest_rate=12.0,
    periodicity="MONTHLY",
    start_date=None,
):
    from app.models.credit_model import CreditCreate, Periodicity
    return CreditCreate(
        client_id=CLIENT_ID,
        initial_capital=initial_capital,
        annual_interest_rate=annual_interest_rate,
        periodicity=Periodicity(periodicity),
        start_date=start_date or date.today(),
    )


class TestInstallmentGeneration:
    @pytest.mark.asyncio
    async def test_generates_12_installments_by_default(self):
        # GIVEN a new credit with 12 default periods
        from app.services.credit_service import CreditService

        mock_db = AsyncMock()
        inserted = []

        async def capture_insert(data):
            inserted.extend(data)
            return AsyncMock(data=[])

        mock_db.table.return_value.insert.side_effect = capture_insert

        service = CreditService(mock_db, USER_ID)
        body = _make_credit_create()

        credit = {"id": "credit-new", "user_id": USER_ID}
        await service._generate_installments(credit, body)

        # THEN 12 installments inserted
        assert len(inserted) == 12

    @pytest.mark.asyncio
    async def test_installment_dates_follow_periodicity(self):
        # GIVEN MONTHLY periodicity
        from app.services.credit_service import CreditService

        mock_db = AsyncMock()
        captured_rows = []

        async def capture_insert(data):
            captured_rows.extend(data)
            return AsyncMock(data=[])

        mock_db.table.return_value.insert.side_effect = capture_insert

        service = CreditService(mock_db, USER_ID)
        start = date(2026, 1, 1)
        body = _make_credit_create(start_date=start)
        credit = {"id": "credit-x", "user_id": USER_ID}
        await service._generate_installments(credit, body)

        # THEN period 1 date = start + 30 days
        assert captured_rows[0]["expected_date"] == (start + timedelta(days=30)).isoformat()
        # Period 2 = start + 60 days
        assert captured_rows[1]["expected_date"] == (start + timedelta(days=60)).isoformat()

    @pytest.mark.asyncio
    async def test_interest_portion_uses_calculations_py(self):
        # GIVEN 10000 capital, 12% annual, MONTHLY → 100/period
        from app.services.credit_service import CreditService

        mock_db = AsyncMock()
        captured_rows = []

        async def capture_insert(data):
            captured_rows.extend(data)
            return AsyncMock(data=[])

        mock_db.table.return_value.insert.side_effect = capture_insert

        service = CreditService(mock_db, USER_ID)
        body = _make_credit_create(initial_capital=10000.0, annual_interest_rate=12.0, periodicity="MONTHLY")
        credit = {"id": "credit-y", "user_id": USER_ID}
        await service._generate_installments(credit, body)

        # THEN first installment interest = 100.00
        assert captured_rows[0]["interest_portion"] == pytest.approx(100.0, abs=0.01)

    @pytest.mark.asyncio
    async def test_installments_start_as_upcoming(self):
        # GIVEN any valid credit
        from app.services.credit_service import CreditService

        mock_db = AsyncMock()
        captured_rows = []

        async def capture_insert(data):
            captured_rows.extend(data)
            return AsyncMock(data=[])

        mock_db.table.return_value.insert.side_effect = capture_insert

        service = CreditService(mock_db, USER_ID)
        body = _make_credit_create()
        credit = {"id": "credit-z", "user_id": USER_ID}
        await service._generate_installments(credit, body)

        # THEN all statuses are UPCOMING
        assert all(r["status"] == "UPCOMING" for r in captured_rows)

    @pytest.mark.asyncio
    async def test_paid_value_initialized_to_zero(self):
        # GIVEN any valid credit
        from app.services.credit_service import CreditService

        mock_db = AsyncMock()
        captured_rows = []

        async def capture_insert(data):
            captured_rows.extend(data)
            return AsyncMock(data=[])

        mock_db.table.return_value.insert.side_effect = capture_insert

        service = CreditService(mock_db, USER_ID)
        body = _make_credit_create()
        credit = {"id": "credit-w", "user_id": USER_ID}
        await service._generate_installments(credit, body)

        assert all(r["paid_value"] == 0.0 for r in captured_rows)
