# Integration Tests — Natillera PWA

These tests hit a real PostgreSQL database (Supabase local or remote).
No mocks. No simulated logic.

## What is tested

| File | Cases |
|---|---|
| `test_rls.py` | Case 1: cross-user isolation; Case 2: INSERT with wrong user_id |
| `test_triggers.py` | Case 3: installment immutable fields; Case 4: history append-only |
| `test_payment_atomicity.py` | Case 5: full rollback on mid-transaction failure |
| `test_cascade_delete.py` | Case 6: client delete cascades to all children |

## Prerequisites

### Option A — Supabase local (recommended)

```bash
# Install Supabase CLI
npm install -g supabase

# Start local stack (Docker required)
cd /home/duver-betancur/Training/natillera-pwa
supabase start

# Apply migrations
supabase db push
# or manually:
psql "$DATABASE_URL" -f database/migrations/001_initial_schema.sql
psql "$DATABASE_URL" -f database/migrations/002_rls_policies.sql
psql "$DATABASE_URL" -f database/migrations/003_triggers_and_functions.sql
```

`supabase start` prints the local DB URL. It looks like:
```
DB URL: postgresql://postgres:postgres@localhost:54322/postgres
```

### Option B — Remote Supabase test project

Create a dedicated test project in the Supabase dashboard. Run migrations via the SQL editor or `supabase db push --linked`.

## Environment variables

Create `.env` in the repo root (or export before running):

```env
# Direct PostgreSQL connection — NOT the pooler URL, NOT the anon/service key
DATABASE_URL=postgresql://postgres:<password>@<host>:<port>/postgres
```

For Supabase local the default is:
```env
DATABASE_URL=postgresql://postgres:postgres@localhost:54322/postgres
```

## Install test dependencies

```bash
pip install -r tests/integration/requirements.txt
```

## Run

```bash
pytest tests/integration/ -v
```

Run a single file:
```bash
pytest tests/integration/test_rls.py -v
```

Run a single test:
```bash
pytest tests/integration/test_triggers.py::TestInstallmentImmutability::test_locked_field_update_is_blocked -v
```

## How RLS is exercised

Tests use two kinds of connections:

- `raw_conn` — connects as the `postgres` superuser (bypasses RLS). Used for seeding data that must exist before the assertion.
- `as_user(uuid)` — sets `role = authenticated` and `request.jwt.claims = {"sub": "<uuid>"}` via `SET LOCAL`, which makes `auth.uid()` return the given UUID. Used to simulate a real authenticated user session.

Both are wrapped in a transaction that rolls back after each test, so no state persists between tests.

## Notes

- The `auth.users` table is managed by Supabase. Tests insert directly into it using the superuser connection to satisfy FK constraints without needing a real sign-up flow.
- The `financial_history` immutability trigger fires at the PostgreSQL level before RLS. Cascade deletes from FK constraints (client delete) do bypass the trigger and remove history rows — this is expected and tested.
- `pytest-asyncio` requires `asyncio_mode = auto` or the `pytestmark = pytest.mark.asyncio` marker on each module. Both patterns are present.
