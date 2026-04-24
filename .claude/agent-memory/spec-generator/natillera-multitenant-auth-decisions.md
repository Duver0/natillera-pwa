---
name: Natillera multi-tenant auth architecture decisions
description: Core decisions for transforming single-user financial PWA into multi-tenant system with Supabase Auth + RLS
type: project
---

## Finalized Architectural Decisions (SPEC-002)

**Auth Provider**: Supabase Auth (chosen over Firebase)
- **Why**: Free tier, built-in to PostgreSQL, native RLS support, zero marginal cost beyond database. JWT issuance + token refresh built-in.
- **How to apply**: All JWT validation against Supabase JWKS public keys; no hardcoded secrets in frontend.

**Data Isolation Model**: user_id FK on every table + RLS policies + backend middleware
- **Why**: Triple-layer defense (RLS is final enforcement, backend filter prevents accidental leaks, middleware injects context).
- **How to apply**: ALL queries MUST include `WHERE user_id = auth.uid()` in RLS and `WHERE user_id = self.user_id` in services. BaseService pattern enforces this.

**Denormalization**: user_id on Installment (even though derivable via Credit → Client)
- **Why**: RLS single-table query vs JOIN performance. Slight denormalization justified.
- **How to apply**: Trigger on installment INSERT syncs user_id from credit record.

**Session Storage**: localStorage (JWT) + refresh token rotation (handled by Supabase)
- **Why**: PWA simplicity, no server-side session table needed, Supabase rotates tokens automatically.
- **How to apply**: Frontend stores tokens in localStorage; token refresh interceptor on 401. No httpOnly cookies (PWA constraint).

**Password Policy**: Minimum 8 chars, uppercase, lowercase, number (Supabase enforces)
- **Why**: Basic security; avoids common passwords (future hardening: zxcvbn library).
- **How to apply**: Supabase Auth settings; frontend validation mirrors backend.

**Ownership Verification**: Two-layer check (backend _ensure_ownership + RLS)
- **Why**: Defense in depth. If backend filter bug, RLS rejects. If RLS bug, backend 403.
- **How to apply**: Every service mutation calls `await self._ensure_ownership(entity_id)` before update/delete.

**Error Messages**: Generic "not_found_or_forbidden" for cross-user access (not "you don't own this")
- **Why**: Prevent user enumeration attacks (attacker cannot discover if user/entity exists).
- **How to apply**: 403 Forbidden with message like "resource_not_found" regardless of whether record exists or user owns it.

**Multi-device Logout**: Single logout invalidates refresh_token globally
- **Why**: Simplicity. No device-specific tokens (MVP scope).
- **How to apply**: POST /auth/logout calls Supabase signOut() which invalidates all sessions for that user.

**RLS Policies**: Applied to every table without exception
- **Why**: Database is source of truth for access control. Cannot be bypassed by app code.
- **How to apply**: CREATE POLICY for every table + user_id FK. Test: SELECT as different users, verify isolation.

---

## Changes to v2.0 Spec (SPEC-001)

**No business logic changes**: Interest calc, mora detection, payment order → unchanged.
**Only data isolation added**: Every table gains user_id FK + RLS + backend filter.

**Schema Changes**:
- clients: phone + document_id unique per (user_id, col) not globally
- credits, installments, payments, savings, savings_liquidations, financial_history: all add user_id FK + indexes

**Service Layer**: All inherit BaseService, forcing user_id injection.

**Router Layer**: All endpoints inject user context via Depends(get_user_id).

---

## Testing Strategy

**Unit**: Auth middleware JWT validation, BaseService user_id filtering
**Integration**: Multi-user isolation (User A cannot read User B's data)
**Security**: RLS as final enforcement; intentional backend filter bypass should still fail at DB layer

## Deployment Sequence

1. Supabase setup + RLS (non-breaking, read-only initially)
2. Auth endpoints + middleware (new routes, not touching existing)
3. Service refactoring (gradual, all behind feature flag if needed)
4. Frontend auth UI (new pages, no impact on existing dashboard)
5. Data migration (if existing single-user data must carry forward → assign user_id=<system_admin>)

---

## Future Enhancements (Out of Scope MVP)

- Email verification (Supabase flow already supports)
- Password reset (Supabase recovery flow)
- Social login (OAuth via Supabase)
- Two-factor authentication (TOTP)
- Device-specific refresh tokens (track login source)
- Account delegation (one user manages multiple sub-accounts)
- Role-based access (admin, operator, viewer roles)
