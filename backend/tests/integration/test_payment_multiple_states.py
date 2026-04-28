"""
Integration Test: payment applied across overdue + future installments (3-pool algorithm).
Validates CF-3: strict order OVERDUE_INTEREST → OVERDUE_PRINCIPAL → FUTURE_PRINCIPAL.
"""
import pytest
from decimal import Decimal
from datetime import date, timedelta
from uuid import uuid4

from app.services.payment_service import _compute_breakdown_3pool

TODAY = date.today()
OVERDUE_DATE = (TODAY - timedelta(days=30)).isoformat()
FUTURE_DATE = (TODAY + timedelta(days=30)).isoformat()

INST_OVERDUE = str(uuid4())
INST_FUTURE = str(uuid4())


def _installments():
    return [
        {
            "id": INST_OVERDUE,
            "expected_date": OVERDUE_DATE,
            "expected_value": "600.00",
            "interest_portion": "100.00",
            "principal_portion": "500.00",
            "paid_value": "0.00",
            "status": "UPCOMING",
        },
        {
            "id": INST_FUTURE,
            "expected_date": FUTURE_DATE,
            "expected_value": "300.00",
            "interest_portion": "80.00",
            "principal_portion": "220.00",
            "paid_value": "0.00",
            "status": "UPCOMING",
        },
    ]


def test_payment_700_covers_overdue_then_future():
    """GIVEN overdue $600 + future $300 WHEN $700 payment THEN order: overdue_interest→overdue_principal→future."""
    # GIVEN
    installments = _installments()
    amount = Decimal("700.00")

    # WHEN
    applied, total_principal, remaining = _compute_breakdown_3pool(installments, amount, TODAY)

    # THEN — strict pool order respected
    types_in_order = [e.type for e in applied]
    interest_entries = [e for e in applied if e.type == "OVERDUE_INTEREST"]
    principal_entries = [e for e in applied if e.type == "OVERDUE_PRINCIPAL"]
    future_entries = [e for e in applied if e.type == "FUTURE_PRINCIPAL"]

    assert interest_entries, "OVERDUE_INTEREST must be applied first"
    assert sum(e.amount for e in interest_entries) == Decimal("100.00")
    assert sum(e.amount for e in principal_entries) == Decimal("500.00")
    future_applied = sum(e.amount for e in future_entries)
    assert future_applied == Decimal("100.00")  # 700 - 100(interest) - 500(principal) = 100 to future
    assert remaining == Decimal("0.00")


def test_payment_100_covers_only_overdue_interest():
    """GIVEN overdue installment WHEN $100 payment (= interest only) THEN only OVERDUE_INTEREST applied."""
    # GIVEN
    installments = _installments()
    amount = Decimal("100.00")

    # WHEN
    applied, total_principal, remaining = _compute_breakdown_3pool(installments, amount, TODAY)

    # THEN
    assert all(e.type == "OVERDUE_INTEREST" for e in applied)
    assert total_principal == Decimal("0.00")
    assert remaining == Decimal("0.00")


def test_payment_exact_overdue_no_future_touched():
    """GIVEN $600 overdue WHEN exact $600 payment THEN future installment untouched."""
    # GIVEN
    installments = _installments()
    amount = Decimal("600.00")

    # WHEN
    applied, total_principal, remaining = _compute_breakdown_3pool(installments, amount, TODAY)

    # THEN
    future_applied = [e for e in applied if e.installment_id == INST_FUTURE]
    assert not future_applied, "Future installment must not be touched when overdue exactly covered"
    assert remaining == Decimal("0.00")


def test_excess_payment_goes_to_future_principal():
    """GIVEN $1000 payment > total owed $900 THEN remaining goes to future principal, excess=100."""
    # GIVEN
    installments = _installments()
    amount = Decimal("1000.00")

    # WHEN
    applied, total_principal, remaining = _compute_breakdown_3pool(installments, amount, TODAY)

    # THEN — $100 excess beyond $900 total
    assert remaining == Decimal("100.00")


def test_partially_paid_overdue_correctly_offsets():
    """GIVEN overdue installment with $50 already paid WHEN $600 THEN only remaining $550 allocated to overdue."""
    # GIVEN
    installments = [
        {
            "id": INST_OVERDUE,
            "expected_date": OVERDUE_DATE,
            "expected_value": "600.00",
            "interest_portion": "100.00",
            "principal_portion": "500.00",
            "paid_value": "50.00",  # $50 already to interest
            "status": "PARTIALLY_PAID",
        },
    ]
    amount = Decimal("600.00")

    # WHEN
    applied, total_principal, remaining = _compute_breakdown_3pool(installments, amount, TODAY)

    # THEN — only $50 still owed on interest, $500 on principal
    interest_applied = sum(e.amount for e in applied if e.type == "OVERDUE_INTEREST")
    assert interest_applied == Decimal("50.00")
    assert remaining == Decimal("50.00")  # $600 - $50(int) - $500(principal) = $50 leftover
