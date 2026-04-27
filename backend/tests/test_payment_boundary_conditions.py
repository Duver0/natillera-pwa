"""
test_payment_boundary_conditions.py
SPEC-001 §US-005 — Boundary: remaining_payment == installment.remaining exact

RED PHASE.
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


async def test_exact_payment_marks_installment_paid():
    """
    GIVEN: installment remaining = 200, payment = 200 (exact match)
    THEN:  installment status = PAID, no leftover
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
    # No unallocated in process_payment (only in preview)
    # Verify installment would be PAID by checking applied amounts sum to expected_value
    assert applied_total == Decimal(inst["expected_value"])


async def test_exact_payment_partially_paid_installment():
    """
    GIVEN: installment with paid_value=100 already, expected=200, remaining=100
    WHEN:  payment = 100 (exact remaining)
    THEN:  installment fully paid, applied amount = 100
    """
    credit = make_credit(pending=Decimal("1000.00"))
    inst = make_installment(
        credit["id"],
        expected_value=Decimal("200.00"),
        principal=Decimal("100.00"),
        interest=Decimal("100.00"),
        paid=Decimal("100.00"),
        overdue=True,
        status="PARTIALLY_PAID",
    )
    result = await _process(credit, [inst], Decimal("100.00"))

    applied_total = sum(Decimal(str(e["amount"])) for e in result["applied_to"])
    assert applied_total == Decimal("100.00"), "Must apply exactly the remaining amount"


async def test_boundary_zero_remaining_installment_skipped():
    """
    GIVEN: installment already fully paid (paid_value = expected_value)
    WHEN:  any payment applied
    THEN:  that installment receives zero additional allocation
    """
    credit = make_credit(pending=Decimal("1000.00"))
    paid_inst = make_installment(
        credit["id"],
        expected_value=Decimal("200.00"),
        principal=Decimal("100.00"),
        interest=Decimal("100.00"),
        paid=Decimal("200.00"),
        overdue=False,
        status="PAID",
    )
    future_inst = make_installment(
        credit["id"],
        expected_value=Decimal("200.00"),
        principal=Decimal("100.00"),
        interest=Decimal("100.00"),
        overdue=False,
    )
    result = await _process(credit, [paid_inst, future_inst], Decimal("100.00"))

    for entry in result["applied_to"]:
        assert entry["installment_id"] != paid_inst["id"], "Fully paid installment must be skipped"


async def test_boundary_minimum_decimal_precision():
    """
    GIVEN: payment of 0.01 (minimum precision)
    THEN:  no precision loss, applied amount = 0.01 exactly
    """
    credit = make_credit(pending=Decimal("1000.00"))
    inst = make_installment(
        credit["id"],
        expected_value=Decimal("100.00"),
        principal=Decimal("50.00"),
        interest=Decimal("50.00"),
        overdue=True,
    )
    result = await _process(credit, [inst], Decimal("0.01"))

    applied_total = sum(Decimal(str(e["amount"])) for e in result["applied_to"])
    assert applied_total == Decimal("0.01"), "Minimum precision must be preserved"


async def test_boundary_pending_capital_never_negative():
    """
    GIVEN: any payment scenario
    THEN:  pending_capital in snapshot is always >= 0
    """
    credit = make_credit(pending=Decimal("100.00"))
    inst = make_installment(
        credit["id"],
        expected_value=Decimal("100.00"),
        principal=Decimal("100.00"),
        interest=Decimal("0.00"),
        overdue=True,
    )
    result = await _process(credit, [inst], Decimal("9999.00"))

    snapshot = result["updated_credit_snapshot"]
    assert Decimal(str(snapshot["pending_capital"])) >= Decimal("0.00")


async def test_boundary_version_incremented():
    """
    GIVEN: credit at version=5
    WHEN:  payment applied successfully
    THEN:  snapshot.version = 6
    """
    credit = make_credit(pending=Decimal("500.00"), version=5)
    inst = make_installment(credit["id"], overdue=True)
    result = await _process(credit, [inst], Decimal("10.00"))

    snapshot = result["updated_credit_snapshot"]
    assert snapshot["version"] == 6, "Version must be incremented after successful payment"
