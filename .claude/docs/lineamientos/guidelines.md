# 📋 Lineamientos de Desarrollo
# Versión: 1.0.0
# Última actualización: 2026-02-25

## 1. Estándares de Código

### Nomenclatura
- Clases: PascalCase → `UserService`, `OrderRepository`
- Métodos/Variables: camelCase → `getUserById`, `totalAmount`
- Constantes: UPPER_SNAKE_CASE → `MAX_RETRY_COUNT`
- Archivos: kebab-case → `user-service.ts`, `order-repository.java`

### Estructura de Carpetas
```
src/
├── controllers/    ← Solo reciben y responden requests
├── services/       ← Lógica de negocio
├── repositories/   ← Acceso a datos
├── models/         ← Entidades y DTOs
├── utils/          ← Funciones utilitarias
└── tests/          ← Todos los tests
```

### Reglas de Código
- Máximo 20 líneas por función
- Máximo 200 líneas por clase
- Sin números mágicos (usar constantes nombradas)
- Sin comentarios que expliquen QUÉ hace el código
- Manejo explícito de errores en cada función

## 2. Estándares de Testing

### Cobertura Mínima Requerida
- Unitarios: 80% mínimo
- Integración: todos los endpoints cubiertos
- E2E: todos los flujos críticos cubiertos

### Nomenclatura de Tests
```
given_[contexto]_when_[acción]_then_[resultado esperado]
Ejemplo: given_validUser_when_login_then_returnToken
```

### Estructura de Tests (AAA)
- **Arrange**: preparar datos de prueba
- **Act**: ejecutar la acción bajo prueba
- **Assert**: verificar el resultado esperado

## 3. Estándares de API

### Convenciones REST
- GET    /recursos         → listar todos
- GET    /recursos/:id     → obtener uno
- POST   /recursos         → crear
- PUT    /recursos/:id     → actualizar completo
- PATCH  /recursos/:id     → actualizar parcial
- DELETE /recursos/:id     → eliminar

### Formato de Respuesta Exitosa
```json
{
  "success": true,
  "data": {},
  "message": "Operación exitosa",
  "timestamp": "2026-02-25T00:00:00Z"
}
```

### Formato de Respuesta de Error
```json
{
  "success": false,
  "error": {
    "code": "USER_NOT_FOUND",
    "message": "El usuario no existe",
    "details": []
  },
  "timestamp": "2026-02-25T00:00:00Z"
}
```

## 4. Estándares de Git

### Ramas
- `main`                          → producción (protegida)
- `develop`                       → integración
- `feature/[ticket]-descripcion`  → nuevas funcionalidades
- `bugfix/[ticket]-descripcion`   → corrección de bugs
- `hotfix/[ticket]-descripcion`   → corrección urgente en producción

### Commits (Conventional Commits)
```
feat: agrega autenticación con JWT
fix: corrige validación de email en registro
test: agrega tests de integración para UserController
docs: actualiza README con instrucciones de instalación
refactor: extrae lógica de validación a UserValidator
chore: actualiza dependencias de seguridad
```

## 5. Estándares de Seguridad

- Sin credenciales hardcodeadas (usar variables de entorno)
- Validar TODOS los inputs del usuario antes de procesarlos
- Sanitizar datos antes de persistir en base de datos
- Logs sin información sensible (passwords, tokens, datos personales)
- Dependencias auditadas regularmente (sin vulnerabilidades críticas)
- Autenticación requerida en todos los endpoints privados

## 6. Estándares de Pipeline

### Quality Gates Obligatorios (bloquean el avance)
- Build exitoso
- Cobertura de código >= 80%
- 0 tests fallidos
- 0 vulnerabilidades críticas (OWASP)
- Lint sin errores

### Stages del Pipeline en Orden
1. `lint`              → análisis estático
2. `build`             → compilación
3. `unit-test`         → unitarios + cobertura
4. `integration-test`  → integración backend
5. `contract-test`     → verificación de contratos
6. `e2e-test`          → pruebas end-to-end
7. `security-scan`     → análisis de vulnerabilidades
8. `deploy-staging`    → despliegue en staging

### Ambientes
- `develop` → despliega en DEV automáticamente
- `main`    → despliega en STAGING automáticamente
- `release` → despliega en PROD con aprobación manual
