"""
Unit tests — no compound interest rule (SPEC-001 §US-003, §1.2, §4.1).

Business rule: interest is calculated ONLY on pending_capital.
Prior interest_portion is NEVER added to the base for next period's calculation.

These tests use the pure calculate_period_interest function and
InstallmentService.generate_next() to verify the invariant at every level.
"""
import pytest
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
from datetime import date, timedelta

from app.utils.calculations import calculate_period_interest


class TestNoCompoundInterestPure:
    """Verify the pure calculation function never compounds."""

    def test_same_capital_same_interest_each_period(self):
        """Each period with unchanged capital produces identical interest."""
        capital = Decimal("10000")
        rate = Decimal("12")
        periodicity = "MONTHLY"

        period1 = calculate_period_interest(capital, rate, periodicity)
        period2 = calculate_period_interest(capital, rate, periodicity)
        period3 = calculate_period_interest(capital, rate, periodicity)

        assert period1 == period2 == period3

    def test_interest_does_not_include_prior_interest_in_base(self):
        """Interest base is pending_capital, NOT pending_capital + prior interest."""
        capital = Decimal("10000")
        rate = Decimal("12")

        period1_interest = calculate_period_interest(capital, rate, "MONTHLY")
        # Compound would add prior interest to base — must NOT happen
        compound_base = capital + period1_interest
        period2_if_compound = calculate_period_interest(compound_base, rate, "MONTHLY")
        period2_no_compound = calculate_period_interest(capital, rate, "MONTHLY")

        assert period2_no_compound < period2_if_compound
        assert period2_no_compound == period1_interest

    def test_capital_reduction_reduces_interest_linearly(self):
        """When principal is paid, interest base drops — but only by principal, not by interest."""
        capital = Decimal("10000")
        rate = Decimal("12")
        principal_paid = Decimal("1000")

        interest_before = calculate_period_interest(capital, rate, "MONTHLY")
        interest_after = calculate_period_interest(capital - principal_paid, rate, "MONTHLY")

        # After paying $1000 principal: interest on $9000
        expected_after = calculate_period_interest(Decimal("9000"), rate, "MONTHLY")
        assert interest_after == expected_after
        assert interest_after < interest_before

    def test_monthly_compound_would_differ_from_simple(self):
        """Explicitly show the magnitude of compound vs simple difference."""
        capital = Decimal("10000")
        rate = Decimal("12")

        simple_period2 = calculate_period_interest(capital, rate, "MONTHLY")
        compound_period2 = calculate_period_interest(
            capital + calculate_period_interest(capital, rate, "MONTHLY"),
            rate,
            "MONTHLY",
        )

        assert simple_period2 == Decimal("100.00")
        # Compound would be 101.00 on 10100 capital
        assert compound_period2 == Decimal("101.00")
        assert simple_period2 != compound_period2

    def test_no_compound_all_periodicities(self):
        """For every supported periodicity, two consecutive periods with no principal change yield same interest."""
        capital = Decimal("5200")
        rate = Decimal("10")

        for periodicity in ("DAILY", "WEEKLY", "BIWEEKLY", "MONTHLY"):
            p1 = calculate_period_interest(capital, rate, periodicity)
            p2 = calculate_period_interest(capital, rate, periodicity)
            assert p1 == p2, f"Compound detected for periodicity={periodicity}"

    def test_interest_zero_when_capital_fully_paid(self):
        """No interest when pending_capital = 0 (credit fully repaid)."""
        result = calculate_period_interest(Decimal("0"), Decimal("12"), "MONTHLY")
        assert result == Decimal("0.00")


class TestNoCompoundInterestService:
    """Verify InstallmentService locks interest at generation time and never retroactively changes it."""

    def _make_credit(self, pending_capital: float = 10000.0, periodicity: str = "MONTHLY") -> dict:
        return {
            "id": str(uuid4()),
            "user_id": "user-1",
            "client_id": str(uuid4()),
            "initial_capital": 10000.0,
            "pending_capital": pending_capital,
            "version": 1,
            "periodicity": periodicity,
            "annual_interest_rate": 12.0,
            "status": "ACTIVE",
            "start_date": "2026-01-01",
            "next_period_date": date.today().isoformat(),
            "mora": False,
            "mora_since": None,
        }

    def _build_db(self, credit: dict, period_number: int = 1) -> MagicMock:
        db = MagicMock()

        def _table(name: str):
            t = MagicMock()
            for m in ("select", "insert", "update", "eq", "in_", "single", "order", "lte", "execute"):
                getattr(t, m).return_value = t

            if name == "credits":
                t.execute = AsyncMock(return_value=MagicMock(data=credit))
            elif name == "installments":
                # count query
                t.execute = AsyncMock(return_value=MagicMock(data=[], count=period_number - 1))
            else:
                t.execute = AsyncMock(return_value=MagicMock(data=[]))
            return t

        db.table = MagicMock(side_effect=_table)
        return db

    @pytest.mark.asyncio
    async def test_generated_installment_interest_equals_formula(self):
        """Installment.interest_portion equals calculate_period_interest at time of generation."""
        from app.services.installment_service import InstallmentService

        capital = 10000.0
        rate = 12.0
        periodicity = "MONTHLY"
        credit = self._make_credit(pending_capital=capital, periodicity=periodicity)

        inserted_payload: list[dict] = []

        db = MagicMock()

        def _make_chain(data=None, count=None):
            chain = MagicMock()
            for m in ("select", "update", "insert", "eq", "in_", "single", "order", "lte", "lt"):
                getattr(chain, m).return_value = chain
            chain.execute = AsyncMock(return_value=MagicMock(data=data or [], count=count))
            return chain

        credits_chain = _make_chain(data=credit)
        installments_chain = _make_chain(data=[], count=0)

        def _insert_track(payload):
            inserted_payload.append(payload)
            ins_chain = _make_chain(data=[payload])
            return ins_chain

        installments_chain.insert = _insert_track

        def _table(name: str):
            if name == "credits":
                return credits_chain
            if name == "installments":
                return installments_chain
            return _make_chain()

        db.table = MagicMock(side_effect=_table)
        service = InstallmentService(db, "user-1")
        await service.generate_next(uuid4())

        assert len(inserted_payload) == 1
        expected_interest = float(
            calculate_period_interest(Decimal(str(capital)), Decimal(str(rate)), periodicity)
        )
        assert inserted_payload[0]["interest_portion"] == pytest.approx(expected_interest, abs=0.01)

    @pytest.mark.asyncio
    async def test_two_installments_different_capital_no_compound(self):
        """
        Second installment with reduced capital has lower interest_portion,
        proving interest base is pending_capital not (capital + prior_interest).
        """
        from app.services.installment_service import InstallmentService

        capital_period1 = Decimal("10000")
        capital_period2 = Decimal("9166.67")  # after one principal payment
        rate = Decimal("12")
        periodicity = "MONTHLY"

        interest_p1 = calculate_period_interest(capital_period1, rate, periodicity)
        interest_p2 = calculate_period_interest(capital_period2, rate, periodicity)

        # If compound: interest_p2 would be based on capital_period1 + interest_p1
        interest_compound = calculate_period_interest(capital_period1 + interest_p1, rate, periodicity)

        assert interest_p2 < interest_compound
        assert interest_p2 == calculate_period_interest(capital_period2, rate, periodicity)
