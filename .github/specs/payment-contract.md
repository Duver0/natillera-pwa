---
id: CONTRACT-PAYMENT-001
status: APPROVED
version: "1.0"
feature: payment-processing
created: 2026-04-24
updated: 2026-04-24
author: orchestrator
parent-spec: natillera-pwa.spec.md
---

# Payment API Contract — Phase 4

## Scope

This document defines the explicit request/response schemas for payment endpoints.
It is the single source of truth for the payment contract. The parent spec §US-005
defines the business rules; this document defines the wire format.

---

## 1. POST /api/v1/payments

### Request Body

```json
{
  "credit_id": "uuid",
  "amount": "Decimal string or number — must be > 0, scale ≤ 2",
  "operator_id": "string (required, who records the payment)",
  "idempotency_key": "string (optional UUID, prevents double-apply on retry)"
}
```

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `credit_id` | UUID | yes | Must belong to authenticated user |
| `amount` | Decimal(12,2) | yes | > 0, server uses ROUND_HALF_EVEN, zero float prohibited |
| `operator_id` | string | yes | Free-text operator identifier, stored in Payment record |
| `idempotency_key` | UUID string | no | If provided and already used, returns original response (no duplicate write) |

### Success Response — 201 Created

```json
{
  "payment_id": "uuid",
  "credit_id": "uuid",
  "total_amount": "string (Decimal, ROUND_HALF_EVEN)",
  "applied_to": [
    {
      "installment_id": "uuid",
      "type": "OVERDUE_INTEREST | OVERDUE_PRINCIPAL | FUTURE_PRINCIPAL",
      "amount": "string (Decimal)"
    }
  ],
  "updated_credit_snapshot": {
    "pending_capital": "string (Decimal)",
    "mora": "boolean",
    "version": "integer (new version after update)"
  }
}
```

### Error Responses

| HTTP Code | Condition |
|-----------|-----------|
| 400 | Credit is not ACTIVE (closed or suspended) |
| 409 | Optimistic lock conflict — Credit.version changed concurrently; client must retry |
| 422 | Pydantic validation error (missing fields, amount ≤ 0) |
| 403 | Credit not found or does not belong to authenticated user |

---

## 2. POST /api/v1/payments/preview

Zero mutation. Computes the exact same allocation breakdown as POST /payments
but writes nothing to the database.

### Request Body

```json
{
  "credit_id": "uuid",
  "amount": "Decimal string or number — must be > 0"
}
```

### Success Response — 200 OK

```json
{
  "credit_id": "uuid",
  "total_amount": "string (Decimal)",
  "applied_to": [
    {
      "installment_id": "uuid",
      "type": "OVERDUE_INTEREST | OVERDUE_PRINCIPAL | FUTURE_PRINCIPAL",
      "amount": "string (Decimal)"
    }
  ],
  "unallocated": "string (Decimal, 0 if payment covers all debt)",
  "updated_credit_snapshot": {
    "pending_capital": "string (Decimal, projected after payment)",
    "mora": "boolean (projected)",
    "version": "integer (unchanged — read-only)"
  }
}
```

Note: `preview` response shape is identical to `POST /payments` response except:
- No `payment_id` field
- `updated_credit_snapshot.version` is the current version (not incremented)
- No side effects whatsoever

---

## 3. Allocation Algorithm (Canonical)

All amounts handled as `Decimal` with `ROUND_HALF_EVEN`. No float arithmetic.

```
GIVEN: remaining = amount (Decimal)
       installments = unpaid installments ORDERED BY expected_date ASC (FIFO)
       today = server UTC date

FOR EACH installment (ordered):
  IF remaining <= 0: BREAK

  is_overdue = installment.expected_date < today AND status != PAID

  IF is_overdue:
    # Phase 1 — Overdue interest first
    interest_remaining = installment.interest_portion - amount_already_applied_to_interest
    IF interest_remaining > 0:
      applied = min(remaining, interest_remaining)
      remaining -= applied
      record: {installment_id, type=OVERDUE_INTEREST, amount=applied}

    # Phase 2 — Overdue principal
    IF remaining > 0:
      principal_remaining = installment.principal_portion - amount_already_applied_to_principal
      IF principal_remaining > 0:
        applied = min(remaining, principal_remaining)
        remaining -= applied
        record: {installment_id, type=OVERDUE_PRINCIPAL, amount=applied}

  ELSE (future installment):
    # Phase 3 — Future principal only
    IF remaining > 0:
      full_remaining = installment.expected_value - installment.paid_value
      IF full_remaining > 0:
        applied = min(remaining, full_remaining)
        remaining -= applied
        record: {installment_id, type=FUTURE_PRINCIPAL, amount=applied}

AFTER LOOP:
  principal_applied = SUM(entries where type IN [OVERDUE_PRINCIPAL, FUTURE_PRINCIPAL])
  new_pending_capital = credit.pending_capital - principal_applied
  IF new_pending_capital <= 0: auto-close credit (status = CLOSED)
  mora = exists any installment with is_overdue=true AND status != PAID after applying
  UPDATE credit SET pending_capital=new_pending_capital, mora=mora, version=version+1
    WHERE id=credit_id AND version=credit.version  -- optimistic lock
  IF update affects 0 rows: RAISE VersionConflict → HTTP 409

  INSERT payment record
  INSERT financial_history event
```

### Overpayment Rule

Per spec §1.3 ambiguity #4: excess reduces `pending_capital` directly.
If `pending_capital` reaches 0: auto-close credit.
Excess beyond zero debt: returned in `unallocated` field. Not refunded automatically.

---

## 4. Service Method Signatures

```python
class PaymentService:

    async def process_payment(self, body: PaymentRequest) -> PaymentResponse:
        """Full payment: allocate + persist + return structured breakdown."""

    async def preview_payment_breakdown(
        self, credit_id: UUID, amount: Decimal
    ) -> PaymentPreviewResponse:
        """
        Pure computation. Zero DB writes.
        Returns same breakdown shape as process_payment minus payment_id.
        """
```

---

## 5. Pydantic Schemas

### PaymentRequest (input)
```python
class PaymentRequest(BaseModel):
    credit_id: UUID
    amount: Decimal = Field(..., gt=0, decimal_places=2)
    operator_id: str = Field(..., min_length=1)
    idempotency_key: Optional[UUID] = None
```

### AppliedToEntry (breakdown line)
```python
class AppliedToEntry(BaseModel):
    installment_id: UUID
    type: Literal["OVERDUE_INTEREST", "OVERDUE_PRINCIPAL", "FUTURE_PRINCIPAL"]
    amount: Decimal
```

### UpdatedCreditSnapshot
```python
class UpdatedCreditSnapshot(BaseModel):
    pending_capital: Decimal
    mora: bool
    version: int
```

### PaymentResponse (POST /payments 201)
```python
class PaymentResponse(BaseModel):
    payment_id: UUID
    credit_id: UUID
    total_amount: Decimal
    applied_to: List[AppliedToEntry]
    updated_credit_snapshot: UpdatedCreditSnapshot
```

### PaymentPreviewResponse (POST /payments/preview 200)
```python
class PaymentPreviewResponse(BaseModel):
    credit_id: UUID
    total_amount: Decimal
    applied_to: List[AppliedToEntry]
    unallocated: Decimal
    updated_credit_snapshot: UpdatedCreditSnapshot
```

---

## 6. Constraints

- All monetary values: `Decimal(12,2)`, rounding mode `ROUND_HALF_EVEN`
- No float anywhere in payment logic (service, schemas, DB write values)
- Installment locked fields (`expected_value`, `principal_portion`, `interest_portion`) are NEVER modified
- Only mutable installment fields: `paid_value`, `status`, `is_overdue`, `paid_at`
- All writes inside a single atomic transaction (Supabase RPC or explicit transaction)
- Optimistic locking: UPDATE WHERE version=X; 0 rows → VersionConflict → 409
