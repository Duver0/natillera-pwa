---
name: risk-identifier
description: Identifica y clasifica riesgos de calidad usando la Regla ASD (Alto=obligatorio, Medio=recomendado, Bajo=opcional). Analiza el SPEC para detectar complejidad, integraciones, datos sensibles y flujos críticos.
argument-hint: "<nombre-feature | nombre-proyecto>"
---

# Skill: risk-identifier [QA]

Identifica y prioriza riesgos de calidad usando la Regla ASD del CoE.

## Regla ASD

```
NIVEL ALTO (A)   → Testing OBLIGATORIO — bloquea el release
NIVEL MEDIO (S)  → Testing RECOMENDADO — documentar si se omite
NIVEL BAJO (D)   → Testing OPCIONAL — priorizar en el backlog
```

## Factores de riesgo

### → ALTO
| Factor | Razón |
|--------|-------|
| Manejo de pagos o saldos | Impacto financiero directo |
| Datos personales (GDPR) | Obligación legal |
| Autenticación/autorización | Compromete toda la seguridad |
| Operaciones destructivas irrecuperables | Sin rollback posible |
| Integraciones con sistemas externos | Dependencia no controlada |
| SLA contractuales | Obligación con el cliente |

### → MEDIO
| Factor | Razón |
|--------|-------|
| Lógica de negocio compleja | Alta probabilidad de defectos |
| Componentes con muchas dependencias | Cambio impacta múltiples áreas |
| Código nuevo sin historial | Sin métricas de confiabilidad |
| Funcionalidades de alta frecuencia de uso | Impacto en muchos usuarios |

### → BAJO
| Factor | Razón |
|--------|-------|
| Features internas o administrativas | Impacto limitado |
| Ajustes estéticos de UI | Sin impacto funcional |
| Refactorizaciones sin cambio de lógica | Sin cambio de comportamiento |

## Entregable: `risk-matrix.md`

Genera en `docs/output/qa/risk-matrix.md`:

```markdown
# Matriz de Riesgos — [Nombre del Proyecto]

## Resumen
Total: X | Alto (A): X | Medio (S): X | Bajo (D): X

## Detalle
| ID    | HU     | Descripción del Riesgo       | Factores       | Nivel | Testing      |
|-------|--------|------------------------------|----------------|-------|--------------|
| R-001 | HU-002 | [descripción]                | [factores]     | A     | Obligatorio  |
| R-002 | HU-003 | [descripción]                | [factores]     | S     | Recomendado  |

## Plan de Mitigación — Riesgos ALTO

### R-001: [descripción]
- **Mitigación**: [controles técnicos]
- **Tests obligatorios**: [tipos de tests a generar]
- **Bloqueante para release**: ✅ Sí
```

## Proceso

1. Leer spec completa en `.github/specs/<feature>.spec.md`
2. Por cada HU y endpoint → evaluar factores de riesgo
3. Asignar nivel ASD con justificación
4. Generar matriz de riesgos
5. Para todos los ALTO → detallar plan de mitigación
