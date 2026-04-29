"""Fake repositories for testing."""
from tests.helpers.fakes.fake_db import FakeDatabase, create_fake_db_with_credit, create_fake_db_with_installments
from tests.helpers.fakes.fake_credit_repo import FakeCreditRepository, create_fake_credit

__all__ = [
    "FakeDatabase",
    "create_fake_db_with_credit",
    "create_fake_db_with_installments",
    "FakeCreditRepository",
    "create_fake_credit",
]