from uuid import UUID
from datetime import date, datetime, timezone, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Optional

from app.services.base_service import BaseService
from app.models.credit_model import CreditCreate
from app.utils.calculations import PERIOD_DAYS, calculate_period_interest
from app.repositories.credit_repository import CreditRepository


class CreditService(BaseService):

    async def create(self, body: CreditCreate) -> dict:
        # Verify client ownership
        client_result = await (
            self.db.table("clients")
            .select("id,user_id")
            .eq("id", str(body.client_id))
            .eq("user_id", self.user_id)
            .is_("deleted_at", "null")
            .single()
            .execute()
        )
        if not client_result.data:
            self._raise_forbidden("client")

        offset = PERIOD_DAYS.get(body.periodicity, 30)
        next_period_date = body.start_date + timedelta(days=offset)

        payload = {
            "user_id": self.user_id,
            "client_id": str(body.client_id),
            "initial_capital": float(body.initial_capital),
            "pending_capital": float(body.initial_capital),
            "version": 1,
            "periodicity": body.periodicity,
            "annual_interest_rate": float(body.annual_interest_rate),
            "status": "ACTIVE",
            "start_date": body.start_date.isoformat(),
            "next_period_date": next_period_date.isoformat(),
            "mora": False,
            "mora_since": None,
        }
        result = await self.db.table("credits").insert(payload).execute()
        credit = result.data[0]

        # Generate initial installment schedule (Option A: dynamic — first 12 periods)
        await self._generate_installments(credit, body)

        # Record history
        await self._record_history(
            event_type="CREDIT_CREATED",
            client_id=str(body.client_id),
            credit_id=credit["id"],
            amount=float(body.initial_capital),
            description=f"Credit created for {float(body.initial_capital)}",
            metadata={"periodicity": body.periodicity, "annual_interest_rate": float(body.annual_interest_rate)},
        )
        return credit

    async def list_all(self, client_id: Optional[UUID] = None, status: Optional[str] = None) -> List[dict]:
        query = self.db.table("credits").select("*").eq("user_id", self.user_id)
        if client_id:
            query = query.eq("client_id", str(client_id))
        if status:
            query = query.eq("status", status)
        result = await query.execute()
        return result.data

    async def get_by_id(self, credit_id: UUID) -> dict:
        """Fetch credit, recalculate mora, append precomputed aggregates."""
        result = await (
            self.db.table("credits")
            .select("*")
            .eq("id", str(credit_id))
            .eq("user_id", self.user_id)
            .single()
            .execute()
        )
        if not result.data:
            self._raise_forbidden("credit")
        credit = result.data
        credit = await self._refresh_mora(credit)
        credit = await self._append_aggregates(credit)
        return credit

    async def _append_aggregates(self, credit: dict) -> dict:
        """
        Precompute and attach derived fields for the credit detail response.
        All math reuses calculations.py — no new formulas here.
        """
        today = date.today()
        credit_id = credit["id"]

        # Fetch all unpaid installments
        inst_result = await (
            self.db.table("installments")
            .select("*")
            .eq("credit_id", credit_id)
            .in_("status", ["UPCOMING", "PARTIALLY_PAID"])
            .order("expected_date")
            .execute()
        )
        installments = inst_result.data or []

        overdue = [i for i in installments if date.fromisoformat(i["expected_date"]) < today]
        upcoming = [i for i in installments if date.fromisoformat(i["expected_date"]) >= today]

        # Overdue interest + capital totals
        overdue_interest_total = Decimal("0")
        overdue_capital_total = Decimal("0")
        for inst in overdue:
            paid = Decimal(str(inst["paid_value"]))
            interest = Decimal(str(inst["interest_portion"]))
            principal = Decimal(str(inst["principal_portion"]))
            interest_unpaid = max(Decimal("0"), interest - max(Decimal("0"), paid))
            capital_unpaid = max(Decimal("0"), principal - max(Decimal("0"), paid - interest))
            overdue_interest_total += interest_unpaid
            overdue_capital_total += capital_unpaid

        # Interest due current period (from calculations.py)
        pending_capital = Decimal(str(credit["pending_capital"]))
        annual_rate = Decimal(str(credit["annual_interest_rate"]))
        periodicity = credit["periodicity"]
        interest_due_current_period = float(
            calculate_period_interest(pending_capital, annual_rate, periodicity)
        )

        # next installment
        next_installment = upcoming[0] if upcoming else None

        # mora_status
        mora_status = {
            "in_mora": credit["mora"],
            "since_date": credit.get("mora_since"),
        }

        credit["interest_due_current_period"] = interest_due_current_period
        credit["overdue_interest_total"] = float(overdue_interest_total)
        credit["overdue_capital_total"] = float(overdue_capital_total)
        credit["next_installment"] = next_installment
        credit["upcoming_installments"] = upcoming[:5]
        credit["overdue_installments"] = overdue
        credit["mora_status"] = mora_status
        return credit

    async def _refresh_mora(self, credit: dict) -> dict:
        today = date.today().isoformat()
        overdue_result = await (
            self.db.table("installments")
            .select("id,expected_date")
            .eq("credit_id", credit["id"])
            .in_("status", ["UPCOMING", "PARTIALLY_PAID"])
            .lt("expected_date", today)
            .execute()
        )
        overdue = overdue_result.data or []
        mora_fresh = len(overdue) > 0
        mora_since = min(r["expected_date"] for r in overdue) if overdue else None

        if mora_fresh != credit["mora"] or (mora_fresh and credit.get("mora_since") != mora_since):
            await (
                self.db.table("credits")
                .update({
                    "mora": mora_fresh,
                    "mora_since": mora_since,
                    "version": credit["version"] + 1,
                })
                .eq("id", credit["id"])
                .execute()
            )
            credit["mora"] = mora_fresh
            credit["mora_since"] = mora_since
            credit["version"] += 1

        # Mark overdue installments
        if overdue:
            ids = [r["id"] for r in overdue]
            await (
                self.db.table("installments")
                .update({"is_overdue": True})
                .in_("id", ids)
                .execute()
            )
        return credit

    async def _generate_installments(self, credit: dict, body: CreditCreate, num_periods: int = 12) -> None:
        """
        Generate initial installment schedule: num_periods installments.
        Spec Option A: dynamic — fixed at creation time, no retroactive changes.
        Interest per period via calculate_period_interest (calculations.py).
        """
        pending_capital = Decimal(str(body.initial_capital))
        annual_rate = Decimal(str(body.annual_interest_rate))
        periodicity = body.periodicity
        offset_days = PERIOD_DAYS.get(periodicity, 30)
        installments = []

        for period in range(1, num_periods + 1):
            expected_date = body.start_date + timedelta(days=offset_days * period)
            interest = calculate_period_interest(pending_capital, annual_rate, periodicity)
            # Principal portion: capital / remaining periods
            principal = (pending_capital / Decimal(num_periods - period + 1)).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            expected_value = interest + principal

            installments.append({
                "user_id": self.user_id,
                "credit_id": credit["id"],
                "period_number": period,
                "expected_date": expected_date.isoformat(),
                "expected_value": float(expected_value),
                "principal_portion": float(principal),
                "interest_portion": float(interest),
                "paid_value": 0.0,
                "is_overdue": False,
                "status": "UPCOMING",
            })

        if installments:
            await self.db.table("installments").insert(installments).execute()

    async def check_mora_status(self, credit_id: UUID) -> dict:
        """
        Query overdue installments and return mora state dict.
        Does NOT persist; call get_by_id() if you need the full credit with persisted mora.
        Returns: {"mora": bool, "mora_since": str | None}
        """
        repo = CreditRepository(self.db)
        today = date.today().isoformat()
        overdue = await repo.find_overdue_installments(str(credit_id), today)
        mora = len(overdue) > 0
        mora_since = min(r["expected_date"] for r in overdue) if overdue else None
        return {"mora": mora, "mora_since": mora_since}

    async def update(self, credit_id: UUID, patch: dict) -> dict:
        """
        Update a credit using optimistic locking when 'version' key is provided in patch.
        patch must include 'expected_version' for optimistic path; otherwise blind update.
        Raises HTTPException(409) on version conflict.
        """
        from fastapi import HTTPException

        repo = CreditRepository(self.db)
        expected_version = patch.pop("expected_version", None)
        try:
            if expected_version is not None:
                return await repo.update_with_version(str(credit_id), self.user_id, expected_version, patch)
            return await repo.update(str(credit_id), self.user_id, patch)
        except ValueError as exc:
            if "version_conflict" in str(exc):
                raise HTTPException(status_code=409, detail="version_conflict")
            raise

    async def delete(self, credit_id: UUID) -> None:
        """Soft-delete a credit by setting status=CLOSED."""
        repo = CreditRepository(self.db)
        await repo.soft_delete(str(credit_id), self.user_id)
        credit = await repo.find_by_id(str(credit_id), self.user_id)
        if credit:
            await self._record_history(
                event_type="CREDIT_CLOSED",
                client_id=credit["client_id"],
                credit_id=str(credit_id),
                amount=float(credit.get("pending_capital", 0)),
                description="Credit closed",
                metadata={},
            )

    async def _record_history(self, event_type: str, client_id: str, credit_id: str,
                               amount: float, description: str, metadata: dict) -> None:
        await self.db.table("financial_history").insert({
            "user_id": self.user_id,
            "event_type": event_type,
            "client_id": client_id,
            "credit_id": credit_id,
            "amount": amount,
            "description": description,
            "metadata": metadata,
            "operator_id": self.user_id,
        }).execute()
