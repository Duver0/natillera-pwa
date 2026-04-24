---
name: performance-analyzer
description: Analiza y define estrategias de performance testing. Clasifica pruebas en Load, Stress, Spike y Soak. Define SLAs, umbrales de alerta y el plan de ejecución con k6.
argument-hint: "<nombre-feature | nombre-proyecto>"
---

# Skill: performance-analyzer [QA]

Define y planifica pruebas de performance basadas en los SLAs del SPEC.

## Tipos de pruebas (según qa-guidelines CoE)

### Load Testing (Carga normal)
```
Propósito:  Comportamiento bajo la carga esperada en producción
Cuándo:     Antes de cada release con cambios en APIs de alto tráfico
Duración:   15-30 minutos
Patrón k6:  0 → 100 VUs (2min) → 100 VUs sostenido (15min) → 0 (2min)
```

### Stress Testing (Carga máxima)
```
Propósito:  Encontrar el punto de quiebre y validar degradación graceful
Cuándo:     Antes de lanzamientos importantes / eventos de alto tráfico
Duración:   30-60 minutos
Patrón k6:  0→100 (5min) → 200 (5min) → 300 (10min) → 400 VUs (10min)
```

### Spike Testing (Picos repentinos)
```
Propósito:  Verificar recuperación ante picos abruptos de tráfico
Cuándo:     Eventos programados (Black Friday, lanzamientos)
Duración:   20-30 minutos
Patrón k6:  50 VUs base → 800 VUs en 30s → 50 VUs base
```

### Soak Testing (Resistencia)
```
Propósito:  Detectar memory leaks, connection pool exhaustion
Cuándo:     Antes de releases mayores
Duración:   2-4 horas mínimo (requerimiento qa-guidelines: ≥ 120 min)
Patrón k6:  100 VUs constantes durante 2-4 horas
```

## Umbrales SLA base (adaptar a los del SPEC)

```javascript
export const thresholds = {
  'http_req_duration': [
    'p(50) < 200ms',    // mediana bajo 200ms
    'p(95) < 1000ms',   // 95% bajo 1 segundo (P95)
    'p(99) < 2000ms',   // 99% bajo 2 segundos
  ],
  'http_req_failed': ['rate < 0.01'],  // < 1% de errores
  'http_reqs': ['rate > 100'],         // > 100 TPS mínimo
};
```

## Entregable: `performance-plan.md`

Genera en `docs/output/qa/performance-plan.md`:

```markdown
# Plan de Performance — [Proyecto]

## SLAs Definidos
| Métrica    | Objetivo   | Mínimo Aceptable | Fuente        |
|------------|------------|------------------|---------------|
| P95        | < 500ms    | < 1000ms         | [HU o contrato]|
| TPS        | > 200      | > 100            | [HU o contrato]|
| Error rate | < 0.1%     | < 1%             | Estándar CoE  |

## Pruebas Planificadas
| Tipo  | Endpoint(s) | VUs    | Duración | Trigger            |
|-------|------------|--------|----------|--------------------|
| Load  | POST /faq  | 100    | 20 min   | Pre-release        |
| Soak  | GET /faq   | 50     | 2 horas  | Release mayor      |

## Ambiente y Datos
- Ambiente: staging (NO producción)
- Datos: sintéticos, creados con fixtures de test
- Brecha de capacidad documentada: [staging vs producción]
```

## Reglas CoE

- Línea base de performance OBLIGATORIA en pipeline CI
- Scripts con datos de un solo uso — sin texto plano de secretos
- Correlacionar reportes con CPU/RAM del servidor
- Duración mínima de soak: 120 minutos
