from uuid import UUID
from datetime import date
from decimal import Decimal
from typing import List

from app.services.base_service import BaseService
from app.models.savings_model import SavingsContributionCreate
from app.utils.calculations import calculate_savings_interest
from app.config import get_settings


class SavingsService(BaseService):

    async def add_contribution(self, body: SavingsContributionCreate) -> dict:
        # Verify client ownership
        client_result = await (
            self.db.table("clients")
            .select("id")
            .eq("id", str(body.client_id))
            .eq("user_id", self.user_id)
            .is_("deleted_at", "null")
            .single()
            .execute()
        )
        if not client_result.data:
            self._raise_forbidden("client")

        contribution_date = (body.contribution_date or date.today()).isoformat()
        payload = {
            "user_id": self.user_id,
            "client_id": str(body.client_id),
            "contribution_amount": float(body.contribution_amount),
            "contribution_date": contribution_date,
            "status": "ACTIVE",
        }
        result = await self.db.table("savings").insert(payload).execute()
        saving = result.data[0]

        # History event
        await self.db.table("financial_history").insert({
            "user_id": self.user_id,
            "event_type": "SAVINGS_CONTRIBUTION",
            "client_id": str(body.client_id),
            "amount": float(body.contribution_amount),
            "description": f"Savings contribution of {body.contribution_amount}",
            "metadata": {"contribution_date": contribution_date},
            "operator_id": self.user_id,
        }).execute()

        return saving

    async def liquidate(self, client_id: UUID) -> dict:
        # Verify client ownership
        client_result = await (
            self.db.table("clients")
            .select("id")
            .eq("id", str(client_id))
            .eq("user_id", self.user_id)
            .is_("deleted_at", "null")
            .single()
            .execute()
        )
        if not client_result.data:
            self._raise_forbidden("client")

        # Fetch all ACTIVE contributions
        active_result = await (
            self.db.table("savings")
            .select("*")
            .eq("client_id", str(client_id))
            .eq("user_id", self.user_id)
            .eq("status", "ACTIVE")
            .execute()
        )
        active = active_result.data or []
        if not active:
            raise ValueError("No active savings contributions to liquidate")

        total_contributions = Decimal(str(sum(float(s["contribution_amount"]) for s in active)))
        settings = get_settings()
        savings_rate = Decimal(str(settings.savings_rate))
        interest_earned = calculate_savings_interest(total_contributions, savings_rate)
        total_delivered = total_contributions + interest_earned
        liquidation_date = date.today().isoformat()

        # Mark all ACTIVE as LIQUIDATED
        ids = [s["id"] for s in active]
        await (
            self.db.table("savings")
            .update({"status": "LIQUIDATED", "liquidated_at": liquidation_date})
            .in_("id", ids)
            .execute()
        )

        # Create liquidation record
        liq_payload = {
            "user_id": self.user_id,
            "client_id": str(client_id),
            "total_contributions": float(total_contributions),
            "interest_earned": float(interest_earned),
            "total_delivered": float(total_delivered),
            "interest_rate": float(savings_rate),
            "liquidation_date": liquidation_date,
        }
        liq_result = await self.db.table("savings_liquidations").insert(liq_payload).execute()
        liquidation = liq_result.data[0]

        # History event
        await self.db.table("financial_history").insert({
            "user_id": self.user_id,
            "event_type": "SAVINGS_LIQUIDATION",
            "client_id": str(client_id),
            "amount": float(total_delivered),
            "description": f"Savings liquidated: {total_delivered}",
            "metadata": {
                "total_contributions": float(total_contributions),
                "interest_earned": float(interest_earned),
                "interest_rate": float(savings_rate),
            },
            "operator_id": self.user_id,
        }).execute()

        return liquidation

    async def list_contributions(self, client_id: UUID) -> List[dict]:
        client_result = await (
            self.db.table("clients")
            .select("id")
            .eq("id", str(client_id))
            .eq("user_id", self.user_id)
            .single()
            .execute()
        )
        if not client_result.data:
            self._raise_forbidden("client")

        result = await (
            self.db.table("savings")
            .select("*")
            .eq("client_id", str(client_id))
            .order("contribution_date", desc=True)
            .execute()
        )
        return result.data
