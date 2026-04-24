---
description: Reglas de formato y ciclo de vida para archivos spec. Se cargan cuando se trabaja en specs o requerimientos.
paths:
  - ".github/specs/**"
  - ".github/requirements/**"
---

# Reglas de Gestión de Specs — ASDD

## Ciclo de vida obligatorio

```
DRAFT → APPROVED → IN_PROGRESS → IMPLEMENTED → DEPRECATED
```

| Estado | Quién lo asigna | Condición |
|--------|----------------|-----------|
| `DRAFT` | spec-generator | Spec recién generada, pendiente de revisión |
| `APPROVED` | Usuario / Tech Lead | Spec revisada y aprobada para implementar |
| `IN_PROGRESS` | orchestrator | Implementación iniciada |
| `IMPLEMENTED` | orchestrator | Código + tests + QA completos |
| `DEPRECATED` | Usuario | Feature descartado o reemplazado |

**Regla de oro: NUNCA escribir código de implementación si la spec no está en estado `APPROVED`.**

## Frontmatter obligatorio en toda spec

```yaml
---
id: SPEC-001
status: DRAFT
feature: nombre-del-feature
created: YYYY-MM-DD
updated: YYYY-MM-DD
author: spec-generator
version: "1.0"
related-specs: []
---
```

## Secciones obligatorias

Toda spec DEBE tener estas tres secciones:

### 1. REQUERIMIENTOS
- Descripción del feature
- Historias de usuario (Como / Quiero / Para que)
- Criterios de aceptación en Gherkin (Dado / Cuando / Entonces)
- Reglas de negocio

### 2. DISEÑO
- Modelos de datos (MongoDB — campos, tipos, validaciones)
- API Endpoints (método, ruta, request, response, códigos HTTP)
- Diseño frontend (páginas, componentes, hooks, services)
- Arquitectura y dependencias

### 3. LISTA DE TAREAS
- Checklist backend (implementación + tests)
- Checklist frontend (implementación + tests)
- Checklist QA (Gherkin, cobertura, validación)

## Nombre de archivo

```
.github/specs/<nombre-feature-en-kebab-case>.spec.md

# Ejemplos correctos:
.github/specs/dark-mode-toggle.spec.md
.github/specs/faq-management.spec.md
.github/specs/user-profile-update.spec.md

# Incorrecto:
.github/specs/DarkMode.spec.md      # no PascalCase
.github/specs/dark_mode.spec.md     # no snake_case
```

## Transición de estado

Al aprobar una spec (DRAFT → APPROVED):
```yaml
status: APPROVED
updated: 2026-03-12
```

Al iniciar implementación (APPROVED → IN_PROGRESS):
```yaml
status: IN_PROGRESS
updated: 2026-03-12
```

Al completar (IN_PROGRESS → IMPLEMENTED):
```yaml
status: IMPLEMENTED
updated: 2026-03-12
```

## Requerimientos (`.github/requirements/`)

Los archivos de requerimientos son **pre-specs** en lenguaje de negocio:
- Sin diseño técnico
- Formato libre o structured user story
- Input para `spec-generator`
- Se archivan (no se eliminan) al generar la spec

```
.github/requirements/<nombre-feature>.md
```
