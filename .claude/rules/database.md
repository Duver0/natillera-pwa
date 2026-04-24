---
description: Reglas de acceso a datos para este proyecto (MongoDB + Motor async + Pydantic v2).
paths:
  - "**/models/**"
  - "**/repositories/**"
  - "**/entities/**"
  - "**/schemas/**"
  - "**/migrations/**"
---

# Reglas de Base de Datos — MongoDB + Motor async

## Stack aprobado

- **MongoDB** — base de datos principal (única, sin persistencia relacional)
- **Motor async** (`motor.motor_asyncio`) — ÚNICO cliente aprobado, siempre async
- **Pydantic v2** — schemas de modelos (request/response/documento interno)

**Prohibido:** PyMongo síncrono, SQLAlchemy, Django ORM, bases de datos relacionales (PostgreSQL, MySQL, SQLite).

## Convenciones de MongoDB

- Colecciones en snake_case plural: `users`, `faqs`
- IDs de usuario: `uid` string de Firebase (no usar `_id` de MongoDB en respuestas API)
- Timestamps: `created_at` / `updated_at` generados en la app con `datetime.utcnow()`
- Paginación via `skip` / `limit` en queries
- Acceso asíncrono exclusivamente: todas las operaciones usan `async def` + `await`

## Separación de Modelos (obligatorio)

| Modelo | Propósito | Contiene |
|--------|-----------|----------|
| **Create / Input** | Datos que el cliente envía para crear | Solo campos que el cliente provee |
| **Update / Patch** | Datos para actualizar | Todos los campos opcionales |
| **Response / Output** | Lo que la API retorna | Campos seguros para exponer (sin `_id`) |
| **Document / Entity** | Documento interno de MongoDB | Campos internos + `uid` + timestamps |

## Reglas de Diseño

- **IDs como strings** — exponer `uid` (Firebase) en contratos API, nunca `_id` de Mongo
- **Timestamps UTC** — `created_at` / `updated_at` en la app, nunca en el cliente
- **Índices justificados** — solo crear índices con un caso de uso documentado
- **Sin datos sensibles en texto plano** — nunca almacenar passwords sin hash
- **Repositorio como única puerta de acceso a MongoDB** — services no tocan Motor directamente

## Patrón de Repositorio (obligatorio)

```python
# repositories/faq_repository.py
class FaqRepository:
    def __init__(self, db):
        self.collection = db["faqs"]

    async def find_all(self) -> list[dict]:
        return await self.collection.find({}).to_list(None)

    async def insert(self, doc: dict) -> dict:
        result = await self.collection.insert_one(doc)
        return {**doc, "uid": str(result.inserted_id)}
```

## Anti-patrones Prohibidos

- PyMongo síncrono en contexto async (bloquea el event loop)
- Queries N+1 (iterar llamadas a DB en un bucle)
- Lógica de negocio en repositorios
- Acceso directo a Motor desde services (siempre via repository)
- `_id` de MongoDB en respuestas API
- Concatenación de strings en queries (NoSQL injection)
- Estado de conexión global mutable
