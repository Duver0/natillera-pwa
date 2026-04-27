"""
test_payment_multi_installment.py
SPEC-001 §US-005 — Payment across multiple overdue + mixed overdue+future installments.

RED PHASE.
"""
import pytest
from decimal import Decimal
from datetime import date, timedelta

from tests.conftest_payment import make_credit, make_installment, build_db_mock, PAST, FUTURE


pytestmark = pytest.mark.asyncio


async def _process(credit, installments, amount: Decimal, post_overdue=None):
    from app.services.payment_service import PaymentService
    from app.models.payment_model import PaymentRequest

    db = build_db_mock(credit, installments, post_payment_overdue=post_overdue or [])
    service = PaymentService(db, "user-1")
    req = PaymentRequest(credit_id=credit["id"], amount=amount, operator_id="user-1")
    return await service.process_payment(req)


async def test_multi_overdue_fifo_order():
    """
    GIVEN: 3 overdue installments (period 1, 2, 3) — all unpaid
    WHEN:  payment covers exactly installment 1
    THEN:  period 1 cleared first (FIFO by expected_date), periods 2+3 untouched
    """
    credit = make_credit(pending=Decimal("900.00"))
    inst1 = make_installment(
        credit["id"],
        expected_value=Decimal("150.00"),
        principal=Decimal("100.00"),
        interest=Decimal("50.00"),
        overdue=True,
        expected_date=date(2020, 1, 1),
    )
    inst2 = make_installment(
        credit["id"],
        expected_value=Decimal("150.00"),
        principal=Decimal("100.00"),
        interest=Decimal("50.00"),
        overdue=True,
        expected_date=date(2020, 2, 1),
    )
    inst3 = make_installment(
        credit["id"],
        expected_value=Decimal("150.00"),
        principal=Decimal("100.00"),
        interest=Decimal("50.00"),
        overdue=True,
        expected_date=date(2020, 3, 1),
    )
    result = await _process(credit, [inst1, inst2, inst3], Decimal("150.00"))

    inst1_applied = sum(Decimal(str(e["amount"])) for e in result["applied_to"] if e["installment_id"] == inst1["id"])
    inst2_applied = sum(Decimal(str(e["amount"])) for e in result["applied_to"] if e["installment_id"] == inst2["id"])
    inst3_applied = sum(Decimal(str(e["amount"])) for e in result["applied_to"] if e["installment_id"] == inst3["id"])

    assert inst1_applied == Decimal("150.00"), "Period 1 must be cleared first"
    assert inst2_applied == Decimal("0.00"), "Period 2 must not be touched"
    assert inst3_applied == Decimal("0.00"), "Period 3 must not be touched"


async def test_multi_overdue_then_future():
    """
    GIVEN: 2 overdue (100 each) + 1 future (100)
    WHEN:  payment = 250
    THEN:  both overdue cleared (200), then 50 to future
    """
    credit = make_credit(pending=Decimal("900.00"))
    ov1 = make_installment(
        credit["id"],
        expected_value=Decimal("100.00"),
        principal=Decimal("60.00"),
        interest=Decimal("40.00"),
        overdue=True,
        expected_date=date(2020, 1, 1),
    )
    ov2 = make_installment(
        credit["id"],
        expected_value=Decimal("100.00"),
        principal=Decimal("60.00"),
        interest=Decimal("40.00"),
        overdue=True,
        expected_date=date(2020, 2, 1),
    )
    fut = make_installment(
        credit["id"],
        expected_value=Decimal("100.00"),
        principal=Decimal("60.00"),
        interest=Decimal("40.00"),
        overdue=False,
        expected_date=date(2030, 1, 1),
    )
    result = await _process(credit, [ov1, ov2, fut], Decimal("250.00"))

    ov1_applied = sum(Decimal(str(e["amount"])) for e in result["applied_to"] if e["installment_id"] == ov1["id"])
    ov2_applied = sum(Decimal(str(e["amount"])) for e in result["applied_to"] if e["installment_id"] == ov2["id"])
    fut_applied = sum(Decimal(str(e["amount"])) for e in result["applied_to"] if e["installment_id"] == fut["id"])

    assert ov1_applied == Decimal("100.00")
    assert ov2_applied == Decimal("100.00")
    assert fut_applied == Decimal("50.00")


async def test_multi_installment_pending_capital_decremented_correctly():
    """
    GIVEN: 2 overdue each with interest=50, principal=100
    WHEN:  payment = 300 (clears both)
    THEN:  pending_capital decremented by total principal applied = 200
    """
    credit = make_credit(pending=Decimal("1000.00"))
    ov1 = make_installment(
        credit["id"],
        expected_value=Decimal("150.00"),
        principal=Decimal("100.00"),
        interest=Decimal("50.00"),
        overdue=True,
        expected_date=date(2020, 1, 1),
    )
    ov2 = make_installment(
        credit["id"],
        expected_value=Decimal("150.00"),
        principal=Decimal("100.00"),
        interest=Decimal("50.00"),
        overdue=True,
        expected_date=date(2020, 2, 1),
    )
    result = await _process(credit, [ov1, ov2], Decimal("300.00"))

    snapshot = result["updated_credit_snapshot"]
    assert Decimal(str(snapshot["pending_capital"])) == Decimal("800.00")


async def test_multi_installment_applied_to_has_entry_per_installment():
    """
    GIVEN: 3 installments all overdue
    WHEN:  payment covers all 3
    THEN:  applied_to has entries for each installment id
    """
    credit = make_credit(pending=Decimal("900.00"))
    installments = [
        make_installment(
            credit["id"],
            expected_value=Decimal("100.00"),
            principal=Decimal("60.00"),
            interest=Decimal("40.00"),
            overdue=True,
            expected_date=date(2020, i, 1),
        )
        for i in [1, 2, 3]
    ]
    result = await _process(credit, installments, Decimal("300.00"))

    inst_ids_in_result = {e["installment_id"] for e in result["applied_to"]}
    for inst in installments:
        assert inst["id"] in inst_ids_in_result, f"Installment {inst['id']} not in applied_to"
