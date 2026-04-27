"""
PaymentService — P0 Remediation (2026-04-24).
Contract: .github/specs/payment-contract.md

Architecture after remediation:
- process_payment()           → thin wrapper: calls process_payment_atomic RPC (single txn)
- preview_payment_breakdown() → pure, zero writes, uses corrected 3-pool global logic
- All allocation / locking / mora logic lives in SQL (003_payment_atomic_rpc.sql)

CF-1 resolved: single RPC call = single PostgreSQL transaction
CF-2 resolved: optimistic lock inside RPC — installments only written after lock acquired
CF-3 resolved: 3-pool global allocation enforced in SQL and mirrored in preview
CF-4 resolved: mora_since set to MIN(expected_date) of remaining overdue in RPC
CF-5 resolved: idempotency_key forwarded to RPC; cached 200 returned on hit

Rules:
- Decimal everywhere, ROUND_HALF_EVEN, no float
- LOCKED installment fields (expected_value, principal_portion, interest_portion, expected_date) NEVER written
- Single RPC call per payment — no extra Python round-trips for core logic
"""
from uuid import UUID
from datetime import date
from decimal import Decimal, ROUND_HALF_EVEN
from typing import List, Optional

from fastapi import HTTPException

from app.services.base_service import BaseService
from app.models.payment_model import (
    PaymentRequest,
    AppliedToEntry,
    UpdatedCreditSnapshot,
    PaymentResponse,
    PaymentPreviewResponse,
)


class VersionConflict(Exception):
    """Raised when RPC reports VersionConflict (SQLSTATE P0001)."""


def _decimal(value) -> Decimal:
    """Convert any value to Decimal with ROUND_HALF_EVEN and 2 decimal places."""
    d = Decimal(str(value))
    return d.quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)


def _compute_breakdown_3pool(
    installments: list,
    amount: Decimal,
    today: date,
) -> tuple[List[AppliedToEntry], Decimal, Decimal]:
    """
    3-pool global allocation algorithm (mirrors SQL RPC logic exactly).
    Used exclusively by preview_payment_breakdown — ZERO DB writes.

    Algorithm (CF-3 compliant):
      PASS 1 — collect global pool totals across ALL installments
      PASS 2 — distribute per-installment FIFO within each pool

    Returns:
        (applied_entries, total_principal_applied, remaining_after)
    """
    # ----------------------------------------------------------------
    # PASS 1: Aggregate global pools
    # ----------------------------------------------------------------
    pool_overdue_interest: Decimal = Decimal("0.00")
    pool_overdue_principal: Decimal = Decimal("0.00")
    pool_future_principal: Decimal = Decimal("0.00")

    for inst in installments:
        inst_paid     = _decimal(inst["paid_value"])
        inst_expected = _decimal(inst["expected_value"])
        inst_interest = _decimal(inst["interest_portion"])
        expected_date = date.fromisoformat(inst["expected_date"])
        is_overdue    = expected_date < today and inst.get("status") != "PAID"

        if is_overdue:
            # Interest still unpaid by this installment
            already_to_interest  = min(inst_paid, inst_interest)
            interest_owed        = inst_interest - already_to_interest
            # Principal still unpaid (from paid_value beyond interest portion)
            principal_owed       = max(Decimal("0.00"), inst_expected - max(inst_paid, inst_interest))

            pool_overdue_interest  += max(Decimal("0.00"), interest_owed)
            pool_overdue_principal += max(Decimal("0.00"), principal_owed)
        elif inst.get("status") != "PAID":
            future_owed = max(Decimal("0.00"), inst_expected - inst_paid)
            pool_future_principal += future_owed

    # ----------------------------------------------------------------
    # PASS 1b: Consume payment against global pools (strict order)
    # ----------------------------------------------------------------
    remaining = amount

    applied_interest  = min(remaining, pool_overdue_interest)
    remaining        -= applied_interest

    applied_principal = min(remaining, pool_overdue_principal)
    remaining        -= applied_principal

    applied_future    = min(remaining, pool_future_principal)
    remaining        -= applied_future

    total_principal = applied_principal + applied_future

    # ----------------------------------------------------------------
    # PASS 2: Distribute per-installment FIFO within each pool
    # Mirrors SQL loop so preview output == RPC output exactly.
    # ----------------------------------------------------------------
    applied: List[AppliedToEntry] = []
    pool1_left = applied_interest
    pool2_left = applied_principal
    pool3_left = applied_future

    for inst in installments:
        if pool1_left <= Decimal("0.00") and pool2_left <= Decimal("0.00") and pool3_left <= Decimal("0.00"):
            break

        inst_paid     = _decimal(inst["paid_value"])
        inst_expected = _decimal(inst["expected_value"])
        inst_interest = _decimal(inst["interest_portion"])
        expected_date = date.fromisoformat(inst["expected_date"])
        is_overdue    = expected_date < today and inst.get("status") != "PAID"

        if is_overdue:
            already_to_interest = min(inst_paid, inst_interest)
            interest_owed       = max(Decimal("0.00"), inst_interest - already_to_interest)
            principal_owed      = max(Decimal("0.00"), inst_expected - max(inst_paid, inst_interest))

            if pool1_left > Decimal("0.00") and interest_owed > Decimal("0.00"):
                take = min(pool1_left, interest_owed)
                pool1_left -= take
                applied.append(AppliedToEntry(
                    installment_id=inst["id"],
                    type="OVERDUE_INTEREST",
                    amount=take,
                ))

            if pool2_left > Decimal("0.00") and principal_owed > Decimal("0.00"):
                take = min(pool2_left, principal_owed)
                pool2_left -= take
                applied.append(AppliedToEntry(
                    installment_id=inst["id"],
                    type="OVERDUE_PRINCIPAL",
                    amount=take,
                ))
        elif inst.get("status") != "PAID":
            future_owed = max(Decimal("0.00"), inst_expected - inst_paid)
            if pool3_left > Decimal("0.00") and future_owed > Decimal("0.00"):
                take = min(pool3_left, future_owed)
                pool3_left -= take
                applied.append(AppliedToEntry(
                    installment_id=inst["id"],
                    type="FUTURE_PRINCIPAL",
                    amount=take,
                ))

    return applied, total_principal, remaining


class PaymentService(BaseService):

    async def process_payment(self, body: PaymentRequest) -> dict:
        """
        Thin wrapper — delegates ALL allocation, locking, and persistence to
        process_payment_atomic PostgreSQL RPC (single atomic transaction).

        CF-1: atomicity guaranteed by SQL transaction
        CF-2: optimistic lock acquired inside RPC before any writes
        CF-3: 3-pool global allocation in SQL
        CF-4: mora_since computed correctly in SQL
        CF-5: idempotency_key forwarded to RPC; cached 200 on hit

        On idempotent hit  → return cached response as 200 (not 409)
        On VersionConflict → raise HTTPException 409
        On CreditNotFound  → raise HTTPException 403
        On CreditClosed    → raise HTTPException 400
        On AmountInvalid   → raise HTTPException 400
        """
        try:
            rpc_result = await self.db.rpc(
                "process_payment_atomic",
                {
                    "p_credit_id":        str(body.credit_id),
                    "p_amount":           str(_decimal(body.amount)),
                    "p_operator_id":      body.operator_id,
                    "p_idempotency_key":  str(body.idempotency_key) if body.idempotency_key else None,
                }
            ).execute()
        except Exception as exc:
            exc_str = str(exc)
            if "VersionConflict" in exc_str or "P0001" in exc_str:
                raise HTTPException(status_code=409, detail="credit_version_conflict_retry")
            if "CreditNotFound" in exc_str or "P0004" in exc_str:
                raise HTTPException(status_code=403, detail="credit_not_found")
            if "CreditClosed" in exc_str or "P0002" in exc_str:
                raise HTTPException(status_code=400, detail="credit_not_active")
            if "AmountInvalid" in exc_str or "P0003" in exc_str:
                raise HTTPException(status_code=400, detail="amount_invalid")
            raise

        data = rpc_result.data
        if not data:
            raise HTTPException(status_code=500, detail="rpc_no_response")

        # Idempotent hit → return cached result as 200 (no new payment created)
        # Caller gets the same response shape regardless of idempotent or not
        snapshot = data["updated_credit_snapshot"]
        return {
            "payment_id": data["payment_id"],
            "credit_id":  data["credit_id"],
            "total_amount": data["total_amount"],
            "applied_to": data["applied_to"],
            "updated_credit_snapshot": {
                "pending_capital": snapshot["pending_capital"],
                "mora":            snapshot["mora"],
                "version":         snapshot["version"],
            },
            # Internal flag — router may use for 200 vs 201 decision on idempotent hit
            "_idempotent": data.get("idempotent", False),
        }

    async def preview_payment_breakdown(
        self, credit_id, amount: Decimal
    ) -> dict:
        """
        Pure computation — ZERO DB writes.
        Uses corrected 3-pool global allocation (CF-3 compliant).
        Output matches RPC output exactly for same input.
        Contract: .github/specs/payment-contract.md §2
        """
        credit_id_str = str(credit_id)
        amount = _decimal(amount)

        credit_result = await (
            self.db.table("credits")
            .select("*")
            .eq("id", credit_id_str)
            .eq("user_id", self.user_id)
            .single()
            .execute()
        )
        credit = credit_result.data
        if not credit:
            self._raise_forbidden("credit")

        if credit["status"] != "ACTIVE":
            raise HTTPException(status_code=400, detail="credit_not_active")

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
        applied_entries, total_principal_applied, remaining_after = _compute_breakdown_3pool(
            installments, amount, today
        )

        pending_capital = _decimal(credit["pending_capital"])
        projected_capital = max(Decimal("0.00"), pending_capital - total_principal_applied)

        # Excess beyond installments reduces capital (same rule as process_payment)
        unallocated = Decimal("0.00")
        if remaining_after > Decimal("0.00"):
            excess_to_capital = min(remaining_after, projected_capital)
            projected_capital = max(Decimal("0.00"), projected_capital - excess_to_capital)
            unallocated = remaining_after - excess_to_capital

        # Mora projection: any overdue installment not fully cleared by this payment?
        applied_by_inst: dict[str, Decimal] = {}
        for e in applied_entries:
            key = str(e.installment_id)
            applied_by_inst[key] = applied_by_inst.get(key, Decimal("0.00")) + e.amount

        mora_projected = False
        mora_since_projected: Optional[date] = None
        for inst in installments:
            inst_id = inst["id"]
            expected_date = date.fromisoformat(inst["expected_date"])
            if expected_date >= today or inst.get("status") == "PAID":
                continue
            paid_so_far  = _decimal(inst["paid_value"])
            additionally = applied_by_inst.get(inst_id, Decimal("0.00"))
            total_paid   = paid_so_far + additionally
            if total_paid < _decimal(inst["expected_value"]):
                mora_projected = True
                if mora_since_projected is None or expected_date < mora_since_projected:
                    mora_since_projected = expected_date

        applied_to_raw = [
            {
                "installment_id": str(e.installment_id),
                "type": e.type,
                "amount": str(e.amount),
            }
            for e in applied_entries
        ]

        return {
            "credit_id": credit_id_str,
            "total_amount": str(amount),
            "applied_to": applied_to_raw,
            "unallocated": str(unallocated),
            "updated_credit_snapshot": {
                "pending_capital": str(projected_capital),
                "mora": mora_projected,
                "version": credit["version"],  # unchanged — read-only preview
            },
        }

    async def preview_payment(self, credit_id: UUID, amount) -> dict:
        """Alias for preview_payment_breakdown (legacy endpoint support)."""
        return await self.preview_payment_breakdown(credit_id, _decimal(amount))

    async def list_payments(self, credit_id: UUID) -> list:
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
