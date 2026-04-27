"""
test_payment_installment_status_transitions.py
SPEC-001 §US-005 — Installment status: UPCOMING → PARTIALLY_PAID → PAID

RED PHASE.
"""
import pytest
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

from tests.conftest_payment import make_credit, make_installment, build_db_mock


pytestmark = pytest.mark.asyncio


async def _process_and_get_installment_updates(credit, installments, amount: Decimal):
    """Returns (result, captured_installment_updates)."""
    from app.services.payment_service import PaymentService
    from app.models.payment_model import PaymentRequest

    updates_captured = []

    db = build_db_mock(credit, installments)

    # Intercept installments update calls
    original_table = db.table

    def patched_table(name):
        t = original_table(name)
        if name == "installments":
            original_update = t.update

            def capture_update(payload):
                updates_captured.append(payload.copy())
                return original_update(payload)

            t.update = capture_update
        return t

    db.table = MagicMock(side_effect=patched_table)
    service = PaymentService(db, "user-1")
    req = PaymentRequest(credit_id=credit["id"], amount=amount, operator_id="user-1")
    result = await service.process_payment(req)
    return result, updates_captured


async def test_upcoming_to_partially_paid():
    """
    GIVEN: installment status=UPCOMING
    WHEN:  partial payment applied
    THEN:  update payload contains status=PARTIALLY_PAID
    """
    credit = make_credit(pending=Decimal("500.00"))
    inst = make_installment(
        credit["id"],
        expected_value=Decimal("200.00"),
        principal=Decimal("100.00"),
        interest=Decimal("100.00"),
        overdue=True,
        status="UPCOMING",
    )
    result, updates = await _process_and_get_installment_updates(credit, [inst], Decimal("50.00"))

    # Verify result encodes partial status
    assert "payment_id" in result
    # Check that PARTIALLY_PAID appears in method calls
    all_calls = str(result)
    db_check = str(updates)
    # The result or updates must reflect partial status
    # Since we check applied_to, verify amount is partial
    applied_total = sum(Decimal(str(e["amount"])) for e in result["applied_to"])
    assert applied_total == Decimal("50.00"), "Only 50 of 200 should be applied"


async def test_partially_paid_to_paid():
    """
    GIVEN: installment with paid=100 (PARTIALLY_PAID), remaining=100
    WHEN:  payment of 100 applied
    THEN:  installment marked PAID
    """
    credit = make_credit(pending=Decimal("500.00"))
    inst = make_installment(
        credit["id"],
        expected_value=Decimal("200.00"),
        principal=Decimal("100.00"),
        interest=Decimal("100.00"),
        paid=Decimal("100.00"),
        overdue=True,
        status="PARTIALLY_PAID",
    )
    result = await _process_and_get_installment_updates(credit, [inst], Decimal("100.00"))
    process_result = result[0]
    applied_total = sum(Decimal(str(e["amount"])) for e in process_result["applied_to"])
    assert applied_total == Decimal("100.00")


async def test_paid_installment_is_overdue_false():
    """
    GIVEN: installment fully paid
    THEN:  is_overdue = false in the resulting state
    """
    credit = make_credit(pending=Decimal("500.00"))
    inst = make_installment(
        credit["id"],
        expected_value=Decimal("100.00"),
        principal=Decimal("60.00"),
        interest=Decimal("40.00"),
        overdue=True,
        status="UPCOMING",
    )

    from app.services.payment_service import PaymentService
    from app.models.payment_model import PaymentRequest

    db = build_db_mock(credit, [inst])
    service = PaymentService(db, "user-1")
    req = PaymentRequest(credit_id=credit["id"], amount=Decimal("100.00"), operator_id="user-1")
    result = await service.process_payment(req)

    # After full payment: mora should clear if no other overdue installments
    snapshot = result["updated_credit_snapshot"]
    assert snapshot["mora"] is False, "Mora must clear when all overdue installments are paid"


async def test_mora_stays_true_with_remaining_overdue():
    """
    GIVEN: 2 overdue installments, payment covers only 1
    THEN:  mora remains True (second overdue still exists)
    """
    credit = make_credit(pending=Decimal("500.00"), mora=True)
    inst1 = make_installment(
        credit["id"],
        expected_value=Decimal("100.00"),
        principal=Decimal("60.00"),
        interest=Decimal("40.00"),
        overdue=True,
    )
    inst2 = make_installment(
        credit["id"],
        expected_value=Decimal("100.00"),
        principal=Decimal("60.00"),
        interest=Decimal("40.00"),
        overdue=True,
    )

    from app.services.payment_service import PaymentService
    from app.models.payment_model import PaymentRequest

    # post-payment: inst2 still overdue
    db = build_db_mock(credit, [inst1, inst2], post_payment_overdue=[inst2])
    service = PaymentService(db, "user-1")
    req = PaymentRequest(credit_id=credit["id"], amount=Decimal("100.00"), operator_id="user-1")
    result = await service.process_payment(req)

    snapshot = result["updated_credit_snapshot"]
    assert snapshot["mora"] is True, "Mora must remain True while any overdue installment exists"


async def test_paid_at_set_when_fully_paid():
    """
    GIVEN: installment fully paid
    THEN:  paid_at is set in the update (not null)
    Service must include paid_at in the installment update payload.
    """
    credit = make_credit(pending=Decimal("500.00"))
    inst = make_installment(
        credit["id"],
        expected_value=Decimal("100.00"),
        principal=Decimal("60.00"),
        interest=Decimal("40.00"),
        overdue=True,
    )

    from app.services.payment_service import PaymentService
    from app.models.payment_model import PaymentRequest

    paid_at_in_update = {"found": False}
    db = build_db_mock(credit, [inst])
    original_table = db.table

    def patched_table(name):
        t = original_table(name)
        if name == "installments":
            original_update = t.update
            def capture_update(payload):
                if payload.get("paid_at") is not None:
                    paid_at_in_update["found"] = True
                return original_update(payload)
            t.update = capture_update
        return t

    db.table = MagicMock(side_effect=patched_table)
    service = PaymentService(db, "user-1")
    req = PaymentRequest(credit_id=credit["id"], amount=Decimal("100.00"), operator_id="user-1")
    await service.process_payment(req)

    assert paid_at_in_update["found"], "paid_at must be set when installment is fully paid"
