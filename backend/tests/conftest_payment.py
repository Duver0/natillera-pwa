"""
Shared fixtures and helpers for Phase 4 payment tests.
All tests use mocked DB — no real Supabase connection required.
Decimal everywhere — zero float in payment logic assertions.

Mock design:
- db.table("credits") SELECT → returns credit dict via .single().execute().data
- db.table("credits") UPDATE → returns [credit] list (simulates 1 row updated, success)
- db.table("installments") SELECT first call → returns installments list
- db.table("installments") UPDATE each → returns [{}] (success)
- db.table("installments") SELECT second (post-payment overdue) → returns post_payment_overdue
- db.table("payments") INSERT → returns [payment_record]
- all others → empty list
"""
from decimal import Decimal
from datetime import date
from unittest.mock import AsyncMock, MagicMock, call
from uuid import uuid4


TODAY = date(2026, 4, 24)
PAST = date(2020, 1, 1)
FUTURE = date(2030, 1, 1)


def make_credit(
    pending: Decimal = Decimal("1000.00"),
    mora: bool = False,
    version: int = 1,
    status: str = "ACTIVE",
) -> dict:
    return {
        "id": str(uuid4()),
        "user_id": "user-1",
        "client_id": str(uuid4()),
        "pending_capital": str(pending),
        "mora": mora,
        "mora_since": None,
        "status": status,
        "version": version,
    }


def make_installment(
    credit_id: str,
    expected_value: Decimal = Decimal("200.00"),
    principal: Decimal = Decimal("100.00"),
    interest: Decimal = Decimal("100.00"),
    paid: Decimal = Decimal("0.00"),
    overdue: bool = False,
    status: str = "UPCOMING",
    expected_date: date = None,
) -> dict:
    if expected_date is None:
        expected_date = PAST if overdue else FUTURE
    return {
        "id": str(uuid4()),
        "credit_id": credit_id,
        "expected_value": str(expected_value),
        "principal_portion": str(principal),
        "interest_portion": str(interest),
        "paid_value": str(paid),
        "is_overdue": overdue,
        "status": status,
        "expected_date": expected_date.isoformat(),
    }


def build_db_mock(
    credit: dict,
    installments: list,
    post_payment_overdue: list = None,
) -> MagicMock:
    """
    Build a Supabase-style async mock that correctly routes:
    - credits SELECT  → returns credit (single record)
    - credits UPDATE  → returns [credit] (1 row updated = success, optimistic lock passes)
    - installments SELECT #1 → returns installments (unpaid list)
    - installments UPDATE    → returns [{}] per call
    - installments SELECT #2 → returns post_payment_overdue (mora recheck)
    - payments INSERT        → returns [payment_record]
    """
    if post_payment_overdue is None:
        post_payment_overdue = []

    payment_id = str(uuid4())
    payment_record = {
        "id": payment_id,
        "credit_id": credit["id"],
        "amount": str(credit.get("pending_capital", "0")),
        "payment_date": TODAY.isoformat(),
        "applied_to": [],
        "recorded_by": "user-1",
        "created_at": "2026-04-24T00:00:00",
    }

    # State for installments select call ordering
    installments_select_calls = {"n": 0}
    installments_update_calls = {"n": 0}

    db = MagicMock()

    def make_chain(execute_fn):
        """Create a chainable mock where all chain methods return self, execute = execute_fn."""
        t = MagicMock()
        t.select.return_value = t
        t.insert.return_value = t
        t.update.return_value = t
        t.delete.return_value = t
        t.eq.return_value = t
        t.in_.return_value = t
        t.lt.return_value = t
        t.order.return_value = t
        t.single.return_value = t
        t.range.return_value = t
        t.execute = execute_fn
        return t

    def credits_execute_fn():
        # Used for BOTH select and update chains — distinguish by how we got here.
        # For single() (select): data = credit dict
        # For update chain: data = [credit] (list, 1 row = success)
        # We can't distinguish easily without tracking, so return a mock that works for both:
        # - .data that is a dict → used by select (credit_result.data → dict)
        # - len() check in update: we return a list [credit] for update
        # Solution: return MagicMock(data=[credit]) always — for select, service accesses .data
        # directly after .single(), which per Supabase client returns the single record, not list.
        # The service does: credit_result.data → expects a dict.
        # For update: service does: len(update_result.data or []) == 0
        # We need data to be a dict for select, and [dict] for update.
        # Since we can't distinguish, use a compromise: data = credit (dict).
        # len(dict) = number of keys > 0, so optimistic lock passes. Works for both.
        return MagicMock(data=credit)

    async def credits_execute_async():
        return credits_execute_fn()

    def installments_execute_by_context(operation):
        """Returns appropriate response based on whether it's a select or update."""
        async def _exec():
            if operation == "select":
                installments_select_calls["n"] += 1
                n = installments_select_calls["n"]
                if n == 1:
                    return MagicMock(data=installments)
                else:
                    # Second select = post-payment overdue check
                    return MagicMock(data=post_payment_overdue)
            elif operation == "update":
                return MagicMock(data=[{}])
            else:
                return MagicMock(data=[])
        return _exec

    def table_side_effect(name: str):
        if name == "credits":
            t = MagicMock()
            t.select.return_value = t
            t.single.return_value = t
            t.eq.return_value = t
            t.in_.return_value = t
            t.lt.return_value = t
            t.order.return_value = t

            # Update chain: update returns a different sub-mock that returns list
            update_chain = MagicMock()
            update_chain.eq.return_value = update_chain
            update_chain.execute = AsyncMock(return_value=MagicMock(data=[credit]))
            t.update.return_value = update_chain

            t.execute = AsyncMock(return_value=MagicMock(data=credit))
            t.insert.return_value = t
            return t

        elif name == "installments":
            t = MagicMock()
            t.eq.return_value = t
            t.in_.return_value = t
            t.lt.return_value = t
            t.order.return_value = t

            # select chain
            select_chain = MagicMock()
            select_chain.eq.return_value = select_chain
            select_chain.in_.return_value = select_chain
            select_chain.lt.return_value = select_chain
            select_chain.order.return_value = select_chain

            def make_select_execute():
                async def _exec():
                    installments_select_calls["n"] += 1
                    n = installments_select_calls["n"]
                    if n == 1:
                        return MagicMock(data=installments)
                    else:
                        return MagicMock(data=post_payment_overdue)
                return _exec

            select_chain.execute = make_select_execute()
            t.select.return_value = select_chain

            # update chain
            update_chain = MagicMock()
            update_chain.eq.return_value = update_chain
            update_chain.execute = AsyncMock(return_value=MagicMock(data=[{}]))
            t.update.return_value = update_chain

            t.insert.return_value = t
            t.delete.return_value = t
            return t

        elif name == "payments":
            t = MagicMock()
            t.select.return_value = t
            t.eq.return_value = t
            t.order.return_value = t
            t.execute = AsyncMock(return_value=MagicMock(data=[payment_record]))
            t.insert.return_value = t
            t.insert.return_value.execute = AsyncMock(return_value=MagicMock(data=[payment_record]))

            # More robust: insert returns a chain that executes correctly
            ins = MagicMock()
            ins.execute = AsyncMock(return_value=MagicMock(data=[payment_record]))
            t.insert.return_value = ins
            return t

        else:
            t = MagicMock()
            t.select.return_value = t
            t.insert.return_value = t
            t.update.return_value = t
            t.delete.return_value = t
            t.eq.return_value = t
            t.in_.return_value = t
            t.lt.return_value = t
            t.order.return_value = t
            t.single.return_value = t
            t.execute = AsyncMock(return_value=MagicMock(data=[]))
            ins = MagicMock()
            ins.execute = AsyncMock(return_value=MagicMock(data=[]))
            t.insert.return_value = ins
            return t

    db.table = MagicMock(side_effect=table_side_effect)
    return db
