# Natillera PWA

Aplicación PWA multi-tenant para gestión de créditos, clientes y pagos de natilleras.

## Stack

- **Frontend**: React 18 + TypeScript + Vite + Redux Toolkit (RTK Query) + React Router v6 + TailwindCSS + vite-plugin-pwa
- **Backend**: FastAPI (Python) + Pydantic
- **DB / Auth**: Supabase (PostgreSQL + Row Level Security)
- **Hosting**:
  - Frontend: GitHub Pages
  - Backend: Railway
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

### 1. Supabase (crear manualmente)

1. Crea cuenta en supabase.com
2. Crea un nuevo proyecto
3. En **Project Settings → API**:
   - Copia la **Project URL** → `SUPABASE_URL`
   - Copia la **anon public** key → `SUPABASE_ANON_KEY`
   - Copia la **service_role** key (cuidado: solo para backend) → `SUPABASE_SERVICE_ROLE`
4. Ejecuta las migraciones en `database/migrations/` desde el SQL Editor de Supabase

### 2. GitHub Pages (Frontend)

1. Ve a Settings → Pages
2. En "Build and deployment" → Source: **GitHub Actions**
3. No necesitas configurar nada más

### 3. Railway/Render (Backend - opcional)

1. Crea cuenta en railway.app o render.com
2. Connect tu repositorio de GitHub
3. Configura las variables de entorno en el panel del servicio

---

## Servicios Externos

### Supabase (Base de datos + Auth)

**Cuenta:** supabase.com

| Recurso | Configuración |
|---------|---------------|
| Proyecto | Crear nuevo proyecto |
| Database | Ejecutar migraciones de `database/migrations/` |
| API Keys | Project Settings → API |

**Keys obtenidas:**
- `SUPABASE_URL` - Project URL
- `SUPABASE_ANON_KEY` - anon public key
- `SUPABASE_SERVICE_ROLE` - service_role key (secreta)

---

### GitHub Pages (Frontend)

**Cuenta:** github.com (tu cuenta)

| Configuración | Valor |
|---------------|-------|
| Repository | Settings → Pages |
| Source | GitHub Actions |
| Dominio | `https://duver0.github.io/natillera-pwa` |

**Variables GitHub Actions:**
| Variable | Valor |
|----------|-------|
| `VITE_API_URL` | URL del backend (Railway) |
| `VITE_SUPABASE_URL` | URL de Supabase |
| `VITE_SUPABASE_ANON_KEY` | Anon key |

---

### Railway (Backend)

**Cuenta:** railway.app

| Configuración | Valor |
|---------------|-------|
| Repo | Connect desde GitHub |
| Root Directory | `backend` |
| Docker | Usa `backend/Dockerfile` |

**Variables en Railway:**
| Variable | Valor |
|----------|-------|
| `ENVIRONMENT` | `production` |
| `SUPABASE_URL` | URL de Supabase |
| `SUPABASE_SERVICE_ROLE` | Service role key |
| `SUPABASE_ANON_KEY` | Anon key |
| `CORS_ORIGINS` | `["https://duver0.github.io"]` |
| `SAVINGS_RATE` | `10.0` |

**Secrets GitHub Actions:**
| Secret | Descripción |
|--------|-------------|
| `RAILWAY_TOKEN` | Railway Account Settings → Tokens |
| `RAILWAY_SERVICE_ID` | ID del servicio en Railway |

---

## Variables que DEBES crear manualmente

### GitHub (Settings → Secrets and variables → Actions)

**Secrets (confidenciales):**

| Secret | Descripción | Ejemplo |
|--------|-------------|---------|
| `SUPABASE_SERVICE_ROLE` | Service role key de Supabase | `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...` |
| `RAILWAY_TOKEN` | Token de Railway (si usas Railway) | `railway_p...` |
| `RAILWAY_SERVICE_ID` | ID del servicio en Railway | `abc123...` |

**Variables (públicas):**

| Variable | Valor |
|----------|-------|
| `VITE_API_URL` | URL del backend (ej: `https://tu-backend.railway.app`) |
| `VITE_SUPABASE_URL` | `https://udqyhsefshijnzktwbds.supabase.co` |
| `VITE_SUPABASE_ANON_KEY` | `sb_publishable_VbAiz6-aTC72qZXQNXngag_GSPxsDAh` |

### Railway/Render (panel del servicio)

Configura estas variables en el dashboard de tu proveedor:

| Variable | Valor |
|----------|-------|
| `ENVIRONMENT` | `production` |
| `SUPABASE_URL` | `https://udqyhsefshijnzktwbds.supabase.co` |
| `SUPABASE_SERVICE_ROLE` | Tu service role key |
| `SUPABASE_ANON_KEY` | `sb_publishable_VbAiz6-aTC72qZXQNXngag_GSPxsDAh` |
| `CORS_ORIGINS` | `["https://duver0.github.io"]` |
| `SAVINGS_RATE` | `10.0` |

---
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

## Deployment

### Frontend → GitHub Pages

El frontend se despliega automáticamente a GitHub Pages con el workflow `.github/workflows/deploy.yml`.

**Configuración:**
1. Ve a Settings → Pages
2. En "Build and deployment" → Source: **GitHub Actions**
3. Los secrets necesarios están configurados en el workflow

### Backend → Railway/Render/Fly.io

El backend (FastAPI) requiere un servicio que soporte Python. Opciones recomendadas:

**Railway (recomendado):**
1. Crea cuenta en railway.app
2. Connect tu repo de GitHub
3. Configura las variables de entorno:
   - `ENVIRONMENT=production`
   - `SUPABASE_URL` → tu URL de Supabase
   - `SUPABASE_SERVICE_ROLE` → tu service role key
   - `SUPABASE_ANON_KEY` → tu anon key
   - `CORS_ORIGINS=["https://tu-dominio.github.io"]`
   - `SAVINGS_RATE=10.0`
4. Railway detectará FastAPI y hará el deploy automático

**Render:**
1. Crea cuenta en render.com
2. Connect tu repo
3. Configura同样的 variables de entorno

### Variables de entorno en producción

| Variable | Descripción |
|----------|-------------|
| `ENVIRONMENT` | `production` |
| `SUPABASE_URL` | URL de tu proyecto Supabase |
| `SUPABASE_ANON_KEY` | Anon key (pública) |
| `SUPABASE_SERVICE_ROLE` | Service role key (secreta) |
| `CORS_ORIGINS` | Dominios permitidos, ej: `["https://user.github.io"]` |
| `SAVINGS_RATE` | Porcentaje de ahorro (default: 10.0) |

## Running with Docker

```bash
# 1. Copy and configure environment variables
cp .env.example .env
# Edit .env with your Supabase credentials

# 2. Start all services
docker compose up --build

# 3. Access the app
# Frontend: http://localhost:5173
# Backend: http://localhost:8000
# Backend health: http://localhost:8000/health
```

### Notes

- Uses Supabase cloud (not local PostgreSQL) — Configure `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE` in `.env`
- Frontend accesses backend via `http://backend:8000` inside Docker network
- Backend exposes health endpoint at `/health`
