"""
test_payment_mandatory_order.py
SPEC-001 §US-005 — Payment mandatory order: OVERDUE_INTEREST → OVERDUE_PRINCIPAL → FUTURE_PRINCIPAL

Contract: payment-contract.md §3 Allocation Algorithm

RED PHASE: These tests verify the NEW structured response contract.
The current payment_service returns a raw dict from DB insert.
These tests FAIL until PaymentService is refactored to return PaymentResponse.
"""
import pytest
from decimal import Decimal
from unittest.mock import AsyncMock, patch
from datetime import date

from tests.conftest_payment import make_credit, make_installment, build_db_mock, PAST, FUTURE


pytestmark = pytest.mark.asyncio


async def _process(credit, installments, amount: Decimal, post_overdue=None):
    from app.services.payment_service import PaymentService
    from app.models.payment_model import PaymentRequest

    db = build_db_mock(credit, installments, post_payment_overdue=post_overdue or [])
    service = PaymentService(db, "user-1")
    req = PaymentRequest(
        credit_id=credit["id"],
        amount=amount,
        operator_id="user-1",
    )
    return await service.process_payment(req)


async def test_mandatory_order_only_overdue_interest_consumed():
    """
    GIVEN: 1 overdue installment (interest=200, principal=500)
    WHEN:  payment = 100 (less than interest)
    THEN:  applied_to contains only OVERDUE_INTEREST entry, amount=100
           OVERDUE_PRINCIPAL not present
    """
    credit = make_credit(pending=Decimal("1000.00"))
    inst = make_installment(
        credit["id"],
        expected_value=Decimal("700.00"),
        principal=Decimal("500.00"),
        interest=Decimal("200.00"),
        overdue=True,
    )
    result = await _process(credit, [inst], Decimal("100.00"))

    # Contract: result must have payment_id, applied_to list, updated_credit_snapshot
    assert "payment_id" in result
    applied = result["applied_to"]
    types = [e["type"] for e in applied]

    assert "OVERDUE_INTEREST" in types, "Must consume overdue interest first"
    assert "OVERDUE_PRINCIPAL" not in types, "Must NOT touch principal before interest cleared"
    assert "FUTURE_PRINCIPAL" not in types

    interest_total = sum(Decimal(str(e["amount"])) for e in applied if e["type"] == "OVERDUE_INTEREST")
    assert interest_total == Decimal("100.00")


async def test_mandatory_order_interest_then_principal():
    """
    GIVEN: 1 overdue installment (interest=200, principal=500)
    WHEN:  payment = 700 (exact)
    THEN:  200 → OVERDUE_INTEREST, 500 → OVERDUE_PRINCIPAL
    """
    credit = make_credit(pending=Decimal("1000.00"))
    inst = make_installment(
        credit["id"],
        expected_value=Decimal("700.00"),
        principal=Decimal("500.00"),
        interest=Decimal("200.00"),
        overdue=True,
    )
    result = await _process(credit, [inst], Decimal("700.00"))

    applied = result["applied_to"]
    interest_total = sum(Decimal(str(e["amount"])) for e in applied if e["type"] == "OVERDUE_INTEREST")
    principal_total = sum(Decimal(str(e["amount"])) for e in applied if e["type"] == "OVERDUE_PRINCIPAL")

    assert interest_total == Decimal("200.00")
    assert principal_total == Decimal("500.00")


async def test_mandatory_order_overdue_before_future():
    """
    GIVEN: 1 overdue installment (200) + 1 future installment (200)
    WHEN:  payment = 200
    THEN:  all goes to overdue, zero to future
    """
    credit = make_credit(pending=Decimal("1000.00"))
    overdue_inst = make_installment(
        credit["id"],
        expected_value=Decimal("200.00"),
        principal=Decimal("100.00"),
        interest=Decimal("100.00"),
        overdue=True,
    )
    future_inst = make_installment(
        credit["id"],
        expected_value=Decimal("200.00"),
        principal=Decimal("100.00"),
        interest=Decimal("100.00"),
        overdue=False,
    )
    result = await _process(credit, [overdue_inst, future_inst], Decimal("200.00"))

    applied = result["applied_to"]
    future_applied = sum(Decimal(str(e["amount"])) for e in applied if e["type"] == "FUTURE_PRINCIPAL")
    overdue_applied = sum(
        Decimal(str(e["amount"])) for e in applied
        if e["type"] in ("OVERDUE_INTEREST", "OVERDUE_PRINCIPAL")
    )

    assert overdue_applied == Decimal("200.00"), "Overdue must be fully cleared before future"
    assert future_applied == Decimal("0.00"), "Future must not receive any payment while overdue exists"


async def test_mandatory_order_response_has_required_fields():
    """
    Contract: POST /payments must return payment_id, total_amount, applied_to, updated_credit_snapshot
    """
    credit = make_credit(pending=Decimal("500.00"))
    inst = make_installment(credit["id"], overdue=True)
    result = await _process(credit, [inst], Decimal("50.00"))

    assert "payment_id" in result, "Response must contain payment_id"
    assert "total_amount" in result, "Response must contain total_amount"
    assert "applied_to" in result, "Response must contain applied_to"
    assert "updated_credit_snapshot" in result, "Response must contain updated_credit_snapshot"

    snapshot = result["updated_credit_snapshot"]
    assert "pending_capital" in snapshot
    assert "mora" in snapshot
    assert "version" in snapshot


async def test_mandatory_order_applied_to_has_installment_id():
    """
    Contract: each applied_to entry must include installment_id (per payment-contract.md §1)
    """
    credit = make_credit(pending=Decimal("500.00"))
    inst = make_installment(
        credit["id"],
        expected_value=Decimal("200.00"),
        principal=Decimal("100.00"),
        interest=Decimal("100.00"),
        overdue=True,
    )
    result = await _process(credit, [inst], Decimal("100.00"))

    for entry in result["applied_to"]:
        assert "installment_id" in entry, "Each applied_to entry must have installment_id"
        assert entry["installment_id"] == inst["id"]


async def test_mandatory_order_amounts_are_decimal_not_float():
    """
    Hard constraint: all monetary amounts must be Decimal or Decimal-serializable strings.
    No float allowed in applied_to entries.
    """
    credit = make_credit(pending=Decimal("1000.00"))
    inst = make_installment(
        credit["id"],
        expected_value=Decimal("200.00"),
        principal=Decimal("100.00"),
        interest=Decimal("100.00"),
        overdue=True,
    )
    result = await _process(credit, [inst], Decimal("100.00"))

    for entry in result["applied_to"]:
        amount = entry["amount"]
        # Must be Decimal or string that can be parsed to Decimal without precision loss
        assert not isinstance(amount, float), f"Float detected in applied_to entry: {amount!r}"
        # Must be parseable as Decimal
        Decimal(str(amount))

    total = result["total_amount"]
    assert not isinstance(total, float), f"Float detected in total_amount: {total!r}"
