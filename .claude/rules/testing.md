---
description: Principios de testing. Aplica a cualquier framework. Framework: pytest (backend) + Vitest (frontend).
paths:
  - "**/tests/**"
  - "**/__tests__/**"
  - "**/*.test.*"
  - "**/*.spec.*"
  - "**/test_*.py"
---

# Reglas de Testing

## Referencia de Stack
Lee `.claude/rules/backend.md` para:
- Framework de testing del proyecto (pytest, Jest, Vitest, JUnit, etc.)
- Herramientas de mock y fixtures
- Comandos para ejecutar tests

## Principios Universales (independiente del framework)

### Estructura AAA obligatoria
```
// GIVEN — preparar datos y contexto
// WHEN  — ejecutar la acción bajo prueba
// THEN  — verificar el resultado esperado
```

### Pirámide de Testing
| Nivel | % recomendado | Qué cubre |
|-------|--------------|-----------|
| **Unitarios** | ~70% | Lógica de negocio aislada con mocks |
| **Integración** | ~20% | Flujos entre capas, endpoints HTTP |
| **E2E** | ~10% | Flujos críticos de usuario |

### Reglas de Oro del Testing
- **Independencia** — cada test se puede ejecutar solo, en cualquier orden
- **Aislamiento** — mockear SIEMPRE dependencias externas (DB, APIs, auth, tiempo)
- **Determinismo** — sin `sleep()`, sin dependencia de fechas reales, sin datos de producción
- **Cobertura mínima ≥ 80%** en lógica de negocio (quality gate bloqueante en CI)
- **Nombres descriptivos** — `test_<función>_<escenario>_<resultado_esperado>`
- **Un assert lógico por test** — si necesitas varios, separar en tests distintos

### Por cada unidad cubrir
- ✅ Happy path — datos válidos, flujo exitoso
- ❌ Error path — excepción esperada, respuesta de error
- 🔲 Edge case — vacío, duplicado, límites, permisos

## Anti-patrones Prohibidos
- Tests que dependen del orden de ejecución
- Llamadas reales a servicios externos (DB, APIs, auth)
- `console.log` / `print` permanentes en tests
- Lógica condicional dentro de un test (if/else)
- Datos de producción real en fixtures

## Estrategia de Regresión
- **Smoke suite** (`@smoke`): happy paths críticos → corre en cada PR
- **Regresión completa** (`@regression`): todo → corre nightly o pre-release
- Un test con `@critico` entra automáticamente al smoke suite
