"""
test_optimistic_locking_retry.py
SPEC-001 §1.2 — Version Control / Concurrent Payment Race

Fix for Week 2 residual risk #3: "payment_service.py optimistic lock gap —
if eq("version", credit["version"]) update matches 0 rows, service does not detect it
and silently proceeds."

Contract: version mismatch → VersionConflict exception → HTTP 409

RED PHASE.
"""
import pytest
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

from tests.conftest_payment import make_credit, make_installment


pytestmark = pytest.mark.asyncio


def build_version_conflict_db(credit, installments):
    """DB mock where credits UPDATE returns 0 rows (version mismatch)."""
    db = MagicMock()

    def table_side_effect(name):
        t = MagicMock()
        t.select.return_value = t
        t.delete.return_value = t
        t.eq.return_value = t
        t.in_.return_value = t
        t.lt.return_value = t
        t.order.return_value = t
        t.single.return_value = t

        if name == "credits":
            t.execute = AsyncMock(return_value=MagicMock(data=credit))
            # update chains: update().eq().eq().execute() → 0 rows
            update_chain = MagicMock()
            update_chain.eq.return_value = update_chain
            update_chain.execute = AsyncMock(return_value=MagicMock(data=[]))  # 0 rows = conflict
            t.update.return_value = update_chain
            t.insert.return_value = t
        elif name == "installments":
            t.execute = AsyncMock(return_value=MagicMock(data=installments))
            upd = MagicMock()
            upd.eq.return_value = upd
            upd.execute = AsyncMock(return_value=MagicMock(data=[{}]))
            t.update.return_value = upd
            t.insert.return_value = t
        else:
            t.insert.return_value = t
            t.execute = AsyncMock(return_value=MagicMock(data=[]))

        return t

    db.table = MagicMock(side_effect=table_side_effect)
    return db


async def test_version_conflict_raises_exception():
    """
    GIVEN: credit at version=1
    WHEN:  UPDATE WHERE version=1 affects 0 rows (concurrent write bumped version)
    THEN:  PaymentService raises VersionConflict (or equivalent) — NOT silent
    """
    from app.services.payment_service import PaymentService
    from app.models.payment_model import PaymentRequest

    credit = make_credit(pending=Decimal("500.00"), version=1)
    inst = make_installment(credit["id"], overdue=True)

    db = build_version_conflict_db(credit, [inst])
    service = PaymentService(db, "user-1")
    req = PaymentRequest(credit_id=credit["id"], amount=Decimal("50.00"), operator_id="user-1")

    with pytest.raises(Exception) as exc_info:
        await service.process_payment(req)

    # Must raise — not silently proceed
    assert exc_info.value is not None


async def test_version_conflict_exception_type_is_version_conflict():
    """
    GIVEN: version mismatch
    THEN:  raised exception has a recognizable type (VersionConflict or similar)
           OR the error message/type indicates a conflict, not a generic error
    """
    from app.services.payment_service import PaymentService
    from app.models.payment_model import PaymentRequest

    credit = make_credit(pending=Decimal("500.00"), version=1)
    inst = make_installment(credit["id"], overdue=True)

    db = build_version_conflict_db(credit, [inst])
    service = PaymentService(db, "user-1")
    req = PaymentRequest(credit_id=credit["id"], amount=Decimal("50.00"), operator_id="user-1")

    with pytest.raises(Exception) as exc_info:
        await service.process_payment(req)

    err = exc_info.value
    # Accept either a named VersionConflict exception or an HTTPException with 409 status
    err_type = type(err).__name__
    err_str = str(err).lower()
    is_version_conflict = (
        "version" in err_type.lower()
        or "conflict" in err_type.lower()
        or "409" in err_str
        or "conflict" in err_str
        or "version" in err_str
        or getattr(err, "status_code", None) == 409
    )
    assert is_version_conflict, f"Expected version conflict error, got: {err_type}: {err}"


async def test_version_conflict_does_not_insert_payment():
    """
    GIVEN: version conflict mid-payment
    THEN:  payments table insert never called (no phantom payment record)
    """
    from app.services.payment_service import PaymentService
    from app.models.payment_model import PaymentRequest

    credit = make_credit(pending=Decimal("500.00"), version=1)
    inst = make_installment(credit["id"], overdue=True)
    payment_calls = {"count": 0}

    db = MagicMock()

    def table_side_effect(name):
        t = MagicMock()
        t.select.return_value = t
        t.delete.return_value = t
        t.eq.return_value = t
        t.in_.return_value = t
        t.lt.return_value = t
        t.order.return_value = t
        t.single.return_value = t

        if name == "credits":
            t.execute = AsyncMock(return_value=MagicMock(data=credit))
            update_chain = MagicMock()
            update_chain.eq.return_value = update_chain
            update_chain.execute = AsyncMock(return_value=MagicMock(data=[]))
            t.update.return_value = update_chain
            t.insert.return_value = t
        elif name == "installments":
            t.execute = AsyncMock(return_value=MagicMock(data=[inst]))
            upd = MagicMock()
            upd.eq.return_value = upd
            upd.execute = AsyncMock(return_value=MagicMock(data=[{}]))
            t.update.return_value = upd
            t.insert.return_value = t
        elif name == "payments":
            payment_calls["count"] += 1
            t.execute = AsyncMock(return_value=MagicMock(data=[{"id": "p1"}]))
            t.insert.return_value = t
        else:
            t.insert.return_value = t
            t.execute = AsyncMock(return_value=MagicMock(data=[]))

        return t

    db.table = MagicMock(side_effect=table_side_effect)
    service = PaymentService(db, "user-1")
    req = PaymentRequest(credit_id=credit["id"], amount=Decimal("50.00"), operator_id="user-1")

    with pytest.raises(Exception):
        await service.process_payment(req)

    assert payment_calls["count"] == 0, "Payment insert must not be called on version conflict"


async def test_successful_payment_does_not_raise():
    """
    GIVEN: no version conflict (update returns 1 row)
    THEN:  no exception raised, result has payment_id
    """
    from app.services.payment_service import PaymentService
    from app.models.payment_model import PaymentRequest
    from tests.conftest_payment import build_db_mock

    credit = make_credit(pending=Decimal("500.00"), version=1)
    inst = make_installment(credit["id"], overdue=True)

    db = build_db_mock(credit, [inst])
    service = PaymentService(db, "user-1")
    req = PaymentRequest(credit_id=credit["id"], amount=Decimal("50.00"), operator_id="user-1")

    result = await service.process_payment(req)
    assert "payment_id" in result
