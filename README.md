# Natillera PWA

Aplicación PWA multi-tenant para gestión de créditos, clientes y pagos de natilleras.

## Stack

- **Frontend**: React 18 + TypeScript + Vite + Redux Toolkit (RTK Query) + React Router v6 + TailwindCSS + vite-plugin-pwa
- **Backend**: FastAPI (Python) + Pydantic
- **DB / Auth**: Supabase (PostgreSQL + Row Level Security)
- **Tests**: Pytest (backend), Vitest + Testing Library (frontend)

## Estructura

```
natillera-pwa/
├── backend/            # FastAPI app
│   ├── app/
│   │   ├── routes/     # endpoints HTTP
│   │   ├── services/   # lógica de negocio
│   │   └── models/
│   └── tests/
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   ├── components/
│   │   ├── store/      # RTK slices + apiSlice
│   │   └── __tests__/
│   └── public/
├── database/
│   ├── migrations/     # SQL schema changes
│   └── schema.md
├── docs/runbooks/
├── scripts/
└── .github/
    ├── specs/          # specs ASDD
    └── qa/             # reportes QA
```

## Setup

### Requisitos
- Node 18+
- Python 3.11+
- Supabase CLI (para desarrollo local)

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # completar SUPABASE_URL, SUPABASE_ANON_KEY, SUPABASE_SERVICE_ROLE
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
cp .env.example .env   # completar VITE_API_URL, VITE_SUPABASE_URL, VITE_SUPABASE_ANON_KEY
npm run dev
```

### Base de datos

```bash
supabase start
# Aplicar migrations de database/migrations/
```

## Tests

```bash
# Backend
cd backend && pytest

# Frontend
cd frontend && npm test

# Integration (requiere supabase start)
cd backend && pytest tests/integration/
```

## Flujo ASDD

El proyecto sigue Agent-Spec-Driven Development:

1. Spec aprobada en `.github/specs/<feature>.spec.md`
2. Implementación backend ∥ frontend
3. Tests unitarios ∥
4. QA final en `.github/qa/`

## Roadmap

- ✅ **Semana 1**: Auth multi-tenant + setup inicial
- ✅ **Semana 2**: CRUD clientes, créditos, pagos, dashboard, PWA shell
- ⏳ **Semana 3**: Por definir

Reportes en `.github/qa/week-*-report.md`.
