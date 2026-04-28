---
id: SPEC-003
status: APPROVED
feature: auth-service-fix
created: 2026-04-28
updated: 2026-04-28
author: spec-generator
version: "1.0"
related-specs:
  - SPEC-001 (natillera-pwa)
  - SPEC-002 (natillera-auth-multitenant)
---

# Auth Service Fix — Supabase Auth Integration

## 1. REQUERIMIENTOS

### Problema Actual
El AuthService intenta insertar directamente en `auth.users` lo cual no es posible. Se debe usar Supabase Auth Client API.

### User Story - Registro de Usuario
```
Como: usuario nuevo
Quiero: registrarme con email y contraseña
Para: acceder a la aplicación con mi cuenta personal
```

#### Criterios Gherkin - Registro
```gherkin
Feature: User Registration
  Scenario: Registro exitoso con email y contraseña válida
    Given usuario en página de registro
    When ingresa email válido y contraseña (≥8 chars, 1 mayúscula, 1 número)
    And hace click en "Registrarse"
    Then Supabase Auth crea el usuario
    And retorna access_token y refresh_token
    And redirecciona al dashboard

  Scenario: Email ya registrado
    Given email existe en Supabase Auth
    When intenta registrarse con ese email
    Then retorna error "email_already_exists"
    And muestra mensaje de error

  Scenario: Contraseña débil
    Given contraseña < 8 caracteres
    When intenta registrarse
    Then retorna error "weak_password"
    And muestra requisitos de contraseña
```

### User Story - Login
```
Como: usuario registrado
Quiero: iniciar sesión con email y contraseña
Para: acceder a mi cuenta
```

#### Criterios Gherkin - Login
```gherkin
Feature: User Login
  Scenario: Login exitoso
    Given usuario con cuenta registrada
    When ingresa email y contraseña correctos
    Then Supabase Auth valida credenciales
    And retorna access_token y refresh_token
    And redirecciona al dashboard

  Scenario: Credenciales inválidas
    Given email o contraseña incorrectos
    When intenta login
    Then retorna error "invalid_credentials"
    And muestra mensaje genérico (no revelar qué campo está mal)

  Scenario: Usuario no existe
    Given email no está registrado
    When intenta login
    Then retorna error "invalid_credentials"
    And muestra mismo mensaje que credenciales inválidas
```

### User Story - Logout
```
Como: usuario autenticado
Quiero: cerrar sesión
Para: terminar mi sesión en el dispositivo
```

### Reglas de Negocio
1. **Auth via Supabase Client**: Usar `supabase.auth.sign_up()` y `supabase.auth.sign_in_with_password()` - NO insert directo a auth.users
2. **Password policy**: Mínimo 8 caracteres, 1 mayúscula, 1 número
3. **Token expiry**: access_token 1 hora, refresh_token 30 días
4. **Error handling**: No revelar si el email existe o no (security)

---

## 2. DISEÑO

### 2.1 Backend - AuthService Modifications

#### Ubicación
`backend/app/services/auth_service.py`

#### Cambios Requeridos

```python
# AFTER FIX - Usar Supabase Auth Client
from supabase import create_client, Client
from app.config import get_settings

class AuthService:
    def __init__(self, db):
        self.db = db
        settings = get_settings()
        self._supabase: Client = None
        self._supabase_url = settings.supabase_url

    async def _get_supabase_client(self) -> Client:
        """Get or create Supabase client with anon key for auth"""
        if self._supabase is None:
            settings = get_settings()
            self._supabase = create_client(
                settings.supabase_url,
                settings.supabase_anon_key
            )
        return self._supabase

    async def register(self, body: RegisterRequest) -> AuthResponse:
        """Register using Supabase Auth API"""
        supabase = await self._get_supabase_client()
        
        try:
            response = supabase.auth.sign_up({
                "email": body.email,
                "password": body.password,
                "options": {
                    "email_redirect_to": f"{settings.supabase_url}/auth/callback"
                }
            })
            
            if response.user is None:
                raise ValueError("registration_failed")
            
            return AuthResponse(
                access_token=response.session.access_token,
                refresh_token=response.session.refresh_token,
                user=UserInfo(
                    id=response.user.id,
                    email=response.user.email
                )
            )
        except Exception as e:
            if "email_already_exists" in str(e):
                raise ValueError("email_already_exists")
            raise ValueError(f"registration_failed: {e}")

    async def login(self, body: LoginRequest) -> AuthResponse:
        """Login using Supabase Auth API"""
        supabase = await self._get_supabase_client()
        
        try:
            response = supabase.auth.sign_in_with_password({
                "email": body.email,
                "password": body.password
            })
            
            if response.user is None:
                raise ValueError("invalid_credentials")
            
            return AuthResponse(
                access_token=response.session.access_token,
                refresh_token=response.session.refresh_token,
                user=UserInfo(
                    id=response.user.id,
                    email=response.user.email
                )
            )
        except Exception as e:
            raise ValueError("invalid_credentials")

    async def logout(self, access_token: str) -> None:
        """Logout using Supabase Auth API"""
        supabase = await self._get_supabase_client()
        supabase.auth.sign_out()
```

#### Modelos Actualizados

```python
# backend/app/models/auth_model.py
from pydantic import BaseModel, EmailStr
from typing import Optional

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str  # min_length=8, will validate in service

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class RefreshRequest(BaseModel):
    refresh_token: str

class UserInfo(BaseModel):
    id: str
    email: EmailStr

class AuthResponse(BaseModel):
    access_token: str
    refresh_token: str
    user: UserInfo
```

### 2.2 CORS Configuration

#### Verificar que /auth/register esté en paths públicos
`backend/app/middleware/auth.py`:

```python
PUBLIC_PATHS = {
    "/api/v1/auth/login",
    "/api/v1/auth/register",
    "/api/v1/auth/refresh",
    "/health",
    "/debug/env",
    "/openapi.json",
    "/docs",
    "/redoc",
}
```

### 2.3 Frontend - Auth Integration

#### RTK Query ya configurado
- `frontend/src/store/api/apiSlice.ts` ya tiene `BASE_URL`
- `frontend/src/store/slices/authSlice.ts` maneja tokens

#### Pages a verificar
- `frontend/src/pages/LoginPage.tsx` - llama POST /auth/login
- `frontend/src/pages/RegisterPage.tsx` - llama POST /auth/register

---

## 3. LISTA DE TAREAS

### 3.1 Backend

- [ ] Modificar `auth_service.py` para usar Supabase Auth Client
  - [ ] Implementar `_get_supabase_client()` con anon key
  - [ ] Fix `register()` usando `supabase.auth.sign_up()`
  - [ ] Fix `login()` usando `supabase.auth.sign_in_with_password()`
  - [ ] Fix `logout()` usando `supabase.auth.sign_out()`
- [ ] Verificar CORS en `auth_router.py` (debe estar en PUBLIC_PATHS)
- [ ] Test manual: POST /auth/register desde curl
- [ ] Test manual: POST /auth/login desde curl

### 3.2 Frontend

- [ ] Verificar que LoginPage llama correctamente `/auth/login`
- [ ] Verificar que RegisterPage llama correctamente `/auth/register`
- [ ] Verificar manejo de errores 401/500 en UI

### 3.3 Testing

- [ ] Test: Registro exitoso devuelve 201 con tokens
- [ ] Test: Registro con email existente devuelve 400
- [ ] Test: Login con credenciales correctas devuelve tokens
- [ ] Test: Login con credenciales incorrectas devuelve 401
- [ ] Test: Registro desde GitHub Pages (CORS)

---

## 4. RIESGOS

| Riesgo | Impacto | Mitigación |
|--------|---------|-------------|
| Supabase Auth API rate limits | Medio | Implementar retry con backoff |
| Token refresh manual | Alto | Usar Supabase session management |
| CORS sigue fallando | Alto | Verificar header en respuesta OPTIONS |
| Password policy no se valida | Medio | Validar en backend antes de llamar Auth API |

---

## 5. DEPENDENCIAS

- Supabase URL configurado en Railway
- Supabase Anon Key configurado en Railway
- CORS permitido para https://duver0.github.io
