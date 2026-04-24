# Week 2 Gate — Stabilization Checklist

Date: 2026-04-23
Status: GATE IN PROGRESS — live DB items blocked on human operator

---

## Checklist

### PWA Installability

- [x] `manifest.json` present — name, short_name, theme_color (#2563eb), background_color (#f9fafb), display=standalone, start_url=/ — VERIFIED
- [x] `vite.config.ts` — VitePWA plugin configured, icon refs match manifest, Workbox NetworkFirst on `/api/v1/` — VERIFIED
- [ ] Icon files present — `frontend/public/icons/icon-192.png` + `icon-512.png` — PENDING-HUMAN (run `python scripts/generate-icons.py`)
- [ ] `npm run build` clean — no icon-missing warnings — PENDING-HUMAN (blocked on icon generation)

### Schema Consistency (grep vs migration — offline verifiable)

- [x] `savings_contributions` mismatch FIXED — `client_service.py` line 98 changed from `savings_contributions` to `savings` (matches migration 001)
- [x] `savings_service.py` uses `savings` — CORRECT
- [x] `savings_liquidations` — used in `savings_service.py` + defined in migration 001 — ALIGNED
- [x] `financial_history` — used in payment/savings/credit services + defined in migration 001 — ALIGNED
- [x] `clients`, `credits`, `installments`, `payments` — all service references match migration 001 table names — VERIFIED by grep

### Endpoint Health (unit test coverage)

- [x] `GET /clients/:id/summary` — 4 unit tests, mock DB, no 500 in normal flow — VERIFIED
- [x] `POST /payments/preview` — 5 unit tests, mock DB — VERIFIED
- [x] `GET /credits/:id` — 5 unit tests, aggregate computation — VERIFIED
- [x] Auth endpoints — 12 unit tests (register/login/logout/refresh) — VERIFIED
- [x] No endpoint intentionally returns 500 in normal flow — reviewed services, exceptions are HTTPException (403/422/400)

### RLS (requires live DB)

- [ ] User B cannot SELECT/UPDATE/DELETE User A's data — integration tests written (`test_rls.py`) — PENDING-HUMAN (needs `supabase start`)
- [ ] INSERT with foreign user_id rejected by WITH CHECK policy — test written — PENDING-HUMAN
- [ ] Multiple users verified in isolation — PENDING-HUMAN

### Payment Atomicity (requires live DB)

- [ ] Payment allocation order enforced: overdue_interest → overdue_principal → future_principal — integration tests written (`test_full_lifecycle.py`) — PENDING-HUMAN
- [ ] Optimistic lock (version field) prevents double-apply — logic present in `payment_service.py`, DB-level test PENDING-HUMAN
- [ ] Credit auto-closes when pending_capital reaches 0 — logic verified in `payment_service.py`, DB state test PENDING-HUMAN

### Integration Tests Passing (requires live DB)

- [ ] `test_rls.py` — 5 tests (RLS isolation + insert rejection) — NOT RUN
- [ ] `test_triggers.py` — 7 tests (installment immutability + history append-only) — NOT RUN
- [ ] `test_full_lifecycle.py` — 12 tests (lifecycle, payment, mora, cascade, savings) — NOT RUN
- [ ] All tests marked PENDING-HUMAN pending `supabase start` (see `docs/runbooks/supabase-local-bringup.md`)

---

## Summary: What is verifiable offline vs pending live run

| Check | State | Blocker |
|-------|-------|---------|
| manifest.json valid | DONE | — |
| vite-plugin-pwa config valid | DONE | — |
| Icon files generated | PENDING-HUMAN | `python scripts/generate-icons.py` |
| `npm run build` clean | PENDING-HUMAN | Icon files needed |
| Schema: `savings_contributions` → `savings` fix | DONE | — |
| Schema: all other tables aligned | DONE | — |
| Endpoint unit tests (no 500 normal flow) | DONE | — |
| RLS multi-user isolation | PENDING-HUMAN | `supabase start` |
| Payment atomicity | PENDING-HUMAN | `supabase start` |
| Full integration suite passing | PENDING-HUMAN | `supabase start` |

---

## Residual Risks (explicit)

1. **Icon files not committed** — `scripts/generate-icons.py` must be run by a human with Python available. Until icons exist, `npm run build` may warn and PWA installability criteria is not met by a browser.
2. **Live Supabase never validated** — RLS, triggers, and atomicity are only covered by unit tests with mocks. A DB-level bug could exist that mocks would not catch.
3. **`payment_service.py` optimistic lock gap** — if `eq("version", credit["version"])` update matches 0 rows (concurrent write), the service does not detect it and silently proceeds. No version-conflict error is raised. This is a data integrity risk in high-concurrency scenarios.
4. **No migration 003** — trigger for `installment immutability` and `financial_history append-only` referenced in `test_triggers.py` must exist in DB schema. If those triggers are not in a migration file, `test_triggers.py` will fail on a fresh DB.

---

## Human Actions Required to Close Gate

```
1. python scripts/generate-icons.py
2. cd frontend && npm run build  (confirm clean)
3. supabase start
4. psql $DATABASE_URL -f database/migrations/001_initial_schema.sql
5. psql $DATABASE_URL -f database/migrations/002_rls_policies.sql
6. pytest tests/integration/ -v | tee .github/qa/live-validation-output.txt
7. Mark all PENDING-HUMAN items above as DONE or file new issues
```
