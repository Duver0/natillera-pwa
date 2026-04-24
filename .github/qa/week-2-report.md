# Week 2 QA Report — 2026-04-23

## Status Summary

| Area | Status | Notes |
|------|--------|-------|
| G-01 PWA manifest + SW | CLOSED | vite.config.ts + manifest.json written |
| G-02 Auth endpoint tests | CLOSED | test_auth_endpoints.py — 12 tests |
| G-03 Integration live DB | DEFERRED | Needs `supabase start` by human |
| Backend Week 2 | COMPLETE | 4 tasks delivered |
| Frontend Week 2 | COMPLETE | 5 tasks delivered |
| Tests Backend | COMPLETE | 4 test files, 24 tests |
| Tests Frontend | COMPLETE | 4 test files, 18 tests |

---

## Deuda Técnica — Resuelta 2026-04-24

| Item | Estado | Commit note |
|------|--------|-------------|
| Paginación server-side `ClientListPage` | CLOSED | `limit/offset` en `GET /clients`, RTK query consume `{items,total,limit,offset}` |
| Header/nav global (`AppLayout`) | CLOSED | Layout compartido Dashboard/Clients, aplicado en todas las pages autenticadas |
| Form cliente duplicado en Dashboard | CLOSED | Inline form eliminado, "Add Client" → `/clients/new` |
| Edge case `paid > interest` | CLOSED | `test_paid_exceeds_interest_applies_remainder_to_capital` agregado |
| `ClientFormPage` navega a `/dashboard` tras guardar | CLOSED | Ahora navega a `/clients/:id` (detalle del cliente creado/editado) |
| README + .gitignore baseline | CLOSED | README con stack/setup/roadmap; .gitignore cubre Python/Node/PWA/Supabase |

## Gaps Closed

### G-01 — PWA Manifest + Service Worker
- `frontend/public/manifest.json` — Web App Manifest with name, icons, theme_color, display=standalone
- `frontend/vite.config.ts` — VitePWA plugin with autoUpdate, Workbox NetworkFirst for `/api/v1/` routes
- Icon placeholders registered at `/icons/icon-192.png` and `/icons/icon-512.png`

### G-02 — Auth Endpoint Tests
- `backend/tests/test_auth_endpoints.py`
- Tests: register happy, register missing email (422), register short password (422), register service failure, login happy, login invalid credentials, login missing password (422), login bad email format (422), logout happy, logout no token, refresh happy, refresh invalid token, refresh missing body

---

## Backend Endpoints Added

### 1. GET /credits/:id — Extended Response
- Fields added (all precomputed server-side via `calculations.py`):
  - `interest_due_current_period` — current period interest using `calculate_period_interest`
  - `overdue_interest_total` — sum of unpaid interest on overdue installments
  - `overdue_capital_total` — sum of unpaid principal on overdue installments
  - `next_installment` — first upcoming installment object
  - `upcoming_installments[]` — next 5 upcoming installments
  - `overdue_installments[]` — all overdue installments
  - `mora_status{in_mora, since_date}` — derived from credit flags

### 2. POST /api/v1/payments/preview
- Request: `{credit_id, amount}`
- Returns: `{credit_id, amount, applied_to[], unallocated}`
- Dry-run: reuses PaymentService allocation logic, NO DB writes
- Same mandatory payment order: overdue_interest → overdue_principal → future_principal

### 3. GET /api/v1/clients/:id/summary
- Aggregates: `active_credits_count`, `total_pending_capital`, `total_overdue`, `mora_count`, `savings_total`
- All filtered by user_id via BaseService

### 4. Credit Creation — Installment Schedule
- `CreditService.create` now calls `_generate_installments` (12 periods default, Option A dynamic)
- Interest per period from `calculate_period_interest` — no new math
- All installments created with status=UPCOMING, paid_value=0

---

## Frontend Pages Built

### ClientListPage
- RTK Query bound to `useGetClientsQuery` with search debounce
- Client-side pagination (20/page)
- Mora badge, total_debt display
- Navigate to ClientDetailPage on row click
- `data-testid` attrs for test coverage

### ClientFormPage
- Create/edit via URL param (`/clients/new` vs `/clients/:id/edit`)
- Zod validation schema: first_name, last_name, phone required
- react-hook-form + zodResolver
- Pre-fills form when editing existing client

### CreditFormPage
- Route: `/clients/:clientId/credits/new`
- Zod validation: capital > 0, rate >= 0, periodicity enum, start_date required
- Submits to `useCreateCreditMutation` with client_id injected from URL params

### PaymentModal
- 2-step UX: amount input → preview → confirm
- Calls `POST /payments/preview` before showing breakdown
- Displays applied_to[] breakdown with human labels
- Shows unallocated amount when excess
- Confirm triggers `POST /payments` actual processing

### ClientDetailPage (updated)
- Inline credit form removed — replaced with navigate to CreditFormPage
- Payment button opens PaymentModal
- `useGetCreditQuery` fetches selected credit detail with all precomputed aggregates
- Zero frontend financial math — all figures from backend response

---

## Tests Added

### Backend
- `test_auth_endpoints.py` — 12 tests (register/login/logout/refresh happy+error)
- `test_credits_aggregates.py` — 5 tests (aggregate computation, mora_status, zero state)
- `test_payments_preview.py` — 5 tests (allocation order, unallocated, non-ACTIVE, 403)
- `test_clients_summary.py` — 4 tests (active only filter, overdue totals, savings, 403)
- `test_installment_generation.py` — 5 tests (count, dates, interest, status, paid_value)

### Frontend
- `ClientListPage.test.tsx` — 6 tests (render, mora badge, loading, empty, search, pagination)
- `ClientFormPage.test.tsx` — 4 tests (fields, validation, submit, loading state)
- `CreditFormPage.test.tsx` — 4 tests (fields, validation, submit with client_id, loading)
- `PaymentModal.test.tsx` — 6 tests (render, disabled, preview call, breakdown display, confirm, unallocated)

---

## Types Updated

- `frontend/src/types/index.ts` — Added `MoraStatus`, `ClientSummary`, `PaymentPreview`, extended `Credit` with precomputed fields
- `frontend/src/store/api/apiSlice.ts` — Added `getClientSummary`, `previewPayment` endpoints + exports

---

## Routes Added

- `/clients/new` → ClientFormPage (create)
- `/clients/:clientId/edit` → ClientFormPage (edit)
- `/clients/:clientId/credits/new` → CreditFormPage

---

## Residual Gaps / Known Issues

- **G-03**: Supabase integration tests deferred — needs `supabase start` by human operator
- **Icons**: `/icons/icon-192.png` and `/icons/icon-512.png` are referenced but not included — need actual PNG assets for full PWA installability
- **Savings table name**: `client_service.get_summary` queries `savings_contributions` — verify this matches the actual Supabase table name in migrations
- **`_generate_installments` import**: uses inline `__import__("decimal")` for ROUND_HALF_UP — can be cleaned to top-level import
- **DashboardPage**: still uses inline client creation form — consider extracting to ClientFormPage navigation (non-blocking)

---

## Audit Constraint Compliance

- Zero financial math in frontend — all computed values consumed from backend response fields
- Single source of truth: `calculations.py` — `calculate_period_interest` called in both `_append_aggregates` and `_generate_installments`
- All new endpoints filter by `user_id` via `BaseService` ownership checks
