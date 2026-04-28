"""
Domain calculations — single source of truth.
Frontend MUST NOT duplicate any of these formulas.
"""
from decimal import Decimal, ROUND_HALF_UP

PERIODS_PER_YEAR: dict[str, int] = {
    "DAILY": 365,
    "WEEKLY": 52,
    "BIWEEKLY": 26,
    "MONTHLY": 12,
}

PERIOD_DAYS: dict[str, int] = {
    "DAILY": 1,
    "WEEKLY": 7,
    "BIWEEKLY": 14,
    "MONTHLY": 30,
}


def calculate_period_interest(
    pending_capital: Decimal,
    annual_rate: Decimal,
    periodicity: str,
) -> Decimal:
    """
    interest = pending_capital * (annual_rate / 100) / periods_per_year

    Example:
      pending_capital = 10000
      annual_rate = 12 (%)
      periodicity = MONTHLY (12 periods/year)
      result = 10000 * 0.12 / 12 = 100.00

    Returns Decimal rounded to 2 decimal places.
    Interest is NEVER compound (spec rule: no compounding).
    """
    if pending_capital <= Decimal(0):
        return Decimal("0.00")

    periods = Decimal(PERIODS_PER_YEAR.get(periodicity, 12))
    raw = pending_capital * (annual_rate / Decimal(100)) / periods
    return raw.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def calculate_principal_portion(
    pending_capital: Decimal,
    remaining_periods: int,
) -> Decimal:
    """
    principal = pending_capital / remaining_periods

    Rounded to 2 decimal places.
    """
    if remaining_periods <= 0:
        return pending_capital.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    raw = pending_capital / Decimal(remaining_periods)
    return raw.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def calculate_savings_interest(
    total_contributions: Decimal,
    savings_rate: Decimal,
) -> Decimal:
    """
    interest = total_contributions * (savings_rate / 100)

    Example: $1500 * 10% = $150.00
    """
    raw = total_contributions * (savings_rate / Decimal(100))
    return raw.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
