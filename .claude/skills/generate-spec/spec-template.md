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

# Spec: [Nombre de la Funcionalidad]

> **Estado:** `DRAFT` → aprobar con `status: APPROVED` antes de iniciar implementación.
> **Ciclo de vida:** DRAFT → APPROVED → IN_PROGRESS → IMPLEMENTED → DEPRECATED

---

## 1. REQUERIMIENTOS

### Descripción
Resumen de la funcionalidad en 2-3 oraciones. Qué hace, para quién y qué problema resuelve.

### Requerimiento de Negocio
El requerimiento original tal como fue proporcionado por el usuario (o copiado de `.github/requirements/<feature>.md`).

### Historias de Usuario

#### HU-01: [Título descriptivo corto]

```
Como:        [rol del usuario — ej. Usuario autenticado, Administrador]
Quiero:      [acción o funcionalidad concreta]
Para:        [valor o beneficio esperado por el negocio]

Prioridad:   Alta / Media / Baja
Estimación:  XS / S / M / L / XL
Dependencias: HU-X, HU-Y o Ninguna
Capa:        Backend / Frontend / Ambas
```

#### Criterios de Aceptación — HU-01

**Happy Path**
```gherkin
CRITERIO-1.1: [nombre del escenario exitoso]
  Dado que:  [contexto inicial válido]
  Cuando:    [acción del usuario]
  Entonces:  [resultado esperado verificable]
```

**Error Path**
```gherkin
CRITERIO-1.2: [nombre del escenario de error]
  Dado que:  [contexto inicial]
  Cuando:    [acción inválida o datos incorrectos]
  Entonces:  [manejo del error esperado con código HTTP y mensaje]
```

**Edge Case** *(si aplica)*
```gherkin
CRITERIO-1.3: [nombre del caso borde]
  Dado que:  [contexto de borde]
  Cuando:    [acción en el límite]
  Entonces:  [resultado esperado en el límite]
```

### Reglas de Negocio
1. Regla de validación (ej. "el campo X es obligatorio y no puede superar 100 caracteres")
2. Regla de autorización (ej. "solo el Administrador puede eliminar")
3. Regla de integridad (ej. "el nombre debe ser único")

---

## 2. DISEÑO

### Modelos de Datos

#### Entidades afectadas
| Entidad | Almacén | Cambios | Descripción |
|---------|---------|---------|-------------|
| `FeatureEntity` | tabla/colección `features` | nueva / modificada | descripción del recurso |

#### Campos del modelo
| Campo | Tipo | Obligatorio | Validación | Descripción |
|-------|------|-------------|------------|-------------|
| `id` | string / UUID | sí | auto-generado | Identificador único |
| `name` | string | sí | max 100 chars | Nombre del recurso |
| `description` | string | no | max 500 chars | Descripción |
| `created_at` | datetime (UTC) | sí | auto-generado | Timestamp creación |
| `updated_at` | datetime (UTC) | sí | auto-generado | Timestamp actualización |

#### Índices / Constraints
- Listar índices necesarios con su justificación de uso (búsqueda frecuente, unicidad, etc.)

### API Endpoints

#### POST /api/v1/[features]
- **Descripción**: Crea un nuevo recurso
- **Auth requerida**: sí / no
- **Request Body**:
  ```json
  { "name": "string", "description": "string (opcional)" }
  ```
- **Response 201**:
  ```json
  { "id": "uuid", "name": "string", "created_at": "iso8601", "updated_at": "iso8601" }
  ```
- **Response 400**: campo obligatorio faltante o inválido
- **Response 401**: token ausente o expirado
- **Response 409**: conflicto de unicidad

#### GET /api/v1/[features]
- **Descripción**: Lista todos los recursos
- **Auth requerida**: sí / no
- **Response 200**: `[{ "id": "uuid", "name": "string", ... }]`

#### GET /api/v1/[features]/{id}
- **Auth requerida**: sí / no
- **Response 200**: recurso completo
- **Response 404**: no encontrado

#### PUT /api/v1/[features]/{id}
- **Auth requerida**: sí / no
- **Request Body**: campos opcionales a actualizar
- **Response 200**: recurso actualizado
- **Response 404**: no encontrado

#### DELETE /api/v1/[features]/{id}
- **Auth requerida**: sí / no
- **Response 204**: eliminado exitosamente
- **Response 404**: no encontrado

### Diseño Frontend

#### Componentes nuevos
| Componente | Archivo | Props principales | Descripción |
|------------|---------|------------------|-------------|
| `FeatureCard` | `components/FeatureCard` | `item, onDelete, onEdit` | Tarjeta de un ítem |
| `FeatureFormModal` | `components/FeatureFormModal` | `isOpen, onSubmit, onClose` | Modal de creación/edición |

#### Páginas nuevas
| Página | Archivo | Ruta | Protegida |
|--------|---------|------|-----------|
| `FeaturePage` | `pages/FeaturePage` | `/features` | sí / no |

#### Hooks y State
| Hook / Store | Archivo | Retorna | Descripción |
|------|---------|---------|-------------|
| `useFeature` | `hooks/useFeature` | `{ items, loading, error, create, update, remove }` | CRUD del feature |

#### Services (llamadas API)
| Función | Archivo | Endpoint |
|---------|---------|---------|
| `getFeatures(token)` | `services/featureService` | `GET /api/v1/features` |
| `createFeature(data, token)` | `services/featureService` | `POST /api/v1/features` |
| `updateFeature(id, data, token)` | `services/featureService` | `PUT /api/v1/features/{id}` |
| `deleteFeature(id, token)` | `services/featureService` | `DELETE /api/v1/features/{id}` |

### Arquitectura y Dependencias
- Paquetes nuevos requeridos: ninguno / listar si aplica
- Servicios externos: listar integraciones (auth, storage, third-party APIs)
- Impacto en punto de entrada de la app: registrar router/módulo si aplica

### Notas de Implementación
> Observaciones técnicas, decisiones de diseño o advertencias para los agentes de desarrollo.

---

## 3. LISTA DE TAREAS

> Checklist accionable para todos los agentes. Marcar cada ítem (`[x]`) al completarlo.
> El Orchestrator monitorea este checklist para determinar el progreso.

### Backend

#### Implementación
- [ ] Crear modelos `[Feature]Create`, `[Feature]Update`, `[Feature]Response`, `[Feature]Document`
- [ ] Implementar `[Feature]Repository` — métodos CRUD
- [ ] Implementar `[Feature]Service` — lógica de negocio de HU-01
- [ ] Implementar router/controller `/api/v1/[features]` — endpoints CRUD
- [ ] Registrar en punto de entrada de la app

#### Tests Backend
- [ ] `test_[service]_create_success` — happy path creación
- [ ] `test_[service]_create_duplicate_raises_conflict` — error unicidad
- [ ] `test_[service]_get_not_found_raises_error` — error not found
- [ ] `test_[repo]_insert_returns_document` — repositorio insert
- [ ] `test_[router]_post_returns_201` — endpoint creación
- [ ] `test_[router]_post_returns_401_no_token` — sin autenticación
- [ ] `test_[router]_get_returns_200` — listado

### Frontend

#### Implementación
- [ ] Crear `[feature]Service` — funciones para todos los endpoints
- [ ] Crear `use[Feature]` — hook/store con estado, loading, error y acciones CRUD
- [ ] Implementar `[Feature]Card` + estilos
- [ ] Implementar `[Feature]FormModal` + estilos
- [ ] Implementar `[Feature]Page` + estilos — layout completo
- [ ] Registrar ruta `/[features]` en el sistema de rutas

#### Tests Frontend
- [ ] `[FeatureCard] renders name correctly`
- [ ] `[FeatureCard] calls onDelete when button clicked`
- [ ] `[FeatureFormModal] submits form with correct data`
- [ ] `use[Feature] loads items on mount`
- [ ] `use[Feature] handles create error gracefully`
- [ ] `[FeaturePage] renders list of items`

### QA
- [ ] Ejecutar skill `/gherkin-case-generator` → criterios CRITERIO-1.1, 1.2, 1.3
- [ ] Ejecutar skill `/risk-identifier` → clasificación ASD de riesgos
- [ ] Revisar cobertura de tests contra criterios de aceptación
- [ ] Validar que todas las reglas de negocio están cubiertas
- [ ] Actualizar estado spec: `status: IMPLEMENTED`
