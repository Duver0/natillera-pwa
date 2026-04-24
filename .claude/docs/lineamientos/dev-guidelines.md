
# Resumen de Lineamientos de Desarrollo (CoE DevArq)

Este documento centraliza los principios y reglas **obligatorias** para garantizar que el software diseñado, construido y desplegado sea seguro, limpio, mantenible y resiliente. 

---

### 1. Codificación Segura por Defecto (LIN-DEV-003)
**Objetivo:** Integrar la seguridad desde el diseño para proteger datos y eliminar vulnerabilidades conocidas antes del despliegue.
*   **Validación Estricta:** Toda entrada de datos externos debe ser validada (mediante schemas declarativos) y sanitizada en el punto de entrada.
*   **Prevención de Inyecciones:** Es obligatorio usar consultas 100% parametrizadas (SQL, NoSQL, OS, etc.). Se prohíbe la concatenación de strings.
*   **Control de Acceso:** Todo endpoint debe requerir autenticación y autorización robusta. Cero credenciales hardcodeadas.
*   **Protección de Datos:** Cifrado obligatorio de datos sensibles tanto en tránsito (TLS) como en reposo.
*   **Protección en Logs y Errores:** Prohibido registrar PII o datos sensibles en logs. Los mensajes de error no deben revelar detalles internos como *stack traces* o rutas al cliente.
*   **Pipelines y Secretos:** Uso bloqueante de SAST y análisis de dependencias (SCA) en el pipeline de CI. Cero secretos (API keys, tokens) en código fuente, configuraciones o historial de Git.

### 2. Código Limpio / Clean Code (LIN-DEV-001)
**Objetivo:** Producir código legible, mantenible y autoexplicativo.
*   **Claridad:** El código debe transmitir su intención con nombres descriptivos (alineados al dominio de negocio). Se prohíben comentarios que traduzcan lo obvio o etiquetas "TODO" en ramas protegidas.
*   **Responsabilidad Única (SRP):** Las funciones deben hacer una sola cosa. Límites: ≤ 50 líneas (LOC), complejidad ciclomática ≤ 10, y máximo 5 parámetros.
*   **Eliminación de Deuda:** No debe existir código duplicado, código muerto ni "valores mágicos" no declarados como constantes.
*   **Tipado y Estructura:** Tipos explícitos obligatorios en APIs públicas (se prohíbe el uso de `any` o `dynamic`). Los archivos no deben exceder las 400 líneas y se prohíben las dependencias circulares.

### 3. Principios de Diseño (LIN-DEV-002)
**Objetivo:** Asegurar bajo acoplamiento, alta cohesión y testabilidad.
*   **Cumplimiento SOLID:** Respetar estrictamente los 5 principios. Las clases deben tener una sola responsabilidad, el código debe estar cerrado a modificaciones, y las dependencias deben estar invertidas mediante abstracciones.
*   **Capas Definidas:** La capa de dominio (negocio) no debe importar librerías de infraestructura.
*   **Testabilidad:** Las clases de negocio deben instanciarse sin infraestructura real. Toda dependencia externa debe ser inyectada.
*   **Resiliencia y Excepciones:** Las llamadas a servicios externos requieren *timeouts*, *retries* controlados (con backoff), *fallbacks* y *circuit breakers*. Se prohíben los bloques `catch` vacíos o silenciados.

### 4. Diseño de APIs (LIN-DEV-010)
**Objetivo:** Crear APIs interoperables, seguras y evolucionables.
*   **URIs Semánticas:** Usar siempre sustantivos en plural para los recursos y usar los métodos HTTP correctos (POST = crear, PUT/PATCH = modificar, GET = leer).
*   **Respuestas Estándar:** Uso de códigos HTTP exactos y respuestas de error en formato *Problem Details* (RFC 9457). El sobre (envelope) de la respuesta debe tener un campo `data`.
*   **Idempotencia:** Endpoints POST de creación obligan al uso del header `Idempotency-Key` (inter-servicios).
*   **Evolución:** Incluir la versión en la URI (ej. `/v1/`). Los *breaking changes* solo se permiten actualizando la versión mayor y deprecando la anterior.
*   **Controles de Datos:** Colecciones requieren paginación obligatoria (límite máximo 100). Filtrado, ordenamiento y búsquedas deben ir por *query parameters*.
*   **Protección:** Implementar siempre *Rate Limiting* y exponer cabeceras `X-RateLimit-*`.

### 5. Datos y Persistencia (LIN-DEV-012)
**Objetivo:** Hacer el acceso a datos consistente, auditable y resistente a errores de rendimiento.
*   **Esquema como Código:** Toda alteración a la Base de Datos se hace mediante *migraciones versionadas* en el repositorio. Éstas siempre deben ser compatibles hacia atrás (backward-compatible).
*   **Convenciones Universales:** Nombrado de objetos en `snake_case` y plural. Toda tabla de negocio debe tener campos de auditoría (`created_at`, `updated_at`) y estrategia de *soft delete* unificada (`deleted_at`).
*   **Rendimiento:** Las columnas usadas en filtros o cruces (`WHERE`, `JOIN`) requieren índices. Se prohíbe el antipatrón N+1 queries (no iterar llamadas en bucles).
*   **Transacciones y Pooling:** *Connection pooling* obligatorio. Las transacciones de base de datos no deben englobar llamadas de red externas a otros servicios.

### 6. Arquitectura Event-Driven y Mensajería (LIN-DEV-013)
**Objetivo:** Comunicación asíncrona trazable y resiliente ante fallos.
*   **Formato de Eventos:** Todo evento debe basarse en la especificación **CloudEvents** y los *schemas* deben estar versionados y documentados usando AsyncAPI.
*   **Idempotencia del Consumidor:** Todo suscriptor debe ser capaz de procesar un evento repetido produciendo el efecto una sola vez (detectando duplicados).
*   **Atomicidad (Outbox Pattern):** Prohibido publicar eventos directamente desde una transacción de la BD; se debe usar el *Outbox Pattern* para evitar "dual writes".
*   **Gestión de Fallos:** Configurar reintentos con *backoff* exponencial y forzar el uso de *Dead Letter Queues* (DLQ) para eventos que agotan sus intentos.
*   **Seguridad:** Absolutamente cero PII o datos sensibles explícitos en el payload; se debe referenciar el ID o cifrar la información.

### 7. Estrategia de Testing (LIN-DEV-005)
**Objetivo:** Automatización de pruebas bajo la "pirámide de testing" y prevención de regresiones.
*   **Cobertura:** La cobertura de código en lógica de negocio debe ser de **≥ 80%**, y este umbral funciona como un *quality gate* bloqueante en CI.
*   **Distribución:** Debe priorizarse pruebas unitarias (~70%), integraciones (~20%) y E2E (~10%).
*   **Determinismo:** Los tests no deben depender del orden de ejecución, base de datos de producción, fechas, o usar `sleep` para sincronización temporal (cero tests intermitentes o "flaky").
*   **Metodología:** Desarrollo dirigido por pruebas (TDD) es requerido para lógica crítica, y se exige pruebas de contrato (CDC) para APIs expuestas.

### 8. Observabilidad (LIN-DEV-007)
**Objetivo:** Todo servicio debe generar métricas, logs estructurados y trazas por defecto.
*   **Logging:** Los logs deben salir en formato estructurado (JSON) conteniendo obligatoriamente `timestamp` (ISO-8601), nivel y `correlationId`. Se prohíbe el volcado de PII, contraseñas o datos financieros completos en logs.
*   **Métricas Técnicas:** Exponer endpoints base (ej. `/metrics`) con patrón RED (Rate, Errors, Duration) y USE (Utilization, Saturation, Errors) sin usar *labels* de alta cardinalidad (como un ID de usuario individual).
*   **Trazabilidad Distribuida:** Requerida propagación del W3C Trace Context usando herramientas estándar como OpenTelemetry.
*   **Estado (Health):** Endpoints obligatorios de `liveness` y `readiness` para orquestadores (K8s).

### 9. Revisión de Pares / Code Review (LIN-DEV-004)
**Objetivo:** Asegurar calidad colaborativa y que ningún código entre a producción sin una validación explícita.
*   **Proceso Bloqueante:** TODO cambio requiere pasar por un Pull Request y tener al menos **1 aprobación** de un revisor (≥ 2 para módulos *core*) antes de ingresar a ramas principales.
*   **Calidad de la Revisión:** El PR debe poseer una buena descripción y estar avalado contra todo el checklist de normas CoE (diseño, seguridad, pruebas). Las correcciones requeridas (`blocking:`) evitan la aprobación hasta ser solucionadas.
*   **Eficiencia:** Los PRs no deben sobrepasar las 400 líneas modificadas, y los tiempos de primera respuesta por revisores deben ser ≤ 4 horas.

### 10. Documentación Técnica (LIN-DEV-009)
**Objetivo:** Evitar silos de conocimiento atando la documentación directamente al código.
*   **README y Onboarding:** Todo proyecto debe contar con un `README.md` exhaustivo y un proceso que permita a un desarrollador nuevo ejecutar el sistema en ≤ 1 día.
*   **Mantenimiento "In-Pull":** Toda documentación afectada por un código debe modificarse **en el mismo PR** (API, Diagramas, Runbooks).
*   **Formatos Claros:** Decisiones de diseño en registros de arquitectura (ADRs); diagramas con el *C4 Model*; manuales y *Runbooks* en repositorios productivos para respuesta a incidentes.
*   **Validación:** Documentación estructurada (ej. OpenAPI/AsyncAPI) debe ser comprobada automáticamente en el Pipeline de CI (linter de contratos).

### 11. Versionamiento y Entrega Continua (LIN-DEV-008)
**Objetivo:** Mantener un historial de Git predecible como fuente de la verdad para empaquetamiento y despliegue.
*   **Convenciones Rigurosas:** Uso imperativo de *Conventional Commits* (`feat:`, `fix:`, `chore:`, etc.) que en conjunto alimentan de forma automática la regla de Versionamiento Semántico (*SemVer*) y la creación de notas (*Changelogs*).
*   **CI como Guardián:** Implementación de *Quality Gates* bloqueantes. Falla el merge si la cobertura no alcanza o si las herramientas de escaneo (SAST/SCA) arrojan vulnerabilidades altas/críticas.
*   **Seguridad de Operaciones:** Absolutamente cero secretos en pipelines (usar Vaults o mecanismos nativos). Ramas protegidas; prohibido empujar directamente al `main` o borrar el historial.
*   **Reproducibilidad:** Fijar dependencias explícitas (*lock files*) y etiquetas de imágenes en Docker.

---
*Este documento resume los pilares técnicos del CoE DevArq. Toda desviación a reglas marcadas como `Critical` amerita resolución inmediata o excepciones justificadas formalmente con mitigación de riesgos y fecha de caducidad aprobada.*