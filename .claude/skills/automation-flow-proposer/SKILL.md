---
name: automation-flow-proposer
description: Propone qué flujos automatizar, con qué framework, en qué orden y bajo qué criterios de ROI. Evalúa repetitividad, estabilidad, impacto y costo manual para priorizar la hoja de ruta de automatización.
argument-hint: "<nombre-feature | nombre-proyecto>"
---

# Skill: automation-flow-proposer [QA]

Identifica qué flujos tienen mejor ROI para automatizar y define la hoja de ruta.

## Los 4 criterios de automatización (TODOS deben cumplirse)

```
✅ REPETITIVO   — Se ejecuta frecuentemente (por release, sprint o diariamente)
✅ ESTABLE      — No cambia con frecuencia (> 1 sprint sin cambios significativos)
✅ ALTO IMPACTO — Su falla en producción tiene consecuencias importantes
✅ COSTO ALTO   — Ejecutarlo manualmente es costoso o propenso a error humano
```

## Matriz de priorización (ROI)

```markdown
| Flujo     | Repetitivo | Estable | Alto Impacto | Costo Manual | ROI | Prioridad |
|-----------|-----------|---------|--------------|--------------|-----|-----------|
| FLUJO-001 | ✅ Alta   | ✅ Sí  | ✅ Alta      | ✅ Alto      | 4/4 | P1        |
| FLUJO-002 | ✅ Alta   | ✅ Sí  | ⚠️ Media   | ✅ Alto      | 3/4 | P2        |
| FLUJO-006 | ❌ Baja  | ✅ Sí  | ✅ Alta      | ❌ Bajo     | 2/4 | P3        |
| FLUJO-007 | ✅ Alta   | ❌ No  | ⚠️ Media   | ✅ Alto      | 2/4 | Posponer  |
```

## Selección del framework

```
PARA APLICACIONES WEB (E2E):
  Playwright → Primera opción para stack JS/TS — multi-browser, CI-first
  Cypress    → Si ya existe en el proyecto

PARA APIs REST (sin UI):
  pytest + httpx → Para backend Python/FastAPI
  Supertest      → Para backends Node.js

PARA PERFORMANCE:
  k6             → Si hay SLAs definidos

CRITERIO:
  1. Concordancia con el stack tecnológico
  2. Curva de aprendizaje del equipo
  3. Integración con CI/CD actual
  4. Costo de mantenimiento a largo plazo
```

## Entregable: `automation-proposal.md`

Genera en `docs/output/qa/automation-proposal.md`:

```markdown
# Propuesta de Automatización — [Proyecto]

## Resumen Ejecutivo
Flujos candidatos: X | P1 (automatizar ya): X | P2: X | Posponer: X
Framework recomendado: [nombre + justificación]
Costo estimado de implementación: X sprints

## Hoja de Ruta (por prioridad)
### Sprint 1 — P1
- FLUJO-001: [nombre] — [estimación]
- FLUJO-004: [nombre] — [estimación]

### Sprint 2 — P2
- FLUJO-002: [nombre] — [estimación]

## DoR de Automatización
- [ ] Caso ejecutado manualmente con éxito (sin bugs críticos)
- [ ] Datos de prueba identificados y disponibles
- [ ] Ambiente estable
- [ ] Aprobación del equipo

## DoD de Automatización
- [ ] Código revisado por pares
- [ ] Integrado al pipeline CI
- [ ] Trazabilidad con HU mantenida
```
