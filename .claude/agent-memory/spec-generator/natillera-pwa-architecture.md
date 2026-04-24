---
name: Natillera PWA Financial Design
description: Architecture, core business rules, and tech stack for personal loans + savings PWA
type: project
---

## Financial Domain Rules (Non-negotiable)

**Why:** These are core to loan accounting correctness. Any violation risks client disputes and audit failures.

**How to apply:** All features, services, migrations must validate against these rules before merge.

- **Interest always on pending_capital only**: No compound interest, no interest on prior interest or overdue debt. Formula: `interest = pending_capital * (annual_rate / periods_per_year)`
- **Payment mandatory order**: 1. Overdue interest 2. Overdue capital 3. Future capital. No discretion.
- **State separation**: `pending_capital`, `generated_interest`, `overdue_debt` must never overlap/mix
- **Mora = informational flag**: No penalties, no extra interest. Purely visual (date > expected_date AND unpaid)
- **Partial payment = overdue_debt**: Remainder immediately moves to overdue_debt. NO schedule recalc. NO installment modification.
- **Cascade delete**: Delete client → all credits, savings, history removed. Relational integrity required.

## Tech Stack

**Backend:** FastAPI (async) + Motor (MongoDB async driver) per backend.md rules. Alternate: Supabase PostgreSQL if relational integrity critical.

**Frontend:** React 18 + TypeScript + Redux Toolkit + RTK Query + Supabase client. Vite + Tailwind + Workbox (PWA).

**Persistence:** Supabase PostgreSQL (free tier, ACID transactions, realtime subscriptions, relational FK enforcement). Firebase Firestore as fallback (more denormalization, eventual consistency).

**Auth:** Firebase Admin SDK (stateless token verification on backend) + optional Supabase auth overlay on frontend.

## Folder Structure Summary

```
backend/ → FastAPI + Motor (repositories, services, routes, models per backend.md)
frontend/ → React + Redux + RTK Query (pages, components, store, hooks, types)
.github/specs/ → Spec files (natillera-pwa.spec.md = SPEC-001)
.github/workflows/ → CI/CD (pytest backend, vite frontend, deploy)
```

## Implementation Phases

1. **Phase 1** (Week 1): Client CRUD + foundation (FastAPI, Motor, Pydantic models)
2. **Phase 2** (Week 2-3): Credit module + interest calc + installment generation
3. **Phase 3** (Week 3-4): Payment processing with mandatory order + atomicity
4. **Phase 4** (Week 4-5): Savings liquidation + audit history
5. **Phase 5** (Week 5-6): Integration tests, PWA optimization, docker, deploy

## Critical Test Scenarios

- Interest NOT compound (verify period 2 calc)
- Payment mandatory order (overdue interest → capital → future, no skipping)
- Mora detection (date > expected_date AND unpaid = mora true)
- Cascade delete (delete client → verify credits/savings/history gone)
- Partial payment (remainder → overdue_debt, no schedule recalc)

## Ambiguities Resolved

1. **Credit closure**: Auto when `pending_capital = 0 AND overdue_debt = 0`
2. **Interest accrual timing**: On period START (before installment date)
3. **Savings rate**: Global config, per-liquidation snapshot
4. **Payment on multiple installments**: FIFO (first unpaid by expected_date)
5. **Decimal precision**: Always 2 decimals, quantize("0.01")

## Known Risks

- Interest calculation errors (High) → unit tests + accountant audit
- Payment order not applied (High) → atomic transactions + contract tests
- Mora status stale (Medium) → recalc on read + hourly cron
- Concurrent payments (Medium) → optimistic locking or row-level locks
- PWA offline data conflicts (Medium) → sync queue + optimistic UI

## Out of Scope (MVP)

- Document upload, bulk import, SMS/email, i18n, analytics dashboards, 2FA
