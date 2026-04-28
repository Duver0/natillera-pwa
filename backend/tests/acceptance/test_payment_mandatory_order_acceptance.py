"""
Gherkin Acceptance Tests — Payment Mandatory Order (CF-3).
Spec scenario: $900 owed (interest $100, capital $500, future $300), payment $700
→ apply in strict order: OVERDUE_INTEREST → OVERDUE_PRINCIPAL → FUTURE_PRINCIPAL.
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


def _spec_installments():
    """Installments matching spec scenario: $600 overdue (int=100, principal=500) + $300 future."""
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


# ---------------------------------------------------------------------------
# Scenario 1: spec example — $700 on $900 owed
# ---------------------------------------------------------------------------

def test_payment_700_spec_scenario_mandatory_order():
    """
    GIVEN $900 owed (overdue: $100 interest + $500 capital, future $300)
    WHEN $700 payment
    THEN order: $100 OVERDUE_INTEREST → $500 OVERDUE_PRINCIPAL → $100 FUTURE_PRINCIPAL, remaining=0.
    """
    # GIVEN
    installments = _spec_installments()
    amount = Decimal("700.00")

    # WHEN
    applied, total_principal, remaining = _compute_breakdown_3pool(installments, amount, TODAY)

    # THEN
    interest_total = sum(e.amount for e in applied if e.type == "OVERDUE_INTEREST")
    principal_total = sum(e.amount for e in applied if e.type == "OVERDUE_PRINCIPAL")
    future_total = sum(e.amount for e in applied if e.type == "FUTURE_PRINCIPAL")

    assert interest_total == Decimal("100.00"), "Pool 1: overdue interest must be $100"
    assert principal_total == Decimal("500.00"), "Pool 2: overdue principal must be $500"
    assert future_total == Decimal("100.00"), "Pool 3: $100 remaining goes to future"
    assert remaining == Decimal("0.00")


# ---------------------------------------------------------------------------
# Scenario 2: interest-only payment, principal untouched
# ---------------------------------------------------------------------------

def test_payment_100_covers_only_interest_pool():
    """
    GIVEN $900 owed WHEN $100 payment
    THEN only OVERDUE_INTEREST applied, OVERDUE_PRINCIPAL and FUTURE untouched.
    """
    # GIVEN
    installments = _spec_installments()

    # WHEN
    applied, _, remaining = _compute_breakdown_3pool(installments, Decimal("100.00"), TODAY)

    # THEN
    assert all(e.type == "OVERDUE_INTEREST" for e in applied)
    assert sum(e.amount for e in applied) == Decimal("100.00")
    assert remaining == Decimal("0.00")


# ---------------------------------------------------------------------------
# Scenario 3: payment skips interest (already paid) → goes straight to principal
# ---------------------------------------------------------------------------

def test_payment_skips_paid_interest_goes_to_principal():
    """
    GIVEN overdue installment with $100 interest already paid
    WHEN $200 payment
    THEN no OVERDUE_INTEREST entry, $200 goes to OVERDUE_PRINCIPAL.
    """
    # GIVEN
    installments = [
        {
            "id": INST_OVERDUE,
            "expected_date": OVERDUE_DATE,
            "expected_value": "600.00",
            "interest_portion": "100.00",
            "principal_portion": "500.00",
            "paid_value": "100.00",  # interest already covered
            "status": "PARTIALLY_PAID",
        },
    ]

    # WHEN
    applied, total_principal, remaining = _compute_breakdown_3pool(
        installments, Decimal("200.00"), TODAY
    )

    # THEN
    interest_applied = sum(e.amount for e in applied if e.type == "OVERDUE_INTEREST")
    principal_applied = sum(e.amount for e in applied if e.type == "OVERDUE_PRINCIPAL")

    assert interest_applied == Decimal("0.00"), "Interest already paid — pool 1 must be empty"
    assert principal_applied == Decimal("200.00")
    assert remaining == Decimal("0.00")


# ---------------------------------------------------------------------------
# Scenario 4: full payment of all owed → mora clears
# ---------------------------------------------------------------------------

def test_full_payment_900_clears_all_pools():
    """
    GIVEN $900 owed WHEN $900 payment THEN all pools exhausted, remaining=0.
    """
    # GIVEN
    installments = _spec_installments()

    # WHEN
    applied, total_principal, remaining = _compute_breakdown_3pool(
        installments, Decimal("900.00"), TODAY
    )

    # THEN
    total_applied = sum(e.amount for e in applied)
    assert total_applied == Decimal("900.00")
    assert remaining == Decimal("0.00")


# ---------------------------------------------------------------------------
# Scenario 5: overpayment → excess beyond all pools
# ---------------------------------------------------------------------------

def test_overpayment_1000_generates_remaining():
    """
    GIVEN $900 owed WHEN $1000 payment THEN $100 remaining (excess beyond installments).
    """
    # GIVEN
    installments = _spec_installments()

    # WHEN
    applied, total_principal, remaining = _compute_breakdown_3pool(
        installments, Decimal("1000.00"), TODAY
    )

    # THEN
    assert remaining == Decimal("100.00")


# ---------------------------------------------------------------------------
# Scenario 6: multiple overdue installments — FIFO within each pool
# ---------------------------------------------------------------------------

def test_multiple_overdue_fifo_allocation():
    """
    GIVEN 2 overdue installments WHEN payment covers first overdue interest + some principal
    THEN FIFO: older installment interest consumed before newer.
    """
    # GIVEN
    older_date = (TODAY - timedelta(days=60)).isoformat()
    newer_date = (TODAY - timedelta(days=30)).isoformat()
    inst_older = str(uuid4())
    inst_newer = str(uuid4())

    installments = [
        {
            "id": inst_older,
            "expected_date": older_date,
            "expected_value": "200.00",
            "interest_portion": "100.00",
            "principal_portion": "100.00",
            "paid_value": "0.00",
            "status": "UPCOMING",
        },
        {
            "id": inst_newer,
            "expected_date": newer_date,
            "expected_value": "200.00",
            "interest_portion": "100.00",
            "principal_portion": "100.00",
            "paid_value": "0.00",
            "status": "UPCOMING",
        },
    ]
    amount = Decimal("150.00")

    # WHEN — $200 total interest; $150 payment covers first $100 interest + $50 interest of second
    applied, _, remaining = _compute_breakdown_3pool(installments, amount, TODAY)

    # THEN — OVERDUE_INTEREST entries exist, total = $150
    interest_applied = sum(e.amount for e in applied if e.type == "OVERDUE_INTEREST")
    assert interest_applied == Decimal("150.00")
    assert remaining == Decimal("0.00")
