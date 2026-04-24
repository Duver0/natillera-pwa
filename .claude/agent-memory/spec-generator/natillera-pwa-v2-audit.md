---
name: Natillera PWA Spec v2.0 Audit & Refactor
description: Critical audit findings from v1.0 (redundancies, race conditions, contradictions) and refactoring decisions applied in v2.0
type: project
---

## Critical Problems Found in v1.0

### A. Domain Contradictions

1. **Interest Accrual During Mora (UNRESOLVED)**
   - v1.0 stated: "No new interest accrued if mora = true"
   - But also conflated overdue_debt with mora state
   - **Resolution**: mora = true → NO new installments generated, NO interest accrued (explicit rule added to v2.0)

2. **Duplicate Interest Tracking (CRITICAL)**
   - Credit.generated_interest (credit-level accumulator)
   - Installment.interest_portion (per-installment breakdown)
   - Same info, two places → sync nightmare
   - **Resolution**: DELETE Credit.generated_interest entirely. Interest single source = installments only.

3. **Opaque Overdue Debt (CRITICAL)**
   - Defined as "unpaid principal + interest" but treated as single aggregate field
   - Payment mandatory order says "overdue interest → overdue capital" but can't split opaque aggregate
   - **Resolution**: Convert to derived calculation from per-installment status. No Credit.overdue_debt field.

4. **Interest Timing Ambiguous**
   - "On period start" vs "before expected_date" — same thing? when exactly?
   - **Resolution**: Interest included in installment at period boundary (before expected_date is the boundary itself)

5. **Mora Flag Staleness**
   - No mechanism to keep mora fresh after payments
   - Risk: client pays, mora still true in UI
   - **Resolution**: Mora recalculated on EVERY credit.get() call (zero-staleness design)

6. **Architecture Contradiction**
   - v1.0 section 2.2: Full FastAPI backend architecture
   - v1.0 section 2.5: "No backend required for client-side ops"
   - **Resolution**: Explicit choice made = FastAPI + Supabase. Backend handles ALL business logic. Frontend presentation-only.

### B. Redundancies & Calculable State

1. **Credit.total_debt, Client.mora_count**
   - Both entirely derivable from credit queries
   - v1.0 persisted them
   - **Resolution**: Marked as DERIVED in v2.0. OK for cache/denormalization but not source-of-truth.

2. **Installment.status as proxy for overdue**
   - v1.0 had installment.status = OVERDUE
   - But mora = true is credit-level flag that's separate
   - **Resolution**: status = [UPCOMING, PARTIALLY_PAID, PAID, SUSPENDED]. Separate is_overdue boolean (expected_date < today check).

### C. Implementation Risks

1. **Race Condition on Concurrent Payments**
   - Two payments simultaneous on same credit → both read stale pending_capital
   - v1.0 mentioned risk but no solution
   - **Resolution**: Added Credit.version field. Optimistic locking with retry logic.

2. **Atomicity Not Explicit**
   - v1.0 said "atomic transaction" but didn't define transaction boundaries in code
   - **Resolution**: v2.0 section 4.2 explicitly shows `async with db.begin() as tx:` pattern. All-or-nothing.

3. **Interest Compounding Loophole**
   - If interest paid as capital, does next period's interest compound on it?
   - **Resolution**: Explicit: Interest calculated ONLY on pending_capital. Prior interest never becomes new principal.

4. **Installment Variability Undefined**
   - Once created, does installment.expected_value change if pending_capital changes?
   - v1.0 said "NO schedule recalc" but didn't specify installment is LOCKED
   - **Resolution**: LOCKED. Once created, expected_value, principal_portion, interest_portion immutable forever.

### D. Undefined Decisions Resolved

1. **Credit Closure Criteria** → Auto-close when pending_capital = 0 AND all installments paid
2. **Interest Accrual Timing** → Before expected_date (at period boundary)
3. **Savings Rate** → Global env var, snapshot in liquidation record
4. **Multiple Simultaneous Payments** → FIFO by expected_date, strict mandatory order
5. **Interest During Mora** → STOPS (mora = true → no interest)
6. **Installment Variability** → FIXED (immutable after creation)
7. **Concurrent Payment Safety** → Optimistic locking via version field

---

## Refactoring Decisions Applied

### Decision Set 1: Single Source of Truth for Interest

**Chosen**: Delete Credit.generated_interest. All interest in Installment.interest_portion.

**Why**: Eliminates redundancy. Interest tracked once per-installment. Derivable: total_interest = SUM(installments.interest_portion).

**Implementation**:
```
DELETE Credit.generated_interest
KEEP Installment.interest_portion (locked at creation)
DERIVE pending_interest = SUM(interest_portion WHERE status != PAID)
```

---

### Decision Set 2: Structured Overdue Tracking

**Chosen**: Delete opaque Credit.overdue_debt. Replace with structured per-installment tracking.

**Why**: Payment mandatory order requires splitting interest vs principal. Impossible with aggregate field.

**Implementation**:
```
DELETE Credit.overdue_debt
ADD Installment.is_overdue boolean (true if expected_date < today AND status != PAID)
DERIVE overdue_interest = SUM(interest_portion WHERE is_overdue)
DERIVE overdue_principal = SUM(principal_portion WHERE is_overdue)
DERIVE future_capital = pending_capital - overdue_principal
```

---

### Decision Set 3: Interest Accrual — Fixed Installments

**Chosen**: Installment.expected_value LOCKED at creation. Never changes.

**Why**: Spec says "NO schedule recalculation". Locking prevents retroactive changes. Clean design.

**Formula**:
```
interest_amount = pending_capital_at_creation * (annual_rate/100) / periods_per_year
principal_amount = pending_capital_at_creation / remaining_periods
expected_value = principal_amount + interest_amount (LOCKED)
```

---

### Decision Set 4: Mora Status — Derived, Recalculated on Every Read

**Chosen**: Keep Credit.mora boolean BUT recalculate on every credit.get().

**Why**: UI needs fast boolean check. But MUST be fresh. No cron job needed; simple query + update.

**Implementation**:
```python
async def get_credit(credit_id):
    credit = await repo.get_by_id(credit_id)
    overdue = await find_unpaid_overdue_installments(credit_id)
    mora_fresh = bool(overdue)
    if mora_fresh != credit.mora:
        credit.mora = mora_fresh
        await repo.update(credit)
    return credit
```

---

### Decision Set 5: Payment Application Flow — Per-Installment

**Chosen**: Mandatory order applied per-installment, not aggregates.

**Logic**:
```
For each unpaid installment (sorted by expected_date ASC):
  1. Apply overdue interest first (if expected_date < today)
  2. Apply overdue principal next
  3. Apply future principal (upcoming installments)
  Update installment.paid_value, installment.status, installment.is_overdue
  Reduce credit.pending_capital by total principal applied
  Recalculate credit.mora
Atomically: all updates or rollback
```

---

### Decision Set 6: Interest During Mora — Stops

**Chosen**: mora = true → interest_generation stops.

**Why**: Standard practice. Protects client; debt doesn't grow during mora.

**Implementation**:
```python
async def should_generate_installment(credit):
    mora = await calculate_mora_status(credit.id)
    return not mora  # Only generate if NOT in mora
```

---

### Decision Set 7: Concurrent Payment Handling — Optimistic Locking

**Chosen**: Version field on Credit. Retry on conflict.

**Why**: Simpler than pessimistic row locks. Prevents race conditions. 409 response to client.

**Implementation**:
```python
# On UPDATE credit:
UPDATE credits SET ... WHERE id=X AND version=<old_version>
# If rows=0 (version mismatch), return 409 CONFLICT → client retries
# On success, increment version
```

---

### Decision Set 8: Architecture — FastAPI + Supabase

**Chosen**: FastAPI backend + Supabase PostgreSQL. NO Supabase-only option.

**Why**:
- Backend rules mandate FastAPI + async
- Financial system needs server-side business logic (not frontend logic)
- Supabase for DB (ACID, relational integrity, realtime subscriptions)
- Clean separation: backend enforces rules, frontend cannot bypass

**Deleted**:
- MongoDB option (v1.0 section 2.3)
- "No backend required" claim (v1.0 section 2.5)
- Architecture diagram choice between mongo/postgres

---

## Schema Changes Summary

### Tables Refactored

**Credit**:
- ADDED: `version: int` (optimistic locking)
- DELETED: `generated_interest` (now derived from installments)
- MODIFIED: mora now recalc on read, not cached

**Installment**:
- ADDED: `is_overdue: boolean` (expected_date < today check)
- MODIFIED: all values (expected_value, principal_portion, interest_portion) marked IMMUTABLE via documentation + constraints

**Payment**:
- ADDED: explicit `applied_to` JSONB array with breakdown (overdue_interest, overdue_principal, future_principal)

**FinancialHistory**:
- No change, but now more critical (payment breakdown logged here)

---

## Testing Strategy Changes

v1.0 focused on unit tests in isolation. v2.0 requires:

1. **Mora Staleness Tests**: Verify mora recalculated on every get_credit() call
2. **Installment Immutability Tests**: Verify no UPDATE to installment values after creation
3. **Optimistic Locking Tests**: Concurrent updates → version conflict → 409 retry
4. **Payment Breakdown Tests**: Verify applied_to breakdown matches mandatory order exactly
5. **Interest Stops in Mora Tests**: Verify no installment generated when mora=true

---

## Backward Compatibility

v1.0 spec is INCOMPATIBLE with v2.0. All v1.0 implementations must be rewritten:

1. Remove generated_interest from Credit model
2. Remove opaque overdue_debt
3. Add version field to Credit
4. Add is_overdue to Installment
5. Refactor payment service to apply per-installment, not aggregates
6. Recalculate mora on every credit.get()

**Recommendation**: Start fresh from v2.0 spec. Don't try to migrate v1.0 code.

---

## Key Takeaway

**v1.0 was architecturally sound but had critical domain contradictions and redundancies that would cause bugs.**

**v2.0 enforces single source of truth, resolves all ambiguities, and provides explicit algorithms for every critical operation.**

**Next step: Implementation can proceed with confidence. No architectural debates during coding.**
