import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def mock_db():
    """Mock database for tests."""
    db = MagicMock()
    db.table = MagicMock(return_value=db)
    db.select = MagicMock(return_value=db)
    db.insert = MagicMock(return_value=db)
    db.update = MagicMock(return_value=db)
    db.eq = MagicMock(return_value=db)
    db.is_ = MagicMock(return_value=db)
    db.in_ = MagicMock(return_value=db)
    db.lt = MagicMock(return_value=db)
    db.single = MagicMock(return_value=db)
    db.order = MagicMock(return_value=db)
    db.execute = AsyncMock()
    return db


@pytest.fixture
def test_app(mock_db):
    """Create test app without lifespan (no DB init)."""
    from app.main import app
    from app.dependencies import get_user_id, get_db
    
    app.dependency_overrides[get_user_id] = lambda: "test-user-id"
    app.dependency_overrides[get_db] = lambda: mock_db
    yield app
    app.dependency_overrides.clear()
