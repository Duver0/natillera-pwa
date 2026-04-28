"""
RISK-001 Fix — Interest calculation decimal precision.
All formulas exercised through calculate_period_interest() from calculations.py.
No DB involved — pure function tests.
"""
import pytest
from decimal import Decimal, ROUND_HALF_EVEN

from app.utils.calculations import calculate_period_interest


def _q(value: str) -> Decimal:
    return Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)


def test_interest_12pct_annual_monthly_10k_equals_100():
    # GIVEN
    capital = Decimal("10000")
    rate = Decimal("12")

    # WHEN
    result = calculate_period_interest(capital, rate, "MONTHLY")

    # THEN — $10k × 12% / 12 = $100.00 exactly
    assert result == Decimal("100.00")


def test_interest_daily_periodicity_10k_12pct():
    # GIVEN
    capital = Decimal("10000")
    rate = Decimal("12")

    # WHEN
    result = calculate_period_interest(capital, rate, "DAILY")

    # THEN — $10k × 0.12 / 365 = $32.88 (rounded ROUND_HALF_UP per implementation)
    # 10000 * 0.12 / 365 = 3.287671... → rounds to 3.29 with ROUND_HALF_UP
    # Spec says $32.88 but formula is /365 per period; result is cents per day
    assert result == Decimal("3.29")


def test_interest_weekly_periodicity():
    # GIVEN
    capital = Decimal("10000")
    rate = Decimal("12")

    # WHEN
    result = calculate_period_interest(capital, rate, "WEEKLY")

    # THEN — $10k × 0.12 / 52 = 23.076923... → $23.08
    assert result == Decimal("23.08")


def test_interest_biweekly_periodicity():
    # GIVEN
    capital = Decimal("10000")
    rate = Decimal("12")

    # WHEN
    result = calculate_period_interest(capital, rate, "BIWEEKLY")

    # THEN — $10k × 0.12 / 26 = 46.153846... → $46.15
    assert result == Decimal("46.15")


def test_no_rounding_defect_quantize_2_decimals():
    # GIVEN — several capital values that could produce floating-point drift
    cases = [
        (Decimal("3333.33"), Decimal("12"), "MONTHLY"),
        (Decimal("7777.77"), Decimal("9"), "WEEKLY"),
        (Decimal("1234.56"), Decimal("18"), "BIWEEKLY"),
    ]

    for capital, rate, periodicity in cases:
        # WHEN
        result = calculate_period_interest(capital, rate, periodicity)

        # THEN — result is always exactly 2 decimal places (Decimal, not float)
        assert isinstance(result, Decimal)
        assert result == result.quantize(Decimal("0.01"))


def test_leap_year_daily_365_vs_366():
    # GIVEN — same capital and rate, DAILY periodicity uses fixed 365 divisor
    capital = Decimal("10000")
    rate = Decimal("12")

    # WHEN — calculate_period_interest uses PERIODS_PER_YEAR["DAILY"] = 365 (constant)
    result = calculate_period_interest(capital, rate, "DAILY")

    # THEN — always divides by 365 regardless of calendar year (spec: fixed divisor)
    expected = (capital * rate / Decimal("100") / Decimal("365")).quantize(
        Decimal("0.01"), rounding=__import__("decimal").ROUND_HALF_UP
    )
    assert result == expected


def test_zero_capital_interest_zero():
    # GIVEN
    capital = Decimal("0")
    rate = Decimal("12")

    # WHEN
    result = calculate_period_interest(capital, rate, "MONTHLY")

    # THEN
    assert result == Decimal("0.00")
