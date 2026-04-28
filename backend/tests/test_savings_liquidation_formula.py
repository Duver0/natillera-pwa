"""
Unit tests — SavingsService liquidation formula (SPEC-001 §US-007, §1.2).
Formula: interest = total_contributions * (SAVINGS_RATE / 100)
         total_delivered = total_contributions + interest
Mocked DB — no real DB.
"""
import pytest
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import date


def _make_active_savings(amounts: list[float], client_id: str) -> list[dict]:
    return [
        {
            "id": str(uuid4()),
            "client_id": client_id,
            "contribution_amount": a,
            "status": "ACTIVE",
        }
        for a in amounts
    ]


def _build_db(client_id: str, active: list[dict], liq_record: dict):
    db = MagicMock()

    def _table(name: str):
        t = MagicMock()
        for m in ("select", "insert", "update", "eq", "in_", "is_", "lt", "single", "order"):
            getattr(t, m).return_value = t

        if name == "clients":
            t.execute = AsyncMock(return_value=MagicMock(data={"id": client_id, "user_id": "user-1"}))
        elif name == "savings":
            t.execute = AsyncMock(return_value=MagicMock(data=active))
        elif name == "savings_liquidations":
            t.execute = AsyncMock(return_value=MagicMock(data=[liq_record]))
        else:
            t.execute = AsyncMock(return_value=MagicMock(data=[]))
        return t

    db.table = MagicMock(side_effect=_table)
    return db


@pytest.mark.asyncio
async def test_liquidation_formula_1000_500_at_10_percent():
    """
    SPEC example: $1000 + $500 = $1500, 10% → interest=$150, total=$1650.
    """
    from app.services.savings_service import SavingsService

    client_id = str(uuid4())
    active = _make_active_savings([1000.0, 500.0], client_id)
    liq = {
        "id": str(uuid4()),
        "client_id": client_id,
        "total_contributions": 1500.0,
        "interest_earned": 150.0,
        "total_delivered": 1650.0,
        "interest_rate": 10.0,
        "liquidation_date": date.today().isoformat(),
        "created_at": "2026-04-27T00:00:00",
    }
    db = _build_db(client_id, active, liq)

    with patch("app.services.savings_service.get_settings") as ms:
        ms.return_value.savings_rate = 10.0
        service = SavingsService(db, "user-1")
        result = await service.liquidate(client_id)

    assert result["total_contributions"] == 1500.0
    assert result["interest_earned"] == 150.0
    assert result["total_delivered"] == 1650.0


@pytest.mark.asyncio
async def test_liquidation_rate_snapshot_matches_env():
    """
    SPEC: interest_rate in SavingsLiquidation = snapshot of SAVINGS_RATE at liquidation time.
    """
    from app.services.savings_service import SavingsService

    client_id = str(uuid4())
    active = _make_active_savings([2000.0], client_id)
    liq = {
        "id": str(uuid4()),
        "client_id": client_id,
        "total_contributions": 2000.0,
        "interest_earned": 300.0,
        "total_delivered": 2300.0,
        "interest_rate": 15.0,
        "liquidation_date": date.today().isoformat(),
        "created_at": "2026-04-27T00:00:00",
    }
    db = _build_db(client_id, active, liq)

    with patch("app.services.savings_service.get_settings") as ms:
        ms.return_value.savings_rate = 15.0
        service = SavingsService(db, "user-1")
        result = await service.liquidate(client_id)

    assert result["interest_rate"] == 15.0


@pytest.mark.asyncio
async def test_liquidation_zero_active_contributions_raises():
    """No ACTIVE contributions → ValueError."""
    from app.services.savings_service import SavingsService

    client_id = str(uuid4())
    db = _build_db(client_id, active=[], liq_record={})

    with patch("app.services.savings_service.get_settings") as ms:
        ms.return_value.savings_rate = 10.0
        service = SavingsService(db, "user-1")
        with pytest.raises(ValueError, match="No active savings"):
            await service.liquidate(client_id)


@pytest.mark.asyncio
async def test_liquidation_marks_all_contributions_as_liquidated():
    """All ACTIVE contributions must be marked LIQUIDATED atomically."""
    from app.services.savings_service import SavingsService

    client_id = str(uuid4())
    ids = [str(uuid4()), str(uuid4())]
    active = [
        {"id": ids[0], "client_id": client_id, "contribution_amount": 500.0, "status": "ACTIVE"},
        {"id": ids[1], "client_id": client_id, "contribution_amount": 500.0, "status": "ACTIVE"},
    ]
    liq = {
        "id": str(uuid4()), "client_id": client_id,
        "total_contributions": 1000.0, "interest_earned": 100.0,
        "total_delivered": 1100.0, "interest_rate": 10.0,
        "liquidation_date": date.today().isoformat(), "created_at": "2026-04-27T00:00:00",
    }

    update_called_with: list = []
    db = MagicMock()

    def _table(name: str):
        t = MagicMock()
        for m in ("select", "insert", "update", "eq", "in_", "is_", "lt", "single", "order"):
            getattr(t, m).return_value = t

        original_update = t.update

        def track_update(payload):
            if name == "savings":
                update_called_with.append(payload)
            return original_update(payload)

        t.update = track_update

        if name == "clients":
            t.execute = AsyncMock(return_value=MagicMock(data={"id": client_id, "user_id": "user-1"}))
        elif name == "savings":
            t.execute = AsyncMock(return_value=MagicMock(data=active))
        elif name == "savings_liquidations":
            t.execute = AsyncMock(return_value=MagicMock(data=[liq]))
        else:
            t.execute = AsyncMock(return_value=MagicMock(data=[]))
        return t

    db.table = MagicMock(side_effect=_table)

    with patch("app.services.savings_service.get_settings") as ms:
        ms.return_value.savings_rate = 10.0
        service = SavingsService(db, "user-1")
        await service.liquidate(client_id)

    assert any(p.get("status") == "LIQUIDATED" for p in update_called_with)


@pytest.mark.asyncio
async def test_liquidation_creates_history_event():
    """SAVINGS_LIQUIDATION event must be written to financial_history."""
    from app.services.savings_service import SavingsService

    client_id = str(uuid4())
    active = _make_active_savings([1000.0], client_id)
    liq = {
        "id": str(uuid4()), "client_id": client_id,
        "total_contributions": 1000.0, "interest_earned": 100.0,
        "total_delivered": 1100.0, "interest_rate": 10.0,
        "liquidation_date": date.today().isoformat(), "created_at": "2026-04-27T00:00:00",
    }

    history_inserts: list[dict] = []
    db = MagicMock()

    def _table(name: str):
        t = MagicMock()
        for m in ("select", "insert", "update", "eq", "in_", "is_", "lt", "single", "order"):
            getattr(t, m).return_value = t

        original_insert = t.insert

        def track_insert(payload):
            if name == "financial_history":
                history_inserts.append(payload)
            return original_insert(payload)

        t.insert = track_insert

        if name == "clients":
            t.execute = AsyncMock(return_value=MagicMock(data={"id": client_id, "user_id": "user-1"}))
        elif name == "savings":
            t.execute = AsyncMock(return_value=MagicMock(data=active))
        elif name == "savings_liquidations":
            t.execute = AsyncMock(return_value=MagicMock(data=[liq]))
        else:
            t.execute = AsyncMock(return_value=MagicMock(data=[]))
        return t

    db.table = MagicMock(side_effect=_table)

    with patch("app.services.savings_service.get_settings") as ms:
        ms.return_value.savings_rate = 10.0
        service = SavingsService(db, "user-1")
        await service.liquidate(client_id)

    assert any(e.get("event_type") == "SAVINGS_LIQUIDATION" for e in history_inserts)


@pytest.mark.asyncio
async def test_add_contribution_creates_savings_record():
    """add_contribution() writes savings record and history event."""
    from app.services.savings_service import SavingsService
    from app.models.savings_model import SavingsContributionCreate

    client_id = str(uuid4())
    saving_record = {
        "id": str(uuid4()), "user_id": "user-1", "client_id": client_id,
        "contribution_amount": 800.0, "contribution_date": date.today().isoformat(),
        "status": "ACTIVE", "liquidated_at": None, "created_at": "2026-04-27T00:00:00",
    }

    db = MagicMock()

    def _table(name: str):
        t = MagicMock()
        for m in ("select", "insert", "update", "eq", "in_", "is_", "lt", "single", "order"):
            getattr(t, m).return_value = t
        if name == "clients":
            t.execute = AsyncMock(return_value=MagicMock(data={"id": client_id, "user_id": "user-1"}))
        elif name == "savings":
            t.execute = AsyncMock(return_value=MagicMock(data=[saving_record]))
        else:
            t.execute = AsyncMock(return_value=MagicMock(data=[]))
        return t

    db.table = MagicMock(side_effect=_table)
    service = SavingsService(db, "user-1")
    body = SavingsContributionCreate(client_id=client_id, contribution_amount=800)

    result = await service.add_contribution(body)

    assert result["contribution_amount"] == 800.0
    assert result["status"] == "ACTIVE"
