from uuid import UUID
from datetime import date, timedelta
from decimal import Decimal
from typing import List, Optional

from app.services.base_service import BaseService
from app.utils.calculations import (
    calculate_period_interest,
    calculate_principal_portion,
    PERIOD_DAYS,
)


REMAINING_PERIODS_DEFAULT = 12  # fallback when credit has no term set


class InstallmentService(BaseService):

    def should_generate_installment(self, credit: dict) -> bool:
        """
        Return True if the credit is eligible for a new installment today.

        Conditions (all must be True):
          - status == ACTIVE
          - mora == False
          - pending_capital > 0
          - next_period_date <= today
        """
        if credit.get("status") != "ACTIVE":
            return False
        if credit.get("mora", False):
            return False
        if float(credit.get("pending_capital", 0)) <= 0:
            return False
        next_period_str = credit.get("next_period_date")
        if not next_period_str:
            return False
        next_period = date.fromisoformat(next_period_str)
        return next_period <= date.today()

    async def generate_installment(self, credit_id: UUID) -> dict:
        """
        Public alias used by the daily cron job.
        Delegates to generate_next(); re-raises ValueError with credit context.
        """
        try:
            return await self.generate_next(credit_id)
        except ValueError as exc:
            raise ValueError(f"Credit {credit_id}: {exc}") from exc

    async def run_daily_installment_job(self) -> dict:
        """
        System-level daily job: find all ACTIVE, non-mora credits whose
        next_period_date is today or in the past, and generate one installment
        for each.

        This method does NOT filter by user_id — it operates across all users.
        It should be called with a service-role Supabase client to bypass RLS.

        Returns a summary dict:
          {"processed": <int>, "errors": [{"credit_id": ..., "error": ...}, ...]}
        """
        today = date.today().isoformat()

        result = await (
            self.db.table("credits")
            .select("id,user_id")
            .eq("status", "ACTIVE")
            .eq("mora", False)
            .lte("next_period_date", today)
            .execute()
        )
        credits = result.data or []

        processed = 0
        errors: list = []

        for credit_row in credits:
            credit_id = UUID(credit_row["id"])
            # Temporarily adopt the credit owner's user_id so ownership checks
            # in generate_next() pass. The caller uses a service-role client so
            # RLS is bypassed at the DB level.
            original_user_id = self.user_id
            self.user_id = credit_row["user_id"]
            try:
                await self.generate_next(credit_id)
                processed += 1
            except Exception as exc:
                errors.append({"credit_id": str(credit_id), "error": str(exc)})
            finally:
                self.user_id = original_user_id

        return {"processed": processed, "errors": errors}

    async def generate_next(self, credit_id: UUID) -> dict:
        """
        Generate a single installment with LOCKED values.
        Blocked if mora = true or credit not ACTIVE.
        """
        credit_result = await (
            self.db.table("credits")
            .select("*")
            .eq("id", str(credit_id))
            .eq("user_id", self.user_id)
            .single()
            .execute()
        )
        if not credit_result.data:
            self._raise_forbidden("credit")
        credit = credit_result.data

        if credit["status"] != "ACTIVE":
            raise ValueError(f"Credit {credit_id} is not ACTIVE")
        if credit["mora"]:
            raise ValueError(f"Credit {credit_id} is in mora; installment generation blocked")
        if float(credit["pending_capital"]) <= 0:
            raise ValueError(f"Credit {credit_id} has no remaining capital")

        # Count existing installments for period_number
        count_result = await (
            self.db.table("installments")
            .select("id", count="exact")
            .eq("credit_id", str(credit_id))
            .execute()
        )
        period_number = (count_result.count or 0) + 1

        pending_capital = Decimal(str(credit["pending_capital"]))
        annual_rate = Decimal(str(credit["annual_interest_rate"]))
        periodicity = credit["periodicity"]

        interest_portion = calculate_period_interest(pending_capital, annual_rate, periodicity)
        principal_portion = calculate_principal_portion(pending_capital, REMAINING_PERIODS_DEFAULT)
        expected_value = (principal_portion + interest_portion)

        expected_date_str = credit["next_period_date"] or date.today().isoformat()
        expected_date = date.fromisoformat(expected_date_str)

        payload = {
            "user_id": self.user_id,
            "credit_id": str(credit_id),
            "period_number": period_number,
            "expected_date": expected_date.isoformat(),
            "expected_value": float(expected_value),
            "principal_portion": float(principal_portion),
            "interest_portion": float(interest_portion),
            "paid_value": 0.0,
            "is_overdue": False,
            "status": "UPCOMING",
        }
        result = await self.db.table("installments").insert(payload).execute()
        installment = result.data[0]

        # Advance next_period_date
        offset = PERIOD_DAYS.get(periodicity, 30)
        new_next = expected_date + timedelta(days=offset)
        await (
            self.db.table("credits")
            .update({
                "next_period_date": new_next.isoformat(),
                "version": credit["version"] + 1,
            })
            .eq("id", str(credit_id))
            .execute()
        )

        # Record history
        await self.db.table("financial_history").insert({
            "user_id": self.user_id,
            "event_type": "INSTALLMENT_GENERATED",
            "client_id": credit["client_id"],
            "credit_id": str(credit_id),
            "amount": float(expected_value),
            "description": f"Installment {period_number} generated",
            "metadata": {
                "period_number": period_number,
                "principal_portion": float(principal_portion),
                "interest_portion": float(interest_portion),
                "expected_date": expected_date.isoformat(),
            },
            "operator_id": "system",
        }).execute()

        return installment

    async def list_for_credit(self, credit_id: UUID, status: Optional[str] = None) -> List[dict]:
        # Ownership via credit check
        credit_result = await (
            self.db.table("credits")
            .select("id")
            .eq("id", str(credit_id))
            .eq("user_id", self.user_id)
            .single()
            .execute()
        )
        if not credit_result.data:
            self._raise_forbidden("credit")

        query = (
            self.db.table("installments")
            .select("*")
            .eq("credit_id", str(credit_id))
            .order("expected_date")
        )
        if status:
            query = query.eq("status", status)
        result = await query.execute()
        return result.data
