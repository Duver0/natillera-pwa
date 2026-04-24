
# Guía de Lineamientos y Mejores Prácticas: Ingeniería de Calidad

Este documento extrae y consolida las prácticas y directrices más importantes definidas por el Centro de Excelencia de QA de Sofka, enfocadas en consolidar la **Calidad Aumentada** bajo una visión *AI-First*.

## 1. Lineamientos de Gestión y Colaboración (Ecosistema de Trabajo)
Establecen los fundamentos para eliminar silos y operar con claridad mediante flujos ágiles asistidos.
*   **Estructura y escalamiento:** Es fundamental conocer la estructura del equipo (líder directo, gestor, test manager, líder técnico) para asegurar continuidad operativa y decisiones ágiles.
*   **Onboarding:** Se requiere un proceso de integración bien definido para conocer el contexto técnico/funcional y las herramientas de la cuenta.
*   **Acuerdos Ágiles (DoR & DoD):** El Ingeniero de Calidad debe cuidar y acompañar el cumplimiento de los criterios de *Definition of Ready* y *Definition of Done* junto con el equipo.
*   **Comunicación e Información:** Se debe mantener un ciclo de retroalimentación regular con el cliente, sincronización de cronogramas con Desarrollo y utilizar un repositorio central para la trazabilidad de la información.
*   **Mejora Continua:** Fomentar prácticas de *Agile Testing*, el aprendizaje a partir de incidentes en producción, el cuidado de la salud del código (cobertura, duplicidad, seguridad) y mantener un plan de evolución y madurez.

## 2. Lineamientos de Estrategia y Planificación (Enfoque Predictivo)
La planificación deja de ser un documento formal para ser una referencia viva basada en el riesgo (*Risk-Based Testing*).
*   **Auditoría Temprana (Shift-Left):** Revisar requerimientos o Historias de Usuario con IA desde el inicio para detectar ambigüedades, asegurando la *Testabilidad* bajo criterios INVEST.
*   **Entendimiento de Dependencias:** Usar IA para descubrir dependencias técnicas y de integración ocultas en la documentación.
*   **Estrategia Inteligente y Riesgos:** Orientar los niveles y tipos de prueba (priorizando APIs/Servicios) apoyándose en la IA y en matrices de riesgo vivas para enfocar el esfuerzo en áreas de alto impacto.
*   **Estimación y Regresión:** La IA funciona como un *par consultor* para contrastar las estimaciones de esfuerzo y para optimizar el set de pruebas de regresión, eliminando redundancias.
*   **Plan de Pruebas Centralizado:** Generar un plan claro con apoyo de IA y socializarlo en el repositorio central.

## 3. Lineamientos de Diseño y Cobertura (Génesis de Escenarios)
Transforma la creación manual de casos utilizando IA generativa para ampliar la cobertura y la calidad.
*   **Escenarios Gherkin:** Utilizar IA generativa para redactar casos (*Given-When-Then*), incluyendo flujos principales, alternos y de borde, los cuales luego son validados por el ingeniero.
*   **Técnicas y Contratos:** Aplicar técnicas de diseño (caja negra/blanca) sabiendo que el objetivo no es la exhaustividad, sino maximizar la cobertura de riesgos. Analizar contratos de API tempranamente para detectar inconsistencias en las capas de integración.
*   **Datos y Trazabilidad:** Generar datos de prueba sintéticos apoyados por IA cuidando la privacidad e integridad. Asegurar la trazabilidad verificando con IA que los escenarios cubran las historias de usuario y priorizar la ejecución según el impacto.

## 4. Lineamientos de Ejecución (Manual y Exploratoria Aumentada)
Las personas se concentran en analizar comportamientos complejos y la IA apoya en diagnósticos y evidencias operativas.
*   **Documentación de Ciclos:** Vincular evidencia, hallazgos y el ciclo de ejecución a cada caso de prueba.
*   **Pruebas Exploratorias:** Deben estar guiadas por mapas de riesgo generados con IA para enfocar áreas sensibles o con deuda técnica.
*   **Gestión de Defectos:** Reportar errores con contexto claro; la IA puede estructurar el borrador del reporte y proponer un análisis de causa raíz. Es obligatorio tener un flujo de estados del defecto acordado, compartido y realizar pruebas de confirmación (re-test) con evidencia.
*   **Apoyo Experto:** Se puede usar visión artificial para resaltar anomalías visuales automáticamente. El Ingeniero de QA es quien realiza la validación experta final de los resultados y facilita la etapa de aceptación (UAT).

## 5. Lineamientos de Ingeniería de Automatización
La automatización es una solución de ingeniería robusta y mantenible donde la IA es un par de programación.
*   **Arquitectura y Código:** Usar arquetipos claros por niveles y estrategias de ramas como *GitFlow* o *Trunk-Based Development*. La IA actúa como copiloto para acelerar la implementación (co-programación).
*   **Mantenimiento y Resiliencia:** Promover la calidad temprana del código estático, las revisiones entre pares (y con IA) y el uso de *self-healing* para que los frameworks se adapten a cambios en la aplicación.
*   **Continuous Testing:** Integrar las pruebas selectivas (basadas en impacto) en pipelines de CI/CD, con un pipeline dedicado específicamente a la estabilidad (regresivas).
*   **DoR de Automatización:** Requisitos mínimos para automatizar: éxito manual previo sin bugs críticos, caso de prueba detallado, datos identificados, viabilidad técnica comprobada, ambiente estable y aprobación del equipo.
*   **DoD de Automatización:** Un script finaliza cuando el código es revisado (por pares/IA), usa datos desacoplados, se integra al pipeline, cuenta con documentación, mantiene trazabilidad y se entrega al equipo.

## 6. Lineamientos de Observabilidad y Control
Busca tener visibilidad del estado real del *release* combinando pruebas manuales y automatizadas.
*   **Métricas y Reportes:** Analizar los datos con IA para entender la cobertura, el comportamiento de defectos y construir reportes enfocados en tendencias y toma de decisiones para el negocio, no solo en "estatus" numérico.
*   **Riesgos Evolutivos:** Ajustar constantemente la matriz de riesgos basada en los hallazgos reales de la ejecución.

## 7. Lineamientos de Performance (Eficiencia Anticipada)
Disciplina continua para predecir el comportamiento del sistema bajo estrés real.
*   **Gobernanza:** Conversar sobre rendimiento desde el refinamiento (*Sprint Planning*). Implementar un **DoR de Performance estricto** (objetivos claros y umbrales como P95 o TPS) y mantener trazabilidad con la Historia de Usuario.
*   **Scripts Inteligentes:** Usar arquetipos estandarizados, priorizar la modularidad de fragmentos de código y usar IA para correlaciones dinámicas o *linting*.
*   **Datos y Ambiente:** Utilizar "datos de un solo uso", gestionar secretos en bóvedas (sin texto plano) y documentar siempre la brecha de capacidad entre el ambiente de pruebas y producción.
*   **Ejecución y Observabilidad:** Correlacionar reportes con métricas de infraestructura (CPU, RAM). Las pruebas de línea base deben ser requisito en el pipeline, ejecutarse inteligentemente según el impacto, y las de resistencia deben durar mínimo 120 minutos. Emplear IA para el diagnóstico automático frente a históricos.

## 8. Lineamientos de Uso de Herramientas de IA
Ecosistema de Sofka diseñado para cuidar la información y trabajar eficientemente.
*   **Consentimiento:** Es obligatorio contar con el consentimiento explícito del cliente antes de usar IA, alineado con acuerdos de privacidad.
*   **Portal SKAI:** Interfaz principal, segura y controlada para acceder a LLMs y configurar instrucciones personalizadas del proyecto.
*   **Gemini:** Para razonamiento complejo, análisis de código, reportes narrativos y documentos extensos, dentro del entorno seguro de Sofka.
*   **NotebookLM:** Para conectar la base de conocimiento del proyecto (requerimientos, manuales) en un solo contexto, resolviendo dudas y hallando inconsistencias.
*   **GitHub Copilot y Healenium:** Copilot para asistir en la escritura de código de automatización; Healenium para incorporar capacidades de autocurado (*self-healing*) en interfaces de usuario.
