---
feature: auth-persistence
status: IMPLEMENTED
created: 2026-05-06
updated: 2026-05-06
author: spec-generator
---

# Spec: Auth Session Persistence

## Problema

La sesión de autenticación se pierde al recargar la página. El JWT token obtenido via Supabase client no se persiste entre sesiones de navegador.

## Causa Raíz

El Redux slice `authSlice.ts` almacena el token solo en memoria (estado de Redux). Al recargar, Redux se reinicia y el token se pierde. No hay mecanismo de rehidratación desde `localStorage` ni suscripción al evento `onAuthStateChange` de Supabase.

## Objetivo

Garantizar que la sesión de usuario persista a través de recargas de página, usando `localStorage` como capa de persistencia y el listener nativo de Supabase como fuente de verdad.

## Alcance

### IN SCOPE
- Persistencia del token JWT y datos de sesión en `localStorage`
- Rehidratación del estado Redux al mount de la aplicación
- Suscripción a `supabase.auth.onAuthStateChange` para sincronizar estado
- Unit tests para el auth slice actualizado
- Integration tests para el flujo login → reload → estado persistido

### OUT OF SCOPE
- Cambios en el backend FastAPI (ya valida tokens JWT de Supabase correctamente)
- Cambios en RTK Query `apiSlice.ts` (el `baseQuery` ya inyecta headers desde Redux state)
- Implementación de refresh token manual (Supabase lo maneja internamente)

## Diseño Técnico

### Estrategia de Persistencia

Supabase SDK ya persiste la sesión en `localStorage` bajo la clave `supabase.auth.token` de forma automática. El problema es que Redux no se rehidrata desde ahí al arrancar.

**Solución en dos capas:**

1. **Rehidratación al mount** — Al iniciar la app, leer la sesión activa via `supabase.auth.getSession()` e inicializar el Redux slice con esa sesión.
2. **Listener reactivo** — Suscribirse a `supabase.auth.onAuthStateChange` para mantener Redux sincronizado con cualquier cambio posterior (login, logout, token refresh).

### Cambios Requeridos

#### `src/store/slices/authSlice.ts`

```typescript
// Nuevas acciones a agregar:
setSession(state, action: PayloadAction<{ user: User; token: string } | null>)
// Reemplaza o complementa la acción existente de login/logout
// para recibir datos de sesión desde el listener de Supabase
```

Estado del slice debe incluir:
```typescript
interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;  // true durante la rehidratación inicial
  error: string | null;
}
```

La clave `isLoading: true` en el estado inicial evita el "flash" de contenido no autenticado durante la rehidratación.

#### `src/App.tsx`

```typescript
useEffect(() => {
  // 1. Rehidratar desde sesión existente
  supabase.auth.getSession().then(({ data: { session } }) => {
    dispatch(setSession(session ? { user: session.user, token: session.access_token } : null));
  });

  // 2. Suscribirse a cambios futuros
  const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
    dispatch(setSession(session ? { user: session.user, token: session.access_token } : null));
  });

  return () => subscription.unsubscribe();
}, [dispatch]);
```

#### `src/store/api/apiSlice.ts`

Sin cambios. El `prepareHeaders` ya lee el token desde Redux state — una vez que el state se rehidrate correctamente, los headers se inyectarán de forma transparente.

### Flujo Completo

```
App mount
  └── getSession() ──► sesión existe ──► dispatch(setSession({user, token}))
                   └── no existe     ──► dispatch(setSession(null))
       ↓
  onAuthStateChange suscripción activa
       ↓
  Usuario hace login ──► Supabase persiste en localStorage ──► evento dispara ──► Redux se actualiza
  Usuario recarga    ──► getSession() lee localStorage ──► Redux se rehidrata ──► isLoading: false
  Usuario hace logout ──► Supabase limpia localStorage ──► evento dispara ──► Redux se limpia
```

## Criterios de Aceptación

1. **Login → Reload**: Después de hacer login y recargar la página, el usuario permanece autenticado.
2. **Sin flash de contenido**: El estado `isLoading: true` previene que se muestre la pantalla de login durante la rehidratación.
3. **Logout limpia todo**: El logout elimina la sesión de localStorage y Redux queda en estado no autenticado.
4. **Token refresh automático**: Supabase refresca el token silenciosamente; Redux se actualiza via `onAuthStateChange`.
5. **Sin cambios en backend**: Los endpoints de FastAPI continúan funcionando sin modificaciones.

## Tests Requeridos

### Unit Tests — `authSlice`
- `setSession` con sesión válida → estado autenticado
- `setSession` con `null` → estado no autenticado
- Estado inicial tiene `isLoading: true`
- `isLoading` pasa a `false` después de `setSession`

### Integration Tests — Persistencia
- Mock de `supabase.auth.getSession` retornando sesión → verificar Redux state rehidratado
- Mock de `onAuthStateChange` disparando evento `SIGNED_IN` → Redux actualizado
- Mock de `onAuthStateChange` disparando evento `SIGNED_OUT` → Redux limpiado
- Simular reload: reiniciar store, ejecutar efecto de mount, verificar estado final

## Archivos Afectados

| Archivo | Tipo de cambio |
|---|---|
| `src/store/slices/authSlice.ts` | MODIFICAR — agregar `setSession`, `isLoading` en estado |
| `src/App.tsx` | MODIFICAR — agregar `useEffect` de rehidratación y listener |
| `src/store/slices/__tests__/authSlice.test.ts` | CREAR — unit tests |
| `src/App.test.tsx` | CREAR o MODIFICAR — integration tests de persistencia |

## Notas de Implementación

- No introducir `redux-persist` — Supabase ya gestiona la persistencia en localStorage. Agregar redux-persist sería redundante y añadiría complejidad innecesaria.
- El `useEffect` debe vivir en `App.tsx` (o en el componente raíz) para que el listener esté activo durante toda la vida de la app.
- Si existe un componente `<AuthProvider>` o similar, el `useEffect` puede moverse ahí para mejor separación de responsabilidades.
