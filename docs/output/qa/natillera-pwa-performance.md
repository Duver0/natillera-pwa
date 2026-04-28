# Natillera PWA — Performance Baseline
# SPEC-001 v2.2 | QA Lead | 2026-04-27
# Trigger: SLAs defined in spec §3.3 Performance Tests

---

## SLA Targets (from SPEC-001 §3.3)

| Operation | Target | Priority |
|-----------|--------|----------|
| GET /clients (1000 records) | < 500ms P95 | High |
| GET /credits/{id}/installments (100 records) | < 300ms P95 | High |
| POST /payments (atomic transaction) | < 1s P95 | Critical |
| Frontend initial load | < 2s on simulated 3G | Medium |
| List scroll (1000 records) | 60fps sustained | Low |

---

## Backend SLAs

### SLA-01 — GET /clients (1000 records) < 500ms P95

**Baseline Conditions**
- 1000 active client records in Supabase PostgreSQL
- No deleted_at filter applied (worst case: full scan with index)
- Single authenticated user (MVP scope)
- Query must use `idx_clients_deleted` and `idx_clients_phone`

**Validation Method**
- Tool: `pytest` + `httpx` async timing OR `k6` script with 10 VUs
- Sample: 50 requests, measure P50 / P95 / P99
- Pass: P95 < 500ms

**Risks**
- No `LIMIT` clause on current endpoint spec → full table scan possible
- Supabase free tier connection pool: 10 concurrent connections max. At 10 VUs, pooling contention expected.
- Mitigation: add `LIMIT 100 OFFSET n` pagination. Confirmed index exists: `idx_clients_deleted`.

**Infrastructure Gap Note**
- Test environment: Supabase free tier (shared compute).
- Production: capacity not specified. Results in test env expected to be 2–3x slower than production due to shared resources.

---

### SLA-02 — GET /credits/{id}/installments (100 records) < 300ms P95

**Baseline Conditions**
- 100 installments per credit (long-running daily credit scenario)
- Filter by `credit_id` uses `idx_installments_credit`
- Optional filter by `status` or `is_overdue`

**Validation Method**
- Pre-seed DB with 100 installments per test credit
- 30 sequential requests, measure P95
- Pass: P95 < 300ms

**Risks**
- Query includes mora recalculation on `GET /credits/{id}` (writes to DB on read-path if mora changed).
- Concurrent mora-recalc writes under load can cause lock contention.
- Mitigation: batch mora update at end of request, not per-installment.

---

### SLA-03 — POST /payments (atomic transaction) < 1s P95

**Baseline Conditions**
- Credit with 5 mixed overdue + upcoming installments
- Payment triggers SQL RPC `process_payment_atomic` (single transaction)
- RPC reads installments, applies 3-pool allocation, updates credit + installments + inserts payment + history in one txn

**Validation Method**
- 20 sequential payment requests (no concurrency, to avoid version conflicts)
- Measure wall-clock from request sent to 201 received
- Pass: P95 < 1000ms

**Risks**
- SQL RPC includes history insert inside transaction — adds latency.
- Supabase free tier: cold-start latency on first call can be 500–800ms.
- Mitigation: warm-up request before load run. History insert is low-cost (single row).

**Concurrency Note**
- Under concurrent load, version conflicts (409) inflate latency metrics. Measure 409s separately. SLA applies to successful 201 responses only.

---

## Frontend SLAs

### SLA-04 — Initial Load < 2s on Simulated 3G

**Tool**: Lighthouse CLI or Chrome DevTools Network throttle (3G: 1.6 Mbps down / 750 Kbps up / 150ms RTT)

**Metrics to Capture**
- First Contentful Paint (FCP)
- Largest Contentful Paint (LCP)
- Time to Interactive (TTI)
- Bundle size (JS + CSS)

**Current State**
- Service worker + manifest: NOT implemented (Phase 8 open — confirmed blocker in task list)
- Without service worker: no offline fallback, no asset caching, LCP depends on API response
- Vite + React 18 bundle: not measured yet

**Pass Criteria**
- LCP < 2s on 3G
- JS bundle < 300KB (gzipped)
- Lighthouse Performance score >= 85

**Risks**
- Redux Toolkit + RTK Query adds ~30KB gzipped
- No code-splitting confirmed — all routes may load on initial render
- Service worker absent → no cache-first for assets → every cold load hits network

**Mitigation**
- Implement lazy loading per route (`React.lazy + Suspense`)
- Implement service worker (Workbox via vite-plugin-pwa) before Lighthouse run
- Target: LCP < 1.5s (buffer for variance)

---

### SLA-05 — List Scroll 60fps (1000 records)

**Tool**: Chrome DevTools Performance tab, frame rate monitor

**Baseline**: ClientList or InstallmentView rendering 1000 rows without virtualization

**Pass Criteria**
- Scroll FPS >= 55fps sustained over 3 seconds of continuous scroll
- No layout thrash (no forced reflow on scroll)

**Risks**
- No virtual scroll implemented (Phase 7 open)
- 1000 DOM nodes will cause paint and layout bottleneck on mobile

**Mitigation**
- Implement pagination at 50 records/page before measuring
- If pagination deferred: add `react-window` or `@tanstack/virtual` for list virtualization

---

## Performance Test Execution Checklist

| # | Test | Tool | Status |
|---|------|------|--------|
| 1 | GET /clients (1000 records) | httpx / k6 | NOT RUN |
| 2 | GET /credits/:id/installments | httpx timing | NOT RUN |
| 3 | POST /payments atomic | httpx sequential | NOT RUN |
| 4 | Frontend Lighthouse (Performance) | Lighthouse CLI | NOT RUN |
| 5 | Frontend Lighthouse (Accessibility) | Lighthouse CLI | NOT RUN |
| 6 | Frontend Lighthouse (Best Practices) | Lighthouse CLI | NOT RUN |
| 7 | List scroll FPS | Chrome DevTools | NOT RUN |

**Blocker before performance run**: Service worker + manifest must be implemented (currently NOT DONE, confirmed in spec task list). Without it, Lighthouse scores are not representative of final PWA.
