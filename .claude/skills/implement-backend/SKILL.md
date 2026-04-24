---
name: implement-backend
description: Implementa un feature completo en el backend. Requiere spec con status APPROVED en .github/specs/.
argument-hint: "<nombre-feature>"
---

# Implement Backend

## Prerequisitos
1. Leer spec: `.github/specs/<feature>.spec.md` — sección 2 (modelos, endpoints)
2. Leer stack: `.claude/rules/backend.md`
3. Leer arquitectura: `.claude/rules/backend.md`

## Orden de implementación
```
models → repositories → services → routes → registrar en punto de entrada
```

| Capa | Responsabilidad |
|------|-----------------|
| **Models / Schemas** | Validación de tipos e input/output (Create, Update, Response, Document) |
| **Repositories** | Acceso a DB — queries CRUD sin lógica de negocio |
| **Services** | Lógica de negocio pura — orquesta repositorios |
| **Routes / Controllers** | Parsing HTTP + DI + delegar al service |

## Patrón de DI (obligatorio en routes)
- Inyectar dependencias en la firma del handler (no instanciar inline en el cuerpo)
- El service recibe el repo por parámetro; el router instancia ambos

Ver patrones específicos del stack en `.claude/rules/backend.md`.

## Reglas
Ver `.claude/rules/backend.md` — async, naming, errores, timestamps.

## Restricciones
- Solo `backend/` (o equivalente del proyecto). No tocar `frontend/`.
- No generar tests (responsabilidad de `test-engineer-backend`).
