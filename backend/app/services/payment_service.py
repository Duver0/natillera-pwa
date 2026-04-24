from uuid import UUID
from datetime import date
from decimal import Decimal
from typing import List

from app.services.base_service import BaseService
from app.models.payment_model import PaymentRequest


class PaymentService(BaseService):

    async def process_payment(self, body: PaymentRequest) -> dict:
        """
        Apply payment in MANDATORY order:
        1. Overdue interest (interest_portion where is_overdue = true)
        2. Overdue principal (principal_portion where is_overdue = true)
        3. Future principal (remaining unpaid upcoming installments)

        All steps must succeed atomically.
        Uses optimistic locking via credit.version.
        """
        credit_id = str(body.credit_id)
        operator_id = self.user_id

        # Fetch credit with ownership check
        credit_result = await (
            self.db.table("credits")
            .select("*")
            .eq("id", credit_id)
            .eq("user_id", self.user_id)
            .single()
            .execute()
        )
        if not credit_result.data:
            self._raise_forbidden("credit")
        credit = credit_result.data

        if credit["status"] != "ACTIVE":
            raise ValueError("Cannot process payment on non-ACTIVE credit")

        # Fetch all unpaid installments sorted by expected_date ASC
        installments_result = await (
            self.db.table("installments")
            .select("*")
            .eq("credit_id", credit_id)
            .in_("status", ["UPCOMING", "PARTIALLY_PAID"])
            .order("expected_date")
            .execute()
        )
        installments = installments_result.data or []

        today = date.today()
        # Recalculate is_overdue in-memory
        for inst in installments:
            inst["is_overdue"] = date.fromisoformat(inst["expected_date"]) < today

        remaining = Decimal(str(body.amount))
        applied_breakdown: List[dict] = []
        updated_installments: List[dict] = []

        for inst in installments:
            if remaining <= Decimal("0"):
                break

            inst_paid = Decimal(str(inst["paid_value"]))
            inst_expected = Decimal(str(inst["expected_value"]))
            inst_interest = Decimal(str(inst["interest_portion"]))
            inst_principal = Decimal(str(inst["principal_portion"]))
            remaining_owed = inst_expected - inst_paid

            if remaining_owed <= Decimal("0"):
                continue

            if inst["is_overdue"]:
                # Step 1: overdue interest
                interest_unpaid = max(Decimal("0"), inst_interest - max(Decimal("0"), inst_paid))
                if interest_unpaid > Decimal("0"):
                    applied = min(remaining, interest_unpaid)
                    remaining -= applied
                    inst_paid += applied
                    applied_breakdown.append({
                        "type": "OVERDUE_INTEREST",
                        "amount": float(applied),
                        "installment_id": inst["id"],
                    })

                # Step 2: overdue principal
                if remaining > Decimal("0"):
                    principal_unpaid = max(Decimal("0"), inst_expected - inst_paid)
                    applied = min(remaining, principal_unpaid)
                    remaining -= applied
                    inst_paid += applied
                    applied_breakdown.append({
                        "type": "OVERDUE_PRINCIPAL",
                        "amount": float(applied),
                        "installment_id": inst["id"],
                    })
            else:
                # Step 3: future principal
                future_unpaid = inst_expected - inst_paid
                if future_unpaid > Decimal("0") and remaining > Decimal("0"):
                    applied = min(remaining, future_unpaid)
                    remaining -= applied
                    inst_paid += applied
                    applied_breakdown.append({
                        "type": "FUTURE_PRINCIPAL",
                        "amount": float(applied),
                        "installment_id": inst["id"],
                    })

            # Determine new status
            if inst_paid >= inst_expected:
                new_status = "PAID"
                paid_at = today.isoformat()
            elif inst_paid > Decimal("0"):
                new_status = "PARTIALLY_PAID"
                paid_at = None
            else:
                new_status = inst["status"]
                paid_at = None

            updated_installments.append({
                "id": inst["id"],
                "paid_value": float(inst_paid),
                "status": new_status,
                "paid_at": paid_at,
                "is_overdue": inst["is_overdue"] and new_status != "PAID",
            })

        # Persist installment updates
        for upd in updated_installments:
            inst_id = upd.pop("id")
            await (
                self.db.table("installments")
                .update(upd)
                .eq("id", inst_id)
                .execute()
            )

        # Calculate principal applied
        principal_applied = sum(
            b["amount"] for b in applied_breakdown
            if b["type"] in ("OVERDUE_PRINCIPAL", "FUTURE_PRINCIPAL")
        )
        new_pending_capital = float(credit["pending_capital"]) - principal_applied
        new_pending_capital = max(0.0, new_pending_capital)

        # Recalculate mora after payment
        post_overdue_result = await (
            self.db.table("installments")
            .select("id")
            .eq("credit_id", credit_id)
            .in_("status", ["UPCOMING", "PARTIALLY_PAID"])
            .lt("expected_date", today.isoformat())
            .execute()
        )
        mora_after = len(post_overdue_result.data or []) > 0

        # Auto-close if pending_capital reaches zero
        new_status = "CLOSED" if new_pending_capital <= 0 else credit["status"]

        await (
            self.db.table("credits")
            .update({
                "pending_capital": new_pending_capital,
                "mora": mora_after,
                "mora_since": None if not mora_after else credit.get("mora_since"),
                "version": credit["version"] + 1,
                "status": new_status,
            })
            .eq("id", credit_id)
            .eq("version", credit["version"])  # optimistic lock
            .execute()
        )

        payment_date = (body.payment_date or today).isoformat()
        payment_payload = {
            "user_id": self.user_id,
            "credit_id": credit_id,
            "amount": float(body.amount),
            "payment_date": payment_date,
            "applied_to": applied_breakdown,
            "notes": body.notes,
            "recorded_by": operator_id,
        }
        payment_result = await self.db.table("payments").insert(payment_payload).execute()
        payment = payment_result.data[0]

        # History event
        await self.db.table("financial_history").insert({
            "user_id": self.user_id,
            "event_type": "PAYMENT_RECORDED",
            "client_id": credit["client_id"],
            "credit_id": credit_id,
            "amount": float(body.amount),
            "description": f"Payment of {body.amount} processed",
            "metadata": {
                "payment_id": payment["id"],
                "total_amount": float(body.amount),
                "applied_to": applied_breakdown,
            },
            "operator_id": operator_id,
        }).execute()

        return payment

    async def preview_payment(self, credit_id: UUID, amount: float) -> dict:
        """
        Dry-run: compute allocation breakdown WITHOUT persisting anything.
        Reuses the same allocation logic as process_payment.
        """
        credit_id_str = str(credit_id)

        credit_result = await (
            self.db.table("credits")
            .select("*")
            .eq("id", credit_id_str)
            .eq("user_id", self.user_id)
            .single()
            .execute()
        )
        if not credit_result.data:
            self._raise_forbidden("credit")
        credit = credit_result.data

        if credit["status"] != "ACTIVE":
            raise ValueError("Cannot preview payment on non-ACTIVE credit")

        installments_result = await (
            self.db.table("installments")
            .select("*")
            .eq("credit_id", credit_id_str)
            .in_("status", ["UPCOMING", "PARTIALLY_PAID"])
            .order("expected_date")
            .execute()
        )
        installments = installments_result.data or []

        today = date.today()
        for inst in installments:
            inst["is_overdue"] = date.fromisoformat(inst["expected_date"]) < today

        remaining = Decimal(str(amount))
        applied_breakdown: List[dict] = []

        for inst in installments:
            if remaining <= Decimal("0"):
                break

            inst_paid = Decimal(str(inst["paid_value"]))
            inst_expected = Decimal(str(inst["expected_value"]))
            inst_interest = Decimal(str(inst["interest_portion"]))
            remaining_owed = inst_expected - inst_paid

            if remaining_owed <= Decimal("0"):
                continue

            if inst["is_overdue"]:
                interest_unpaid = max(Decimal("0"), inst_interest - max(Decimal("0"), inst_paid))
                if interest_unpaid > Decimal("0"):
                    applied = min(remaining, interest_unpaid)
                    remaining -= applied
                    inst_paid += applied
                    applied_breakdown.append({
                        "type": "OVERDUE_INTEREST",
                        "amount": float(applied),
                        "installment_id": inst["id"],
                    })

                if remaining > Decimal("0"):
                    principal_unpaid = max(Decimal("0"), inst_expected - inst_paid)
                    applied = min(remaining, principal_unpaid)
                    remaining -= applied
                    applied_breakdown.append({
                        "type": "OVERDUE_PRINCIPAL",
                        "amount": float(applied),
                        "installment_id": inst["id"],
                    })
            else:
                future_unpaid = inst_expected - inst_paid
                if future_unpaid > Decimal("0") and remaining > Decimal("0"):
                    applied = min(remaining, future_unpaid)
                    remaining -= applied
                    applied_breakdown.append({
                        "type": "FUTURE_PRINCIPAL",
                        "amount": float(applied),
                        "installment_id": inst["id"],
                    })

        return {
            "credit_id": credit_id_str,
            "amount": amount,
            "applied_to": applied_breakdown,
            "unallocated": float(remaining),
        }

    async def list_payments(self, credit_id: UUID) -> list:
        # Ownership check via credit
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

        result = await (
            self.db.table("payments")
            .select("*")
            .eq("credit_id", str(credit_id))
            .order("created_at", desc=True)
            .execute()
        )
        return result.data
