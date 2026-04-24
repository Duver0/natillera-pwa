"""
Tests for POST /payments/preview (dry-run allocation).
No DB writes; verifies allocation logic mirrors process_payment order.
"""
import pytest
from unittest.mock import AsyncMock
from datetime import date, timedelta

CREDIT_ID = "bbbbbbbb-0000-0000-0000-000000000002"
USER_ID = "user-002"
YESTERDAY = (date.today() - timedelta(days=1)).isoformat()
TOMORROW = (date.today() + timedelta(days=1)).isoformat()

BASE_CREDIT = {
    "id": CREDIT_ID,
    "user_id": USER_ID,
    "client_id": "client-002",
    "initial_capital": 5000.0,
    "pending_capital": 5000.0,
    "version": 1,
    "periodicity": "MONTHLY",
    "annual_interest_rate": 12.0,
    "status": "ACTIVE",
    "mora": False,
    "mora_since": None,
}


def _make_installment(period, expected_date, paid=0.0, status="UPCOMING"):
    return {
        "id": f"inst-{period}",
        "credit_id": CREDIT_ID,
        "period_number": period,
        "expected_date": expected_date,
        "expected_value": 500.0,
        "principal_portion": 450.0,
        "interest_portion": 50.0,
        "paid_value": paid,
        "status": status,
    }


def _build_service(credit, installments):
    from app.services.payment_service import PaymentService

    mock_db = AsyncMock()

    credit_exec = AsyncMock(return_value=AsyncMock(data=credit))
    inst_exec = AsyncMock(return_value=AsyncMock(data=installments))

    mock_db.table.return_value.select.return_value.eq.return_value.eq.return_value.single.return_value.execute = credit_exec
    mock_db.table.return_value.select.return_value.eq.return_value.in_.return_value.order.return_value.execute = inst_exec

    return PaymentService(mock_db, USER_ID)


class TestPaymentPreview:
    @pytest.mark.asyncio
    async def test_preview_overdue_interest_allocated_first(self):
        # GIVEN one overdue installment, small payment (covers only interest)
        from app.services.payment_service import PaymentService
        from uuid import UUID

        mock_db = AsyncMock()

        overdue = _make_installment(1, YESTERDAY)
        mock_db.table.return_value.select.return_value.eq.return_value.eq.return_value.single.return_value.execute = AsyncMock(
            return_value=AsyncMock(data=BASE_CREDIT)
        )
        mock_db.table.return_value.select.return_value.eq.return_value.in_.return_value.order.return_value.execute = AsyncMock(
            return_value=AsyncMock(data=[overdue])
        )

        service = PaymentService(mock_db, USER_ID)
        result = await service.preview_payment(UUID(CREDIT_ID), 50.0)

        # THEN first allocation is OVERDUE_INTEREST
        assert result["applied_to"][0]["type"] == "OVERDUE_INTEREST"
        assert result["applied_to"][0]["amount"] == pytest.approx(50.0)
        assert result["unallocated"] == pytest.approx(0.0)

    @pytest.mark.asyncio
    async def test_preview_excess_goes_to_future_capital(self):
        # GIVEN no overdue, payment exceeds one upcoming installment
        from app.services.payment_service import PaymentService
        from uuid import UUID

        mock_db = AsyncMock()
        upcoming = _make_installment(1, TOMORROW)
        mock_db.table.return_value.select.return_value.eq.return_value.eq.return_value.single.return_value.execute = AsyncMock(
            return_value=AsyncMock(data=BASE_CREDIT)
        )
        mock_db.table.return_value.select.return_value.eq.return_value.in_.return_value.order.return_value.execute = AsyncMock(
            return_value=AsyncMock(data=[upcoming])
        )

        service = PaymentService(mock_db, USER_ID)
        result = await service.preview_payment(UUID(CREDIT_ID), 600.0)

        types = [a["type"] for a in result["applied_to"]]
        assert "FUTURE_PRINCIPAL" in types
        # 600 - 500 = 100 unallocated (no more installments)
        assert result["unallocated"] == pytest.approx(100.0)

    @pytest.mark.asyncio
    async def test_preview_no_installments_returns_full_unallocated(self):
        # GIVEN no installments at all
        from app.services.payment_service import PaymentService
        from uuid import UUID

        mock_db = AsyncMock()
        mock_db.table.return_value.select.return_value.eq.return_value.eq.return_value.single.return_value.execute = AsyncMock(
            return_value=AsyncMock(data=BASE_CREDIT)
        )
        mock_db.table.return_value.select.return_value.eq.return_value.in_.return_value.order.return_value.execute = AsyncMock(
            return_value=AsyncMock(data=[])
        )

        service = PaymentService(mock_db, USER_ID)
        result = await service.preview_payment(UUID(CREDIT_ID), 200.0)

        assert result["applied_to"] == []
        assert result["unallocated"] == pytest.approx(200.0)

    @pytest.mark.asyncio
    async def test_preview_non_active_credit_raises(self):
        # GIVEN credit in CLOSED status
        from app.services.payment_service import PaymentService
        from uuid import UUID

        closed_credit = dict(BASE_CREDIT)
        closed_credit["status"] = "CLOSED"

        mock_db = AsyncMock()
        mock_db.table.return_value.select.return_value.eq.return_value.eq.return_value.single.return_value.execute = AsyncMock(
            return_value=AsyncMock(data=closed_credit)
        )

        service = PaymentService(mock_db, USER_ID)

        with pytest.raises(ValueError, match="non-ACTIVE"):
            await service.preview_payment(UUID(CREDIT_ID), 100.0)

    @pytest.mark.asyncio
    async def test_preview_forbidden_credit(self):
        # GIVEN credit not found for this user
        from app.services.payment_service import PaymentService
        from uuid import UUID
        from fastapi import HTTPException

        mock_db = AsyncMock()
        mock_db.table.return_value.select.return_value.eq.return_value.eq.return_value.single.return_value.execute = AsyncMock(
            return_value=AsyncMock(data=None)
        )

        service = PaymentService(mock_db, USER_ID)

        with pytest.raises(HTTPException) as exc:
            await service.preview_payment(UUID(CREDIT_ID), 100.0)
        assert exc.value.status_code == 403
