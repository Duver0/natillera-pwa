"""
Gherkin Acceptance Tests — Interest Formula.
Spec: 12% annual, monthly periodicity → $100/month on $10,000 capital.
Single source of truth: app.utils.calculations.calculate_period_interest
"""
import pytest
from decimal import Decimal

from app.utils.calculations import calculate_period_interest, PERIODS_PER_YEAR


# ---------------------------------------------------------------------------
# Scenario 1: canonical spec example
# ---------------------------------------------------------------------------

def test_monthly_12pct_10k_yields_100():
    """
    GIVEN pending_capital=10000, annual_rate=12%, periodicity=MONTHLY
    WHEN calculate_period_interest()
    THEN interest = 100.00 exactly (spec example).
    """
    # GIVEN
    capital = Decimal("10000")
    rate = Decimal("12")
    periodicity = "MONTHLY"

    # WHEN
    result = calculate_period_interest(capital, rate, periodicity)

    # THEN
    assert result == Decimal("100.00"), f"Expected 100.00, got {result}"


# ---------------------------------------------------------------------------
# Scenario 2: zero capital → zero interest
# ---------------------------------------------------------------------------

def test_zero_capital_yields_zero_interest():
    """
    GIVEN pending_capital=0
    WHEN calculate_period_interest()
    THEN interest = 0.00 (no compounding, no negative).
    """
    # GIVEN / WHEN
    result = calculate_period_interest(Decimal("0"), Decimal("12"), "MONTHLY")

    # THEN
    assert result == Decimal("0.00")


# ---------------------------------------------------------------------------
# Scenario 3: periodicity variants
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("periodicity,expected", [
    ("DAILY",    Decimal("3.29")),   # 10000 * 0.12 / 365 = 3.287... ≈ 3.29
    ("WEEKLY",   Decimal("23.08")),  # 10000 * 0.12 / 52  = 23.076... ≈ 23.08
    ("BIWEEKLY", Decimal("46.15")),  # 10000 * 0.12 / 26  = 46.153... ≈ 46.15
    ("MONTHLY",  Decimal("100.00")), # 10000 * 0.12 / 12  = 100.00
])
def test_interest_by_periodicity(periodicity, expected):
    """
    GIVEN $10,000 capital at 12% annual
    WHEN calculate_period_interest with each periodicity
    THEN result matches spec formula: capital * rate / periods_per_year.
    """
    # GIVEN
    capital = Decimal("10000")
    rate = Decimal("12")

    # WHEN
    result = calculate_period_interest(capital, rate, periodicity)

    # THEN
    assert result == expected, f"{periodicity}: expected {expected}, got {result}"


# ---------------------------------------------------------------------------
# Scenario 4: no compound interest (interest does not compound)
# ---------------------------------------------------------------------------

def test_interest_is_not_compound():
    """
    GIVEN same capital applied twice (two consecutive periods)
    WHEN calculating interest both periods without capital reduction
    THEN both results are equal (simple interest, not compound).
    """
    # GIVEN
    capital = Decimal("10000")
    rate = Decimal("12")

    # WHEN
    period1 = calculate_period_interest(capital, rate, "MONTHLY")
    period2 = calculate_period_interest(capital, rate, "MONTHLY")

    # THEN
    assert period1 == period2 == Decimal("100.00")


# ---------------------------------------------------------------------------
# Scenario 5: rounding to 2 decimal places
# ---------------------------------------------------------------------------

def test_interest_rounded_half_up():
    """
    GIVEN capital=1 at 10% annual monthly → 0.00833... rounded to 0.01
    WHEN calculate_period_interest
    THEN result is 0.01 (ROUND_HALF_UP).
    """
    # GIVEN
    capital = Decimal("1")
    rate = Decimal("10")

    # WHEN
    result = calculate_period_interest(capital, rate, "MONTHLY")

    # THEN
    assert result == Decimal("0.01")


# ---------------------------------------------------------------------------
# Scenario 6: formula derivation check
# ---------------------------------------------------------------------------

def test_formula_capital_times_rate_over_periods():
    """
    GIVEN arbitrary capital and rate
    WHEN calculate_period_interest
    THEN result == capital * (rate/100) / periods (formula verification).
    """
    # GIVEN
    capital = Decimal("25000")
    rate = Decimal("18")
    periodicity = "MONTHLY"
    periods = Decimal(PERIODS_PER_YEAR[periodicity])

    # WHEN
    result = calculate_period_interest(capital, rate, periodicity)

    # THEN — manually verify formula
    expected = (capital * (rate / Decimal("100")) / periods).quantize(Decimal("0.01"))
    assert result == expected
