"""
Tests for GET /clients/:id/summary
"""
import pytest
from unittest.mock import AsyncMock, patch
from uuid import UUID
from fastapi import HTTPException

CLIENT_ID = "cccccccc-0000-0000-0000-000000000003"
USER_ID = "user-003"

BASE_CLIENT = {
    "id": CLIENT_ID,
    "user_id": USER_ID,
    "first_name": "Ana",
    "last_name": "Gomez",
    "phone": "3001234567",
    "deleted_at": None,
}

ACTIVE_CREDIT = {
    "id": "credit-a",
    "user_id": USER_ID,
    "status": "ACTIVE",
    "pending_capital": 5000.0,
    "mora": True,
}

CLOSED_CREDIT = {
    "id": "credit-b",
    "user_id": USER_ID,
    "status": "CLOSED",
    "pending_capital": 0.0,
    "mora": False,
}


class TestClientSummary:
    def _build_service(self):
        from app.services.client_service import ClientService

        mock_db = AsyncMock()
        return ClientService(mock_db, USER_ID), mock_db

    @pytest.mark.asyncio
    async def test_summary_aggregates_active_credits_only(self):
        # GIVEN one active + one closed credit
        service, mock_db = self._build_service()

        # get_by_id chain
        mock_db.table.return_value.select.return_value.eq.return_value.eq.return_value.is_.return_value.single.return_value.execute = AsyncMock(
            return_value=AsyncMock(data=BASE_CLIENT)
        )
        # credits query
        mock_db.table.return_value.select.return_value.eq.return_value.eq.return_value.execute = AsyncMock(
            return_value=AsyncMock(data=[ACTIVE_CREDIT, CLOSED_CREDIT])
        )
        # overdue installments
        mock_db.table.return_value.select.return_value.in_.return_value.in_.return_value.lt.return_value.execute = AsyncMock(
            return_value=AsyncMock(data=[])
        )
        # savings
        mock_db.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.execute = AsyncMock(
            return_value=AsyncMock(data=[])
        )

        result = await service.get_summary(UUID(CLIENT_ID))

        # THEN only active credit counted
        assert result["active_credits_count"] == 1
        assert result["total_pending_capital"] == pytest.approx(5000.0)
        assert result["mora_count"] == 1

    @pytest.mark.asyncio
    async def test_summary_overdue_totals_from_installments(self):
        # GIVEN active credit with overdue installments
        service, mock_db = self._build_service()

        mock_db.table.return_value.select.return_value.eq.return_value.eq.return_value.is_.return_value.single.return_value.execute = AsyncMock(
            return_value=AsyncMock(data=BASE_CLIENT)
        )
        mock_db.table.return_value.select.return_value.eq.return_value.eq.return_value.execute = AsyncMock(
            return_value=AsyncMock(data=[ACTIVE_CREDIT])
        )
        mock_db.table.return_value.select.return_value.in_.return_value.in_.return_value.lt.return_value.execute = AsyncMock(
            return_value=AsyncMock(data=[
                {"expected_value": 1000.0, "paid_value": 200.0},
                {"expected_value": 500.0, "paid_value": 0.0},
            ])
        )
        mock_db.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.execute = AsyncMock(
            return_value=AsyncMock(data=[])
        )

        result = await service.get_summary(UUID(CLIENT_ID))

        # 800 + 500 = 1300
        assert result["total_overdue"] == pytest.approx(1300.0)

    @pytest.mark.asyncio
    async def test_summary_savings_total_from_active_contributions(self):
        # GIVEN active savings contributions
        service, mock_db = self._build_service()

        mock_db.table.return_value.select.return_value.eq.return_value.eq.return_value.is_.return_value.single.return_value.execute = AsyncMock(
            return_value=AsyncMock(data=BASE_CLIENT)
        )
        mock_db.table.return_value.select.return_value.eq.return_value.eq.return_value.execute = AsyncMock(
            return_value=AsyncMock(data=[])
        )
        mock_db.table.return_value.select.return_value.in_.return_value.in_.return_value.lt.return_value.execute = AsyncMock(
            return_value=AsyncMock(data=[])
        )
        mock_db.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.execute = AsyncMock(
            return_value=AsyncMock(data=[
                {"contribution_amount": 300.0},
                {"contribution_amount": 200.0},
            ])
        )

        result = await service.get_summary(UUID(CLIENT_ID))

        assert result["savings_total"] == pytest.approx(500.0)

    @pytest.mark.asyncio
    async def test_summary_client_not_found_raises_403(self):
        # GIVEN client not found
        service, mock_db = self._build_service()

        mock_db.table.return_value.select.return_value.eq.return_value.eq.return_value.is_.return_value.single.return_value.execute = AsyncMock(
            return_value=AsyncMock(data=None)
        )

        with pytest.raises(HTTPException) as exc:
            await service.get_summary(UUID(CLIENT_ID))
        assert exc.value.status_code == 403
