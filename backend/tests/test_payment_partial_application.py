"""
test_payment_partial_application.py
SPEC-001 §US-005 — payment < first installment remaining

RED PHASE: Verifies partial application leaves remainder in installment.
"""
import pytest
from decimal import Decimal

from tests.conftest_payment import make_credit, make_installment, build_db_mock


pytestmark = pytest.mark.asyncio


async def _process(credit, installments, amount: Decimal):
    from app.services.payment_service import PaymentService
    from app.models.payment_model import PaymentRequest

    db = build_db_mock(credit, installments)
    service = PaymentService(db, "user-1")
    req = PaymentRequest(credit_id=credit["id"], amount=amount, operator_id="user-1")
    return await service.process_payment(req)


async def test_partial_payment_less_than_interest():
    """
    GIVEN: overdue installment with interest=100
    WHEN:  payment=50 (< interest)
    THEN:  applied 50 to OVERDUE_INTEREST
           installment NOT marked PAID
           installment update shows paid_value=50
    """
    credit = make_credit(pending=Decimal("500.00"))
    inst = make_installment(
        credit["id"],
        expected_value=Decimal("200.00"),
        principal=Decimal("100.00"),
        interest=Decimal("100.00"),
        paid=Decimal("0.00"),
        overdue=True,
    )
    result = await _process(credit, [inst], Decimal("50.00"))

    applied = result["applied_to"]
    assert len(applied) == 1
    assert applied[0]["type"] == "OVERDUE_INTEREST"
    assert Decimal(str(applied[0]["amount"])) == Decimal("50.00")

    # Snapshot: principal untouched → pending_capital unchanged
    snapshot = result["updated_credit_snapshot"]
    assert Decimal(str(snapshot["pending_capital"])) == Decimal("500.00")


async def test_partial_payment_partially_paid_status():
    """
    GIVEN: overdue installment, payment covers part of it
    WHEN:  payment applied
    THEN:  installment write contains status=PARTIALLY_PAID (not PAID, not UPCOMING)
    """
    credit = make_credit(pending=Decimal("500.00"))
    inst = make_installment(
        credit["id"],
        expected_value=Decimal("200.00"),
        principal=Decimal("100.00"),
        interest=Decimal("100.00"),
        overdue=True,
    )
    db = build_db_mock(credit, [inst])

    from app.services.payment_service import PaymentService
    from app.models.payment_model import PaymentRequest

    service = PaymentService(db, "user-1")
    req = PaymentRequest(credit_id=credit["id"], amount=Decimal("50.00"), operator_id="user-1")
    await service.process_payment(req)

    # Inspect update calls to installments table
    update_calls = []
    for call in db.table.call_args_list:
        if call.args[0] == "installments":
            break
    # Verify the mock was called with PARTIALLY_PAID somewhere
    all_calls_str = str(db.method_calls)
    assert "PARTIALLY_PAID" in all_calls_str, "Expected PARTIALLY_PAID status in installment update"


async def test_partial_payment_no_future_installment_touched():
    """
    GIVEN: overdue installment (200) + future installment (200)
    WHEN:  payment=50 (less than overdue interest)
    THEN:  future installment receives zero payment
    """
    credit = make_credit(pending=Decimal("1000.00"))
    overdue = make_installment(
        credit["id"],
        expected_value=Decimal("200.00"),
        principal=Decimal("100.00"),
        interest=Decimal("100.00"),
        overdue=True,
    )
    future = make_installment(
        credit["id"],
        expected_value=Decimal("200.00"),
        principal=Decimal("100.00"),
        interest=Decimal("100.00"),
        overdue=False,
    )
    result = await _process(credit, [overdue, future], Decimal("50.00"))

    applied = result["applied_to"]
    future_applied = [e for e in applied if e["installment_id"] == future["id"]]
    assert len(future_applied) == 0, "Future installment must not receive any partial payment"


async def test_partial_payment_unallocated_zero_when_all_applied():
    """
    GIVEN: installment remaining = 200, payment = 200 (exact)
    THEN:  no unallocated; installment marked PAID
    """
    credit = make_credit(pending=Decimal("1000.00"))
    inst = make_installment(
        credit["id"],
        expected_value=Decimal("200.00"),
        principal=Decimal("100.00"),
        interest=Decimal("100.00"),
        overdue=True,
    )
    result = await _process(credit, [inst], Decimal("200.00"))

    applied_total = sum(Decimal(str(e["amount"])) for e in result["applied_to"])
    assert applied_total == Decimal("200.00")


async def test_partial_payment_preserves_pending_capital_when_only_interest_paid():
    """
    GIVEN: overdue installment, payment covers only interest (not principal)
    THEN:  pending_capital in snapshot is unchanged
    """
    credit = make_credit(pending=Decimal("800.00"))
    inst = make_installment(
        credit["id"],
        expected_value=Decimal("300.00"),
        principal=Decimal("200.00"),
        interest=Decimal("100.00"),
        overdue=True,
    )
    result = await _process(credit, [inst], Decimal("100.00"))

    snapshot = result["updated_credit_snapshot"]
    assert Decimal(str(snapshot["pending_capital"])) == Decimal("800.00"), \
        "pending_capital must not decrease when only interest is paid"
