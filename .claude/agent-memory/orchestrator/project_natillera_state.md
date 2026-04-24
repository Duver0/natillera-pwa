---
name: natillera-pwa project state
description: Current implementation state of Natillera PWA — which phases completed, what was built, known blockers
type: project
---

Week 2 + gap fixes complete 2026-04-23.

**Why:** User requested ASDD full implementation from SPEC-001 v2.0 + SPEC-002 v1.0.

**What was built (Week 1):**
- database/migrations/001-003.sql — all tables, RLS policies, triggers
- backend/app/ — full FastAPI app: config, db, main, middleware, models, services, routes
- frontend/src/ — React 18 + RTK Query: types, store, hooks, pages (Login, Register, Dashboard, ClientDetail)
- backend/tests/ — pytest unit tests
- frontend/src/__tests__/ — vitest tests for authSlice, LoginPage, RegisterPage, ProtectedRoute
- Integration tests in tests/integration/ — 6 cases (need live Supabase)

**What was built (Week 2 — 2026-04-23):**
- G-01 CLOSED: frontend/public/manifest.json + vite.config.ts (VitePWA + Workbox)
- G-02 CLOSED: backend/tests/test_auth_endpoints.py (12 tests)
- G-03 DEFERRED: integration tests blocked on `supabase start`
- Backend: GET /credits/:id extended with 7 precomputed aggregate fields (calculations.py used)
- Backend: POST /api/v1/payments/preview — dry-run allocation endpoint
- Backend: GET /api/v1/clients/:id/summary — 5 aggregate fields
- Backend: credit creation generates 12-period installment schedule
- Frontend: ClientListPage (search + pagination), ClientFormPage (create/edit + zod), CreditFormPage (zod)
- Frontend: PaymentModal (2-step preview+confirm via /payments/preview)
- Frontend: ClientDetailPage updated — consumes precomputed fields, zero frontend math, PaymentModal wired
- Frontend: types.ts extended (MoraStatus, ClientSummary, PaymentPreview)
- Frontend: apiSlice extended (getClientSummary, previewPayment)
- Tests: 4 backend test files (19 tests), 4 frontend test files (20 tests)
- QA report: .github/qa/week-2-report.md

**Semana 2 — CLOSED 2026-04-24 (all agent-fixable items done):**
- `__import__("decimal").ROUND_HALF_UP` replaced with clean `from decimal import ROUND_HALF_UP` in credit_service.py
- Route `/clients` added to App.tsx → ClientListPage (was implemented but unreachable)
- DashboardPage: "View All" button added → navigates to /clients

**Semana 2 deuda técnica — CERRADA 2026-04-24:**
- Paginación server-side: `list_all` ahora acepta `limit/offset`, retorna `{items, total, limit, offset}`. Backend router expone `GET /clients?limit&offset&search`. Frontend `apiSlice.getClients` actualizado; `ClientListPage` usa `offset` server-side.
- AppLayout compartido creado en `frontend/src/components/AppLayout.tsx` — nav global (Dashboard, Clients) + header con logout. Aplicado a: DashboardPage, ClientListPage (via App.tsx), ClientDetailPage, ClientFormPage, CreditFormPage.
- Inline form de cliente eliminado de DashboardPage — "Add Client" redirige a `/clients/new`.
- Test edge case `paid > interest` agregado a `backend/tests/test_credits_aggregates.py` (via `preview_payment`).

**Residual blockers (require human action):**
- G-03: integration tests need `supabase start` from human
- Icon PNG assets (icon-192, icon-512) — need real PNG files for PWA installability
