---
name: Frontend stack and test infrastructure
description: Tech stack, test framework, and key architectural decisions for natillera-pwa frontend tests
type: project
---

Frontend is React 19 + Vite + RTK Query (not plain Axios/hooks as the frontend.md rule describes — the actual implementation uses Redux Toolkit + RTK Query).

Test framework: Vitest + React Testing Library + msw (mock service worker for node).

Setup file: `frontend/src/test-setup.ts` — installs @testing-library/jest-dom and overrides localStorage with a MemoryStorage polyfill.

Shared test utility: `frontend/src/test-utils.tsx` — exports `renderWithProviders(ui, { preloadedState, initialEntries })` and `authenticatedState`.

**Why:** The frontend.md rule bans Redux but the actual codebase uses RTK Query with apiSlice + authSlice. Tests must follow the code, not the rule doc.

**How to apply:** Always use `renderWithProviders` for component/page tests; always mock RTK hooks via `vi.mock('../../store/api/...')` at the file level; use msw setupServer for RTK endpoint integration tests.
