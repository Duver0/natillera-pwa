"""
Unit tests for BaseService ownership enforcement.
SPEC-002 §2.5 — cross-user access must be rejected.
"""
import pytest
from fastapi import HTTPException
from app.services.base_service import BaseService


class ConcreteService(BaseService):
    pass


def test_assert_ownership_passes_for_correct_user():
    service = ConcreteService(db=None, user_id="user-abc")
    record = {"user_id": "user-abc", "id": "123"}
    # Should not raise
    service._assert_ownership(record, "entity")


def test_assert_ownership_raises_for_wrong_user():
    service = ConcreteService(db=None, user_id="user-abc")
    record = {"user_id": "user-xyz", "id": "123"}
    with pytest.raises(HTTPException) as exc_info:
        service._assert_ownership(record, "client")
    assert exc_info.value.status_code == 403
    assert "forbidden" in exc_info.value.detail


def test_assert_ownership_raises_for_none_record():
    service = ConcreteService(db=None, user_id="user-abc")
    with pytest.raises(HTTPException) as exc_info:
        service._assert_ownership(None, "credit")
    assert exc_info.value.status_code == 403


def test_raise_forbidden_always_returns_403():
    service = ConcreteService(db=None, user_id="user-abc")
    with pytest.raises(HTTPException) as exc_info:
        service._raise_forbidden("payment")
    assert exc_info.value.status_code == 403
    assert "payment" in exc_info.value.detail
