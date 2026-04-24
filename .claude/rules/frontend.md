---
description: Reglas de frontend para este proyecto (React 19 + Vite + CSS Modules). Se aplica automáticamente a archivos frontend.
paths:
  - "frontend/**"
  - "client/**"
  - "web/**"
---

# Reglas de Frontend — React 19 + Vite + CSS Modules

## Stack aprobado

- **React 19** con **Vite**
- **CSS Modules** (estilos locales por componente — un `.module.css` por archivo)
- **React Router v6** (rutas de la SPA)
- **Firebase SDK** — autenticación cliente (`onAuthStateChanged`, `signInWithEmailAndPassword`)
- **Axios** — llamadas HTTP al backend

**Prohibido:** Tailwind CSS, Bootstrap, styled-components, CSS-in-JS, Redux, MobX, fetch directo en componentes.

## Arquitectura por Capas

```
services → hooks → components → pages → App.jsx (registrar ruta)
```

| Capa | Responsabilidad | Prohibido |
|------|----------------|-----------|
| `pages/` | Layout, composición de componentes, uso de hooks | Llamadas directas a API, lógica de negocio |
| `components/` | Render UI, recibir props, emitir eventos | Estado global, llamadas a API |
| `hooks/` | Estado local + llamadas a services | Render JSX, acceso directo a MongoDB/Firebase |
| `services/` | Llamadas HTTP (Axios) al backend | Estado, render, lógica de negocio |

## Convenciones Obligatorias

- **CSS**: SIEMPRE CSS Modules — NUNCA clases CSS globales
- **Auth state**: SIEMPRE consumir de `useAuth()` — nunca estado de auth paralelo
- **Variables de entorno**: SIEMPRE prefijo `VITE_` (ej. `VITE_API_URL`)
- **API calls**: van en `services/` via Axios, token siempre desde `useAuth()`
- **Rutas**: registrar en `src/App.jsx` con `<Route>` de React Router v6

## Llamadas a la API (patrón obligatorio)

```js
// services/featureService.js
import axios from 'axios';
const API_BASE = import.meta.env.VITE_API_URL;

export async function getFeatures(token) {
  const res = await axios.get(`${API_BASE}/api/v1/features`, {
    headers: { Authorization: `Bearer ${token}` }
  });
  return res.data;
}
```

```js
// hooks — obtener token siempre de useAuth()
const { token } = useAuth();
```

## Nomenclatura de Archivos

| Artefacto | Convención | Ejemplo |
|-----------|-----------|---------|
| Page | `<Feature>Page.jsx` + `<Feature>Page.module.css` | `FaqPage.jsx` |
| Component | `<Component>.jsx` + `<Component>.module.css` | `FaqFormModal.jsx` |
| Hook | `use<Feature>.js` | `useFaq.js` |
| Service | `<feature>Service.js` | `faqService.js` |

- PascalCase para páginas y componentes (`.jsx`)
- camelCase con prefijo `use` para hooks
- camelCase para services
- Máximo 4 archivos nuevos por feature (page + component + hook + service)

## Estructura de Archivos de Referencia

```
frontend/src/
├── App.jsx
├── config/firebase.js        ← init Firebase (solo aquí)
├── hooks/useAuth.js          ← fuente única de verdad para auth
├── services/authService.js   ← Firebase signIn + POST backend
├── components/               ← componentes reutilizables
└── pages/                    ← FeaturePage.jsx + FeaturePage.module.css
```

## Anti-patrones Prohibidos

- Llamadas Axios directas en componentes o páginas (van en services via hooks)
- Estado de auth duplicado fuera de `useAuth()`
- Estilos globales / clases CSS fuera de CSS Modules
- Lógica de negocio en componentes (va en hooks)
- Hardcodear URLs de API (usar `VITE_API_URL`)

## Lineamientos completos

`.claude/docs/lineamientos/dev-guidelines.md` — Clean Code, SOLID, API REST, Seguridad, Observabilidad.
