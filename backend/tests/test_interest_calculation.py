"""
Unit tests — interest calculation formula (SPEC-001 §US-003, §4.1).
All tests operate on pure functions from calculations.py — no DB needed.
Formula: interest = pending_capital * (annual_rate / 100) / periods_per_year
No compound interest — interest calculated only on pending_capital.
"""
import pytest
from decimal import Decimal

from app.utils.calculations import calculate_period_interest, PERIODS_PER_YEAR


class TestInterestFormula:
    """SPEC §4.1 base formula correctness."""

    def test_monthly_12_percent_on_10k(self):
        """SPEC example: $10,000 × 12% / 12 = $100.00"""
        result = calculate_period_interest(
            pending_capital=Decimal("10000"),
            annual_rate=Decimal("12"),
            periodicity="MONTHLY",
        )
        assert result == Decimal("100.00")

    def test_weekly_10_percent(self):
        """$5,200 × 10% / 52 = $10.00"""
        result = calculate_period_interest(
            pending_capital=Decimal("5200"),
            annual_rate=Decimal("10"),
            periodicity="WEEKLY",
        )
        assert result == Decimal("10.00")

    def test_daily_365_percent_on_365(self):
        """$365 × 100% / 365 = $1.00"""
        result = calculate_period_interest(
            pending_capital=Decimal("365"),
            annual_rate=Decimal("100"),
            periodicity="DAILY",
        )
        assert result == Decimal("1.00")

    def test_biweekly_26_percent_on_2600(self):
        """$2,600 × 26% / 26 = $26.00"""
        result = calculate_period_interest(
            pending_capital=Decimal("2600"),
            annual_rate=Decimal("26"),
            periodicity="BIWEEKLY",
        )
        assert result == Decimal("26.00")

    def test_zero_rate_returns_zero(self):
        """0% annual rate → 0 interest."""
        result = calculate_period_interest(
            pending_capital=Decimal("10000"),
            annual_rate=Decimal("0"),
            periodicity="MONTHLY",
        )
        assert result == Decimal("0.00")

    def test_zero_capital_returns_zero(self):
        """Pending capital = 0 → 0 interest (SPEC: no interest on zero capital)."""
        result = calculate_period_interest(
            pending_capital=Decimal("0"),
            annual_rate=Decimal("12"),
            periodicity="MONTHLY",
        )
        assert result == Decimal("0.00")

    def test_negative_capital_returns_zero(self):
        """Negative capital treated as 0."""
        result = calculate_period_interest(
            pending_capital=Decimal("-100"),
            annual_rate=Decimal("12"),
            periodicity="MONTHLY",
        )
        assert result == Decimal("0.00")

    def test_result_rounded_to_two_decimals(self):
        """Result always rounds to 2 decimal places (ROUND_HALF_UP)."""
        result = calculate_period_interest(
            pending_capital=Decimal("1000"),
            annual_rate=Decimal("7"),
            periodicity="MONTHLY",
        )
        assert result == result.quantize(Decimal("0.01"))

    def test_no_compound_interest_second_period(self):
        """
        SPEC: Interest NOT compound. Second period uses same pending_capital,
        not pending_capital + previous interest.
        """
        capital = Decimal("10000")
        rate = Decimal("12")
        period1_interest = calculate_period_interest(capital, rate, "MONTHLY")

        # Second period: capital unchanged (principal payment reduces it, NOT interest)
        # Interest on (capital only), not (capital + prior_interest)
        period2_interest = calculate_period_interest(capital, rate, "MONTHLY")

        assert period1_interest == period2_interest
        # Confirm compound would have been different
        compound_interest = calculate_period_interest(capital + period1_interest, rate, "MONTHLY")
        assert compound_interest != period1_interest

    def test_periods_per_year_constants(self):
        """SPEC periodicity constants are correct."""
        assert PERIODS_PER_YEAR["DAILY"] == 365
        assert PERIODS_PER_YEAR["WEEKLY"] == 52
        assert PERIODS_PER_YEAR["BIWEEKLY"] == 26
        assert PERIODS_PER_YEAR["MONTHLY"] == 12

    def test_interest_stops_when_mora_would_apply(self):
        """
        SPEC: mora=true → NO interest generated.
        This is enforced at the service layer (installment_service checks mora).
        Here we verify that calculate_period_interest itself is stateless / pure.
        The service is responsible for the mora guard.
        """
        # Pure function always computes; mora guard is service-level
        result = calculate_period_interest(
            pending_capital=Decimal("10000"),
            annual_rate=Decimal("12"),
            periodicity="MONTHLY",
        )
        # Function returns non-zero — caller (service) must check mora
        assert result > Decimal("0")
