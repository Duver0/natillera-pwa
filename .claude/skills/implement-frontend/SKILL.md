---
name: implement-frontend
description: Implementa un feature completo en el frontend. Requiere spec con status APPROVED en .github/specs/.
argument-hint: "<nombre-feature>"
---

# Implement Frontend

## Prerequisitos
1. Leer spec: `.github/specs/<feature>.spec.md` — sección 2.3 (componentes, páginas, hooks)
2. Leer stack: `.claude/rules/backend.md`
3. Leer arquitectura: `.claude/rules/backend.md`

## Orden de implementación
```
services → hooks/state → components → pages/views → registrar ruta
```

| Capa | Responsabilidad |
|------|-----------------|
| **Services** | Llamadas HTTP al backend — sin estado, sin lógica de negocio |
| **Hooks / State** | Estado local, efectos, acciones — consume services |
| **Components** | UI reutilizable — recibe props, emite eventos |
| **Pages / Views** | Composición final — layout + rutas |

## Patrones obligatorios
- Auth state: consumir SÓLO desde el hook/store de auth del proyecto (ver contexto)
- Variables de entorno: URL del API siempre desde variables de entorno, nunca hardcodeada
- Token en header: `Authorization: Bearer <token>` en todas las llamadas protegidas
- Estilos: usar ÚNICAMENTE el sistema de estilos aprobado en el proyecto (ver contexto)

Ver patrones específicos en `.claude/rules/frontend.md` y `.claude/rules/backend.md`.

## Restricciones
- Solo `frontend/` (o equivalente del proyecto). No tocar `backend/`.
- No generar tests (responsabilidad de `test-engineer-frontend`).
