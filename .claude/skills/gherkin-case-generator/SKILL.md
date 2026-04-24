---
name: gherkin-case-generator
description: Mapea flujos críticos, genera escenarios Gherkin y define datos de prueba desde la spec. Output en docs/output/qa/.
argument-hint: "<nombre-feature>"
---

# Gherkin Case Generator

## Proceso
1. Lee spec: `.github/specs/<feature>.spec.md` — criterios de aceptación y reglas de negocio
2. Identifica flujos críticos (happy paths + error paths + edge cases)
3. Genera escenario Gherkin por cada criterio
4. Define datos de prueba sintéticos por escenario
5. Guarda en `docs/output/qa/<feature>-gherkin.md`

## Flujos críticos — identificar primero
| Tipo | Impacto | Incluir en |
|------|---------|-----------|
| Happy path principal | Alto | `@smoke @critico` |
| Validación de entrada | Medio | `@error-path` |
| Autorización / auth | Alto | `@smoke @seguridad` |
| Caso borde | Variable | `@edge-case` |

## Formato Gherkin

```gherkin
#language: es
Característica: [funcionalidad en lenguaje de negocio]

  @happy-path @critico
  Escenario: [flujo exitoso]
    Dado que [precondición de negocio]
    Cuando [acción del usuario]
    Entonces [resultado verificable]

  @error-path
  Escenario: [error esperado]
    Dado que [precondición]
    Cuando [acción inválida]
    Entonces [mensaje de error apropiado]
    Y [la operación NO se realiza]

  @edge-case
  Esquema del escenario: Validar <campo>
    Dado que el usuario ingresa "<valor>"
    Cuando intenta guardar
    Entonces el sistema muestra "<resultado>"
    Ejemplos:
      | valor | resultado              |
      | ""    | "Campo requerido"      |
      | "x"   | "Mínimo 3 caracteres"  |
```

## Datos de prueba — incluir en el documento
| Escenario | Campo | Válido | Inválido | Borde |
|-----------|-------|--------|----------|-------|
| [nombre]  | [campo] | [valor ok] | [valor ko] | [límite] |

## Reglas
- Lenguaje de negocio — sin rutas API ni IDs técnicos en el Gherkin
- Datos siempre sintéticos — NUNCA datos de producción
- Mínimo por HU: 1 happy path + 1 error + 1 edge case
