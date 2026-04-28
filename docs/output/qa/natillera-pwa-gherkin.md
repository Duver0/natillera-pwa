# Natillera PWA — Gherkin Scenario Suite
# SPEC-001 v2.2 | QA Lead | 2026-04-27

---

## Feature: Interest Calculation (US-003)

### Background
```
Given a client exists with id "client-A"
And an ACTIVE credit exists with:
  | field                | value    |
  | initial_capital      | 10000.00 |
  | pending_capital      | 10000.00 |
  | annual_interest_rate | 12.00    |
  | periodicity          | MONTHLY  |
  | mora                 | false    |
```

### Scenario: INT-01 — Monthly interest exactly $100 on $10 000 at 12% annual
```gherkin
Given the credit above is ACTIVE and mora = false
When the system generates the next installment
Then interest_portion = 100.00
And the formula applied is: 10000 * (12 / 100) / 12 = 100.00
And interest_portion is LOCKED and immutable
```

### Scenario: INT-02 — Interest stops when mora = true
```gherkin
Given credit.mora = true (one installment is overdue)
When the daily cron attempts to generate a new installment
Then no installment is created
And no interest is accrued
And credit.next_period_date is NOT advanced
```

### Scenario: INT-03 — Interest never compounds
```gherkin
Given installment #1 has interest_portion = 100.00 and status = PARTIALLY_PAID
When the system generates installment #2
Then interest_portion for #2 = pending_capital * (12/100) / 12
And the prior installment.interest_portion is NOT included in the new calculation
```

### Scenario: INT-04 — Interest formula is WEEKLY (52 periods/year)
```gherkin
Given pending_capital = 10000.00, annual_interest_rate = 12.00, periodicity = WEEKLY
When the system generates the next installment
Then interest_portion = round(10000 * 0.12 / 52, 2) = 23.08
```

---

## Feature: Mora Detection and Lifecycle (US-006)

### Scenario: MORA-01 — Detect mora when installment is overdue
```gherkin
Given a credit has installment #1 with expected_date = yesterday and status = UPCOMING
When GET /credits/{id} is called
Then credit.mora = true
And credit.mora_since = installment #1 expected_date
And installment #1 is_overdue = true
```

### Scenario: MORA-02 — Mora clears when all overdue installments are paid
```gherkin
Given credit.mora = true
And installment #1 is overdue with remaining_unpaid = 600.00
When a payment of 600.00 is registered
Then installment #1 status = PAID
And installment #1 is_overdue = false
And credit.mora = false
And credit.mora_since = null
And the recalculation happens atomically within the payment transaction
```

### Scenario: MORA-03 — Mora persists if any installment remains overdue after partial payment
```gherkin
Given two overdue installments: #1 remaining = 300.00, #2 remaining = 400.00
When a payment of 300.00 is registered
Then installment #1 status = PAID, is_overdue = false
And installment #2 status remains UPCOMING, is_overdue = true
And credit.mora = true (installment #2 still overdue)
```

### Scenario: MORA-04 — Mora recalculated on every read (no stale cache)
```gherkin
Given a credit was read yesterday with mora = false
And time passes until expected_date < today on installment #1
When GET /credits/{id} is called today
Then credit.mora = true (freshly computed, not cached)
And credit is persisted with mora = true if it changed
```

---

## Feature: Payment Mandatory Order (US-005)

### Test Data
```
Credit:     pending_capital = 9000.00
Installment #1 (overdue):  expected_value = 600.00 | interest = 100.00 | principal = 500.00 | paid = 0
Installment #2 (upcoming): expected_value = 300.00 | interest = 100.00 | principal = 200.00 | paid = 0
Total owed = 900.00
```

### Scenario: PAY-01 — $700 payment applies in mandatory order
```gherkin
Given the credit and installments above
When a payment of 700.00 is registered
Then applied_to contains:
  | type               | amount |
  | OVERDUE_INTEREST   | 100.00 |
  | OVERDUE_PRINCIPAL  | 500.00 |
  | FUTURE_PRINCIPAL   | 100.00 |
And installment #1 status = PAID
And installment #2 paid_value = 100.00, status = PARTIALLY_PAID
And credit.pending_capital = 9000.00 - 500.00 - 100.00 = 8400.00
And a Payment record is created with applied_to breakdown
And a FinancialHistory PAYMENT_RECORDED event is created
```

### Scenario: PAY-02 — Payment stops at zero, does not overshoot
```gherkin
Given the same credit with 700.00 remaining owed
When a payment of 700.00 is registered (exact amount)
Then applied_to total = 700.00
And unallocated = 0.00
And installment #1 status = PAID
```

### Scenario: PAY-03 — Partial payment: remainder stays in installment, no schedule recalc
```gherkin
Given installment #1 overdue with expected_value = 600.00, paid_value = 0
When a payment of 50.00 is registered
Then installment #1 paid_value = 50.00
And installment #1 status = PARTIALLY_PAID
And installment #1 expected_value = 600.00 (unchanged, LOCKED)
And no future installments are modified
```

### Scenario: PAY-04 — Overpayment auto-closes credit when pending_capital reaches 0
```gherkin
Given credit.pending_capital = 500.00, single upcoming installment expected_value = 600.00
When a payment of 600.00 is registered
Then installment paid, credit.pending_capital = 0.00
And credit.status = CLOSED
And credit.closed_date = today
```

### Scenario: PAY-05 — Payment rejected on non-ACTIVE credit
```gherkin
Given credit.status = CLOSED
When POST /payments is called with any amount
Then HTTP 400 is returned
And no Payment record is created
And no installment is modified
```

---

## Feature: Installment Locked Values (US-003 / US-004)

### Scenario: LOCK-01 — Locked fields cannot be modified retroactively
```gherkin
Given installment #1 created with:
  | expected_value    | 933.33 |
  | principal_portion | 833.33 |
  | interest_portion  | 100.00 |
When pending_capital decreases after a payment
Then installment #1 expected_value remains 933.33
And installment #1 principal_portion remains 833.33
And installment #1 interest_portion remains 100.00
```

### Scenario: LOCK-02 — Only paid_value and status are mutable on an installment
```gherkin
Given installment #1 exists
When a payment is applied
Then only paid_value, status, is_overdue, and paid_at are updated
And expected_value, principal_portion, interest_portion, expected_date are unchanged
```

---

## Feature: Optimistic Locking — Concurrent Payment (Business Rule §Version Control)

### Scenario: LOCK-OPT-01 — Concurrent payment triggers 409 conflict
```gherkin
Given credit at version = 3
And two simultaneous payment requests arrive for the same credit
When the second request's UPDATE WHERE version=3 returns 0 rows (version bumped by first)
Then HTTP 409 is returned with detail "version conflict"
And no phantom Payment record is created
And the first payment is committed correctly
```

### Scenario: LOCK-OPT-02 — Retry after 409 succeeds
```gherkin
Given client receives HTTP 409 on first payment attempt
When client re-fetches the credit (now version = 4) and retries the payment
Then the payment is processed successfully with the updated version
And HTTP 201 is returned with payment_id
```

---

## Feature: Cascade Delete (US-001)

### Scenario: DEL-01 — Delete client cascades all related data
```gherkin
Given client "client-A" has:
  - 2 active credits
  - 3 installments per credit
  - 1 savings record
  - 5 history events
When DELETE /clients/client-A is confirmed
Then client.deleted_at is set (soft delete)
And all 2 credits are deleted (ON DELETE CASCADE)
And all 6 installments are deleted (ON DELETE CASCADE)
And the savings record is deleted (ON DELETE CASCADE)
And FinancialHistory records remain (ON DELETE CASCADE — client_id FK is preserved)
And a CLIENT_DELETED history event is created
And no orphaned records remain in credits, installments, or savings tables
```

### Scenario: DEL-02 — History is preserved as immutable audit trail after client delete
```gherkin
Given client "client-A" has been soft-deleted
When GET /history?client_id=client-A is called
Then all prior FinancialHistory events remain queryable
And history records are immutable (no update or delete allowed)
```

---

## Feature: Savings Liquidation (US-007)

### Test Data
```
Contributions:
  - contribution_1: amount = 1000.00, status = ACTIVE
  - contribution_2: amount = 500.00,  status = ACTIVE
SAVINGS_RATE env = 10 (%)
```

### Scenario: SAV-01 — Savings liquidation formula: $1500 × 10% → $1650
```gherkin
Given the contributions above (total = 1500.00)
And SAVINGS_RATE = 10
When POST /savings/liquidate is called for client-A
Then total_contributions = 1500.00
And interest_earned = 1500.00 * 10 / 100 = 150.00
And total_delivered = 1650.00
And both contributions status = LIQUIDATED
And liquidated_at = today
And a SavingsLiquidation record is created with snapshot of rate = 10
And a FinancialHistory SAVINGS_LIQUIDATION event is created
```

### Scenario: SAV-02 — Liquidation is atomic: all-or-nothing
```gherkin
Given 3 ACTIVE contributions
When the liquidation transaction fails mid-way (e.g., DB error)
Then all 3 contributions remain status = ACTIVE
And no SavingsLiquidation record is created
And no FinancialHistory event is created
```

### Scenario: SAV-03 — Savings rate is snapshotted at liquidation time
```gherkin
Given SAVINGS_RATE env = 10 at time of liquidation
When a SavingsLiquidation is created
Then SavingsLiquidation.interest_rate = 10.00 (immutable snapshot)
And future changes to SAVINGS_RATE do not alter past liquidations
```

---

## Feature: Auth + Multi-User Data Isolation (SPEC-002 prep)

### Scenario: AUTH-01 — Valid Firebase token required on all protected endpoints
```gherkin
Given a request with no Authorization header
When any protected endpoint is called (GET /clients, POST /payments, etc.)
Then HTTP 401 is returned
And no data is returned or modified
```

### Scenario: AUTH-02 — User A cannot access User B data (RLS enforcement)
```gherkin
Given user-A owns client "client-A" and user-B owns client "client-B"
And both are authenticated with valid tokens
When user-A calls GET /clients
Then only "client-A" is returned
And "client-B" is never exposed in the response
```

### Scenario: AUTH-03 — User A cannot process payment on User B credit
```gherkin
Given credit "credit-B" belongs to user-B
When user-A calls POST /payments with credit_id = credit-B
Then HTTP 403 is returned
And no payment is created
```

---

## Test Data Registry

| ID | Entity | Field | Value | Used in |
|----|--------|-------|-------|---------|
| TD-001 | Credit | pending_capital | 10000.00 | INT-01 to INT-03 |
| TD-002 | Credit | annual_interest_rate | 12.00 | INT-01 to INT-03 |
| TD-003 | Credit | periodicity | MONTHLY | INT-01 |
| TD-004 | Credit | periodicity | WEEKLY | INT-04 |
| TD-005 | Installment | interest_portion (expected) | 100.00 | INT-01 |
| TD-006 | Payment test | amount | 700.00 | PAY-01 |
| TD-007 | Payment test | overdue interest | 100.00 | PAY-01 |
| TD-008 | Payment test | overdue principal | 500.00 | PAY-01 |
| TD-009 | Payment test | future principal (applied) | 100.00 | PAY-01 |
| TD-010 | Savings | total_contributions | 1500.00 | SAV-01 |
| TD-011 | Savings | SAVINGS_RATE | 10 | SAV-01 |
| TD-012 | Savings | total_delivered (expected) | 1650.00 | SAV-01 |
