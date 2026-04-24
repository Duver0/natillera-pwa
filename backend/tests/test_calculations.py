"""
Unit tests for domain calculation functions.
SPEC-001 §4.1 — Interest formula, savings formula.
These are pure functions: no DB, no mocks needed.
"""
import pytest
from decimal import Decimal
from app.utils.calculations import (
    calculate_period_interest,
    calculate_principal_portion,
    calculate_savings_interest,
)


class TestPeriodInterest:
    def test_monthly_12_percent_on_10000(self):
        # GIVEN pending_capital=10000, rate=12%, MONTHLY
        # THEN interest = 10000 * 0.12 / 12 = 100.00
        result = calculate_period_interest(Decimal("10000"), Decimal("12"), "MONTHLY")
        assert result == Decimal("100.00")

    def test_weekly_52_periods(self):
        # 10000 * 0.12 / 52 ≈ 23.08
        result = calculate_period_interest(Decimal("10000"), Decimal("12"), "WEEKLY")
        assert result == Decimal("23.08")

    def test_daily_365_periods(self):
        # 10000 * 0.12 / 365 ≈ 3.29
        result = calculate_period_interest(Decimal("10000"), Decimal("12"), "DAILY")
        assert result == Decimal("3.29")

    def test_biweekly_26_periods(self):
        # 10000 * 0.12 / 26 ≈ 46.15
        result = calculate_period_interest(Decimal("10000"), Decimal("12"), "BIWEEKLY")
        assert result == Decimal("46.15")

    def test_zero_pending_capital_returns_zero(self):
        # SPEC rule: no interest on zero capital
        result = calculate_period_interest(Decimal("0"), Decimal("12"), "MONTHLY")
        assert result == Decimal("0.00")

    def test_zero_interest_rate(self):
        # Interest-free credit
        result = calculate_period_interest(Decimal("5000"), Decimal("0"), "MONTHLY")
        assert result == Decimal("0.00")

    def test_interest_rounded_to_cents(self):
        # Ensures quantize(0.01) is applied
        result = calculate_period_interest(Decimal("7777.77"), Decimal("11"), "MONTHLY")
        # 7777.77 * 0.11 / 12 = 71.296... → 71.30
        assert result == Decimal("71.30")

    def test_no_compound_interest(self):
        # Interest is always calculated on pending_capital, not on prior interest
        interest_1 = calculate_period_interest(Decimal("10000"), Decimal("12"), "MONTHLY")
        interest_2 = calculate_period_interest(Decimal("10000"), Decimal("12"), "MONTHLY")
        # Same pending_capital → same interest (no compounding)
        assert interest_1 == interest_2


class TestPrincipalPortion:
    def test_divide_evenly(self):
        result = calculate_principal_portion(Decimal("1200"), 12)
        assert result == Decimal("100.00")

    def test_rounding_applied(self):
        result = calculate_principal_portion(Decimal("1000"), 3)
        # 1000 / 3 = 333.33...
        assert result == Decimal("333.33")

    def test_zero_remaining_periods_returns_full(self):
        result = calculate_principal_portion(Decimal("500"), 0)
        assert result == Decimal("500.00")


class TestSavingsInterest:
    def test_1500_at_10_percent(self):
        # SPEC: $1000+$500 = $1500, 10% → $150
        result = calculate_savings_interest(Decimal("1500"), Decimal("10"))
        assert result == Decimal("150.00")

    def test_zero_rate(self):
        result = calculate_savings_interest(Decimal("1000"), Decimal("0"))
        assert result == Decimal("0.00")

    def test_rounding(self):
        result = calculate_savings_interest(Decimal("333.33"), Decimal("10"))
        # 333.33 * 0.10 = 33.333 → 33.33
        assert result == Decimal("33.33")
