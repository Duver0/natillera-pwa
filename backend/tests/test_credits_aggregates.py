"""
Tests for GET /credits/:id enriched response:
  interest_due_current_period, overdue_interest_total, overdue_capital_total,
  next_installment, upcoming_installments, overdue_installments, mora_status
"""
import pytest
from unittest.mock import AsyncMock, patch
from datetime import date, timedelta


CREDIT_ID = "aaaaaaaa-0000-0000-0000-000000000001"
USER_ID = "user-001"
TODAY = date.today().isoformat()
YESTERDAY = (date.today() - timedelta(days=1)).isoformat()
TOMORROW = (date.today() + timedelta(days=1)).isoformat()

BASE_CREDIT = {
    "id": CREDIT_ID,
    "user_id": USER_ID,
    "client_id": "client-001",
    "initial_capital": 10000.0,
    "pending_capital": 10000.0,
    "version": 1,
    "periodicity": "MONTHLY",
    "annual_interest_rate": 12.0,
    "status": "ACTIVE",
    "start_date": "2026-01-01",
    "mora": False,
    "mora_since": None,
    "created_at": "2026-01-01T00:00:00",
    "updated_at": "2026-01-01T00:00:00",
}


def _make_installment(period, expected_date, paid=0.0, status="UPCOMING"):
    return {
        "id": f"inst-{period}",
        "credit_id": CREDIT_ID,
        "period_number": period,
        "expected_date": expected_date,
        "expected_value": 1000.0,
        "principal_portion": 900.0,
        "interest_portion": 100.0,
        "paid_value": paid,
        "is_overdue": date.fromisoformat(expected_date) < date.today(),
        "status": status,
    }


class TestCreditAggregates:
    """Unit tests for CreditService._append_aggregates"""

    @pytest.mark.asyncio
    async def test_no_installments_returns_zeros(self):
        # GIVEN credit with no installments
        from app.services.credit_service import CreditService

        mock_db = AsyncMock()
        mock_db.table.return_value.select.return_value.eq.return_value.in_.return_value.order.return_value.execute = AsyncMock(
            return_value=AsyncMock(data=[])
        )

        service = CreditService(mock_db, USER_ID)
        result = await service._append_aggregates(dict(BASE_CREDIT))

        # THEN overdue totals are zero
        assert result["overdue_interest_total"] == 0.0
        assert result["overdue_capital_total"] == 0.0
        assert result["next_installment"] is None
        assert result["upcoming_installments"] == []
        assert result["overdue_installments"] == []

    @pytest.mark.asyncio
    async def test_overdue_installment_contributes_to_totals(self):
        # GIVEN one overdue installment with no payments made
        from app.services.credit_service import CreditService

        mock_db = AsyncMock()
        overdue_inst = _make_installment(1, YESTERDAY)
        mock_db.table.return_value.select.return_value.eq.return_value.in_.return_value.order.return_value.execute = AsyncMock(
            return_value=AsyncMock(data=[overdue_inst])
        )

        service = CreditService(mock_db, USER_ID)
        result = await service._append_aggregates(dict(BASE_CREDIT))

        # THEN overdue_interest_total > 0
        assert result["overdue_interest_total"] > 0
        assert result["overdue_capital_total"] > 0
        assert len(result["overdue_installments"]) == 1

    @pytest.mark.asyncio
    async def test_interest_due_current_period_uses_calculations(self):
        # GIVEN credit with 10000 capital, 12% annual, monthly → 100/month
        from app.services.credit_service import CreditService

        mock_db = AsyncMock()
        upcoming_inst = _make_installment(1, TOMORROW)
        mock_db.table.return_value.select.return_value.eq.return_value.in_.return_value.order.return_value.execute = AsyncMock(
            return_value=AsyncMock(data=[upcoming_inst])
        )

        service = CreditService(mock_db, USER_ID)
        result = await service._append_aggregates(dict(BASE_CREDIT))

        # THEN interest due = 10000 * 0.12 / 12 = 100.00
        assert result["interest_due_current_period"] == pytest.approx(100.0, abs=0.01)

    @pytest.mark.asyncio
    async def test_mora_status_reflects_credit_flag(self):
        # GIVEN credit in mora
        from app.services.credit_service import CreditService

        credit = dict(BASE_CREDIT)
        credit["mora"] = True
        credit["mora_since"] = YESTERDAY

        mock_db = AsyncMock()
        mock_db.table.return_value.select.return_value.eq.return_value.in_.return_value.order.return_value.execute = AsyncMock(
            return_value=AsyncMock(data=[])
        )

        service = CreditService(mock_db, USER_ID)
        result = await service._append_aggregates(credit)

        # THEN mora_status reflects credit state
        assert result["mora_status"]["in_mora"] is True
        assert result["mora_status"]["since_date"] == YESTERDAY

    @pytest.mark.asyncio
    async def test_paid_exceeds_interest_applies_remainder_to_capital(self):
        """
        Edge case: a payment already covers full interest_portion.
        interest_unpaid must be 0 and all remaining goes to principal.

        installment: expected_value=1000, interest_portion=100, principal_portion=900
        paid_value already = 150 (exceeds interest of 100 by 50).
        New payment of 300 should go entirely to principal (interest_unpaid = 0).
        """
        from app.services.payment_service import PaymentService
        from app.models.payment_model import PaymentRequest
        from decimal import Decimal
        from datetime import date, timedelta
        import uuid

        yesterday = (date.today() - timedelta(days=1)).isoformat()
        credit_id = str(uuid.uuid4())
        inst_id = str(uuid.uuid4())

        overdue_inst = {
            "id": inst_id,
            "credit_id": credit_id,
            "period_number": 1,
            "expected_date": yesterday,
            "expected_value": 1000.0,
            "principal_portion": 900.0,
            "interest_portion": 100.0,
            # paid_value=150 means interest already fully covered + 50 on principal
            "paid_value": 150.0,
            "is_overdue": True,
            "status": "PARTIALLY_PAID",
        }

        credit_row = {
            "id": credit_id,
            "user_id": USER_ID,
            "client_id": "client-001",
            "initial_capital": 10000.0,
            "pending_capital": 9850.0,
            "version": 1,
            "periodicity": "MONTHLY",
            "annual_interest_rate": 12.0,
            "status": "ACTIVE",
            "start_date": "2026-01-01",
            "mora": True,
            "mora_since": yesterday,
            "created_at": "2026-01-01T00:00:00",
            "updated_at": "2026-01-01T00:00:00",
        }

        mock_db = AsyncMock()
        # credit fetch
        mock_db.table.return_value.select.return_value.eq.return_value.eq.return_value.single.return_value.execute = AsyncMock(
            return_value=AsyncMock(data=credit_row)
        )
        # installments fetch
        mock_db.table.return_value.select.return_value.eq.return_value.in_.return_value.order.return_value.execute = AsyncMock(
            return_value=AsyncMock(data=[overdue_inst])
        )
        # installment update (ignore)
        mock_db.table.return_value.update.return_value.eq.return_value.execute = AsyncMock(
            return_value=AsyncMock(data=[])
        )
        # post-payment overdue check (no more overdue after full payment)
        post_overdue_mock = AsyncMock(return_value=AsyncMock(data=[]))
        mock_db.table.return_value.select.return_value.eq.return_value.in_.return_value.lt.return_value.execute = post_overdue_mock
        # credit update
        mock_db.table.return_value.update.return_value.eq.return_value.eq.return_value.execute = AsyncMock(
            return_value=AsyncMock(data=[])
        )
        # payment insert
        payment_row = {"id": str(uuid.uuid4()), "amount": 300.0}
        mock_db.table.return_value.insert.return_value.execute = AsyncMock(
            return_value=AsyncMock(data=[payment_row])
        )

        service = PaymentService(mock_db, USER_ID)

        # Run the PURE allocation logic (preview_payment avoids DB writes and is simpler to unit-test)
        # We test via preview_payment which uses the same allocation algorithm
        mock_db2 = AsyncMock()
        mock_db2.table.return_value.select.return_value.eq.return_value.eq.return_value.single.return_value.execute = AsyncMock(
            return_value=AsyncMock(data=credit_row)
        )
        mock_db2.table.return_value.select.return_value.eq.return_value.in_.return_value.order.return_value.execute = AsyncMock(
            return_value=AsyncMock(data=[overdue_inst])
        )

        service2 = PaymentService(mock_db2, USER_ID)
        import uuid as _uuid
        result = await service2.preview_payment(
            credit_id=_uuid.UUID(credit_id), amount=300.0
        )

        # THEN: no OVERDUE_INTEREST entry (already fully paid), all 300 goes to OVERDUE_PRINCIPAL
        interest_entries = [e for e in result["applied_to"] if e["type"] == "OVERDUE_INTEREST"]
        principal_entries = [e for e in result["applied_to"] if e["type"] == "OVERDUE_PRINCIPAL"]

        assert len(interest_entries) == 0, "Interest already covered — no OVERDUE_INTEREST should be allocated"
        assert len(principal_entries) == 1
        assert principal_entries[0]["amount"] == pytest.approx(300.0, abs=0.01)
        assert result["unallocated"] == pytest.approx(0.0, abs=0.01)

    @pytest.mark.asyncio
    async def test_upcoming_installments_limited_to_five(self):
        # GIVEN 8 upcoming installments
        from app.services.credit_service import CreditService

        mock_db = AsyncMock()
        upcoming = [
            _make_installment(i, (date.today() + timedelta(days=30 * i)).isoformat())
            for i in range(1, 9)
        ]
        mock_db.table.return_value.select.return_value.eq.return_value.in_.return_value.order.return_value.execute = AsyncMock(
            return_value=AsyncMock(data=upcoming)
        )

        service = CreditService(mock_db, USER_ID)
        result = await service._append_aggregates(dict(BASE_CREDIT))

        # THEN upcoming_installments capped at 5
        assert len(result["upcoming_installments"]) == 5
