"""
Contract test fixtures — crea TestClient sin lifespan de DB real, con JWT válido.
"""
import pytest
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
from fastapi.testclient import TestClient
from app.main import app, set_test_mode
from app.dependencies import get_user_id, get_db

from tests.helpers.jwt_helpers import generate_rsa_key_pair, make_valid_token, public_key_to_jwk, TEST_KID


TEST_USER_ID = "user-test-uuid-1234"


def create_mock_db():
    """Crea mock de DB para testing."""
    db = MagicMock()
    db.table = MagicMock(return_value=db)
    db.select = MagicMock(return_value=db)
    db.insert = MagicMock(return_value=db)
    db.update = MagicMock(return_value=db)
    db.eq = MagicMock(return_value=db)
    db.in_ = MagicMock(return_value=db)
    db.single = MagicMock(return_value=db)
    db.order = MagicMock(return_value=db)
    db.lt = MagicMock(return_value=db)
    db.rpc = MagicMock(return_value=db)
    db.execute = AsyncMock()
    return db


class AuthenticatedClient(TestClient):
    """TestClient que automáticamente añade JWT válido."""
    
    def __init__(self, *args, **kwargs):
        private_key, _ = generate_rsa_key_pair()
        self._token = make_valid_token(private_key, TEST_USER_ID)
        super().__init__(*args, **kwargs)
    
    def _gen_auth_header(self):
        return {"Authorization": f"Bearer {self._token}"}


@pytest.fixture(autouse=True)
def contract_test_setup(monkeypatch):
    """Setup: activa modo test + mock DB + JWT válido."""
    set_test_mode(True)
    mock_db_instance = create_mock_db()
    
    private_key, public_key = generate_rsa_key_pair()
    test_jwk = public_key_to_jwk(public_key, TEST_KID)
    
    import app.middleware.auth as auth_module
    monkeypatch.setattr(auth_module, '_jwks_cache', {"keys": [test_jwk]})
    monkeypatch.setattr(auth_module, '_jwks_expiry', None)
    monkeypatch.setattr(auth_module, 'SUPABASE_URL', "https://test.supabase.co")
    
    app.dependency_overrides[get_db] = lambda: mock_db_instance
    app.dependency_overrides[get_user_id] = lambda: TEST_USER_ID
    
    yield mock_db_instance
    
    app.dependency_overrides.clear()
    set_test_mode(False)


def create_mock_db():
    """Crea mock de DB para testing."""
    db = MagicMock()
    db.table = MagicMock(return_value=db)
    db.select = MagicMock(return_value=db)
    db.insert = MagicMock(return_value=db)
    db.update = MagicMock(return_value=db)
    db.eq = MagicMock(return_value=db)
    db.in_ = MagicMock(return_value=db)
    db.single = MagicMock(return_value=db)
    db.order = MagicMock(return_value=db)
    db.lt = MagicMock(return_value=db)
    db.rpc = MagicMock(return_value=db)
    db.execute = AsyncMock()
    return db


@pytest.fixture
def mock_db():
    return create_mock_db()


@pytest.fixture
def user_id():
    return "test-user-001"


@pytest.fixture
def client_with_auth(mock_db, user_id):
    app.dependency_overrides[get_user_id] = lambda: user_id
    app.dependency_overrides[get_db] = lambda: mock_db
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c, mock_db
    app.dependency_overrides.clear()


@pytest.fixture
def credit_id():
    return str(uuid4())


@pytest.fixture
def mock_rpc_success(credit_id):
    return MagicMock(data={
        "payment_id": str(uuid4()),
        "credit_id": credit_id,
        "total_amount": "500.00",
        "applied_to": [
            {"installment_id": str(uuid4()), "type": "OVERDUE_INTEREST", "amount": "100.00"}
        ],
        "updated_credit_snapshot": {
            "pending_capital": "9500.00",
            "mora": False,
            "version": 2,
        },
        "idempotent": False,
    })