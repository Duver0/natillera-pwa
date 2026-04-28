---
name: Natillera PWA — Fase 3 Backend Tests
description: Contexto de la suite de tests generada en Fase 3 para SPEC-001 (2026-04-27)
type: project
---

Suite generada en backend/tests/ bajo tres carpetas:
- integration/ — E2E flow, mora lifecycle, 3-pool states, cascade delete, history immutability
- contract/ — API contract tests usando TestClient + dependency_overrides (sin Supabase real)
- acceptance/ — Gherkin: fórmula de interés, orden obligatorio de pagos, fórmula de ahorros

**Why:** Phase 3 deliverable de SPEC-001; cobertura ≥80% en lógica de negocio.
**How to apply:** Al extender tests futuros respetar los tres sub-paquetes y los patrones de mock_db() ya establecidos.

Stack: pytest + pytest-anyio, TestClient de FastAPI, unittest.mock (AsyncMock/MagicMock).
Auth en contract tests: app.dependency_overrides[get_user_id] = lambda: USER_ID.
DB mock: cadena fluente MagicMock con execute=AsyncMock().
