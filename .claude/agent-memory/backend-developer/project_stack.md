---
name: project_stack
description: Backend stack and DB interface pattern for natillera-pwa
type: project
---

FastAPI + asyncpg (local) or Supabase client (prod). DB abstraction via `DatabaseInterface` in `backend/app/db.py`. Services extend `BaseService(db, user_id)` and call `self.db.table(name).select/insert/update/eq/...execute()`. No MongoDB — SPEC corrected to Supabase PostgreSQL. Auth via Supabase JWT (not Firebase Admin).

**Why:** SPEC-001 v2.0 explicitly chose Supabase + FastAPI for ACID guarantees.
**How to apply:** Never use Motor or PyMongo. All DB calls go through DatabaseInterface. Repositories wrap `self._db.table(...)` chains.
