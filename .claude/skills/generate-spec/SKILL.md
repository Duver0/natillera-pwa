---
name: generate-spec
description: Genera una spec técnica ASDD en .github/specs/<feature>.spec.md. Obligatorio antes de cualquier implementación.
argument-hint: "<nombre-feature>: <descripción del requerimiento>"
---

# Generate Spec

## Definition of Ready — validar antes de generar

Una historia puede generar spec solo si cumple:

- [ ] Estructura **Como / Quiero / Para que** completa
- [ ] Términos canónicos del dominio (ver `CLAUDE.md` → Diccionario de Dominio)
- [ ] Criterios BDD: **Dado / Cuando / Entonces** (feliz + validaciones + errores)
- [ ] Contrato API explícito si aplica (método, ruta `/api/v1/...`, request, response, códigos HTTP)
- [ ] Alineada con arquitectura y stack (ver `.claude/rules/backend.md`, `frontend.md`, `database.md`)
- [ ] Dependencias y riesgos identificados

Si el requerimiento no cumple el DoR → listar las preguntas pendientes antes de generar.

## Proceso

1. Busca requerimiento en `.github/requirements/<feature>.md` (si existe, úsalo)
2. Lee las rules: `.claude/rules/backend.md`, `.claude/rules/frontend.md`, `.claude/rules/database.md`
3. Explora código existente — no duplicar modelos ni endpoints existentes
4. Valida DoR (arriba) — si hay ambigüedades, lista preguntas antes de continuar
5. Usa plantilla: `.github/skills/generate-spec/spec-template.md` EXACTAMENTE
6. Guarda en `.github/specs/<nombre-en-kebab-case>.spec.md`

## Frontmatter obligatorio

```yaml
---
id: SPEC-###
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

- `## 1. REQUERIMIENTOS` — HU (Como/Quiero/Para) + criterios Gherkin + reglas de negocio
- `## 2. DISEÑO` — modelos de datos, endpoints API (request/response/HTTP codes), frontend
- `## 3. LISTA DE TAREAS` — checklists backend `[ ]`, frontend `[ ]`, QA `[ ]`

## Restricciones

- Solo leer + crear. No modificar código existente.
- Status siempre `DRAFT`. El usuario aprueba antes de implementar.
