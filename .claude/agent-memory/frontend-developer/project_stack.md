---
name: Actual frontend stack
description: Real tech stack in use — overrides the frontend.md rules which describe a different stack
type: project
---

The project uses React 18 + TypeScript + Vite + Tailwind CSS + RTK Query (not Axios + CSS Modules as stated in .claude/rules/frontend.md).

Auth state comes from `useAuth()` hook at `src/hooks/useAuth.ts`.
All API endpoints live in `src/store/api/apiSlice.ts` — feature files (clientApi.ts, creditApi.ts) re-export from there as stable import boundaries.

**Why:** The codebase was already built this way before frontend.md was written; the rule file describes an older/different intended stack.

**How to apply:** Always follow the codebase patterns (RTK Query, Tailwind), not the frontend.md CSS Modules + Axios rules. No tsconfig.json exists at project root — Vite handles TS compilation.
