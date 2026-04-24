"""
Plantilla para tests de repositorios con MongoDB mockeado.
Copia este archivo a backend/tests/repositories/test_<feature>_repository.py
"""
import pytest
from unittest.mock import AsyncMock, MagicMock

# from app.repositories.feature_repository import FeatureRepository


class TestFeatureRepository:
    """Tests para FeatureRepository (MongoDB mockeado con Motor async)."""

    def setup_method(self):
        """Crea un mock de la colección MongoDB antes de cada test."""
        self.mock_collection = MagicMock()
        self.mock_db = {"features": self.mock_collection}
        # self.repo = FeatureRepository(self.mock_db)

    # ─── Happy Path ─────────────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_create_inserts_document_and_returns_data(self):
        """create() inserta el documento y retorna los datos con _id."""
        mock_result = MagicMock()
        mock_result.inserted_id = "inserted-id-123"
        self.mock_collection.insert_one = AsyncMock(return_value=mock_result)

        # result = await self.repo.create({"uid": "u1", "name": "Test"})
        # assert result["uid"] == "u1"
        # assert "_id" in result
        # self.mock_collection.insert_one.assert_called_once()

    @pytest.mark.asyncio
    async def test_find_by_uid_returns_document(self):
        """find_by_uid() retorna el documento si existe."""
        self.mock_collection.find_one = AsyncMock(
            return_value={"uid": "u1", "name": "Test"}
        )
        # result = await self.repo.find_by_uid("u1")
        # assert result["uid"] == "u1"
        # self.mock_collection.find_one.assert_called_once_with({"uid": "u1"})

    # ─── Error Path ─────────────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_find_by_uid_returns_none_when_not_found(self):
        """find_by_uid() retorna None si el documento no existe."""
        self.mock_collection.find_one = AsyncMock(return_value=None)
        # result = await self.repo.find_by_uid("nonexistent")
        # assert result is None

    # ─── Edge Cases ─────────────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_delete_by_uid_returns_false_when_not_found(self):
        """delete_by_uid() retorna False si el documento no existe."""
        mock_result = MagicMock()
        mock_result.deleted_count = 0
        self.mock_collection.delete_one = AsyncMock(return_value=mock_result)
        # result = await self.repo.delete_by_uid("nonexistent")
        # assert result is False
