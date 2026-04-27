# AGENTS.md

## Commands

### Frontend
```bash
cd frontend
npm install
npm run dev        # dev server at localhost:5173
npm run build      # tsc && vite build
npm test           # vitest run
```

### Backend
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
pytest              # run tests
```

### Integration tests
Requires `supabase start` first:
```bash
cd backend && pytest tests/integration/
```

## Architecture

- **Frontend**: `frontend/src/` - React + RTK + React Router. Entry: `main.tsx`
- **Backend**: `backend/app/` - FastAPI. Entry: `app/main.py`
- **DB**: Supabase (local via `supabase start` + migrations in `database/migrations/`)

## ASDD Workflow

This repo uses the Agent Spec Software Development framework. **Always start with a spec**:

1. Generate spec: Use skill `/generate-spec <feature-name>` or write `.github/specs/<feature>.spec.md`
2. Get spec APPROVED before implementation
3. Implement: Use `/implement-backend` or `/implement-frontend` skills
4. Test: Use `/unit-testing` skill
5. QA: Use `/gherkin-case-generator` or `/risk-identifier` skills

## Setup Required

Both frontend and backend need `.env` files created from `.env.example`:

- **Frontend**: `VITE_API_URL`, `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`
- **Backend**: `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE`

## Key Files

- `.claude/skills/` - Available /commands for ASDD workflow
- `.claude/rules/` - Auto-injected context rules
- `.github/specs/` - Feature specifications
- `docs/output/qa/` - QA artifacts