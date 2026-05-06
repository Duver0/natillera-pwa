---
feature: fix-mixed-content-session-persistence
status: IN_PROGRESS
created: 2026-05-06
updated: 2026-05-06
author: spec-generator
---

# Spec: Fix Mixed Content + Session Persistence

## Contexto y Causa Raiz

Dos bugs reportados en produccion (GitHub Pages HTTPS + Railway backend):

### Bug 1 — Mixed Content Error
**Sintoma:** Browser bloquea requests HTTP desde pagina HTTPS.
**Causa raiz (linea 17 de `apiSlice.ts`):**
```ts
const BASE_URL = (import.meta.env.VITE_API_URL || 'https://natillera-pwa-production.up.railway.app')
  .replace('http://', 'https://')
  .replace('https:/', 'https://')  // TYPO: una barra en el patron de busqueda
```
El segundo `.replace` tiene el patron `'https:/'` (una barra) buscando dentro de `'https://'` (dos barras). En JavaScript, `'https://foo.com'.replace('https:/', 'https://')` devuelve `'https://foo.com'` sin cambio — el replace si funciona en ese caso. Pero si `VITE_API_URL` llega como `http://natillera-pwa-production.up.railway.app` (sin trailing slash), el primer replace produce `https://natillera-pwa-production.up.railway.app`, y el segundo replace busca `https:/` y lo reemplaza por `https://`, resultando en `https:///natillera-pwa-production.up.railway.app` (triple barra). Esto genera una URL malformada que el browser interpreta como HTTP relativo o falla.

**Causa secundaria:** Si `VITE_API_URL` no esta definida en el build de GitHub Actions, el fallback ya es HTTPS correcto, pero si SI esta definida con valor HTTP, el doble-replace produce URL malformada.

### Bug 2 — Sesion no persiste al reload
**Sintoma:** Despues de F5, usuario vuelve a `/login`.
**Causa raiz:** `AppStartup.tsx` llama a `refresh()` usando `apiSlice`, que construye la URL con `BASE_URL` malformada. La peticion falla (network error o Mixed Content), el `.catch` ejecuta `clearAuth()`, borrando tokens del localStorage, y el router redirige a `/login`.

**En resumen: Bug 2 es consecuencia de Bug 1.**

## Alcance del Fix

### Frontend-only — No requiere cambios de backend ni DB

Archivos a modificar:
1. `frontend/src/store/api/apiSlice.ts` — corregir construccion de BASE_URL
2. `frontend/src/components/AppStartup.tsx` — agregar logging y manejo de error mas robusto
3. `frontend/.env.example` — documentar VITE_API_URL con valor HTTPS
4. `.github/workflows/deploy.yml` — verificar que VITE_API_URL se inyecte correctamente (solo lectura/verificacion)

## Cambios Requeridos

### 1. `apiSlice.ts` — BASE_URL fix

**Reemplazar la logica actual** por una construccion limpia y sin side effects:

```ts
// ANTES (buggy)
const BASE_URL = (import.meta.env.VITE_API_URL || 'https://natillera-pwa-production.up.railway.app')
  .replace('http://', 'https://')
  .replace('https:/', 'https://')

// DESPUES (correcto)
const rawUrl = import.meta.env.VITE_API_URL || 'https://natillera-pwa-production.up.railway.app'
const BASE_URL = rawUrl.startsWith('http://') ? rawUrl.replace('http://', 'https://') : rawUrl
```

Requisitos:
- Si `VITE_API_URL` es `http://...` -> convertir a `https://...`
- Si `VITE_API_URL` es `https://...` -> usar tal cual
- Si `VITE_API_URL` no esta definida -> usar fallback HTTPS hardcodeado
- No introducir triple-slash ni URLs malformadas bajo ninguna condicion
- Agregar `console.warn` en desarrollo si la URL resultante es HTTP (imposible en prod, util en dev)

### 2. `AppStartup.tsx` — Error handling mejorado

**Problema adicional:** El `.catch` generico borra tokens ante cualquier error de red, incluyendo errores transitorios. Esto es demasiado agresivo.

**Cambio requerido:**
- Distinguir entre `401 Unauthorized` (token invalido, limpiar) y errores de red/timeout (no limpiar, intentar de nuevo o dejar tokens intactos)
- El error de Mixed Content o network error NO debe disparar `clearAuth()`
- Solo limpiar auth si el servidor responde explicitamente con 401

```ts
// Logica de decision en catch:
.catch((error) => {
  // Solo limpiar si el backend rechazo el token (401)
  // Errores de red (Mixed Content, timeout, CORS) no invalidan el token
  const isAuthError = error?.status === 401 || error?.originalStatus === 401
  if (isAuthError) {
    dispatch(clearAuth())
  }
  // Si es error de red, mantener tokens — el usuario podra reintentar
})
```

### 3. `frontend/.env.example`

Asegurar que exista y documente:
```
VITE_API_URL=https://natillera-pwa-production.up.railway.app
VITE_SUPABASE_URL=https://your-project.supabase.co
VITE_SUPABASE_ANON_KEY=your-anon-key
```

### 4. GitHub Actions (solo verificacion)

Verificar que en `.github/workflows/deploy.yml` el step de build incluya:
```yaml
env:
  VITE_API_URL: ${{ secrets.VITE_API_URL }}
```
Si no esta definido como secret, agregar con valor `https://natillera-pwa-production.up.railway.app`.

**Nota:** Si el secret no existe en el repo, el fallback en `apiSlice.ts` toma valor por defecto correcto (HTTPS). El fix en el codigo es suficiente para ambos casos.

## Criterios de Aceptacion

- [ ] Al recargar la pagina (F5) con sesion activa, el usuario permanece en la ruta actual
- [ ] No aparece error de Mixed Content en consola del browser
- [ ] Si el refreshToken expiro, el usuario es redirigido a `/login` (comportamiento correcto)
- [ ] Si hay error de red transitorio, los tokens se conservan en localStorage
- [ ] `BASE_URL` nunca contiene `http://` en produccion
- [ ] `BASE_URL` nunca contiene triple-slash (`https:///`)
- [ ] Tests verifican la construccion de BASE_URL con diferentes valores de env var

## Tests Requeridos

### Unit tests para `apiSlice.ts`:
- `VITE_API_URL=http://...` → resultado es `https://...`
- `VITE_API_URL=https://...` → resultado sin cambios
- `VITE_API_URL=undefined` → fallback HTTPS correcto
- Ningun caso produce triple-slash

### Integration tests para `AppStartup.tsx`:
- Refresh exitoso: usuario queda autenticado
- Refresh con 401: tokens limpiados, redireccion a login
- Refresh con network error: tokens preservados, no redireccion

## Riesgos y Mitigacion

| Riesgo | Probabilidad | Mitigacion |
|--------|-------------|------------|
| Railway todavia en HTTP (infraestructura) | Media | Fix en codigo fuerza HTTPS; Railway soporta HTTPS por defecto en dominios `.up.railway.app` |
| Token de refresh expirado en prod | Alta | Comportamiento correcto: limpiar y redirigir a login |
| CORS bloqueando requests HTTPS | Baja | Backend ya acepta origin de GitHub Pages (verificar en deploy) |

## Notas de Implementacion

- Los cambios son **exclusivamente frontend** — 2-3 archivos
- No requiere migracion de DB ni cambios de backend
- El fix es retrocompatible con desarrollo local (HTTP localhost no es bloqueado por browsers)
- Prioridad: Bug 1 (BASE_URL) debe resolverse primero; Bug 2 se resuelve como consecuencia + mejora de manejo de errores
