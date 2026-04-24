## Database Schema — Natillera PWA

Migration execution order:

1. `001_initial_schema.sql` — creates all tables with user_id FK, indexes, installment user_id trigger
2. `002_rls_policies.sql` — enables RLS, deploys all ownership policies
3. `003_triggers_and_functions.sql` — updated_at stamps, immutability guards, auth user creation hook

Rollback: `000_rollback.sql` (dev/test only, destroys all data)

Tables: public.users, clients, credits, installments, payments, savings, savings_liquidations, financial_history

Key constraints enforced at DB level:
- installment.expected_value / principal_portion / interest_portion are IMMUTABLE after insert
- financial_history rows are IMMUTABLE (no update or delete)
- user_id on installments, payments, savings auto-synced via triggers from parent record
- phone and document_id unique per user (not globally)
- RLS: every table enforces auth.uid() = user_id for all operations
