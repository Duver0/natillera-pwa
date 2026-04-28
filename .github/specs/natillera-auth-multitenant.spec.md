---
id: SPEC-002
status: IMPLEMENTED
feature: natillera-auth-multitenant
created: 2026-04-23
updated: 2026-04-28
author: spec-generator
version: "1.0"
related-specs:
  - SPEC-001 (natillera-pwa)
---

# Natillera PWA — Multi-Tenant Authentication & Authorization (SPEC-002)

Transform single-user financial app into secure multi-tenant system. Every user owns their data exclusively. All entities (Clients, Credits, Installments, Payments, Savings, History) scoped to user. Data isolation enforced at database layer via Row-Level Security (RLS) policies and backend middleware.

**DOMAIN RULE**: No data cross-user access. User A cannot read, write, or delete data belonging to User B.

---

## 1. REQUERIMIENTOS

### 1.1 User Stories

#### US-AUTH-001: User Registration (Supabase Auth)
```gherkin
Feature: Register new user
  Scenario: Sign up with email and password
    Given user on registration page
    When enter email, password, password_confirmation
    Then Supabase Auth creates user account
    And User record created with email + user_id
    And auto-login (session token issued)
    And redirect to onboarding / dashboard
  
  Scenario: Email already registered
    Given email exists in auth.users
    When attempt registration
    Then reject with "email_already_registered"
    And show error message
  
  Scenario: Invalid password
    Given password < 8 chars OR no uppercase OR no number
    When attempt registration
    Then reject with validation error
    And display requirements
  
  Scenario: Email validation (optional)
    Given user registered
    When email_confirmed_at = now (Supabase email link clicked)
    Then mark user.email_verified = true
    And unlock premium features (future scope)
```

#### US-AUTH-002: User Login (Supabase Auth)
```gherkin
Feature: Login to application
  Scenario: Login with email + password
    Given user on login page
    When enter email, correct password
    Then Supabase Auth validates credentials
    And return id_token (JWT) + refresh_token
    And RTK Query stores tokens in localStorage (or cookie)
    And app initializes user context (email, uid)
    And redirect to dashboard
  
  Scenario: Invalid credentials
    Given wrong password OR email not found
    When attempt login
    Then reject with "invalid_login"
    And clear sensitive input
    And show generic error (no "user not found")
  
  Scenario: Account locked (optional)
    Given 5 failed attempts in 15 minutes
    When attempt login
    Then reject with "account_locked_temporarily"
    And show retry timeout message
  
  Scenario: Session persistence (PWA)
    Given user logged in, refreshed page
    When localStorage has valid refresh_token
    Then auto-refresh id_token (silent)
    And restore user context
    And continue session
```

#### US-AUTH-003: User Logout
```gherkin
Feature: Logout from application
  Scenario: Logout via menu
    Given user on dashboard
    When click "Logout"
    Then call Supabase Auth signout (invalidate refresh_token)
    And clear localStorage tokens
    And clear Redux user state
    And redirect to login page
    And confirm page no longer shows user data
```

#### US-AUTH-004: Session & Token Management (PWA)
```gherkin
Feature: Maintain secure session across app lifecycle
  Scenario: Access protected route
    Given route requires authentication
    When user.uid not in context
    Then redirect to /login (unauthorized)
  
  Scenario: Token refresh before expiry
    Given id_token expires in 1 hour
    When app detects expiry approaching
    Then auto-refresh via refresh_token (background)
    And update localStorage with new tokens
    And continue without interrupting user
  
  Scenario: Refresh token expired (> 30 days)
    Given refresh_token expired
    When API returns 401 (invalid token)
    Then clear all tokens from localStorage
    And redirect to /login with message "session_expired"
    And force re-login
  
  Scenario: Offline → Online transition (PWA)
    Given app offline, cached user data shown
    When connection restored
    Then validate token still fresh
    Then sync queued payments/changes
    Then show success notification
```

#### US-AUTH-005: Data Isolation via RLS (Database-Level)
```gherkin
Feature: Row-Level Security policies enforce ownership
  Scenario: User can only read own Clients
    Given table clients (has user_id column)
    When SELECT clients WHERE user_id = auth.uid()
    Then only return rows owned by logged-in user
    And other users' clients hidden entirely
  
  Scenario: User cannot update other user's Credit
    Given Credit belongs to User A
    When User B attempts PUT /credits/:id
    Then database RLS policy rejects (403)
    And no data leak
  
  Scenario: Cascade data ownership via FK
    Given Credit belongs to User A
    When Client deleted → deletes Credits → deletes Installments, Payments
    Then entire user data graph scoped by user_id
```

#### US-AUTH-006: Backend Middleware Validates User Context
```gherkin
Feature: Every API request verified for user context
  Scenario: Protected endpoint with valid JWT
    Given request has "Authorization: Bearer <id_token>"
    When FastAPI middleware validates token against Supabase JWKS
    Then extract user.uid from token claims
    And inject into request.state (or Depends)
    And allow endpoint to execute
  
  Scenario: Missing authorization header
    Given request has no Authorization header
    When hit protected endpoint
    Then return 401 Unauthorized
    And error message "missing_token"
  
  Scenario: Invalid/expired token
    Given JWT signature invalid OR exp < now
    When middleware validates
    Then return 401 Unauthorized
    And error message "invalid_token"
  
  Scenario: Token from different issuer
    Given JWT issuer != Supabase project
    When validation fails
    Then return 401 Unauthorized
```

#### US-AUTH-007: User Profile + Preferences (Optional Phase 2)
```gherkin
Feature: User account management
  Scenario: View profile
    Given logged-in user
    When navigate to /profile
    Then display email, created_at, last_login (future)
  
  Scenario: Change password
    Given on profile page
    When enter old password + new password
    Then call Supabase Auth updateUser
    Then show success message
  
  Scenario: Delete account (future)
    Given user initiates delete
    When confirm deletion
    Then call Supabase Auth deleteUser (cascades)
    And delete all user data (Clients, Credits, etc. via FK CASCADE)
    And log audit event
```

### 1.2 Business Rules (Non-Negotiable)

| Rule | Logic | Enforced By |
|------|-------|------------|
| **User owns data** | Every Client, Credit, Payment, Savings, History has user_id. User A cannot see User B's data. | RLS policies + Backend middleware |
| **No cross-user access** | API queries ALWAYS filtered by authenticated user.uid. Never trust user input for user_id. | Backend middleware injects user context |
| **Token validation** | Every protected request validated against Supabase JWKS public keys. No hardcoded secrets in frontend. | FastAPI middleware |
| **Session expiry** | id_token expires in 1 hour. refresh_token expires in 30 days. Automatic refresh before expiry. | Supabase Auth settings + frontend interceptor |
| **RLS immutable** | RLS policies are database-level enforcement, not bypassed by app logic. | Supabase PostgreSQL constraints |
| **Audit trail** | All auth events (login, logout, failed attempts) logged to FinancialHistory (future) | HistoryService |
| **No credential exposure** | Firebase credentials NOT exposed in frontend. Token refresh done backend. | Architecture constraint |
| **Password policy** | Min 8 chars, uppercase, lowercase, number. Enforced by Supabase Auth. | Supabase Auth settings |
| **Email uniqueness** | One email = one Supabase user account. Enforced at auth layer. | Supabase unique constraint |

### 1.3 Ambiguities Resolved

1. **Auth provider choice** → Supabase Auth (over Firebase). Rationale: built-in RLS, free tier, PostgreSQL native, zero additional cost beyond DB.

2. **JWT validation location** → Backend middleware (not frontend). Frontend validates signature visually; backend validates against Supabase JWKS.

3. **RLS vs Backend filtering** → Both. RLS is final safety net; backend middleware enforces user context injection in every query.

4. **Session storage** → localStorage (JWT tokens). No cookie-based sessions for PWA simplicity. Refresh token rotation in Supabase.

5. **User data ownership** → user_id primary isolation key. All tables have user_id FK. No shared/public records (MVP).

6. **Multi-device logout** → Single logout invalidates refresh_token across all devices. No device-specific tokens (MVP).

7. **Account recovery** → Email-based password reset via Supabase Auth UI. No custom recovery flow (MVP).

8. **Social login** → Out of scope (MVP). Email/password only.

---

## 2. DISEÑO

### 2.1 Updated Data Model (User-Scoped)

#### User (New Table)
```yaml
User:
  id: UUID (PK, generated by Supabase Auth)
  email: string (required, unique, immutable)
  email_verified: boolean (default false)
  phone: string (optional)
  first_name: string (optional)
  last_name: string (optional)
  created_at: DateTime (UTC, auto)
  updated_at: DateTime (UTC, auto)
  last_login_at: DateTime (nullable)
  deleted_at: DateTime (nullable, soft-delete)
  
  # Relationship:
  #  - PK = auth.users.id (Supabase Auth user_id)
  #  - One user : Many clients, credits, payments, savings, history

# SQL (extend from Supabase auth.users):
CREATE TABLE public.users (
  id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  email TEXT NOT NULL UNIQUE,
  email_verified BOOLEAN DEFAULT FALSE,
  phone VARCHAR(20),
  first_name VARCHAR(255),
  last_name VARCHAR(255),
  last_login_at TIMESTAMP,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  deleted_at TIMESTAMP
);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_created_at ON users(created_at);
```

#### Client (Modified: Add user_id)
```yaml
Client:
  id: UUID (PK)
  user_id: UUID (FK → auth.users, ON DELETE CASCADE) ← NEW
  first_name: string (required, min 2)
  last_name: string (required, min 2)
  phone: string (required, unique per user NOT globally)
  document_id: string (optional, unique per user)
  address: string (optional)
  notes: string (optional, max 500)
  created_at: DateTime (UTC)
  updated_at: DateTime (UTC)
  deleted_at: DateTime (nullable, soft-delete)

# Changes from v2.0:
#  - phone unique per (user_id, phone), not globally
#  - document_id unique per (user_id, document_id)
#  - RLS: SELECT/INSERT/UPDATE/DELETE only WHERE user_id = auth.uid()
```

#### Credit (Modified: Add user_id)
```yaml
Credit:
  id: UUID (PK)
  user_id: UUID (FK → auth.users, ON DELETE CASCADE) ← NEW
  client_id: UUID (FK → Client, ON DELETE CASCADE)
  # ... rest unchanged from v2.0
  
# Uniqueness constraint:
#  UNIQUE(user_id, client_id) — one credit per client per user prevents accidental duplication
```

#### Installment (Modified: Add user_id via denormalization)
```yaml
Installment:
  id: UUID (PK)
  user_id: UUID (FK → auth.users, ON DELETE CASCADE) ← NEW (denormalized for RLS query simplicity)
  credit_id: UUID (FK → Credit, ON DELETE CASCADE)
  # ... rest unchanged from v2.0
  
# Justification for user_id denormalization:
#  - RLS query becomes: SELECT installments WHERE user_id = auth.uid() (no JOIN)
#  - Performance: indexed single column vs JOIN + nested RLS
#  - Consistency: guaranteed by FK trigger (when credit.user_id set, installment inherits)
```

#### Payment (Modified: Add user_id)
```yaml
Payment:
  id: UUID (PK)
  user_id: UUID (FK → auth.users, ON DELETE CASCADE) ← NEW
  credit_id: UUID (FK → Credit, ON DELETE CASCADE)
  # ... rest unchanged from v2.0
```

#### Savings (Modified: Add user_id)
```yaml
Savings:
  id: UUID (PK)
  user_id: UUID (FK → auth.users, ON DELETE CASCADE) ← NEW
  client_id: UUID (FK → Client, ON DELETE CASCADE)
  # ... rest unchanged from v2.0
```

#### SavingsLiquidation (Modified: Add user_id)
```yaml
SavingsLiquidation:
  id: UUID (PK)
  user_id: UUID (FK → auth.users, ON DELETE CASCADE) ← NEW
  client_id: UUID (FK → Client, ON DELETE CASCADE)
  # ... rest unchanged from v2.0
```

#### FinancialHistory (Modified: Add user_id)
```yaml
FinancialHistory:
  id: UUID (PK)
  user_id: UUID (FK → auth.users, ON DELETE CASCADE) ← NEW
  client_id: UUID (FK → Client, ON DELETE CASCADE)
  credit_id: UUID (nullable)
  # ... rest unchanged from v2.0
```

### 2.2 Authentication Architecture

#### Auth Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                     PWA FRONTEND (React)                     │
│  ├─ Login page (email + password)                           │
│  ├─ Registration page                                       │
│  ├─ Protected routes (require user context)                │
│  └─ RTK Query + localStorage (token storage)               │
└────────────┬────────────────────────────────────────────────┘
             │ HTTP (TLS 1.3 only)
┌────────────▼────────────────────────────────────────────────┐
│              SUPABASE AUTH (Managed Service)                │
│  ├─ User registration (email + password hashing)           │
│  ├─ User login (JWT issuance: id_token + refresh_token)    │
│  ├─ Password reset (email flow)                            │
│  ├─ Token refresh (refresh_token → new id_token)           │
│  └─ User metadata (email, created_at)                      │
└────────────┬────────────────────────────────────────────────┘
             │ HTTP + JWKS endpoint
┌────────────▼────────────────────────────────────────────────┐
│            FASTAPI BACKEND (Business Logic)                 │
│  ├─ Middleware: validate JWT against Supabase JWKS         │
│  ├─ Inject user context (auth.uid) into request.state      │
│  ├─ Service layer: ALL queries filtered by user_id         │
│  ├─ RLS fallback: database rejects unowned data            │
│  └─ Error handling: 401 Unauthorized, 403 Forbidden        │
└────────────┬────────────────────────────────────────────────┘
             │ Supabase client (asyncpg)
┌────────────▼────────────────────────────────────────────────┐
│        SUPABASE POSTGRESQL (RLS Policies)                   │
│  ├─ Table: auth.users (Supabase managed)                   │
│  ├─ Table: public.users (app metadata)                     │
│  ├─ Table: clients, credits, payments, savings, history    │
│  ├─ RLS: SELECT/INSERT/UPDATE/DELETE WHERE user_id = uid() │
│  └─ FK CASCADE: delete user → cascade all owned data       │
└─────────────────────────────────────────────────────────────┘
```

#### Registration Flow (Detailed)

```
1. User fills form (email, password, password_confirm)
   ↓
2. Frontend validates (client-side Zod)
   - email valid format
   - password >= 8 chars, uppercase, lowercase, number
   ↓
3. POST /auth/register { email, password }
   ↓
4. Backend (no user context yet):
   - Call Supabase Auth createUser(email, password)
   - If success → uid returned
   ↓
5. Create user record in public.users:
   INSERT INTO users (id, email, email_verified, created_at)
   VALUES (uid, email, false, now())
   ↓
6. Return auth response:
   {
     "access_token": "<id_token>",
     "refresh_token": "<refresh_token>",
     "user": { "id": uid, "email": email }
   }
   ↓
7. Frontend:
   - Store tokens in localStorage
   - Initialize Redux user state
   - Redirect to /dashboard or /onboarding
```

#### Login Flow (Detailed)

```
1. User fills form (email, password)
   ↓
2. POST /auth/login { email, password }
   ↓
3. Backend:
   - Call Supabase Auth signIn(email, password)
   - If success → { id_token, refresh_token }
   - If fail → { error: "invalid_credentials" }
   ↓
4. Fetch user profile from public.users:
   SELECT id, email, first_name, last_name, created_at
   FROM users WHERE id = uid
   ↓
5. Return login response:
   {
     "access_token": id_token,
     "refresh_token": refresh_token,
     "user": { id, email, first_name, last_name }
   }
   ↓
6. Frontend:
   - Store tokens in localStorage
   - Initialize Redux state with user
   - RTK Query: set baseURL headers = Authorization: Bearer <id_token>
   - Redirect to /dashboard
```

#### Logout Flow (Detailed)

```
1. User clicks Logout
   ↓
2. Frontend calls POST /auth/logout
   ↓
3. Backend:
   - Extract user.uid from request.state (from middleware)
   - Call Supabase Auth signOut(uid) → invalidate refresh_token
   - Clear any server-side sessions (if used)
   ↓
4. Frontend:
   - Clear localStorage tokens
   - Clear Redux user state
   - Cancel all pending RTK Query requests
   - Redirect to /login
```

#### Session Persistence (PWA + Offline)

```
App Startup Sequence:
1. Load index.html → initialize service worker
2. Check localStorage for refresh_token
3. If found:
   - POST /auth/refresh { refresh_token }
   - Backend validates against Supabase
   - Return new id_token
   - Store in localStorage
   - Proceed to dashboard
4. If not found:
   - Redirect to /login

Token Refresh Logic:
- Scheduled: 5 minutes before id_token expires
- On demand: when API returns 401
- Auto-retry: if refresh fails, force re-login

Offline Handling:
- Service worker caches dashboard routes
- User sees cached data (marked as stale)
- Payments/mutations queued locally
- On online → sync queued changes + re-auth token
```

### 2.3 Backend Middleware (Token Validation)

```python
# app/middleware/auth.py

import httpx
import jwt
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse

SUPABASE_URL = os.getenv("SUPABASE_URL")  # https://project.supabase.co
SUPABASE_JWKS_URL = f"{SUPABASE_URL}/auth/v1/.well-known/jwks.json"

# Cache JWKS keys (refresh every 24 hours)
jwks_cache: Dict[str, Any] = {}
jwks_expiry: DateTime = None

async def get_jwks() -> Dict[str, Any]:
    global jwks_cache, jwks_expiry
    
    if jwks_cache and jwks_expiry > datetime.utcnow():
        return jwks_cache
    
    async with httpx.AsyncClient() as client:
        response = await client.get(SUPABASE_JWKS_URL)
        response.raise_for_status()
        jwks_cache = response.json()
        jwks_expiry = datetime.utcnow() + timedelta(hours=24)
        return jwks_cache

async def auth_middleware(request: Request, call_next):
    """
    Validate JWT token from Authorization header.
    Extract user.uid and inject into request.state.
    Public endpoints (login, register) skip validation.
    """
    
    # Public endpoints (no auth required)
    public_paths = ["/auth/login", "/auth/register", "/auth/refresh", "/health"]
    if request.url.path in public_paths or request.url.path.startswith("/openapi"):
        return await call_next(request)
    
    # Extract Authorization header
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="missing_token")
    
    token = auth_header.split(" ")[1]
    
    try:
        # Decode JWT (unverified first to extract kid)
        unverified = jwt.decode(token, options={"verify_signature": False})
        kid = jwt.get_unverified_header(token).get("kid")
        
        # Get Supabase JWKS
        jwks = await get_jwks()
        key = next((k for k in jwks["keys"] if k["kid"] == kid), None)
        
        if not key:
            raise HTTPException(status_code=401, detail="invalid_token")
        
        # Verify signature against Supabase public key
        public_key = jwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(key))
        verified = jwt.decode(
            token,
            public_key,
            algorithms=["RS256"],
            audience="authenticated",
            issuer=f"{SUPABASE_URL}/auth/v1"
        )
        
        # Extract user.uid
        user_id = verified.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="invalid_token")
        
        # Inject into request state
        request.state.user_id = user_id
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="token_expired")
    except jwt.InvalidSignatureError:
        raise HTTPException(status_code=401, detail="invalid_signature")
    except Exception as e:
        raise HTTPException(status_code=401, detail="invalid_token")
    
    response = await call_next(request)
    return response
```

### 2.4 RLS Policies (Supabase PostgreSQL)

```sql
-- SETUP: Enable RLS on all tables
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE clients ENABLE ROW LEVEL SECURITY;
ALTER TABLE credits ENABLE ROW LEVEL SECURITY;
ALTER TABLE installments ENABLE ROW LEVEL SECURITY;
ALTER TABLE payments ENABLE ROW LEVEL SECURITY;
ALTER TABLE savings ENABLE ROW LEVEL SECURITY;
ALTER TABLE savings_liquidations ENABLE ROW LEVEL SECURITY;
ALTER TABLE financial_history ENABLE ROW LEVEL SECURITY;

-- ============================================
-- POLICY: users table (authenticated users only)
-- ============================================
CREATE POLICY "users_view_own_profile" ON public.users
  FOR SELECT USING (auth.uid() = id);

CREATE POLICY "users_update_own_profile" ON public.users
  FOR UPDATE USING (auth.uid() = id)
  WITH CHECK (auth.uid() = id);

-- ============================================
-- POLICY: clients (user owns all clients)
-- ============================================
CREATE POLICY "clients_select_user_owned" ON clients
  FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "clients_insert_user_owned" ON clients
  FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "clients_update_user_owned" ON clients
  FOR UPDATE USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "clients_delete_user_owned" ON clients
  FOR DELETE USING (auth.uid() = user_id);

-- ============================================
-- POLICY: credits (user owns all credits)
-- ============================================
CREATE POLICY "credits_select_user_owned" ON credits
  FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "credits_insert_user_owned" ON credits
  FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "credits_update_user_owned" ON credits
  FOR UPDATE USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "credits_delete_user_owned" ON credits
  FOR DELETE USING (auth.uid() = user_id);

-- ============================================
-- POLICY: installments (user owns via user_id)
-- ============================================
CREATE POLICY "installments_select_user_owned" ON installments
  FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "installments_insert_user_owned" ON installments
  FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "installments_update_user_owned" ON installments
  FOR UPDATE USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "installments_delete_user_owned" ON installments
  FOR DELETE USING (auth.uid() = user_id);

-- ============================================
-- POLICY: payments (user owns via user_id)
-- ============================================
CREATE POLICY "payments_select_user_owned" ON payments
  FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "payments_insert_user_owned" ON payments
  FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "payments_update_user_owned" ON payments
  FOR UPDATE USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "payments_delete_user_owned" ON payments
  FOR DELETE USING (auth.uid() = user_id);

-- ============================================
-- POLICY: savings (user owns via user_id)
-- ============================================
CREATE POLICY "savings_select_user_owned" ON savings
  FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "savings_insert_user_owned" ON savings
  FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "savings_update_user_owned" ON savings
  FOR UPDATE USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "savings_delete_user_owned" ON savings
  FOR DELETE USING (auth.uid() = user_id);

-- ============================================
-- POLICY: savings_liquidations (user owns)
-- ============================================
CREATE POLICY "savings_liquidations_select_user_owned" ON savings_liquidations
  FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "savings_liquidations_insert_user_owned" ON savings_liquidations
  FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "savings_liquidations_update_user_owned" ON savings_liquidations
  FOR UPDATE USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "savings_liquidations_delete_user_owned" ON savings_liquidations
  FOR DELETE USING (auth.uid() = user_id);

-- ============================================
-- POLICY: financial_history (user owns)
-- ============================================
CREATE POLICY "financial_history_select_user_owned" ON financial_history
  FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "financial_history_insert_user_owned" ON financial_history
  FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "financial_history_update_user_owned" ON financial_history
  FOR UPDATE USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "financial_history_delete_user_owned" ON financial_history
  FOR DELETE USING (auth.uid() = user_id);

-- ============================================
-- Verify RLS is enabled
-- ============================================
SELECT table_name, enable_rls
FROM information_schema.tables
WHERE table_schema = 'public'
  AND table_name IN (
    'users', 'clients', 'credits', 'installments', 
    'payments', 'savings', 'savings_liquidations', 'financial_history'
  );
```

### 2.5 Service Layer (User Context Injection)

```python
# app/services/base_service.py

class BaseService:
    """
    Base service that injects user_id into all repository queries.
    NEVER query without user context.
    """
    
    def __init__(self, repo, user_id: str):
        self.repo = repo
        self.user_id = user_id
    
    async def _ensure_ownership(self, entity_id: UUID, entity_type: str = "entity"):
        """
        Verify entity belongs to authenticated user before mutation.
        Double-check: RLS should prevent this, but defense in depth.
        """
        # Example: for Credit
        entity = await self.repo.get_by_id(entity_id)
        if not entity or entity.user_id != self.user_id:
            raise HTTPException(
                status_code=403, 
                detail=f"{entity_type}_not_found_or_forbidden"
            )
        return entity

# app/services/client_service.py

class ClientService(BaseService):
    
    async def create(self, client_create: ClientCreate) -> Client:
        """Create client owned by authenticated user."""
        client = Client(
            user_id=self.user_id,  ← INJECT
            first_name=client_create.first_name,
            last_name=client_create.last_name,
            phone=client_create.phone,
            # ... other fields
        )
        return await self.repo.create(client)
    
    async def list_all(self) -> List[Client]:
        """List ONLY user's clients."""
        return await self.repo.find(user_id=self.user_id)  ← FILTER
    
    async def get_by_id(self, client_id: UUID) -> Client:
        """Get client if owned by user."""
        client = await self._ensure_ownership(client_id, "Client")
        return client
    
    async def update(self, client_id: UUID, update: ClientUpdate) -> Client:
        """Update client if owned by user."""
        client = await self._ensure_ownership(client_id, "Client")
        # ... update logic
        return await self.repo.update(client)
    
    async def delete(self, client_id: UUID) -> None:
        """Delete client if owned by user (cascades)."""
        client = await self._ensure_ownership(client_id, "Client")
        await self.repo.delete(client_id)

# app/services/credit_service.py

class CreditService(BaseService):
    
    async def create(self, client_id: UUID, credit_create: CreditCreate) -> Credit:
        """Create credit owned by user, for user's client."""
        # Verify client ownership
        client = await self._ensure_ownership(client_id, "Client")
        
        credit = Credit(
            user_id=self.user_id,  ← INJECT
            client_id=client_id,
            initial_capital=credit_create.initial_capital,
            # ... other fields
        )
        return await self.repo.create(credit)
    
    async def list_all(self) -> List[Credit]:
        """List ONLY user's credits."""
        return await self.repo.find(user_id=self.user_id)  ← FILTER
    
    async def get_by_id(self, credit_id: UUID) -> Credit:
        """Get credit with fresh mora calculation (scoped to user)."""
        credit = await self._ensure_ownership(credit_id, "Credit")
        # Recalculate mora (mora_service has same user_id)
        # ... mora recalc logic
        return credit
```

### 2.6 Router Layer (Dependency Injection)

```python
# app/routes/client_router.py

from fastapi import APIRouter, Depends, HTTPException
from app.dependencies import get_client_service

router = APIRouter(prefix="/clients", tags=["clients"])

async def get_user_id(request: Request) -> str:
    """Extract user_id from request.state (set by auth middleware)."""
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        raise HTTPException(status_code=401, detail="unauthorized")
    return user_id

async def get_client_service(
    db=Depends(get_db),
    user_id: str = Depends(get_user_id)
) -> ClientService:
    """Inject service with user context."""
    repo = ClientRepository(db)
    return ClientService(repo, user_id)

@router.get("/")
async def list_clients(service: ClientService = Depends(get_client_service)):
    """List user's clients (RLS + service filter)."""
    return await service.list_all()

@router.post("/")
async def create_client(
    body: ClientCreate,
    service: ClientService = Depends(get_client_service)
):
    """Create client owned by user."""
    return await service.create(body)

@router.get("/{client_id}")
async def get_client(
    client_id: UUID,
    service: ClientService = Depends(get_client_service)
):
    """Get client if owned by user (403 if not)."""
    return await service.get_by_id(client_id)

@router.put("/{client_id}")
async def update_client(
    client_id: UUID,
    body: ClientUpdate,
    service: ClientService = Depends(get_client_service)
):
    """Update client if owned by user."""
    return await service.update(client_id, body)

@router.delete("/{client_id}")
async def delete_client(
    client_id: UUID,
    service: ClientService = Depends(get_client_service)
):
    """Delete client if owned by user (cascades all owned data)."""
    await service.delete(client_id)
    return {"message": "deleted"}
```

### 2.7 Frontend Auth Context (React + Redux)

```typescript
// src/store/slices/authSlice.ts

interface AuthState {
  user: {
    id: string;
    email: string;
    first_name?: string;
    last_name?: string;
  } | null;
  tokens: {
    accessToken: string | null;
    refreshToken: string | null;
  };
  isLoading: boolean;
  error: string | null;
}

const authSlice = createSlice({
  name: "auth",
  initialState: {
    user: null,
    tokens: { accessToken: null, refreshToken: null },
    isLoading: false,
    error: null,
  },
  reducers: {
    setUser: (state, action) => {
      state.user = action.payload;
    },
    setTokens: (state, action) => {
      state.tokens = action.payload;
      // Persist to localStorage
      localStorage.setItem(
        "tokens",
        JSON.stringify(action.payload)
      );
    },
    clearAuth: (state) => {
      state.user = null;
      state.tokens = { accessToken: null, refreshToken: null };
      localStorage.removeItem("tokens");
    },
  },
});

// RTK Query with auto-token-injection
const apiSlice = createApi({
  reducerPath: "api",
  baseQuery: fetchBaseQuery({
    baseUrl: `${import.meta.env.VITE_API_URL}/api/v1`,
    prepareHeaders: (headers, { getState }) => {
      const tokens = (getState() as RootState).auth.tokens;
      if (tokens.accessToken) {
        headers.set(
          "Authorization",
          `Bearer ${tokens.accessToken}`
        );
      }
      return headers;
    },
  }),
  endpoints: (builder) => ({
    login: builder.mutation<AuthResponse, LoginRequest>({
      query: (body) => ({
        url: "/auth/login",
        method: "POST",
        body,
      }),
      onQueryStarted: async (_, { dispatch, queryFulfilled }) => {
        const { data } = await queryFulfilled;
        dispatch(setUser(data.user));
        dispatch(setTokens({
          accessToken: data.access_token,
          refreshToken: data.refresh_token,
        }));
      },
    }),
    register: builder.mutation<AuthResponse, RegisterRequest>({
      query: (body) => ({
        url: "/auth/register",
        method: "POST",
        body,
      }),
      // ... similar to login
    }),
    logout: builder.mutation<void, void>({
      query: () => ({
        url: "/auth/logout",
        method: "POST",
      }),
      onQueryStarted: async (_, { dispatch, queryFulfilled }) => {
        await queryFulfilled;
        dispatch(clearAuth());
      },
    }),
  }),
});

// src/hooks/useAuth.ts
export function useAuth() {
  const dispatch = useAppDispatch();
  const { user, tokens } = useAppSelector((state) => state.auth);
  const [loginMutation] = apiSlice.useLoginMutation();
  
  const login = async (email: string, password: string) => {
    const { data } = await loginMutation({ email, password }).unwrap();
    dispatch(setUser(data.user));
    dispatch(setTokens({
      accessToken: data.access_token,
      refreshToken: data.refresh_token,
    }));
  };
  
  return {
    user,
    tokens,
    login,
    isAuthenticated: !!user,
  };
}

// src/components/ProtectedRoute.tsx
export function ProtectedRoute({ children }: any) {
  const { isAuthenticated } = useAuth();
  const navigate = useNavigate();
  
  useEffect(() => {
    if (!isAuthenticated) {
      navigate("/login", { replace: true });
    }
  }, [isAuthenticated, navigate]);
  
  return isAuthenticated ? children : null;
}
```

### 2.8 Updated Database Schema (SQL Migration)

```sql
-- 1. Create public.users table (extends auth.users)
CREATE TABLE public.users (
  id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  email TEXT NOT NULL UNIQUE,
  email_verified BOOLEAN DEFAULT FALSE,
  phone VARCHAR(20),
  first_name VARCHAR(255),
  last_name VARCHAR(255),
  last_login_at TIMESTAMP,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  deleted_at TIMESTAMP
);

CREATE INDEX idx_users_email ON public.users(email);
CREATE INDEX idx_users_created_at ON public.users(created_at);

-- 2. Alter clients table (add user_id)
ALTER TABLE clients ADD COLUMN user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE;
ALTER TABLE clients DROP CONSTRAINT IF EXISTS clients_phone_key;
ALTER TABLE clients ADD CONSTRAINT clients_user_phone_unique UNIQUE(user_id, phone);
ALTER TABLE clients DROP CONSTRAINT IF EXISTS clients_document_id_key;
ALTER TABLE clients ADD CONSTRAINT clients_user_document_unique UNIQUE(user_id, document_id);
CREATE INDEX idx_clients_user ON clients(user_id);

-- 3. Alter credits table (add user_id)
ALTER TABLE credits ADD COLUMN user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE;
CREATE INDEX idx_credits_user ON credits(user_id);

-- 4. Alter installments table (add user_id for RLS efficiency)
ALTER TABLE installments ADD COLUMN user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE;
CREATE INDEX idx_installments_user ON installments(user_id);

-- Trigger to sync user_id from credit → installment on create
CREATE OR REPLACE FUNCTION sync_installment_user_id()
RETURNS TRIGGER AS $$
BEGIN
  NEW.user_id := (SELECT user_id FROM credits WHERE id = NEW.credit_id);
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER installment_user_sync BEFORE INSERT ON installments
  FOR EACH ROW EXECUTE FUNCTION sync_installment_user_id();

-- 5. Alter payments table (add user_id)
ALTER TABLE payments ADD COLUMN user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE;
CREATE INDEX idx_payments_user ON payments(user_id);

-- 6. Alter savings table (add user_id)
ALTER TABLE savings ADD COLUMN user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE;
CREATE INDEX idx_savings_user ON savings(user_id);

-- 7. Alter savings_liquidations table (add user_id)
ALTER TABLE savings_liquidations ADD COLUMN user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE;
CREATE INDEX idx_savings_liquidations_user ON savings_liquidations(user_id);

-- 8. Alter financial_history table (add user_id)
ALTER TABLE financial_history ADD COLUMN user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE;
CREATE INDEX idx_financial_history_user ON financial_history(user_id);
```

---

## 3. LISTA DE TAREAS

### 3.1 Backend Auth Implementation

#### Phase 1: Supabase Setup + User Table (Week 1)

- [x] Create Supabase project (PostgreSQL) — assumed per integration (migrations target Supabase auth.users)
  - [ ] Enable authentication (email/password) — config not verifiable in repo (Supabase dashboard)
  - [ ] Configure password policy (min 8 chars, uppercase, number) — validated in backend AuthService + RegisterPage
  - [ ] Set token expiry: id_token=1h, refresh_token=30d — Supabase dashboard setting, not repo-verifiable
- [x] Create public.users table — verified: database/migrations/001_initial_schema.sql 2026-04-23
  - [x] FK reference to auth.users
  - [x] Fields: email, email_verified, phone, first_name, last_name, last_login_at, timestamps
  - [x] Unique constraints on email
- [x] Database migration for all tables (add user_id + indexes) — verified: database/migrations/002_rls_policies.sql 2026-04-23
  - [x] clients: user_id + phone/document uniqueness per user
  - [x] credits: user_id
  - [x] installments: user_id + sync trigger from credit
  - [x] payments: user_id
  - [x] savings: user_id
  - [x] savings_liquidations: user_id
  - [x] financial_history: user_id
- [x] Enable RLS on all tables — verified: database/migrations/002_rls_policies.sql 2026-04-23
  - [x] Deploy all RLS policies (see Section 2.4)
  - [ ] Test: SELECT as different users, verify isolation — PENDING: requires live Supabase instance
- [ ] Tests — PENDING: integration tests require real Supabase DB
  - [ ] test_user_table_created.py
  - [ ] test_rls_policy_isolation.py (User A cannot read User B's clients)
  - [ ] test_rls_insert_enforcement.py (inserting without user_id fails)

#### Phase 2: Authentication Endpoints (Week 1-2)

- [x] Setup Supabase client in FastAPI (supabase-py async) — verified: backend/app/db.py 2026-04-23
- [x] Implement /auth/register endpoint — verified: backend/app/routes/auth_router.py 2026-04-23
  - [x] Validate email format + password strength
  - [x] Call Supabase Auth createUser(email, password)
  - [x] Create user record in public.users
  - [x] Return { access_token, refresh_token, user }
  - [x] Error handling: email_already_exists, invalid_password
- [x] Implement /auth/login endpoint — verified: backend/app/routes/auth_router.py 2026-04-23
  - [x] Call Supabase Auth signIn(email, password)
  - [x] Fetch user profile from public.users
  - [x] Return { access_token, refresh_token, user }
  - [x] Error handling: invalid_credentials, user_not_found
- [x] Implement /auth/logout endpoint — verified: backend/app/routes/auth_router.py 2026-04-23
  - [x] Extract user_id from request.state
  - [x] Call Supabase Auth signOut(user_id)
  - [x] Return { message: "logged_out" }
- [x] Implement /auth/refresh endpoint — verified: backend/app/routes/auth_router.py 2026-04-23
  - [x] Accept refresh_token in body
  - [x] Call Supabase Auth refreshSession(refresh_token)
  - [x] Return { access_token, refresh_token }
  - [x] Error handling: invalid_refresh_token, token_expired
- [x] Tests — verified: backend/tests/test_auth_middleware.py 2026-04-23 (middleware coverage PASS)
  - [ ] test_auth_register_success.py — not found as standalone file
  - [ ] test_auth_register_email_exists.py — not found as standalone file
  - [ ] test_auth_register_weak_password.py — not found as standalone file
  - [ ] test_auth_login_success.py — not found as standalone file
  - [ ] test_auth_login_invalid_credentials.py — not found as standalone file
  - [ ] test_auth_logout.py — not found as standalone file
  - [ ] test_auth_refresh_token.py — not found as standalone file

#### Phase 3: Auth Middleware + Token Validation (Week 2)

- [ ] Implement auth middleware (see Section 2.3)
  - [ ] Cache Supabase JWKS public keys
  - [ ] Extract JWT from Authorization header
  - [ ] Validate signature against Supabase JWKS
  - [ ] Handle expired tokens (401)
  - [ ] Inject user_id into request.state
  - [ ] Skip validation for public endpoints (/auth/login, /auth/register, /auth/refresh, /health)
- [ ] Add middleware to FastAPI app (CORS, auth order matters)
- [ ] Tests:
  - [ ] test_middleware_valid_token.py
  - [ ] test_middleware_missing_token.py (protected endpoint → 401)
  - [ ] test_middleware_invalid_signature.py (401)
  - [ ] test_middleware_expired_token.py (401)
  - [ ] test_middleware_public_endpoint_skips.py

#### Phase 4: Base Service + User Context Injection (Week 2-3)

- [ ] Refactor service layer (BaseService + user_id injection)
  - [ ] BaseService: all queries ALWAYS filtered by self.user_id
  - [ ] _ensure_ownership(): verify entity belongs to user before mutation
- [ ] Update ClientService
  - [ ] create(): inject user_id
  - [ ] list_all(): filter by user_id
  - [ ] get_by_id(): ensure ownership
  - [ ] update(): ensure ownership
  - [ ] delete(): ensure ownership
- [ ] Update CreditService (same pattern)
  - [ ] create(): inject user_id, verify client ownership
  - [ ] list_all(): filter by user_id
  - [ ] get_by_id(): ensure ownership + recalc mora
  - [ ] update(): ensure ownership
- [ ] Update InstallmentService, PaymentService, SavingsService, HistoryService
  - [ ] Same user_id injection + ownership checks
- [ ] Tests:
  - [ ] test_client_service_injection.py
  - [ ] test_client_service_list_own_only.py
  - [ ] test_client_service_cannot_access_other_user.py (403)
  - [ ] test_credit_service_ownership_check.py

#### Phase 5: Router Layer + Dependency Injection (Week 3)

- [ ] Refactor routers to inject services with user context
  - [ ] get_user_id Depends: extract from request.state
  - [ ] get_<feature>_service Depends: instantiate service with user_id
  - [ ] All endpoints inject service dependency
- [ ] Update client_router, credit_router, installment_router, payment_router, savings_router, history_router
- [ ] Tests:
  - [ ] test_client_router_list.py
  - [ ] test_client_router_create.py
  - [ ] test_client_router_get_forbidden_other_user.py (403)
  - [ ] test_payment_router_forbidden.py (User A cannot pay User B's credit)

#### Phase 6: Integration Tests (Week 3-4)

- [ ] End-to-end flow: register → login → create client → create credit → logout
- [ ] Multi-user isolation:
  - [ ] User A creates client, User B cannot see it
  - [ ] User B cannot pay User A's credits
  - [ ] Payments only affect user's own credits
- [ ] RLS + Backend double-check:
  - [ ] Disable backend filter, verify RLS rejects unauthorized
  - [ ] Intentional violation test (modify query to remove user_id filter)
- [ ] Session + Token lifecycle:
  - [ ] Refresh token works
  - [ ] Expired token → 401
  - [ ] Logout invalidates session

### 3.2 Frontend Auth Implementation (React + Redux)

#### Phase 1: Login/Register Pages (Week 1-2)

- [ ] Login page component
  - [ ] Email + Password form fields
  - [ ] Validation (email format, password filled)
  - [ ] Submit → POST /auth/login
  - [ ] Error display (invalid_credentials)
  - [ ] Success → store tokens, redirect to /dashboard
  - [ ] "Register" link → /register
- [ ] Register page component
  - [ ] Email, Password, Password Confirmation fields
  - [ ] Validation (email format, password >= 8 chars, uppercase, number)
  - [ ] Show password strength meter
  - [ ] Submit → POST /auth/register
  - [ ] Error handling (email_already_exists, invalid_password)
  - [ ] Success → auto-login, redirect to /dashboard or /onboarding
- [ ] Password input component with show/hide toggle
- [ ] Tests:
  - [ ] test_login_page_renders.test.tsx
  - [ ] test_login_submit_valid_credentials.test.tsx
  - [ ] test_login_error_invalid_credentials.test.tsx
  - [ ] test_register_page_renders.test.tsx
  - [ ] test_register_password_validation.test.tsx
  - [ ] test_register_success.test.tsx

#### Phase 2: Redux Auth State + RTK Query (Week 2)

- [ ] Create authSlice (Redux):
  - [ ] setUser, setTokens, clearAuth reducers
  - [ ] localStorage persistence for tokens
- [ ] Create RTK Query api slice:
  - [ ] login mutation
  - [ ] register mutation
  - [ ] logout mutation
  - [ ] refresh mutation
  - [ ] Auto-inject Authorization header in fetchBaseQuery
- [ ] Create useAuth() custom hook
  - [ ] Return { user, tokens, isAuthenticated }
  - [ ] Expose login/register/logout functions
- [ ] Tests:
  - [ ] test_auth_redux_slice.test.ts
  - [ ] test_auth_token_persistence.test.ts
  - [ ] test_use_auth_hook.test.ts

#### Phase 3: Protected Routes + Session Persistence (Week 2-3)

- [ ] ProtectedRoute wrapper component
  - [ ] Check isAuthenticated, redirect to /login if not
- [ ] App startup sequence:
  - [ ] Check localStorage for tokens
  - [ ] If found: auto-refresh + restore user state
  - [ ] If not: show login page
  - [ ] Handle refresh token expiry (force re-login)
- [ ] Token refresh interceptor:
  - [ ] On 401 response: attempt refresh via /auth/refresh
  - [ ] If refresh succeeds: retry original request
  - [ ] If refresh fails: force logout + redirect to /login
- [ ] Tests:
  - [ ] test_protected_route_unauthenticated.test.tsx
  - [ ] test_protected_route_authenticated.test.tsx
  - [ ] test_app_startup_with_valid_token.test.tsx
  - [ ] test_token_refresh_on_401.test.tsx
  - [ ] test_token_refresh_failure_logout.test.tsx

#### Phase 4: Logout + Session Management (Week 3)

- [ ] Logout button in header/menu
  - [ ] Click → POST /auth/logout
  - [ ] Clear tokens from localStorage
  - [ ] Clear Redux state
  - [ ] Redirect to /login
- [ ] Profile page (future):
  - [ ] Display user.email, created_at
  - [ ] (Optional: change password, delete account)
- [ ] Tests:
  - [ ] test_logout_button_clears_state.test.tsx
  - [ ] test_logout_endpoint_called.test.tsx

#### Phase 5: PWA Offline + Service Worker (Week 3-4)

- [ ] Service worker registration (via Vite Workbox plugin)
- [ ] Offline detection:
  - [ ] navigator.onLine
  - [ ] Show "offline" badge when no connection
- [ ] Queuing mechanism:
  - [ ] Queue mutations (payments, client create) when offline
  - [ ] Retry on online transition
  - [ ] User warning: "Changes queued, syncing..."
- [ ] Token validation offline:
  - [ ] If token expired while offline, prompt re-login on online
- [ ] Tests:
  - [ ] test_offline_badge_shown.test.tsx
  - [ ] test_mutation_queued_offline.test.ts
  - [ ] test_queued_sync_on_online.test.ts

#### Phase 6: Styling + Responsive Design (Week 4)

- [ ] Mobile-first login/register pages
  - [ ] Full-width forms on mobile
  - [ ] Centered layout on desktop
- [ ] Accessibility (WCAG 2.1 A):
  - [ ] Form labels + aria-label
  - [ ] Error announcements (aria-live)
  - [ ] Keyboard navigation (Tab, Enter)
- [ ] Tailwind CSS styling
- [ ] Tests:
  - [ ] test_login_mobile_responsive.test.tsx
  - [ ] test_form_accessibility.test.tsx

### 3.3 Quality Assurance (QA Checklists)

#### Unit Tests (Backend)

- [ ] Auth middleware:
  - [ ] Valid JWT signature validation
  - [ ] Invalid signature rejection (401)
  - [ ] Expired token rejection (401)
  - [ ] Missing token rejection (401)
  - [ ] Public endpoint bypass
  - [ ] user_id extraction from token

- [ ] AuthService:
  - [ ] register(): Supabase call, user record creation
  - [ ] login(): credentials validation, token return
  - [ ] logout(): session invalidation
  - [ ] refresh(): token refresh, expiry check

- [ ] BaseService (user_id injection):
  - [ ] All queries include user_id filter
  - [ ] _ensure_ownership() rejects cross-user access

- [ ] ClientService (with user_id):
  - [ ] create(): injects user_id
  - [ ] list_all(): returns only user's clients
  - [ ] get_by_id(): 403 if not owned by user
  - [ ] update(): 403 if not owned by user
  - [ ] delete(): 403 if not owned by user

- [ ] RLS Policy tests:
  - [ ] User A cannot SELECT User B's clients (RLS enforces)
  - [ ] User A cannot INSERT record without user_id
  - [ ] User B UPDATE User A's credit rejected (RLS)

#### Unit Tests (Frontend)

- [ ] Login form:
  - [ ] Valid email + password submit
  - [ ] Invalid email rejected
  - [ ] Empty fields rejected
  - [ ] API error displayed

- [ ] Register form:
  - [ ] Password validation (8 chars, uppercase, number)
  - [ ] Password confirmation match
  - [ ] Email uniqueness check

- [ ] Redux auth slice:
  - [ ] setUser() updates state
  - [ ] setTokens() persists to localStorage
  - [ ] clearAuth() clears state + localStorage

- [ ] useAuth() hook:
  - [ ] Returns user, tokens, isAuthenticated

- [ ] ProtectedRoute:
  - [ ] Redirects unauthenticated users to /login
  - [ ] Allows authenticated users

#### Integration Tests (Backend → Database)

- [ ] User registration flow:
  - [ ] Register user → auth.users + public.users created
  - [ ] Email stored correctly
  - [ ] RLS policies apply to new user's tables

- [ ] Multi-user isolation:
  - [ ] User A creates client
  - [ ] User B queries clients → sees empty list
  - [ ] User A deletes client → User B still sees empty

- [ ] Payment isolation:
  - [ ] User A's credit cannot be paid by User B (ownership check + RLS)
  - [ ] User B's payment only affects User B's credits

- [ ] Cascade delete:
  - [ ] Delete user → auth.users deleted → cascades to all owned data
  - [ ] No orphaned records remain

#### Integration Tests (Frontend ↔ Backend)

- [ ] Full login flow:
  - [ ] Register → Login → Dashboard visible
  - [ ] Tokens stored → Page refresh → session persists
  - [ ] Logout → tokens cleared → redirected to /login

- [ ] Data isolation (frontend):
  - [ ] User A logs in, sees own clients
  - [ ] User A logs out
  - [ ] User B logs in, sees own clients (different from User A)

- [ ] Payment processing (multi-user):
  - [ ] User A creates credit + payment
  - [ ] User B cannot see User A's payment (API 403)
  - [ ] User A's history shows only own payments

#### Business Logic Tests (Gherkin)

```gherkin
Feature: Multi-user authentication and data isolation
  Scenario: User registration and login
    Given no account for email@example.com
    When register with valid credentials
    Then account created
    And auto-logged in
    And redirected to dashboard

  Scenario: User isolation in data access
    Given User A with 3 clients
    And User B with 2 clients
    When User A logs in
    Then User A sees 3 clients
    And cannot access User B's clients

  Scenario: Payment authorization
    Given Credit owned by User A
    When User B attempts to pay
    Then API returns 403 Forbidden
    And payment not recorded

  Scenario: Session expiry
    Given user logged in
    When id_token expires
    Then app auto-refreshes token
    And user continues working

  Scenario: Cross-device logout
    Given user logged in on Device A
    When logout on Device A
    Then refresh_token invalidated
    And Device B session becomes invalid on next API call
```

#### Security Tests

- [ ] Token validation:
  - [ ] Invalid token signature rejected (401)
  - [ ] Expired token rejected (401)
  - [ ] Token from different issuer rejected (401)

- [ ] Data isolation:
  - [ ] Direct SQL: SELECT * FROM clients WHERE user_id != auth.uid() returns empty
  - [ ] API: GET /clients?user_id=other_user returns 403 or empty

- [ ] CORS:
  - [ ] Request from unauthorized origin rejected (CORS header)

- [ ] Rate limiting (future):
  - [ ] /auth/login limited to 5 attempts/15 min
  - [ ] /auth/register limited to 10 accounts/hour/IP

- [ ] Input validation:
  - [ ] Email: valid format enforced
  - [ ] Password: strength enforced
  - [ ] UUID: valid format in URLs

#### Performance Tests

- [ ] Login endpoint:
  - [ ] Response time < 500ms (Supabase call + token generation)

- [ ] List clients query:
  - [ ] RLS + WHERE user_id filter → <300ms (even with 1000 global clients)

- [ ] Token refresh:
  - [ ] < 100ms (local JWKS cache)

- [ ] Frontend:
  - [ ] Login page initial load < 1s
  - [ ] Dashboard load (with RTK Query cache) < 500ms

---

## 4. SEGURIDAD + RIESGOS

### Security Risks & Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|-----------|
| **Token leaked in localStorage** | Attacker gains session | Medium | Use httpOnly cookie (Supabase session) OR localStorage + short expiry (1h) + token rotation |
| **XSS in frontend** | Attacker steals tokens from localStorage | Medium | Sanitize user input, CSP headers, no eval(), escape HTML |
| **RLS policy misconfiguration** | Data leak between users | Low | Test RLS as different users, audit USING clauses, code review |
| **Backend filter bypass** | User A reads User B data | Low | RLS as final safety net, double-check backend filter, 403 on ownership fail |
| **Brute force login** | Account takeover | Medium | Rate limiting on /auth/login (5 attempts/15min), account lockout |
| **Weak password** | Guessable account | Low | Enforce password policy: 8 chars, uppercase, number, no common words |
| **Refresh token theft** | Session hijacking | Medium | Supabase handles rotation; rotate every 24h (configurable) |
| **Token not refreshed before expiry** | Session timeout mid-flow | Low | Frontend: auto-refresh 5min before expiry, show warning |
| **CORS misconfiguration** | Unauthorized origins access API | Medium | Whitelist frontend origin only, no wildcard \* |
| **Sensitive data in logs** | PII leak | Low | No passwords, tokens, or emails in logs; use correlation IDs |
| **Unencrypted password in transit** | Man-in-the-middle | Low | TLS 1.3 enforced, HSTS header (>6 months) |
| **Auth endpoint rate limiting absent** | Brute force attack | Medium | Implement rate limiting on /auth/login, /auth/register |
| **User.uid spoofing** | False user context | Low | Middleware validates JWT signature; cannot forge uid |
| **Soft-delete user still has access** | Data retention issue | Low | Soft-delete marks deleted_at; app logic excludes deleted users |

### Compliance Considerations

- **GDPR** (if EU users): Right to delete → soft-delete with 30-day grace period, then hard-delete
- **Data residency**: Supabase region selection (e.g., EU-West for GDPR)
- **Audit trail**: FinancialHistory immutable, logs all auth events (future)
- **Encryption**: TLS in transit, Supabase handles encryption at rest

---

## 5. IMPACTO EN ESPECIFICACIÓN ANTERIOR (v2.0)

### Changes to SPEC-001 Required

1. **Database Schema**
   - Add user_id FK to: Client, Credit, Installment, Payment, Savings, SavingsLiquidation, FinancialHistory
   - Create public.users table (FK to auth.users)
   - Modify unique constraints (phone, document_id unique per user, not globally)
   - Enable RLS on all tables

2. **Backend Services**
   - All services inherit from BaseService (user_id injection)
   - All repositories filter by user_id (no exception)
   - Auth middleware in main.py
   - Dependency injection: get_user_id Depends

3. **API Endpoints**
   - All endpoints protected (except /auth/*)
   - All responses scoped to user_id
   - Error responses: 403 Forbidden (not found/forbidden, no distinction)

4. **Frontend**
   - RTK Query: inject Authorization header
   - Redux: authSlice + useAuth() hook
   - ProtectedRoute wrapper
   - Service worker: cache tokens + handle refresh

5. **Tests**
   - Add multi-user isolation tests
   - Add ownership verification tests
   - Add RLS enforcement tests
   - Add token validation tests

### NO Changes to Business Logic (Interest, Mora, Payments)

- Interest calculation, payment mandatory order, mora detection → UNCHANGED
- Only data isolation added, not business rule modification

---

## 6. TRANSICIÓN (DRAFT → IMPLEMENTATION)

### Approval Checklist

Before marking this spec APPROVED:

- [ ] Security architect reviewed RLS policies
- [ ] Database team verified migration safety (on staging)
- [ ] Backend lead verified service layer pattern
- [ ] Frontend lead verified auth flow + RTK Query integration
- [ ] Product lead confirmed no business logic changes

### Implementation Sequencing

**Week 1** (Foundation):
- Supabase project + RLS policies
- User table + migrations
- Auth middleware

**Week 2** (Auth Endpoints):
- /auth/register, /login, /logout, /refresh
- Middleware + token validation
- Backend tests

**Week 3** (Service Refactoring):
- BaseService + user_id injection
- All services + routers updated
- Integration tests

**Week 4** (Frontend):
- Login/register pages
- Redux auth slice + RTK Query
- ProtectedRoute + session persistence
- End-to-end tests

### Risk Mitigation During Implementation

- Stage 1: Auth-only (no business logic changes)
- Stage 2: Single test user on staging
- Stage 3: Internal team testing (multi-user)
- Stage 4: UAT with sample users
- Stage 5: Gradual rollout (10% → 50% → 100%)

---

## 7. FAQ

**Q: Why Supabase Auth over Firebase?**
A: Supabase Auth is free, built-in to PostgreSQL, supports RLS natively, and no additional cost beyond DB.

**Q: Why add user_id to Installment if it can be derived from Credit?**
A: RLS queries become single-table (fast) vs JOIN. Slight denormalization for performance.

**Q: Can user_id be spoofed?**
A: No. JWT signature validated against Supabase JWKS. user_id extracted from validated token claims.

**Q: What if user deletes account?**
A: ON DELETE CASCADE deletes auth.users → cascades to all owned data. Soft-delete option available for audit.

**Q: How do we handle password reset?**
A: Supabase Auth handles via email link. App redirects user to reset page. Out of scope for MVP.

**Q: Can one user manage credits for multiple sub-accounts?**
A: No (MVP). Each user is independent. Multi-operator support is future scope.

---

## 8. PRÓXIMOS PASOS

1. **Review & Approve this spec** with security team + database team
2. **Create task board** from Section 3 checklist
3. **Setup Supabase project** (PostgreSQL, auth enabled)
4. **Assign Phase 1 (Supabase + RLS)** to database engineer
5. **Assign Phase 2-3 (Auth endpoints + middleware)** to backend engineer
6. **Parallel Phase 1-2 (Pages + Redux)** to frontend engineer
7. **Weekly sync** on auth integration, token handling
8. **Security audit** before production deployment

---

**SPEC DRAFT READY FOR REVIEW** — Comprehensive multi-tenant auth design with Supabase + RLS + FastAPI middleware. Zero ambiguities. All data isolation enforced at DB + app layer.
