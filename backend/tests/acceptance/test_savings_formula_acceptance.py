"""
Gherkin Acceptance Tests — Savings Formula.
Spec scenario: $1000 + $500 contributions, 10% rate → interest $150, delivered $1650.
Single source of truth: app.utils.calculations.calculate_savings_interest
"""
import pytest
from decimal import Decimal

from app.utils.calculations import calculate_savings_interest


# ---------------------------------------------------------------------------
# Scenario 1: canonical spec example
# ---------------------------------------------------------------------------

def test_savings_1500_at_10pct_yields_150_interest():
    """
    GIVEN total_contributions=1500 ($1000 + $500), savings_rate=10%
    WHEN calculate_savings_interest()
    THEN interest = 150.00 (spec example).
    """
    # GIVEN
    contributions = Decimal("1500")
    rate = Decimal("10")

    # WHEN
    interest = calculate_savings_interest(contributions, rate)

    # THEN
    assert interest == Decimal("150.00"), f"Expected 150.00, got {interest}"


def test_savings_total_delivered_equals_contributions_plus_interest():
    """
    GIVEN $1000 + $500 at 10%
    WHEN liquidation computed
    THEN total_delivered = 1500 + 150 = 1650.
    """
    # GIVEN
    contributions = Decimal("1500")
    rate = Decimal("10")

    # WHEN
    interest = calculate_savings_interest(contributions, rate)
    total_delivered = contributions + interest

    # THEN
    assert total_delivered == Decimal("1650.00")


# ---------------------------------------------------------------------------
# Scenario 2: zero contributions
# ---------------------------------------------------------------------------

def test_savings_zero_contributions_yields_zero_interest():
    """
    GIVEN total_contributions=0
    WHEN calculate_savings_interest()
    THEN interest = 0.00.
    """
    # GIVEN / WHEN
    result = calculate_savings_interest(Decimal("0"), Decimal("10"))

    # THEN
    assert result == Decimal("0.00")


# ---------------------------------------------------------------------------
# Scenario 3: formula verification
# ---------------------------------------------------------------------------

def test_savings_formula_contributions_times_rate():
    """
    GIVEN contributions=C, rate=R
    WHEN calculate_savings_interest
    THEN result == C * (R/100) rounded to 2 decimals.
    """
    # GIVEN
    contributions = Decimal("3750")
    rate = Decimal("8")

    # WHEN
    result = calculate_savings_interest(contributions, rate)

    # THEN — 3750 * 0.08 = 300.00
    assert result == Decimal("300.00")


# ---------------------------------------------------------------------------
# Scenario 4: rounding behavior
# ---------------------------------------------------------------------------

def test_savings_interest_rounded_to_2_decimals():
    """
    GIVEN contributions=1 at 3% → 0.03 exactly
    WHEN calculate_savings_interest
    THEN result has 2 decimal places.
    """
    # GIVEN
    result = calculate_savings_interest(Decimal("1"), Decimal("3"))

    # THEN
    assert result == Decimal("0.03")
    assert len(str(result).split(".")[-1]) <= 2


# ---------------------------------------------------------------------------
# Scenario 5: multiple contributions aggregated
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("contributions,rate,expected_interest,expected_total", [
    (Decimal("1000"),  Decimal("10"), Decimal("100.00"),  Decimal("1100.00")),
    (Decimal("2500"),  Decimal("5"),  Decimal("125.00"),  Decimal("2625.00")),
    (Decimal("10000"), Decimal("15"), Decimal("1500.00"), Decimal("11500.00")),
    (Decimal("1500"),  Decimal("10"), Decimal("150.00"),  Decimal("1650.00")),  # spec
])
def test_savings_parametric_scenarios(contributions, rate, expected_interest, expected_total):
    """
    GIVEN various contribution+rate combinations
    WHEN calculate_savings_interest
    THEN interest and total match expected (spec formula verified).
    """
    # GIVEN / WHEN
    interest = calculate_savings_interest(contributions, rate)
    total = contributions + interest

    # THEN
    assert interest == expected_interest, f"Interest mismatch: {interest} != {expected_interest}"
    assert total == expected_total, f"Total mismatch: {total} != {expected_total}"


# ---------------------------------------------------------------------------
# Scenario 6: rate boundary — 0% rate
# ---------------------------------------------------------------------------

def test_savings_zero_rate_yields_no_interest():
    """
    GIVEN savings_rate=0%
    WHEN calculate_savings_interest
    THEN interest = 0.00 (no yield).
    """
    # GIVEN / WHEN
    result = calculate_savings_interest(Decimal("5000"), Decimal("0"))

    # THEN
    assert result == Decimal("0.00")
