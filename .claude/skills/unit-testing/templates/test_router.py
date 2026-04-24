"""
Plantilla para tests de routers FastAPI usando AsyncClient.
Copia este archivo a backend/tests/routes/test_<feature>_router.py
"""
import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch, AsyncMock

# from app.main import app


class TestFeatureRouter:
    """Tests de integración para los endpoints del feature."""

    # ─── Happy Path ─────────────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_post_feature_returns_201(self):
        """POST /feature con datos válidos retorna 201 y el recurso creado."""
        # with patch("app.routes.feature_router.FeatureService") as MockService:
        #     mock_instance = MockService.return_value
        #     mock_instance.create = AsyncMock(return_value={"uid": "u1", "name": "Test"})
        #
        #     async with AsyncClient(
        #         transport=ASGITransport(app=app), base_url="http://test"
        #     ) as client:
        #         response = await client.post(
        #             "/feature",
        #             json={"name": "Test"},
        #             headers={"Authorization": "Bearer fake-token"},
        #         )
        #
        #     assert response.status_code == 201
        #     assert response.json()["uid"] == "u1"
        pass

    # ─── Error Path ─────────────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_post_feature_returns_401_without_token(self):
        """POST /feature sin Authorization header retorna 401 o 422."""
        # async with AsyncClient(
        #     transport=ASGITransport(app=app), base_url="http://test"
        # ) as client:
        #     response = await client.post("/feature", json={"name": "Test"})
        # assert response.status_code in (401, 422)
        pass

    @pytest.mark.asyncio
    async def test_get_feature_returns_404_when_not_found(self):
        """GET /feature/{uid} con uid inexistente retorna 404."""
        # with patch("app.routes.feature_router.FeatureService") as MockService:
        #     mock_instance = MockService.return_value
        #     mock_instance.get_by_uid = AsyncMock(side_effect=ValueError("Not found"))
        #
        #     async with AsyncClient(
        #         transport=ASGITransport(app=app), base_url="http://test"
        #     ) as client:
        #         response = await client.get("/feature/nonexistent")
        #
        #     assert response.status_code == 404
        pass
