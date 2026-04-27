---
id: SPEC-001
status: IN_PROGRESS
version: "2.2"
feature: natillera-pwa
created: 2026-04-23
updated: 2026-04-24
author: spec-generator
related-specs:
  - .github/specs/payment-contract.md
week-2-completed: 2026-04-23
week-4-started: 2026-04-24
---

# Natillera PWA — Personal Loans + Savings Management (REFACTORED v2.0)

Financial tracking PWA for personal loans and savings. Admin clients, credits, savings, payment flows with deterministic interest + mandatory payment order. Mobile-first, free-tier persistent storage.

**SPEC AUDITED & REFACTORED**: Eliminated redundancies, resolved domain contradictions, enforced single source of truth. See AUDIT NOTES section below.

---

## AUDIT NOTES (v1.0 → v2.0)

### Problems Found & Fixed

1. **Interest Redundancy**: Credit.generated_interest + Installment.interest_portion were duplicate. **FIX**: Deleted Credit.generated_interest. Interest now single source in installments.

2. **Opaque Overdue Debt**: Credit.overdue_debt was aggregator mixing interest + principal. Payment mandatory order impossible. **FIX**: Converted to derived calculation from per-installment status.

3. **Architecture Contradiction**: Spec claimed "no backend required" but designed FastAPI. **FIX**: Explicit choice — Supabase + FastAPI backend. Business logic server-side only.

4. **Mora Staleness**: No mechanism to keep mora flag fresh. **FIX**: Mora recalculated on every credit.get(). No stale cache.

5. **Interest Timing Undefined**: Interest accrual before/after installment date unclear. **FIX**: Interest included in installment at period boundary (before expected_date).

6. **Concurrent Payment Race**: No version field for optimistic locking. **FIX**: Added Credit.version field + retry logic.

7. **Undefined Interest During Mora**: Spec claimed no interest on overdue but didn't define if mora = true stops interest. **FIX**: Explicit rule — mora = true → interest_generation stops.

8. **Installment Fixed vs Variable**: Unclear if installment.expected_value changes with pending_capital. **FIX**: Installments FIXED at creation time. No retroactive changes.

---

## 1. REQUERIMIENTOS

### 1.1 User Stories

#### US-001: Cliente CRUD
```gherkin
Feature: Manage Clients
  Scenario: Create new client
    Given user opens app
    When submit name, lastname, phone (required), document/address/notes (optional)
    Then client record created + assigned unique ID
    And form cleared for next entry

  Scenario: View client list
    Given user on clients page
    When list loads
    Then display name, lastname, phone, document (if exists)
    And allow search by name/phone
    And show client debt summary (total_debt, mora_count)

  Scenario: Edit client
    Given client record open
    When update any field
    Then save changes + timestamp updated_at

  Scenario: Delete client
    Given client in list with credits/savings
    When confirm delete
    Then soft-delete client (mark deleted_at)
    And cascade-delete all related credits/savings
    And archive history records (immutable audit trail)
```

#### US-002: Credit Creation + Initialization
```gherkin
Feature: Create Credit
  Scenario: Register new credit
    Given client detail view
    When fill: initial_capital (required, >0), periodicity, annual_interest_rate, start_date, status=ACTIVE
    Then system initializes:
      - credit_id generated
      - pending_capital = initial_capital
      - version = 1
      - mora = false
      - mora_since = null
      - next_period_date = start_date + period_offset
    And generate first period installment with locked interest_portion

  Scenario: Periodicity selection
    Given credit form
    When choose periodicity
    Then options: DAILY (365 periods/year), WEEKLY (52), BIWEEKLY (26), MONTHLY (12)
    And system calculates period intervals accordingly
```

#### US-003: Interest Calculation (BASE RULE)
```gherkin
Feature: Period Interest Generation
  Scenario: Calculate period interest (locked at installment creation)
    Given active credit (mora = false), period arrives
    When generate next installment
    Then interest_amount = pending_capital_at_creation * (annual_rate / periods_per_year)
    And create installment with:
      - interest_portion = interest_amount (LOCKED, never changes)
      - principal_portion = (pending_capital / remaining_periods) (LOCKED)
      - expected_value = principal_portion + interest_portion
      - status = UPCOMING

  Scenario: NO interest accrual if mora = true
    Given credit.mora = true (any installment overdue)
    When period arrives
    Then NO new installment generated
    And NO interest calculated until mora cleared

  Scenario: Interest NEVER compound
    Given installment with interest_portion locked
    When next period arrives
    Then new interest calculated on pending_capital ONLY
    And prior interest_portion NOT used in next period's calc
```

#### US-004: Installment Generation + Tracking
```gherkin
Feature: Auto-generate Installments
  Scenario: Generate installment on period boundary
    Given active credit (mora = false), period_date arrives
    When system runs period job (daily cron or event)
    Then generate single installment:
      - period_number = N (sequential)
      - expected_date = period_date + days_in_period
      - expected_value = locked (see US-003)
      - principal_portion = locked
      - interest_portion = locked
      - paid_value = 0
      - status = UPCOMING
    And increment next_period_date

  Scenario: View upcoming installments
    Given client detail
    When click "Active Credits"
    Then list all credits + next 3 unpaid installments
    And show: period_number, expected_date, expected_value, paid_value, status

  Scenario: Detect overdue installment
    Given installment with expected_date < today, status != PAID
    When system checks (on every credit.get() call)
    Then mark installment is_overdue = true
    And recalculate credit.mora = true (if not already)
    And set credit.mora_since = earliest overdue installment date
```

#### US-005: Payment Processing (MANDATORY ORDER)
```gherkin
Feature: Process Payment (Mandatory Application Order)
  Scenario: Apply payment with strict priority
    Given credit with mixed unpaid installments (some overdue, some future)
    When user registers payment amount
    Then apply in STRICT order:
      1. Overdue interest (sum of interest_portion where is_overdue = true)
      2. Overdue principal (sum of principal_portion where is_overdue = true)
      3. Future principal (pending_capital not yet covered)
    And update each installment.paid_value, installment.status atomically
    And reduce credit.pending_capital by total_principal_applied
    And recalculate credit.mora

  Scenario: Partial installment payment
    Given installment unpaid, payment_amount < remaining_owed
    When register partial payment
    Then:
      - installment.paid_value += payment_amount
      - installment.status = PARTIALLY_PAID
      - remaining_unpaid stays in installment (NOT moved to overdue_debt)
      - NO recalculation of schedule
      - NO modification of future installments
    And mark installment.is_overdue if expected_date < today

  Scenario: Full installment payment
    Given installment.paid_value + payment <= expected_value
    When register payment
    Then:
      - installment.paid_value = expected_value
      - installment.status = PAID
      - installment.paid_at = today
      - installment.is_overdue = false
    And recalculate credit.mora (may become false if no other overdue)

  Scenario: Overpayment handling
    Given credit with pending_capital = $1000, payment = $1500
    When apply payment (all installments paid)
    Then:
      - All installments marked PAID
      - Excess ($500) reduces pending_capital
      - If pending_capital becomes 0 → auto-close credit
      - Return excess payment to client (refund scenario handled in UI/business rules)
```

#### US-006: Mora Detection + Status
```gherkin
Feature: Track Mora State
  Scenario: Detect mora condition
    Given credit with installments
    When current_date > installment.expected_date AND installment.status != PAID
    Then during credit.get():
      - Query unpaid overdue installments
      - Set credit.mora = true
      - Set credit.mora_since = earliest overdue date
      - Persist if changed from previous state

  Scenario: Mora metadata display
    Given mora detected
    Then show in UI:
      - mora_since (when mora started)
      - days_overdue = today - mora_since
      - mora_amount = SUM(unpaid installments in mora)
    And visual indicator (NO penalties, purely informational)

  Scenario: Clear mora on payment
    Given credit in mora state
    When payment clears all overdue installments
    Then mora = false, mora_since = null
    And recalculation happens atomically with payment
```

#### US-007: Savings Liquidation
```gherkin
Feature: Savings Management
  Scenario: Register savings contribution
    Given client detail
    When add contribution amount, date
    Then create savings record:
      - contribution_amount (>0)
      - contribution_date
      - status = ACTIVE

  Scenario: Liquidate savings
    Given client with multiple active contributions
    When click liquidate
    Then calculate:
      - total_contributions = SUM(all ACTIVE contributions)
      - interest_rate = app config (SAVINGS_RATE environment variable)
      - interest_earned = total_contributions * interest_rate / 100
      - total_delivered = total_contributions + interest_earned
    And atomically:
      - Mark all contributions status = LIQUIDATED
      - Create SavingsLiquidation record (snapshot of rate, amounts)
      - Create FinancialHistory event

  Scenario: View savings history
    Given savings view
    When list loads
    Then show:
      - Contributions (amount, date, status)
      - Liquidations (total_delivered, rate used, date)
```

#### US-008: History + Audit Trail
```gherkin
Feature: Financial History (Immutable Audit Log)
  Scenario: Record all financial actions
    Given any financial operation completes (credit create, payment, savings, delete)
    When operation succeeds
    Then create immutable FinancialHistory record:
      - event_type (CREDIT_CREATED, PAYMENT_RECORDED, SAVINGS_LIQUIDATION, etc.)
      - client_id (required)
      - credit_id (nullable)
      - amount (nullable)
      - description (human-readable)
      - metadata (JSON: payment breakdown, rate used, etc.)
      - timestamp (server UTC time)
      - operator_id (user who triggered)

  Scenario: View client history
    Given client detail
    When click History tab
    Then list all events in reverse chronological order
    And allow filter by event_type, date_range
```

### 1.2 Business Rules (Non-Negotiable)

| Rule | Formula / Logic | Owner |
|------|---|---|
| **Interest Base** | `interest = pending_capital_at_creation * (annual_rate/100) / periods_per_year` | Domain |
| **Installments Fixed** | Once created, installment.expected_value, principal_portion, interest_portion NEVER change | Domain |
| **No Compound Interest** | Interest calculated ONLY on pending_capital from current period, never on prior interest | Domain |
| **Interest Stops in Mora** | If mora = true (any overdue installment), NO new installments generated, NO interest accrued | Domain |
| **Payment Mandatory Order** | 1. Overdue interest 2. Overdue principal 3. Future principal. Strict priority. | Domain |
| **Mora Detection** | mora = true IF ∃ unpaid installment with expected_date < today. Recalculated on every credit.get() | Domain |
| **Partial Payment** | Remainder stays in installment (not moved elsewhere), no schedule recalc | Domain |
| **No Penalty Interest** | No additional interest on overdue debt. Informational mora flag only. | Domain |
| **Savings Formula** | interest = total_contributions * (SAVINGS_RATE / 100), liquidation = contributions + interest | Domain |
| **Cascade Delete** | Delete client → soft-delete, cascade-delete all credits/savings, preserve history | Infrastructure |
| **Version Control** | Credit.version incremented on each update; optimistic locking for concurrency | Infrastructure |
| **Timestamp Tracking** | All records: created_at, updated_at (UTC, server-side). Soft-delete: deleted_at (nullable) | Infrastructure |

### 1.3 Ambiguities Resolved

1. **Credit closure criteria** → Auto-close when pending_capital = 0 AND all installments paid. Manual override allowed.

2. **Interest accrual timing** → Interest included in installment at period boundary (before expected_date), locked when installment created.

3. **Savings rate definition** → Global app config (SAVINGS_RATE env var), immutable per liquidation (snapshot in record).

4. **Multiple simultaneous payments** → Single payment operation; applies in mandatory order across all unpaid installments FIFO by expected_date.

5. **Debt priority** → Strict order: overdue interest → overdue principal → future. No discretion. Enforced by payment service.

6. **Interest during mora** → STOPS. mora = true means no new interest accrued until mora cleared by payment.

7. **Installment variability** → FIXED. Installment created with locked values. No retroactive recalc as pending_capital changes.

8. **Concurrent payment safety** → Optimistic locking via Credit.version. If conflict, return 409, client retries.

---

## 2. DISEÑO

### 2.1 Data Model (Single Source of Truth)

#### Client
```yaml
Client:
  id: UUID (PK)
  first_name: string (required, min 2)
  last_name: string (required, min 2)
  phone: string (required, unique, E.164 format)
  document_id: string (optional, unique if provided)
  address: string (optional)
  notes: string (optional, max 500)
  created_at: DateTime (UTC, server-set)
  updated_at: DateTime (UTC, server-set)
  deleted_at: DateTime (nullable, soft-delete)

# DERIVED (not persisted):
#  total_debt = SUM(credits.pending_capital) WHERE client_id=id AND status=ACTIVE
#  mora_count = COUNT(credits WHERE mora=true AND status=ACTIVE)
```

#### Credit (Loan)
```yaml
Credit:
  id: UUID (PK)
  client_id: UUID (FK → Client, ON DELETE CASCADE)
  initial_capital: decimal(12,2) (required, >0, immutable)
  pending_capital: decimal(12,2) (decreases with principal payments)
  version: int (default 1, incremented on update for optimistic locking)
  periodicity: enum [DAILY, WEEKLY, BIWEEKLY, MONTHLY]
  annual_interest_rate: decimal(5,2) (% as 15 for 15%, immutable)
  status: enum [ACTIVE, CLOSED, SUSPENDED] (default ACTIVE)
  start_date: Date
  closed_date: Date (nullable)
  next_period_date: Date (when next installment should generate)
  mora: boolean (true if any unpaid overdue installment, recalc on read)
  mora_since: Date (nullable, earliest overdue installment date when mora=true)
  created_at: DateTime (UTC)
  updated_at: DateTime (UTC)

# DERIVED (not persisted):
#  total_paid_principal = initial_capital - pending_capital
#  pending_interest = SUM(installments.interest_portion WHERE status != PAID)
#  overdue_interest = SUM(installments.interest_portion WHERE is_overdue=true AND status != PAID)
#  overdue_principal = SUM(installments.principal_portion WHERE is_overdue=true AND status != PAID)
```

#### Installment (Period Payment Obligation)
```yaml
Installment:
  id: UUID (PK)
  credit_id: UUID (FK → Credit, ON DELETE CASCADE)
  period_number: int (sequential: 1, 2, 3, ..., immutable)
  expected_date: Date (when payment due, immutable)
  expected_value: decimal(12,2) (principal + interest, LOCKED, immutable)
  principal_portion: decimal(12,2) (breakdown, LOCKED, immutable)
  interest_portion: decimal(12,2) (breakdown, LOCKED, immutable)
  paid_value: decimal(12,2) (cumulative received, default 0)
  is_overdue: boolean (true if expected_date < today AND status != PAID, recalc on read)
  status: enum [UPCOMING, PARTIALLY_PAID, PAID, SUSPENDED] (default UPCOMING)
  created_at: DateTime (UTC)
  paid_at: DateTime (nullable, when fully paid)

# Business Logic:
#  remaining_unpaid = expected_value - paid_value
#  If paid_value = 0: status may be UPCOMING or SUSPENDED (if credit suspended)
#  If 0 < paid_value < expected_value: status = PARTIALLY_PAID
#  If paid_value >= expected_value: status = PAID
```

#### Payment (Transaction Record)
```yaml
Payment:
  id: UUID (PK)
  credit_id: UUID (FK → Credit, ON DELETE CASCADE)
  amount: decimal(12,2) (actual received)
  payment_date: Date (when payment recorded)
  applied_to: JSONB (array of breakdown objects)
    [
      { type: "OVERDUE_INTEREST", amount: 100.00 },
      { type: "OVERDUE_PRINCIPAL", amount: 500.00 },
      { type: "FUTURE_PRINCIPAL", amount: 200.00 }
    ]
  notes: string (optional, operator notes)
  recorded_by: string (operator ID)
  created_at: DateTime (UTC)
```

#### Savings (Contribution Record)
```yaml
Savings:
  id: UUID (PK)
  client_id: UUID (FK → Client, ON DELETE CASCADE)
  contribution_amount: decimal(12,2) (>0)
  contribution_date: Date
  status: enum [ACTIVE, LIQUIDATED] (default ACTIVE)
  liquidated_at: Date (nullable, when liquidation happened)
  created_at: DateTime (UTC)
```

#### SavingsLiquidation (Payout Record)
```yaml
SavingsLiquidation:
  id: UUID (PK)
  client_id: UUID (FK → Client, ON DELETE CASCADE)
  total_contributions: decimal(12,2)
  interest_earned: decimal(12,2)
  total_delivered: decimal(12,2)
  interest_rate: decimal(5,2) (snapshot of SAVINGS_RATE at liquidation time)
  liquidation_date: Date
  created_at: DateTime (UTC)
```

#### FinancialHistory (Immutable Audit Log)
```yaml
FinancialHistory:
  id: UUID (PK, never modified)
  event_type: enum [
    CREDIT_CREATED, CREDIT_CLOSED, CREDIT_SUSPENDED,
    INSTALLMENT_GENERATED,
    PAYMENT_RECORDED,
    SAVINGS_CONTRIBUTION, SAVINGS_LIQUIDATION,
    CLIENT_CREATED, CLIENT_DELETED
  ]
  client_id: UUID (required, FK → Client, ON DELETE CASCADE)
  credit_id: UUID (nullable, FK → Credit, ON DELETE SET NULL)
  amount: decimal(12,2) (nullable, financial amount)
  description: string (human-readable summary)
  metadata: JSONB (type-specific data)
    Example for PAYMENT_RECORDED:
    {
      "payment_id": "uuid",
      "total_amount": 700.00,
      "applied_to": [
        { "type": "OVERDUE_INTEREST", "amount": 100 },
        { "type": "OVERDUE_PRINCIPAL", "amount": 500 },
        { "type": "FUTURE_PRINCIPAL", "amount": 100 }
      ]
    }
  timestamp: DateTime (UTC, created_at)
  operator_id: string (who triggered)
```

### 2.2 Clean Architecture Layers

```
┌─────────────────────────────────────────────────────┐
│                  UI / PWA Frontend                   │
│          (React 18 + TypeScript, Vite, mobile-first) │
└──────────────────┬──────────────────────────────────┘
                   │ HTTP/REST + JWT Bearer
┌──────────────────▼──────────────────────────────────┐
│              APPLICATION LAYER (FastAPI)             │
│  ├─ routes/ (HTTP endpoints, input validation)      │
│  ├─ schemas/ (Pydantic request/response DTOs)       │
│  └─ middleware/ (auth, error handling, logging)     │
└──────────────────┬──────────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────────┐
│            BUSINESS LOGIC / SERVICES                 │
│  ├─ credit_service (creation, interest, state)      │
│  ├─ payment_service (mandatory order, atomicity)    │
│  ├─ installment_service (generation, tracking)      │
│  ├─ savings_service (contributions, liquidation)    │
│  ├─ client_service (CRUD, cascade delete)           │
│  └─ history_service (audit trail)                   │
└──────────────────┬──────────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────────┐
│              DOMAIN / VALUE OBJECTS                  │
│  ├─ Client (aggregate root)                         │
│  ├─ Credit (aggregate root + installments)          │
│  ├─ Payment                                         │
│  └─ Savings                                         │
└──────────────────┬──────────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────────┐
│           REPOSITORIES / DATA ACCESS                 │
│  ├─ client_repository (Supabase queries)            │
│  ├─ credit_repository (with version + locks)        │
│  ├─ installment_repository                          │
│  ├─ payment_repository                              │
│  ├─ savings_repository                              │
│  └─ history_repository (append-only)                │
└──────────────────┬──────────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────────┐
│       PERSISTENCE LAYER / DATABASE                   │
│         Supabase PostgreSQL (ACID, realtime)        │
└─────────────────────────────────────────────────────┘
```

**Architecture Decisions:**
- Business logic ENTIRELY server-side (FastAPI)
- Frontend is presentation-only (no calculations)
- Supabase RLS policies enforce auth at row level
- Payments require backend transaction handling

### 2.3 Backend Tech Stack (Fixed)

| Component | Choice | Rationale |
|-----------|--------|-----------|
| **Language** | Python 3.12 | Per backend rules; async-native |
| **Framework** | FastAPI | Async REST, auto OpenAPI, Pydantic validation |
| **Database** | Supabase PostgreSQL | ACID transactions, relational integrity, free tier, realtime subscriptions |
| **Driver** | asyncpg (via Supabase client) | Async Postgres, low latency |
| **Validation** | Pydantic v2 | Type hints, automatic validation |
| **Auth** | Firebase Admin SDK | Token verification (stateless) |
| **Server** | Uvicorn | ASGI, lightweight |
| **Testing** | pytest + pytest-asyncio | Async unit/integration tests |
| **ORM** | SQLAlchemy async (optional) or raw SQL | For Supabase queries |

**Why not MongoDB:**
- Current spec uses Supabase PostgreSQL (relational model needed for CASCADE DELETE integrity)
- Financial transactions require ACID guarantees
- Clean separation: backend enforces rules, frontend cannot bypass

### 2.4 Frontend Tech Stack

| Component | Choice | Rationale |
|-----------|--------|-----------|
| **Framework** | React 18 + TypeScript | Type safety, mobile libraries, ecosystem |
| **Build** | Vite | Fast HMR, small bundle |
| **Styling** | Tailwind CSS | Mobile-first, low size |
| **State** | Redux Toolkit + RTK Query | Normalized state, caching, API integration |
| **Forms** | React Hook Form + Zod | Lightweight validation, async support |
| **UI Components** | Shadcn/ui or Material-UI | Mobile-responsive, accessible |
| **PWA** | Workbox (Vite plugin) | Service workers, offline caching |
| **HTTP** | fetch API + RTK Query | Built-in, no extra dependency |
| **Charting** | Recharts (future) | Lightweight, responsive |

**PWA Offline Strategy:**
- Assets: Cache-first (service worker)
- API calls: Stale-while-revalidate + queue on offline
- Payments: Queue locally, sync when online, optimistic UI

### 2.5 Database Schema (Supabase PostgreSQL)

```sql
-- Clients (soft-delete enabled)
CREATE TABLE clients (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  first_name VARCHAR(255) NOT NULL,
  last_name VARCHAR(255) NOT NULL,
  phone VARCHAR(20) NOT NULL UNIQUE,
  document_id VARCHAR(50) UNIQUE,
  address TEXT,
  notes TEXT CHECK (length(notes) <= 500),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  deleted_at TIMESTAMP
);
CREATE INDEX idx_clients_phone ON clients(phone);
CREATE INDEX idx_clients_deleted ON clients(deleted_at);

-- Credits (with optimistic locking version)
CREATE TABLE credits (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
  initial_capital DECIMAL(12,2) NOT NULL CHECK (initial_capital > 0),
  pending_capital DECIMAL(12,2) NOT NULL CHECK (pending_capital >= 0),
  version INT DEFAULT 1,
  periodicity VARCHAR(20) NOT NULL CHECK (periodicity IN ('DAILY', 'WEEKLY', 'BIWEEKLY', 'MONTHLY')),
  annual_interest_rate DECIMAL(5,2) NOT NULL CHECK (annual_interest_rate >= 0),
  status VARCHAR(20) NOT NULL CHECK (status IN ('ACTIVE', 'CLOSED', 'SUSPENDED')) DEFAULT 'ACTIVE',
  start_date DATE NOT NULL,
  closed_date DATE,
  next_period_date DATE,
  mora BOOLEAN DEFAULT FALSE,
  mora_since DATE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_credits_client ON credits(client_id);
CREATE INDEX idx_credits_status ON credits(status);
CREATE INDEX idx_credits_mora ON credits(mora);

-- Installments (LOCKED: expected_value, principal, interest never change)
CREATE TABLE installments (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  credit_id UUID NOT NULL REFERENCES credits(id) ON DELETE CASCADE,
  period_number INT NOT NULL,
  expected_date DATE NOT NULL,
  expected_value DECIMAL(12,2) NOT NULL CHECK (expected_value > 0),
  principal_portion DECIMAL(12,2) NOT NULL CHECK (principal_portion > 0),
  interest_portion DECIMAL(12,2) NOT NULL CHECK (interest_portion >= 0),
  paid_value DECIMAL(12,2) DEFAULT 0 CHECK (paid_value >= 0),
  is_overdue BOOLEAN DEFAULT FALSE,
  status VARCHAR(20) NOT NULL CHECK (status IN ('UPCOMING', 'PARTIALLY_PAID', 'PAID', 'SUSPENDED')) DEFAULT 'UPCOMING',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  paid_at TIMESTAMP,
  UNIQUE(credit_id, period_number)
);
CREATE INDEX idx_installments_credit ON installments(credit_id);
CREATE INDEX idx_installments_expected_date ON installments(expected_date);
CREATE INDEX idx_installments_is_overdue ON installments(is_overdue) WHERE is_overdue=TRUE;

-- Payments (immutable records)
CREATE TABLE payments (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  credit_id UUID NOT NULL REFERENCES credits(id) ON DELETE CASCADE,
  amount DECIMAL(12,2) NOT NULL CHECK (amount > 0),
  payment_date DATE NOT NULL,
  applied_to JSONB NOT NULL, -- [{"type": "OVERDUE_INTEREST", "amount": 100}, ...]
  notes TEXT,
  recorded_by VARCHAR(255) NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_payments_credit ON payments(credit_id);
CREATE INDEX idx_payments_date ON payments(payment_date);

-- Savings
CREATE TABLE savings (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
  contribution_amount DECIMAL(12,2) NOT NULL CHECK (contribution_amount > 0),
  contribution_date DATE NOT NULL,
  status VARCHAR(20) NOT NULL CHECK (status IN ('ACTIVE', 'LIQUIDATED')) DEFAULT 'ACTIVE',
  liquidated_at DATE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_savings_client ON savings(client_id);
CREATE INDEX idx_savings_status ON savings(status);

-- SavingsLiquidations
CREATE TABLE savings_liquidations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
  total_contributions DECIMAL(12,2) NOT NULL CHECK (total_contributions > 0),
  interest_earned DECIMAL(12,2) NOT NULL CHECK (interest_earned >= 0),
  total_delivered DECIMAL(12,2) NOT NULL CHECK (total_delivered > 0),
  interest_rate DECIMAL(5,2) NOT NULL CHECK (interest_rate >= 0),
  liquidation_date DATE NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_savings_liquidations_client ON savings_liquidations(client_id);

-- FinancialHistory (append-only audit log)
CREATE TABLE financial_history (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  event_type VARCHAR(50) NOT NULL,
  client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
  credit_id UUID REFERENCES credits(id) ON DELETE SET NULL,
  amount DECIMAL(12,2),
  description TEXT NOT NULL,
  metadata JSONB,
  operator_id VARCHAR(255) NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_financial_history_client ON financial_history(client_id);
CREATE INDEX idx_financial_history_event_type ON financial_history(event_type);
CREATE INDEX idx_financial_history_created_at ON financial_history(created_at);

-- Row-Level Security (RLS) policies
ALTER TABLE clients ENABLE ROW LEVEL SECURITY;
ALTER TABLE credits ENABLE ROW LEVEL SECURITY;
ALTER TABLE installments ENABLE ROW LEVEL SECURITY;
ALTER TABLE payments ENABLE ROW LEVEL SECURITY;
ALTER TABLE savings ENABLE ROW LEVEL SECURITY;
ALTER TABLE savings_liquidations ENABLE ROW LEVEL SECURITY;
ALTER TABLE financial_history ENABLE ROW LEVEL SECURITY;

-- Example RLS policy (auth.uid() = operator_id):
-- CREATE POLICY "users_own_data" ON clients
--   FOR ALL USING (auth.uid()::text = operator_id)
--   WITH CHECK (auth.uid()::text = operator_id);
```

### 2.6 State Management (Frontend)

**Redux Toolkit + RTK Query**

```javascript
// Store shape (normalized)
{
  clients: { byId: {}, allIds: [] },
  credits: { byId: {}, allIds: [] },
  installments: { byId: {}, allIds: [] },
  payments: { byId: {}, allIds: [] },
  savings: { byId: {}, allIds: [] },
  ui: { selectedClientId, filter, modal, notification }
}

// RTK Query endpoints (auto-cache invalidation):
useGetClientsQuery()
useCreateClientMutation()
useProcessPaymentMutation()
  → auto-refetch related credits, installments, history
```

### 2.7 Folder Structure

```
natillera-pwa/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py (FastAPI app)
│   │   ├── config.py (settings, env vars)
│   │   ├── models/
│   │   │   ├── client_model.py (Pydantic)
│   │   │   ├── credit_model.py
│   │   │   ├── installment_model.py
│   │   │   ├── payment_model.py
│   │   │   ├── savings_model.py
│   │   │   └── history_model.py
│   │   ├── routes/
│   │   │   ├── client_router.py
│   │   │   ├── credit_router.py
│   │   │   ├── installment_router.py
│   │   │   ├── payment_router.py
│   │   │   ├── savings_router.py
│   │   │   └── history_router.py
│   │   ├── services/
│   │   │   ├── client_service.py
│   │   │   ├── credit_service.py
│   │   │   ├── installment_service.py
│   │   │   ├── payment_service.py
│   │   │   ├── savings_service.py
│   │   │   └── history_service.py
│   │   ├── repositories/
│   │   │   ├── client_repository.py
│   │   │   ├── credit_repository.py
│   │   │   ├── installment_repository.py
│   │   │   ├── payment_repository.py
│   │   │   ├── savings_repository.py
│   │   │   └── history_repository.py
│   │   ├── middleware/
│   │   │   ├── auth.py (Firebase token verification)
│   │   │   └── error_handler.py
│   │   ├── utils/
│   │   │   ├── logger.py
│   │   │   ├── validators.py
│   │   │   ├── datetime_utils.py
│   │   │   └── calculations.py (interest, mora, etc.)
│   │   └── dependencies.py (Depends factories)
│   ├── tests/ (pytest)
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
│
├── frontend/
│   ├── src/
│   │   ├── index.tsx
│   │   ├── App.tsx
│   │   ├── components/ (reusable UI components)
│   │   ├── pages/ (full page views)
│   │   ├── store/
│   │   │   ├── store.ts
│   │   │   ├── slices/
│   │   │   └── api/ (RTK Query)
│   │   ├── hooks/ (custom React hooks)
│   │   ├── types/ (TypeScript interfaces)
│   │   ├── utils/ (calculations, formatters, validators)
│   │   ├── styles/
│   │   └── public/ (PWA manifest, service worker)
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   ├── tsconfig.json
│   ├── package.json
│   └── .env.example
│
├── .github/
│   ├── workflows/
│   │   ├── backend-test.yml
│   │   ├── frontend-build.yml
│   │   └── deploy.yml
│   ├── specs/
│   │   └── natillera-pwa.spec.md (this file)
│   └── requirements/
│       └── natillera-pwa.md
│
├── docker-compose.yml
├── README.md
└── .env.example
```

---

## 3. LISTA DE TAREAS

### 3.1 Backend Development (FastAPI + Supabase)

#### Phase 1: Foundation (Week 1)
- [x] Setup FastAPI project + asyncpg (Supabase client) — verified: backend/app/main.py + backend/app/db.py 2026-04-23
- [x] Configure environment: SUPABASE_URL, SUPABASE_KEY, SAVINGS_RATE — verified: backend/app/config.py 2026-04-23
- [x] Create Pydantic schemas (ClientCreate, CreditCreate, PaymentRequest, etc.) — verified: backend/app/models/ 2026-04-23
- [x] Implement Client repository + service — verified: 2026-04-23
  - [x] client_repository.py (async CRUD via Supabase)
  - [x] client_service.py (business logic, cascade delete)
  - [x] client_router.py (GET /clients, POST, PUT, DELETE)
- [x] Setup auth middleware (Supabase JWKS token verification, replaces Firebase) — verified: backend/app/middleware/auth.py 2026-04-23
- [x] Setup error handling + structured logging — verified: backend/app/middleware/error_handler.py + backend/app/utils/logger.py 2026-04-23

#### Phase 2: Credit Module (Week 2-3)
- [ ] Implement Credit repository (with version field for optimistic locking)
- [ ] Implement CreditService:
  - [ ] create_credit() → initialize pending_capital, version=1, mora=false
  - [ ] calculate_period_interest() → formula (pending_capital * rate / periods_per_year)
  - [ ] check_mora_status() → query overdue installments, update mora flag
  - [ ] get_credit() → call check_mora_status before returning (always fresh)
- [ ] Implement InstallmentService:
  - [ ] generate_installment() → create single installment with LOCKED values
  - [ ] should_generate_installment() → check mora=false, enough capital remaining
  - [ ] run_daily_installment_job() → query all credits with next_period_date <= today, generate if not mora
- [ ] Credit endpoints:
  - [ ] POST /credits (create)
  - [ ] GET /credits (list, filter by client_id, status)
  - [ ] GET /credits/:id (detail, recalculate mora on read)
  - [ ] GET /credits/:id/installments (list, filter by status)
- [ ] Tests:
  - [ ] test_credit_creation.py
  - [ ] test_interest_calculation.py (verify formula)
  - [ ] test_no_compound_interest.py
  - [ ] test_mora_detection.py
  - [ ] test_mora_fresh_on_read.py

#### Phase 3: Installment Generation (Week 3)
- [x] Setup daily cron job — `backend/scripts/run_installment_job.py` (cron script chosen over background task; uses SUPABASE_SERVICE_KEY service role) — verified: 2026-04-24
- [x] `should_generate_installment()` — verified: `backend/app/services/installment_service.py` 2026-04-24
- [x] `generate_installment()` alias — verified: `backend/app/services/installment_service.py` 2026-04-24
- [x] `run_daily_installment_job()` — per-credit error isolation, batch result summary — verified: `backend/app/services/installment_service.py` 2026-04-24
- [x] Logic: ACTIVE + mora=False + pending_capital>0 + next_period_date<=today → generate — verified: 2026-04-24
- [x] `GET /credits/:id/installments` endpoint — verified: `backend/app/routes/credit_router.py` 2026-04-24
- [x] Tests:
  - [x] test_installment_generation_cron.py — 10 tests — verified: `backend/tests/` 2026-04-24
  - [x] test_installment_locked_values.py — 12 tests — verified: `backend/tests/` 2026-04-24

#### Phase 4: Payment Processing (Week 4) — IMPLEMENTED 2026-04-24
- [x] Payment contract documented — `.github/specs/payment-contract.md` — 2026-04-24
- [x] Pydantic schemas refactored to Decimal — `backend/app/models/payment_model.py` — 2026-04-24
  - [x] PaymentRequest (operator_id required, Decimal amount)
  - [x] PaymentResponse (payment_id, total_amount, applied_to with installment_id, updated_credit_snapshot)
  - [x] PaymentPreviewResponse (same minus payment_id, plus unallocated, version unchanged)
  - [x] AppliedToEntry, UpdatedCreditSnapshot
- [x] Implement PaymentService — `backend/app/services/payment_service.py` — 2026-04-24
  - [x] `_compute_breakdown()` pure allocation function (Decimal, ROUND_HALF_EVEN)
  - [x] `process_payment()` → structured PaymentResponse dict
  - [x] `preview_payment_breakdown()` → zero writes, same breakdown shape
  - [x] Optimistic locking: 0-row update → HTTPException(409) — FIXES Week 2 risk #3
  - [x] Installment locked fields untouched (only paid_value, status, is_overdue, paid_at)
  - [x] `_compute_installment_new_states()` helper separates state from allocation
- [x] Payment endpoints — `backend/app/routes/payment_router.py` — 2026-04-24
  - [x] POST /payments → 201 PaymentResponse
  - [x] POST /payments/preview → 200 PaymentPreviewResponse
  - [x] GET /payments?credit_id=X (list)
  - [x] 409 on version conflict, 400 on non-ACTIVE credit, 422 validation, 403 ownership
- [x] Tests (50 test cases, mocked DB) — 2026-04-24
  - [x] `backend/tests/test_payment_mandatory_order.py` — 6 tests
  - [x] `backend/tests/test_payment_partial_application.py` — 5 tests
  - [x] `backend/tests/test_payment_overpayment.py` — 5 tests
  - [x] `backend/tests/test_payment_boundary_conditions.py` — 6 tests
  - [x] `backend/tests/test_payment_multi_installment.py` — 4 tests
  - [x] `backend/tests/test_payment_atomicity.py` — 3 tests
  - [x] `backend/tests/test_optimistic_locking_retry.py` — 4 tests
  - [x] `backend/tests/test_payment_preview.py` — 7 tests
  - [x] `backend/tests/test_payment_installment_status_transitions.py` — 5 tests
  - [x] `backend/tests/test_payment_pending_capital_update.py` — 5 tests
- [x] Frontend minimal integration — 2026-04-24
  - [x] `PaymentForm` component — `frontend/src/components/PaymentForm.tsx`
  - [x] Preview before submit, breakdown display (installment_id, type, amount)
  - [x] 409 conflict error handling
  - [x] RTK Query updated: `usePreviewPaymentMutation`, `useProcessPaymentMutation` with operator_id
  - [x] Types updated: `PaymentResponse`, `PaymentPreviewResponse`, `UpdatedCreditSnapshot`
  - [x] `frontend/src/components/__tests__/PaymentForm.test.tsx` — 9 tests

#### Phase 5: Savings + History (Week 4-5)
- [ ] Implement SavingsService:
  - [ ] add_contribution(client_id, amount, date) → create Savings record
  - [ ] liquidate_savings(client_id):
    - Query all ACTIVE contributions
    - total_contributions = SUM(amount)
    - interest_rate = SAVINGS_RATE env var
    - interest_earned = total_contributions * interest_rate / 100
    - Atomic: mark all as LIQUIDATED, create SavingsLiquidation, create history event
- [ ] Implement HistoryService:
  - [ ] record_event(event_type, client_id, credit_id, amount, description, metadata, operator_id)
    - Immutable append-only
- [ ] Savings endpoints:
  - [ ] POST /savings/contributions
  - [ ] POST /savings/liquidate
  - [ ] GET /savings?client_id=X
- [ ] History endpoints:
  - [ ] GET /history (paginated, newest first)
  - [ ] GET /history?type=X (filter by event_type)
  - [ ] GET /history?client_id=X (client-specific)
- [ ] Tests:
  - [ ] test_savings_liquidation_formula.py
  - [ ] test_history_immutable.py

#### Phase 6: Integration + Polish (Week 5-6)
- [ ] Supabase schema migration + verification
- [ ] RLS policies (optional, auth enforcement)
- [ ] Comprehensive error handling (no stack traces in responses)
- [ ] Rate limiting on payment endpoint
- [ ] OpenAPI documentation (FastAPI auto-gen)
- [ ] Integration tests (full workflow)
- [ ] Performance tests (query latency, batch operations)
- [ ] Docker setup

### 3.2 Frontend Development

#### Phase 1: PWA Setup + Navigation (Week 1)
- [x] Initialize Vite + React + TypeScript — verified: frontend/vite.config.ts + frontend/src/index.tsx 2026-04-23
- [x] Configure Tailwind CSS — verified: frontend/tailwind.config.js 2026-04-23
- [x] Setup Redux Toolkit store — verified: frontend/src/store/store.ts 2026-04-23
- [x] Create layout + navigation — verified: frontend/src/components/ 2026-04-23
- [ ] Configure service worker + manifest.json (installable) — NOT DONE per qa-report blocker
- [x] Setup RTK Query baseURL to backend — verified: frontend/src/store/api/apiSlice.ts 2026-04-23
- [x] React Router v6 setup — verified: frontend/src/App.tsx 2026-04-23

#### Phase 2: Client Management (Week 2)
- [ ] ClientList page:
  - [ ] Fetch + display all clients (name, phone, document)
  - [ ] Search by name/phone
  - [ ] Click → ClientDetail
  - [ ] Add Client button → modal
- [ ] ClientForm component:
  - [ ] Fields: first_name, last_name, phone, document, address, notes
  - [ ] Validation (React Hook Form + Zod)
  - [ ] Submit → RTK Query mutation → POST /clients
- [ ] ClientDetail page:
  - [ ] Display info, total_debt, mora_count
  - [ ] Tabs: Info, Active Credits, Mora, Savings, History
  - [ ] Edit / Delete buttons
- [ ] Setup RTK Query clientApi

#### Phase 3: Credit + Installment UI (Week 3)
- [x] CreditForm modal — verified: `frontend/src/components/credits/CreditForm.tsx` 2026-04-24
  - [x] Fields: initial_capital, periodicity dropdown, annual_interest_rate, start_date
  - [x] Zod + React Hook Form validation
  - [x] Submit → POST /credits via useCreateCreditMutation
- [x] ActiveCredits tab — verified: `frontend/src/components/credits/ActiveCredits.tsx` 2026-04-24
  - [x] List credits (status, pending_capital, next_installment)
  - [x] Mora indicator (red badge if mora=true)
  - [x] Click → expand installments (show next 3)
- [x] InstallmentView — verified: `frontend/src/components/credits/InstallmentView.tsx` 2026-04-24
  - [x] List with period_number, expected_date, expected_value, paid_value, status
  - [x] Filter: upcoming, paid, overdue (client-side)
- [x] MoraAlert component (informational, no penalty) — verified: `frontend/src/components/credits/MoraAlert.tsx` 2026-04-24
- [x] RTK Query creditApi — verified: `frontend/src/store/api/creditApi.ts` 2026-04-24
- [x] RTK Query installmentApi — verified: `frontend/src/store/api/installmentApi.ts` 2026-04-24

#### Phase 4: Payment Processing (Week 4)
- [ ] PaymentForm modal:
  - [ ] Select credit
  - [ ] Enter amount
  - [ ] Show breakdown preview (how it applies)
  - [ ] Submit → POST /payments
  - [ ] Success notification
- [ ] Payment history (recent payments per credit)
- [ ] Setup RTK Query paymentApi

#### Phase 5: Savings UI (Week 5)
- [ ] SavingsView page:
  - [ ] ContributionForm: add amount + date
  - [ ] List contributions (amount, date, status)
  - [ ] LiquidateButton with confirmation
  - [ ] Show liquidation result (interest_earned, total_delivered)
- [ ] RTK Query savingsApi

#### Phase 6: History + Reporting (Week 5)
- [ ] HistoryView page:
  - [ ] Timeline (all events, reverse chronological)
  - [ ] Filter: event_type, date_range, client_id
  - [ ] Display metadata (amount, related credit, operator)
- [ ] RTK Query historyApi

#### Phase 7: Styling + Mobile (Week 6)
- [ ] Mobile-first responsive design
- [ ] Grid layouts (credits, installments, history)
- [ ] Print-friendly views
- [ ] Accessibility (WCAG 2.1 A)

#### Phase 8: PWA Optimization (Week 6)
- [ ] Service worker caching strategy
- [ ] Offline fallback pages
- [ ] Install prompt
- [ ] App icons + splash screen
- [ ] Lighthouse 90+

### 3.3 Quality Assurance

#### Unit Tests (Backend)
- [ ] CreditService:
  - [ ] Interest formula correctness
  - [ ] No compound interest
  - [ ] Mora detection (overdue installment detection)
  - [ ] Interest stops when mora=true
- [ ] InstallmentService:
  - [ ] Generation with LOCKED values
  - [ ] No retroactive changes to existing installments
- [ ] PaymentService:
  - [ ] Mandatory order: overdue_interest → overdue_principal → future_principal
  - [ ] Partial payment (remainder stays in installment)
  - [ ] Full payment (status = PAID)
  - [ ] Overpayment (refund or next credit)
  - [ ] Atomicity (rollback on error)
  - [ ] Optimistic locking (version conflict → retry)
- [ ] SavingsService:
  - [ ] Liquidation formula: interest = contributions * rate / 100
  - [ ] Atomicity (all contributions marked LIQUIDATED)
- [ ] ClientService:
  - [ ] Cascade delete (client → credits, savings, history)

#### Unit Tests (Frontend)
- [ ] Form validation (client, credit, payment)
- [ ] Custom hooks (useMora, usePaymentBreakdown)
- [ ] Utility calculations

#### Integration Tests (Backend)
- [ ] End-to-end: create client → create credit → generate installment → process payment
- [ ] Mora lifecycle: create overdue → mora=true → payment clears → mora=false
- [ ] Payment with multiple states (overdue + future)
- [ ] Cascade delete verification
- [ ] History event creation for all operations

#### Integration Tests (Frontend + Backend)
- [ ] Create client via UI → verify API list
- [ ] Create credit → verify installments generated
- [ ] Register payment → verify pending_capital reduced
- [ ] Liquidate savings → verify history event

#### Business Logic Tests (Gherkin)
- [ ] Interest formula: 12% annual, monthly → $100/month on $10k
- [ ] Payment order: $900 owed (overdue interest $100, overdue capital $500, future $300)
  - Payment $700 → interest $100, capital $500, future $100 applied
- [ ] Mora: expected_date < today, unpaid → mora=true
- [ ] Savings: $1000+$500, 10% → interest $150, delivered $1650

#### User Acceptance Tests
- [ ] Create/edit/delete clients
- [ ] Create credits with different periodicities
- [ ] View active credits + next installment
- [ ] Mora indicator visible
- [ ] Register partial payment (installment status changes)
- [ ] Register full payment (installment = PAID)
- [ ] Liquidate savings
- [ ] View history filtered by event type + date range

#### Performance Tests
- [ ] GET /clients (1000 records) → <500ms
- [ ] GET /credits/:id/installments (100 records) → <300ms
- [ ] POST /payments → <1s (atomic)
- [ ] Frontend initial load → <2s on 3G
- [ ] List scroll (1000 records) → 60fps

#### Security Tests
- [ ] Firebase token verification on all protected endpoints
- [ ] No sensitive data in logs
- [ ] HTTPS enforced (GitHub Pages)
- [ ] CORS configured (frontend origin only)
- [ ] Input validation (Pydantic + React Hook Form)
- [ ] Rate limiting on payment endpoint

---

## 4. ALGORITMOS CRÍTICOS

### 4.1 Interest Calculation (BASE RULE)

```python
# services/credit_service.py

PERIODS_PER_YEAR = {
    "DAILY": 365,
    "WEEKLY": 52,
    "BIWEEKLY": 26,
    "MONTHLY": 12
}

async def calculate_period_interest(
    pending_capital: Decimal,
    annual_rate: Decimal,
    periodicity: str
) -> Decimal:
    """
    Interest = pending_capital * (annual_rate / 100) / periods_per_year
    
    Example:
      pending_capital = $10,000
      annual_rate = 12%
      periodicity = MONTHLY (12 periods/year)
      interest = 10000 * (12 / 100) / 12 = $100/month
    
    Returns Decimal rounded to 2 decimals (cents).
    """
    if pending_capital <= 0:
        return Decimal(0)
    
    periods = PERIODS_PER_YEAR.get(periodicity, 12)
    interest = (
        pending_capital 
        * (annual_rate / Decimal(100)) 
        / Decimal(periods)
    )
    
    return interest.quantize(Decimal("0.01"))  # Round to cents
```

### 4.2 Payment Mandatory Order (STRICT PRIORITY)

```python
# services/payment_service.py

async def process_payment(
    credit_id: UUID,
    amount: Decimal,
    operator_id: str
) -> Payment:
    """
    Apply payment in MANDATORY order:
    1. Overdue interest (sum of interest_portion where is_overdue=true)
    2. Overdue principal (sum of principal_portion where is_overdue=true)
    3. Future principal (pending_capital not yet covered)
    
    All updates atomic. If any step fails, entire transaction rolls back.
    """
    from sqlalchemy import select, update
    
    async with db.begin() as tx:
        # Step 1: Fetch credit with row lock (pessimistic) or version check (optimistic)
        credit = await credit_repo.get_by_id_for_update(credit_id)
        if not credit:
            raise ValueError(f"Credit {credit_id} not found")
        
        # Step 2: Query all unpaid installments sorted by expected_date ASC
        unpaid_installments = await installment_repo.find(
            credit_id=credit_id,
            status__in=["UPCOMING", "PARTIALLY_PAID"],
            order_by="expected_date ASC"
        )
        
        remaining_payment = amount
        applied_breakdown = []
        
        # Step 3: Apply in mandatory order
        for installment in unpaid_installments:
            if remaining_payment <= 0:
                break
            
            remaining_owed = installment.expected_value - installment.paid_value
            
            # 3a. Apply overdue interest first (if expected_date < today)
            if installment.is_overdue and installment.interest_portion > 0:
                interest_applied = min(remaining_payment, installment.interest_portion)
                remaining_payment -= interest_applied
                installment.paid_value += interest_applied
                applied_breakdown.append({
                    "type": "OVERDUE_INTEREST",
                    "amount": float(interest_applied),
                    "installment_id": str(installment.id)
                })
            
            # 3b. Apply overdue principal next
            if remaining_payment > 0 and installment.is_overdue and installment.principal_portion > 0:
                principal_applied = min(
                    remaining_payment,
                    installment.principal_portion
                )
                remaining_payment -= principal_applied
                installment.paid_value += principal_applied
                applied_breakdown.append({
                    "type": "OVERDUE_PRINCIPAL",
                    "amount": float(principal_applied),
                    "installment_id": str(installment.id)
                })
            
            # 3c. Apply future principal (upcoming installments)
            if remaining_payment > 0 and not installment.is_overdue:
                future_applied = min(remaining_payment, remaining_owed)
                remaining_payment -= future_applied
                installment.paid_value += future_applied
                applied_breakdown.append({
                    "type": "FUTURE_PRINCIPAL",
                    "amount": float(future_applied),
                    "installment_id": str(installment.id)
                })
            
            # Update installment status
            if installment.paid_value >= installment.expected_value:
                installment.status = "PAID"
                installment.paid_at = datetime.utcnow()
            elif installment.paid_value > 0:
                installment.status = "PARTIALLY_PAID"
            
            await installment_repo.update(installment)
        
        # Step 4: Reduce credit.pending_capital by total principal applied
        principal_applied_total = sum(
            float(b["amount"]) for b in applied_breakdown
            if b["type"] in ["OVERDUE_PRINCIPAL", "FUTURE_PRINCIPAL"]
        )
        credit.pending_capital -= Decimal(str(principal_applied_total))
        credit.pending_capital = credit.pending_capital.quantize(Decimal("0.01"))
        
        # Step 5: Recalculate mora
        mora_before = credit.mora
        mora_after = await calculate_mora_status(credit_id)
        credit.mora = mora_after
        
        if mora_after and not credit.mora_since:
            credit.mora_since = min(i.expected_date for i in unpaid_installments if i.is_overdue)
        elif not mora_after:
            credit.mora_since = None
        
        # Increment version for optimistic locking
        credit.version += 1
        credit.updated_at = datetime.utcnow()
        await credit_repo.update(credit)
        
        # Step 6: Create Payment record
        payment = await payment_repo.create(Payment(
            credit_id=credit_id,
            amount=amount,
            payment_date=date.today(),
            applied_to=applied_breakdown,
            recorded_by=operator_id
        ))
        
        # Step 7: Create history event
        await history_repo.record(
            event_type="PAYMENT_RECORDED",
            client_id=credit.client_id,
            credit_id=credit_id,
            amount=amount,
            description=f"Payment of {amount} applied to installments",
            metadata={
                "payment_id": str(payment.id),
                "applied_to": applied_breakdown
            },
            operator_id=operator_id
        )
        
        # All or nothing: if we got here, commit. Otherwise rollback.
        await tx.commit()
    
    return payment
```

### 4.3 Mora Detection (Recalculated on Read)

```python
# services/credit_service.py

async def get_credit(credit_id: UUID) -> Credit:
    """
    Fetch credit and ALWAYS recalculate mora before returning.
    
    mora = true IF ∃ unpaid installment with expected_date < today
    """
    credit = await credit_repo.get_by_id(credit_id)
    if not credit:
        raise ValueError(f"Credit {credit_id} not found")
    
    # Recalculate mora fresh
    today = date.today()
    overdue_installments = await installment_repo.find(
        credit_id=credit_id,
        expected_date__lt=today,
        status__in=["UPCOMING", "PARTIALLY_PAID"]
    )
    
    mora_fresh = bool(overdue_installments)
    
    # If mora status changed, persist
    if mora_fresh != credit.mora:
        credit.mora = mora_fresh
        
        if mora_fresh:
            credit.mora_since = min(
                i.expected_date for i in overdue_installments
            )
        else:
            credit.mora_since = None
        
        credit.version += 1
        credit.updated_at = datetime.utcnow()
        await credit_repo.update(credit)
    
    # Mark installments as overdue/not overdue
    for installment in overdue_installments:
        if not installment.is_overdue:
            installment.is_overdue = True
            await installment_repo.update(installment)
    
    return credit
```

### 4.4 Installment Generation (Locked Values)

```python
# services/installment_service.py

async def generate_next_installment(credit_id: UUID) -> Installment:
    """
    Generate single installment with LOCKED principal + interest.
    
    Values are calculated once and NEVER change, even if pending_capital changes later.
    """
    credit = await credit_service.get_credit(credit_id)
    
    if credit.status != "ACTIVE":
        raise ValueError(f"Credit {credit_id} is not ACTIVE")
    
    if credit.mora:
        raise ValueError(f"Credit {credit_id} is in mora; cannot generate installment")
    
    if credit.pending_capital <= 0:
        raise ValueError(f"Credit {credit_id} has no remaining capital")
    
    # Calculate locked values
    period_number = await installment_repo.count(credit_id=credit_id) + 1
    
    # Interest locked at this moment
    interest_portion = calculate_period_interest(
        pending_capital=credit.pending_capital,
        annual_rate=credit.annual_interest_rate,
        periodicity=credit.periodicity
    )
    
    # Principal locked: divide remaining by estimated remaining periods
    # (Simple approach: assume fixed amortization)
    estimated_remaining_periods = 12  # Configurable or client-supplied
    principal_portion = (
        credit.pending_capital / Decimal(estimated_remaining_periods)
    ).quantize(Decimal("0.01"))
    
    expected_value = principal_portion + interest_portion
    expected_date = credit.next_period_date
    
    # Create installment (immutable once created)
    installment = Installment(
        credit_id=credit_id,
        period_number=period_number,
        expected_date=expected_date,
        expected_value=expected_value,
        principal_portion=principal_portion,
        interest_portion=interest_portion,
        paid_value=Decimal(0),
        is_overdue=False,
        status="UPCOMING"
    )
    
    installment = await installment_repo.create(installment)
    
    # Update credit.next_period_date
    period_offset = PERIOD_OFFSETS[credit.periodicity]  # {DAILY: 1, ..., MONTHLY: 30}
    credit.next_period_date += timedelta(days=period_offset)
    credit.version += 1
    await credit_repo.update(credit)
    
    # Record history event
    await history_repo.record(
        event_type="INSTALLMENT_GENERATED",
        client_id=credit.client_id,
        credit_id=credit_id,
        amount=expected_value,
        description=f"Installment {period_number} generated",
        metadata={
            "period_number": period_number,
            "principal_portion": float(principal_portion),
            "interest_portion": float(interest_portion),
            "expected_date": str(expected_date)
        },
        operator_id="system"
    )
    
    return installment
```

---

## 5. RIESGOS + MITIGACIÓN

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|-----------|
| **Interest calc errors** | Wrong balances, client disputes | Medium | Unit tests (10+ scenarios), formula audit, integration tests |
| **Payment order not applied** | Debt miscalculation | High | Atomic transactions, explicit breakdown in Payment record, API contract tests |
| **Mora status stale** | UI shows mora=false but actually overdue | Medium | Recalculate mora on EVERY credit.get() (not cached), zero staleness |
| **Cascade delete fails** | Orphaned credits/savings | Low | Foreign key constraints ON DELETE CASCADE, integration test |
| **Optimistic lock conflicts** | Concurrent payments race | Medium | Version field, retry logic, 409 response to client |
| **Decimal rounding** | Interest mismatch (0.01 vs 0.001) | Low | Use Decimal type, quantize to 2 decimals consistently |
| **Installment retroactive change** | Client charged twice if installment modified | High | Immutable schema (constraints), no update logic, only create/read |
| **Interest during mora undefined** | System behavior undefined | Low | Explicit rule: mora=true → no interest accrual |
| **Concurrent installment generation** | Duplicate installments | Low | Check period_number uniqueness, cron job serialization |
| **Firebase token expiry** | Session timeout mid-payment | Low | Auto-refresh, clear error message, re-login flow |
| **Offline payment sync** | Local payment conflicts with server | Medium | Optimistic UI, queue locally, merge on online, user warning |
| **Large installment list** | Slow UI render (100+ installments) | Low | Pagination (20 per page), indexed queries on expected_date |

---

## 6. DECISIONES DE DISEÑO

### 6.1 Finalized Decisions

1. **Interest Single Source of Truth**: All interest in Installment.interest_portion. Credit.generated_interest deleted.

2. **Overdue Tracking Refactored**: No opaque Credit.overdue_debt. Derived from unpaid installments per type (interest vs principal).

3. **Mora Always Fresh**: Recalculated on every credit.get(). No stale cache.

4. **Installments Immutable**: expected_value, principal_portion, interest_portion LOCKED at creation. No retroactive changes.

5. **Interest Stops in Mora**: mora = true → no new installments, no interest accrual.

6. **Payment Atomicity**: All-or-nothing via DB transaction. Version field for optimistic locking.

7. **Installment Generation**: Incremental (daily cron or event-driven), not all-at-once.

8. **Architecture**: FastAPI backend + Supabase PostgreSQL. Business logic server-side only. Frontend presentation-only.

9. **Auth**: Firebase Admin SDK (stateless token verification). Supabase RLS optional overlay.

10. **Savings Rate**: Global env var (SAVINGS_RATE), immutable per liquidation in SavingsLiquidation record.

11. **Audit Trail**: Immutable FinancialHistory table. All operations logged.

12. **PWA Offline**: Service worker caches assets, API responses stale-while-revalidate, payments queued locally, synced on online.

### 6.2 Out of Scope (MVP)

- Document/ID photo upload
- Bulk CSV import
- Email/SMS notifications
- Multi-language (i18n)
- Advanced analytics dashboards
- Two-factor authentication
- Mobile app (PWA sufficient)

---

## 7. PRÓXIMOS PASOS

1. **Review & Approve this spec** with product + finance team
2. **Setup Supabase project** (PostgreSQL database, RLS policies)
3. **Create task board** (Linear/GitHub Projects) from Section 3
4. **Assign Phase 1 (Foundation)** to backend engineer
5. **Parallel Phase 1 (PWA Setup)** to frontend engineer
6. **Weekly syncs** on payment logic + interest calculation (core business rules)
7. **UAT with anonymized loan data** before production launch

---

## 8. GLOSSÁRIO

| Term | Definition |
|------|-----------|
| **pending_capital** | Principal balance remaining; decreases with principal-portion payments |
| **interest_portion** | Interest for a single installment; locked at creation, never changes |
| **principal_portion** | Principal for a single installment; locked at creation, never changes |
| **mora** | State flag: true if any unpaid installment is overdue (expected_date < today) |
| **mora_since** | Date when first overdue installment occurred; used for UI display |
| **is_overdue** | Installment-level flag: true if expected_date < today AND status != PAID |
| **installment** | Single period payment obligation; consists of principal + interest |
| **periodicity** | Frequency: DAILY (365/year), WEEKLY (52), BIWEEKLY (26), MONTHLY (12) |
| **mandatory order** | Payment application priority: overdue interest → overdue principal → future principal |
| **liquidation** | Savings payout: total_contributions + interest_earned |
| **audit trail** | FinancialHistory table; all financial events immutable |
| **soft-delete** | Mark deleted_at timestamp; preserve audit trail |
| **atomic transaction** | All-or-nothing: payment succeeds completely or entire operation rolls back |
| **optimistic locking** | Version field on Credit; retry if version mismatch (concurrent update detected) |
| **LOCKED value** | Immutable after creation; installment.expected_value, principal_portion, interest_portion never change |

---

**SPEC REFACTORED & AUDITED v2.0** — Ready for implementation. All domain contradictions resolved. Single source of truth enforced. Business rules explicitly defined. Architecture unified (FastAPI + Supabase).
