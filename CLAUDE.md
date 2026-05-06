# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Quick Start

### Frontend
```bash
cd frontend
npm install
npm run dev          # dev server at localhost:5173
npm run build        # build for production
npm run typecheck    # check TypeScript types
npm test             # run tests (vitest)
npm test:watch       # watch mode
npm test:ui          # UI mode
```

### Backend
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload  # dev server at localhost:8000
pytest                          # run all tests
pytest tests/integration/       # integration tests only (requires supabase start)
```

### Local Database
```bash
supabase start       # start local Supabase (PostgreSQL + Auth)
# Apply migrations from database/migrations/
```

## Architecture Overview

### Frontend Stack
- **React 18** + **TypeScript** + **Vite**
- **Redux Toolkit** with **RTK Query** for state + data fetching (see `src/store/api/apiSlice.ts`)
- **React Router v6** for SPA routing
- **Supabase Client SDK** for authentication (JWT-based)
- **TailwindCSS** for styling
- **Vitest** + **Testing Library** for unit/component tests

**Key pattern:** Data fetching via RTK Query endpoints defined in `src/store/api/*.ts` slices. Components consume data via hooks like `useGetClientsQuery()`. Auth state in Redux slice (`src/store/slices/authSlice.ts`).

### Backend Stack
- **FastAPI** (Python 3.11+) with async/await
- **Supabase PostgreSQL** with Row Level Security (RLS) for multi-tenant isolation
- **Pydantic v2** for request/response validation
- **Pytest** + `pytest-asyncio` for unit/integration tests

**Architecture layers (mandatory):**
```
routes/ → services/ → repositories/ → Supabase
```
- `routes/` — HTTP endpoints, dependency injection
- `services/` — business logic, validation, orchestration
- `repositories/` — database queries via Supabase client
- `models/` — Pydantic schemas (request/response/internal)

### Database
- **Supabase PostgreSQL** with RLS for tenant isolation
- Migrations in `database/migrations/` (executed via Supabase SQL Editor or CLI)
- Schema documented in `database/schema.md`

## Development Workflow (ASDD)

1. **Create spec** — Write `.github/specs/<feature>.spec.md` or use `/generate-spec` skill
2. **Get APPROVED** — Spec must be marked APPROVED before implementation
3. **Implement** — Backend and frontend in parallel using `/implement-backend` or `/implement-frontend` skills
4. **Test** — Use `/unit-testing` skill for comprehensive test coverage
5. **QA** — Use `/gherkin-case-generator` or `/risk-identifier` skills

All specs live in `.github/specs/` with status marker (e.g., `# Status: APPROVED`).

## Key Patterns

### Frontend: RTK Query Data Fetching
```typescript
// src/store/api/clientApi.ts
export const clientApi = apiSlice.injectEndpoints({
  endpoints: (builder) => ({
    getClients: builder.query<Client[], void>({
      query: () => '/clients',
      // RTK Query handles auth headers via baseQuery
    }),
  }),
})

// In component
const { data: clients } = useGetClientsQuery()
```

Auth token automatically injected by RTK Query middleware configured in `store.ts`.

### Backend: Layered Request Handling
```python
# routes/client_router.py
@router.get("/clients")
async def list_clients(auth=Depends(verify_auth)):
    service = ClientService(ClientRepository(auth.user_id))
    return await service.list()

# services/client_service.py
async def list(self):
    return await self.repo.find_by_tenant(self.tenant_id)

# repositories/client_repository.py
async def find_by_tenant(self, tenant_id):
    # Direct Supabase queries via RLS
    return await self.db.from_("clients").select("*").eq("tenant_id", tenant_id).execute()
```

Multi-tenancy enforced via Supabase RLS — no manual tenant checks needed after auth.

### Environment Variables
Frontend: `VITE_*` prefix (used at build time via Vite)
- `VITE_API_URL` — backend API base URL
- `VITE_SUPABASE_URL` — Supabase project URL
- `VITE_SUPABASE_ANON_KEY` — Supabase public key

Backend: Loaded via Pydantic Settings (`app/config.py`)
- `SUPABASE_URL` — Supabase project URL
- `SUPABASE_ANON_KEY` — public key (used by frontend)
- `SUPABASE_SERVICE_ROLE` — secret key (admin operations)
- `ENVIRONMENT` — `development` or `production`
- `CORS_ORIGINS` — allowed domains

## Testing

### Frontend
```bash
cd frontend
npm test                  # single run
npm test:watch           # watch mode
npm test:ui              # interactive UI
```
Tests in `src/__tests__/` and `*.test.ts(x)` files. Mocking via `test-utils.tsx` which wraps Redux + Supabase.

### Backend
```bash
cd backend
pytest                    # all tests
pytest -v               # verbose
pytest tests/unit/      # unit tests only
pytest tests/integration/  # integration (needs supabase start)
pytest --cov           # coverage report
```
Tests organized: `tests/unit/` (mocked), `tests/integration/` (real DB).

## Common Tasks

### Add a new API endpoint (feature)
1. Write spec in `.github/specs/<feature>.spec.md`
2. Implement backend: create `routes/<feature>_router.py`, `services/<feature>_service.py`, `repositories/<feature>_repository.py`, `models/<feature>_model.py`
3. Implement frontend: create RTK Query endpoint in `store/api/<feature>Api.ts`, consume via hooks in components
4. Add tests: `tests/unit/routes/test_<feature>.py`, `tests/unit/services/test_<feature>.py` (backend); component tests (frontend)

### Run a single test
```bash
# Frontend
cd frontend && npm test -- src/__tests__/MyComponent.test.tsx

# Backend
cd backend && pytest tests/unit/services/test_client_service.py::test_create_client
```

### Lint/Format
Frontend: TypeScript type-checking via `npm run typecheck`
Backend: Ruff (linter/formatter) available; check `.ruff_cache/` for config

### Deploy
- **Frontend** — GitHub Pages via `.github/workflows/deploy.yml` (auto on merge to main)
- **Backend** — Railway (or Render) via Docker; set env vars in provider dashboard

## Rules & Constraints

- **Frontend**: TypeScript strict mode. RTK Query for all data fetching. No direct Axios calls in components.
- **Backend**: Async-first (FastAPI + asyncpg). Pydantic v2 for validation. RLS enforces multi-tenancy.
- **Database**: Migrations tracked in `database/migrations/`. Never mutate schema outside migrations.
- **Auth**: Supabase JWT-based. Token verified in backend via Supabase SDK.
- **API Versioning**: All backend routes prefixed `/api/v1/`
- **Specs**: Always APPROVED before implementation. Specs in `.github/specs/`.

## File Structure Reference
```
natillera-pwa/
├── frontend/
│   ├── src/
│   │   ├── App.tsx
│   │   ├── components/      # React components
│   │   ├── pages/           # Page components (SPA routes)
│   │   ├── hooks/           # Custom hooks
│   │   ├── store/
│   │   │   ├── store.ts     # Redux store config
│   │   │   ├── api/         # RTK Query endpoints (apiSlice + feature slices)
│   │   │   ├── slices/      # Auth, UI Redux slices
│   │   └── __tests__/       # Tests
│   └── vitest.config.ts
├── backend/
│   ├── app/
│   │   ├── main.py          # FastAPI app entry
│   │   ├── routes/          # HTTP endpoints
│   │   ├── services/        # Business logic
│   │   ├── repositories/    # DB queries (Supabase)
│   │   ├── models/          # Pydantic schemas
│   │   ├── middleware/      # Auth/CORS middleware
│   │   ├── config.py        # Settings
│   │   └── db.py            # Supabase client
│   ├── tests/
│   │   ├── unit/
│   │   └── integration/
│   └── requirements.txt
├── database/
│   ├── migrations/          # SQL schema files
│   └── schema.md
├── .github/
│   ├── specs/               # Feature specs (ASDD)
│   ├── workflows/           # CI/CD
│   └── qa/                  # QA reports
└── docs/
    └── runbooks/            # Operational docs
```

## Debugging Tips

- **Frontend Redux state**: Use Redux DevTools extension (auto-enabled in dev)
- **RTK Query cache**: Check Redux state under `state.apiSlice.queries`
- **Backend async issues**: Enable `logging` in FastAPI config, check uvicorn output for tracebacks
- **Supabase RLS bugs**: Test queries directly in Supabase SQL Editor with specific user auth token
- **CORS errors**: Verify `CORS_ORIGINS` in backend config matches frontend domain

## References

- AGENTS.md — existing command reference (less detailed)
- README.md — setup & deployment instructions
- database/schema.md — database structure
- .github/specs/ — feature specifications (source of truth for requirements)
