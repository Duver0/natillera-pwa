---
description: Reglas de backend para este proyecto (FastAPI + MongoDB + Motor async). Se aplica automáticamente a archivos backend.
paths:
  - "backend/**"
  - "server/**"
  - "api/**"
  - "app/**"
---

# Reglas de Backend — FastAPI + MongoDB

## Stack aprobado

- **Python 3.12** + **FastAPI** (async REST)
- **Motor** (`motor.motor_asyncio.AsyncIOMotorClient`) — acceso async a MongoDB
- **Pydantic v2** — validación de schemas
- **Firebase Admin SDK** — verificación de `idToken` en cada request protegido
- **Uvicorn** — servidor ASGI

**Prohibido:** PyMongo síncrono, SQLAlchemy, Django, Flask, bases de datos relacionales.

## Arquitectura en Capas

```
routes → services → repositories → MongoDB
```

| Capa | Responsabilidad | Prohibido |
|------|----------------|-----------|
| `routes/` | Parsear HTTP, instanciar deps con `Depends()`, delegar al service | Lógica de negocio, queries MongoDB |
| `services/` | Reglas de negocio, validaciones de dominio, orquestar repos | Queries MongoDB directas, imports de FastAPI |
| `repositories/` | Queries MongoDB (find, insert, update, delete) via Motor | Lógica de negocio |
| `models/` | Schemas Pydantic (request/response/documento interno) | Lógica de negocio, acceso a DB |

## Wiring de Dependencias (patrón obligatorio)

```python
# Correcto — Depends() en la firma del endpoint
@router.post("/")
async def create_item(body: ItemCreate, db=Depends(get_db)):
    repo = ItemRepository(db)
    service = ItemService(repo)
    return await service.create(body)
```

NUNCA inyectar `get_db()` fuera de `Depends()`. NUNCA instanciar repos/services fuera del router.

## Convenciones de Código

- Todas las funciones que tocan DB son `async def` + `await`
- `snake_case` para módulos, funciones y variables
- `uid` de Firebase como clave única en MongoDB (no usar `_id` en respuestas API)
- Colecciones MongoDB en snake_case plural: `users`, `faqs`
- Timestamps: `created_at` / `updated_at` generados en la app con `datetime.utcnow()`
- API versionada: `/api/v1/...`
- Formato de error consistente: `{ "detail": "<mensaje>" }`
- Configuración siempre desde `app.config.settings` o `app.config.database`

## Nomenclatura de Archivos

| Artefacto | Convención | Ejemplo |
|-----------|-----------|---------|
| Router | `<feature>_router.py` | `faq_router.py` |
| Service | `<feature>_service.py` | `faq_service.py` |
| Repository | `<feature>_repository.py` | `faq_repository.py` |
| Model | `<feature>_model.py` | `faq_model.py` |
| Test | `test_<feature>_<layer>.py` | `test_faq_service.py` |

- Máximo 4 archivos nuevos por feature (router + service + repository + model)
- No crear carpetas fuera de la convención de capas sin revisión arquitectónica

## Anti-patrones Prohibidos

- Lógica de negocio en routers
- Queries MongoDB en services (van en repositories)
- Acceso síncrono a MongoDB (PyMongo bloqueante — prohibido en contexto async)
- Singletons globales con estado mutable
- Exposición de errores internos en respuestas públicas (`detail` descriptivo, sin stack trace)
- `_id` de MongoDB en respuestas API (mapear a `uid` u otro campo explícito)
- Credenciales hardcodeadas en código

## Lineamientos completos

`.claude/docs/lineamientos/dev-guidelines.md` — Clean Code, SOLID, API REST, Seguridad, Observabilidad.
