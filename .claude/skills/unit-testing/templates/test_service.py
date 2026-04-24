"""
Plantilla para tests de servicios FastAPI.
Copia este archivo a backend/tests/services/test_<feature>_service.py
"""
import pytest
from unittest.mock import AsyncMock, MagicMock

# from app.services.feature_service import FeatureService


class TestFeatureService:
    """Tests para FeatureService."""

    def setup_method(self):
        """Fixture por método: crea un mock del repositorio antes de cada test."""
        self.mock_repo = MagicMock()

    # ─── Happy Path ─────────────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_create_feature_success(self):
        """Crear un feature con datos válidos retorna el documento creado."""
        self.mock_repo.create = AsyncMock(return_value={
            "uid": "user-123",
            "name": "Test Feature",
        })
        # service = FeatureService(self.mock_repo)
        # result = await service.create({"uid": "user-123", "name": "Test Feature"})
        # assert result["uid"] == "user-123"
        # assert result["name"] == "Test Feature"
        # self.mock_repo.create.assert_called_once()

    # ─── Error Path ─────────────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_create_feature_raises_on_db_error(self):
        """Si el repositorio lanza excepción, el servicio la propaga."""
        self.mock_repo.create = AsyncMock(side_effect=RuntimeError("DB error"))
        # service = FeatureService(self.mock_repo)
        # with pytest.raises(RuntimeError, match="DB error"):
        #     await service.create({"uid": "user-123", "name": "Test"})

    # ─── Edge Cases ─────────────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_get_feature_returns_none_when_not_found(self):
        """Buscar un uid inexistente retorna None o lanza ValueError."""
        self.mock_repo.find_by_uid = AsyncMock(return_value=None)
        # service = FeatureService(self.mock_repo)
        # with pytest.raises(ValueError):
        #     await service.get_by_uid("nonexistent-uid")
