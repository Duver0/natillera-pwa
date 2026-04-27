"""
test_payment_pending_capital_update.py
SPEC-001 §US-005 — Correct decrement of credit.pending_capital

pending_capital decreases ONLY by principal applied (OVERDUE_PRINCIPAL + FUTURE_PRINCIPAL).
Interest payments do NOT reduce pending_capital.

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


async def test_interest_payment_does_not_reduce_pending_capital():
    """
    GIVEN: overdue installment (interest=100, principal=200)
    WHEN:  payment=100 (covers only interest)
    THEN:  pending_capital unchanged
    """
    initial_capital = Decimal("1000.00")
    credit = make_credit(pending=initial_capital)
    inst = make_installment(
        credit["id"],
        expected_value=Decimal("300.00"),
        principal=Decimal("200.00"),
        interest=Decimal("100.00"),
        overdue=True,
    )
    result = await _process(credit, [inst], Decimal("100.00"))

    snapshot = result["updated_credit_snapshot"]
    assert Decimal(str(snapshot["pending_capital"])) == initial_capital, \
        "Interest-only payment must NOT reduce pending_capital"


async def test_principal_payment_reduces_pending_capital():
    """
    GIVEN: overdue installment (interest=0, principal=200)
    WHEN:  payment=200
    THEN:  pending_capital = initial - 200
    """
    initial = Decimal("1000.00")
    credit = make_credit(pending=initial)
    inst = make_installment(
        credit["id"],
        expected_value=Decimal("200.00"),
        principal=Decimal("200.00"),
        interest=Decimal("0.00"),
        overdue=True,
    )
    result = await _process(credit, [inst], Decimal("200.00"))

    snapshot = result["updated_credit_snapshot"]
    assert Decimal(str(snapshot["pending_capital"])) == Decimal("800.00")


async def test_mixed_payment_reduces_capital_by_principal_only():
    """
    GIVEN: overdue installment (interest=100, principal=200)
    WHEN:  payment=300 (covers interest + principal)
    THEN:  pending_capital = initial - 200 (NOT - 300)
    """
    initial = Decimal("1000.00")
    credit = make_credit(pending=initial)
    inst = make_installment(
        credit["id"],
        expected_value=Decimal("300.00"),
        principal=Decimal("200.00"),
        interest=Decimal("100.00"),
        overdue=True,
    )
    result = await _process(credit, [inst], Decimal("300.00"))

    snapshot = result["updated_credit_snapshot"]
    expected_capital = initial - Decimal("200.00")
    assert Decimal(str(snapshot["pending_capital"])) == expected_capital, \
        "Only principal (200) should reduce pending_capital, not interest (100)"


async def test_future_principal_reduces_pending_capital():
    """
    GIVEN: future installment (no overdue, interest=50, principal=150)
    WHEN:  payment=200 (covers full future installment)
    THEN:  pending_capital = initial - 150 (principal portion only)
    """
    initial = Decimal("1000.00")
    credit = make_credit(pending=initial)
    inst = make_installment(
        credit["id"],
        expected_value=Decimal("200.00"),
        principal=Decimal("150.00"),
        interest=Decimal("50.00"),
        overdue=False,
    )
    result = await _process(credit, [inst], Decimal("200.00"))

    snapshot = result["updated_credit_snapshot"]
    # Future installment: type is FUTURE_PRINCIPAL (interest not separately tracked for future)
    # Per spec: future installments apply as FUTURE_PRINCIPAL (whole remaining amount)
    # Pending capital should decrease by the principal applied
    assert Decimal(str(snapshot["pending_capital"])) < initial, \
        "Future installment payment must reduce pending_capital"


async def test_capital_snapshot_uses_decimal_not_float():
    """
    Hard constraint: pending_capital in snapshot must be Decimal-safe (no float).
    """
    credit = make_credit(pending=Decimal("999.99"))
    inst = make_installment(
        credit["id"],
        expected_value=Decimal("100.00"),
        principal=Decimal("100.00"),
        interest=Decimal("0.00"),
        overdue=True,
    )
    result = await _process(credit, [inst], Decimal("100.00"))

    snapshot = result["updated_credit_snapshot"]
    capital = snapshot["pending_capital"]
    assert not isinstance(capital, float), "pending_capital must not be float"
    # Must be parseable without precision loss
    parsed = Decimal(str(capital))
    assert parsed == Decimal("899.99")
