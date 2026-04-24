# ASDD Framework — Guía de Uso (Claude Code)

**ASDD** (Agent Spec Software Development) es un framework de desarrollo asistido por IA que organiza el trabajo de software en cinco fases orquestadas por agentes especializados.

```
Requerimiento → Spec → [Backend ∥ Frontend ∥ DB] → [Tests BE ∥ Tests FE] → QA → Doc (opcional)
```

> Esta guía cubre el uso con **Claude Code CLI**.
> Para uso con **GitHub Copilot Chat**, ver `.github/README.md`.

---

## Requisitos

| Requisito | Detalle |
|---|---|
| Claude Code CLI | Instalado y autenticado (`claude`) |
| Modelo recomendado | `claude-sonnet-4-6` (configurado en `settings.json`) |
| Permisos | `acceptEdits` activado en `settings.json` |

El archivo `.claude/settings.json` ya configura modelo, permisos y hooks. No requiere configuración manual adicional.

---

## Onboarding — nuevo proyecto

Al copiar esta carpeta `.claude/` a un proyecto nuevo, adapta estos archivos **en orden** antes de usar cualquier agente:

| # | Archivo | Qué escribir |
|---|---------|-------------|
| 1 | `README.md` (raíz del proyecto) | Stack, arquitectura, comandos (`install`, `dev`, `test`, `build`), variables de entorno |
| 2 | `.claude/rules/backend.md + frontend.md` | Lenguaje, framework, base de datos, herramientas aprobadas |
| 3 | `.claude/rules/backend.md + frontend.md` | Capas, módulos, bounded contexts |
| 4 | `CLAUDE.md (Diccionario de Dominio)` | Términos canónicos del negocio (glosario) |
| 5 | `CLAUDE.md` (DoR + DoD ya incluidos) | Criterios DoR y DoD del equipo |

Una vez completados, los agentes tienen todo el contexto para operar de forma autónoma.

**No modificar**: `agents/`, `skills/`, `rules/`, `hooks/`

---

## El flujo ASDD paso a paso

### Paso 1 — Spec (obligatorio, siempre primero)

Genera la especificación técnica antes de escribir código:

```
/generate-spec <nombre-feature>
```

O invoca el agente directamente en el chat:
```
@orchestrator genera la spec para: [tu requerimiento]
```

El agente valida el requerimiento y genera `.github/specs/<feature>.spec.md` con estado `DRAFT`.
Revisa y aprueba la spec (cambia a `APPROVED`) antes de continuar.

---

### Paso 2 — Implementación (paralelo)

Con la spec `APPROVED`, el Orchestrator lanza backend, frontend y base de datos en paralelo:

```
/asdd-orchestrate <nombre-feature>
```

O invoca agentes individuales si prefieres control manual:
```
@backend-developer implementa .github/specs/<feature>.spec.md
@frontend-developer implementa .github/specs/<feature>.spec.md
@database-agent diseña el modelo de datos para .github/specs/<feature>.spec.md
```

> **database-agent** solo es necesario si hay cambios en el modelo de datos.

---

### Paso 3 — Tests (paralelo)

Con la implementación completa:

```
/unit-testing <nombre-feature>
```

O invoca cada agente por separado:
```
@test-engineer-backend genera tests para .github/specs/<feature>.spec.md
@test-engineer-frontend genera tests para .github/specs/<feature>.spec.md
```

---

### Paso 4 — QA

```
@qa-agent ejecuta QA para .github/specs/<feature>.spec.md
```

El agente genera: casos Gherkin, matriz de riesgos y (si hay SLAs) plan de performance.

---

### Paso 5 — Documentación *(opcional)*

```
@documentation-agent documenta .github/specs/<feature>.spec.md
```

---

### Flujo completo con Orchestrator

```
/asdd-orchestrate <nombre-feature>
```

El Orchestrator coordina todas las fases con máximo paralelismo automáticamente.

---

## Agentes disponibles (`.claude/agents/`)

| Agente | Fase | Cómo invocar |
|---|---|---|
| `orchestrator` | Entry point | `@orchestrator` o `/asdd-orchestrate` |
| `spec-generator` | Fase 1 | `@spec-generator` o `/generate-spec` |
| `backend-developer` | Fase 2 ∥ | `@backend-developer` o `/implement-backend` |
| `frontend-developer` | Fase 2 ∥ | `@frontend-developer` o `/implement-frontend` |
| `database-agent` | Fase 2 ∥ | `@database-agent` |
| `test-engineer-backend` | Fase 3 ∥ | `@test-engineer-backend` o `/unit-testing` |
| `test-engineer-frontend` | Fase 3 ∥ | `@test-engineer-frontend` o `/unit-testing` |
| `qa-agent` | Fase 4 | `@qa-agent` |
| `documentation-agent` | Fase 5 | `@documentation-agent` |

---

## Skills disponibles (`/comando` en Claude Code)

| Comando | Agente | Qué hace |
|---|---|---|
| `/asdd-orchestrate` | orchestrator | Orquesta el flujo completo o muestra estado actual |
| `/generate-spec` | spec-generator | Genera spec técnica con validación INVEST/IEEE 830 |
| `/implement-backend` | backend-developer | Implementa feature completo en el backend |
| `/implement-frontend` | frontend-developer | Implementa feature completo en el frontend |
| `/unit-testing` | test-engineers | Genera suite de tests (backend + frontend) |
| `/gherkin-case-generator` | qa-agent | Flujos críticos + casos Given-When-Then + datos de prueba |
| `/risk-identifier` | qa-agent | Matriz de riesgos ASD (Alto/Medio/Bajo) |
| `/automation-flow-proposer` | qa-agent | Propone flujos a automatizar con estimación de ROI |
| `/performance-analyzer` | qa-agent | Planifica pruebas de carga y performance |

---

## Rules automáticas (`.claude/rules/`)

Inyectadas automáticamente en el contexto de Claude según el archivo activo:

| Archivo activo | Rule aplicada |
|---|---|
| `backend/**` / `server/**` / `api/**` | `rules/backend.md` |
| `frontend/**` | `rules/frontend.md` |
| Cualquier archivo de modelo/DB | `rules/database.md` |
| `backend/tests/**` / `frontend/src/__tests__/**` | `rules/testing.md` |
| `.github/specs/**` | `rules/specs.md` |

> Las rules son agnosticas de stack. Los detalles del stack real están en `.claude/rules/backend.md + frontend.md`.

---

## Hooks activos (`.claude/hooks/`)

Ejecutados automáticamente por Claude Code según el evento:

| Script | Evento | Acción |
|---|---|---|
| `pre-edit-protection.sh` | `PreToolUse` (Edit/Write) | Bloquea edición de archivos sensibles (`.env`, secrets) |
| `post-spec-validate.sh` | `PostToolUse` (Write/Edit) | Valida frontmatter en archivos `.spec.md` |
| `scripts/notify-sound.sh` | `Stop` / `SubagentStop` / `Notification` | Notificación de sonido al terminar |

Ver `.claude/hooks/README.md` para documentación completa y cómo agregar hooks nuevos.

---

## Lineamientos de referencia

Cargados por los agentes desde `docs/` (proyecto):

| Documento | Contenido |
|---|---|
| `.claude/docs/lineamientos/dev-guidelines.md` | Clean Code, SOLID, API REST, Seguridad, Observabilidad |
| `.claude/docs/lineamientos/qa-guidelines.md` | Estrategia QA, Gherkin, Riesgos, Automatización, Performance |
| `.claude/rules/backend.md + frontend.md` | Stack, herramientas aprobadas, versiones |
| `.claude/rules/backend.md + frontend.md` | Capas, estructura, patrones del proyecto |

---

## Estructura de carpetas

```
Project Root/
│
├── docs/output/                     ← artefactos generados por los agentes
│   ├── qa/                          ← Gherkin, riesgos, performance
│   ├── api/                         ← documentación de API
│   └── adr/                         ← Architecture Decision Records
│       ├── qa/
│       ├── api/
│       └── adr/
│
└── .claude/                         ← framework Claude Code (auto-contenido para compartir)
    ├── README.md                    ← este archivo
    ├── settings.json                ← modelo, permisos, hooks
    ├── settings.local.json          ← overrides locales (no commitar)
    │
    ├── agents/                      ← 9 agentes (sub-agentes de Claude Code)
    │   ├── orchestrator.md
    │   ├── spec-generator.md
    │   ├── backend-developer.md
    │   ├── frontend-developer.md
    │   ├── database-agent.md
    │   ├── test-engineer-backend.md
    │   ├── test-engineer-frontend.md
    │   ├── qa-agent.md
    │   └── documentation-agent.md
    │
    ├── skills/                      ← 9 skills (/comando en Claude Code)
    │   ├── asdd-orchestrate/
    │   ├── generate-spec/
    │   ├── implement-backend/
    │   ├── implement-frontend/
    │   ├── unit-testing/
    │   ├── gherkin-case-generator/
    │   ├── risk-identifier/
    │   ├── automation-flow-proposer/
    │   └── performance-analyzer/
    │
    ├── rules/                       ← instrucciones automáticas por path
    │   ├── backend.md               ← backend/**, server/**, api/**
    │   ├── frontend.md              ← frontend/**
    │   ├── database.md              ← models/**, repositories/**
    │   ├── testing.md               ← tests/**, __tests__/**
    │   └── specs.md                 ← .github/specs/**
    │
    ├── docs/lineamientos/           ← guidelines del framework (incluidos al compartir)
    │   ├── dev-guidelines.md
    │   └── qa-guidelines.md
    │
    ├── hooks/                       ← scripts automáticos por evento
    │   ├── pre-edit-protection.sh
    │   └── post-spec-validate.sh
    │
    └── scripts/                     ← utilidades del framework
        ├── notify-sound.bat
        └── notify-sound.sh
```

> Los archivos de contexto del proyecto viven en `docs/` (raíz del proyecto).
> `.claude/` contiene solo metodología — agents, skills, rules, hooks.

---

## Reglas de Oro

1. **No código sin spec aprobada** — siempre debe existir `.github/specs/<feature>.spec.md` con estado `APPROVED`.
2. **No código no autorizado** — los agentes no generan ni modifican código sin instrucción explícita.
3. **No suposiciones** — si el requerimiento es ambiguo, el agente pregunta antes de actuar.
4. **Transparencia** — el agente explica qué va a hacer antes de hacerlo.
