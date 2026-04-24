# Runbook: Supabase Local Bring-Up

Status: HUMAN-ACTION-REQUIRED — cannot run inside agent sandbox (Docker required)

---

## Prerequisites

- Docker Desktop running (or Docker Engine on Linux)
- Node.js >= 18 (for Supabase CLI)
- Python >= 3.11 (for integration tests)

---

## Step 1: Install Supabase CLI

```bash
# macOS / Linux via npm
npm install -g supabase

# or via Homebrew (macOS)
brew install supabase/tap/supabase

# Verify
supabase --version
```

---

## Step 2: Initialize and Start Supabase

```bash
cd /path/to/natillera-pwa

# Already initialized (supabase/ directory exists if present)
# If not:
supabase init

# Start local Supabase stack (PostgreSQL + Auth + PostgREST + Studio)
supabase start
```

`supabase start` will print a block like:

```
API URL: http://localhost:54321
DB URL:  postgresql://postgres:postgres@localhost:54322/postgres
Studio:  http://localhost:54323
```

Copy the `DB URL` value for step 4.

---

## Step 3: Apply Migrations in Order

```bash
# Apply all migrations manually via psql
export DATABASE_URL="postgresql://postgres:postgres@localhost:54322/postgres"

psql $DATABASE_URL -f database/migrations/001_initial_schema.sql
psql $DATABASE_URL -f database/migrations/002_rls_policies.sql
```

If a `003_*.sql` migration exists, apply it next.

Verify tables exist:

```bash
psql $DATABASE_URL -c "\dt"
# Expected tables: clients, credits, installments, payments, savings, savings_liquidations, financial_history, public.users
```

---

## Step 4: Set Environment Variables

```bash
# In backend/.env (create if not present)
cat > backend/.env <<EOF
DATABASE_URL=postgresql://postgres:postgres@localhost:54322/postgres
SUPABASE_URL=http://localhost:54321
SUPABASE_ANON_KEY=<anon key printed by supabase start>
SUPABASE_SERVICE_ROLE_KEY=<service_role key printed by supabase start>
SAVINGS_RATE=2.0
EOF
```

---

## Step 5: Install Integration Test Dependencies

```bash
cd /path/to/natillera-pwa

pip install asyncpg pytest pytest-asyncio python-dotenv
# Or if requirements file exists:
pip install -r backend/requirements.txt
```

---

## Step 6: Run Integration Tests

```bash
export DATABASE_URL="postgresql://postgres:postgres@localhost:54322/postgres"

pytest tests/integration/ -v 2>&1 | tee .github/qa/live-validation-output.txt
```

Expected output: all tests PASSED. If any fail, check `.github/qa/live-validation-output.txt`.

---

## Step 7: Run DB Validation SQL

```bash
psql $DATABASE_URL -f database/validation/run_all.sql
```

If `database/validation/run_all.sql` does not exist, run these manually:

```sql
-- Verify table structure
SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name;

-- Verify RLS enabled
SELECT tablename, rowsecurity FROM pg_tables WHERE schemaname = 'public';

-- Verify indexes exist
SELECT indexname, tablename FROM pg_indexes WHERE schemaname = 'public' ORDER BY tablename;

-- Verify triggers
SELECT trigger_name, event_object_table FROM information_schema.triggers WHERE trigger_schema = 'public';
```

---

## Step 8: Generate PWA Icons (if not yet generated)

```bash
# Python 3 required
python scripts/generate-icons.py
# Output: frontend/public/icons/icon-192.png, icon-512.png
```

---

## Step 9: Validate PWA Build

```bash
cd frontend
npm install
npm run build
# Must complete with no errors
# Dist will contain icons and manifest
```

---

## Stopping Supabase

```bash
supabase stop
```

---

## Troubleshooting

| Error | Fix |
|-------|-----|
| `Cannot connect to Docker` | Start Docker Desktop / Docker daemon |
| `port 54322 in use` | `supabase stop` then `supabase start` |
| `relation "auth.users" does not exist` | Supabase not started — `supabase start` first |
| `DATABASE_URL not set` | Export it: `export DATABASE_URL=postgresql://...` |
| `asyncpg not installed` | `pip install asyncpg pytest-asyncio` |
