# Registro de Decisiones de Arquitectura (ADR) — VotoSeguro v2

## ADR 001: Cambio de Backend a FastAPI y Monorepo
- **Fecha:** 2026-11-11
- **Estado:** Aceptado
- **Contexto:** La versión previa contemplaba NestJS y un microservicio independiente de Python para IA. Esto generaba duplicación de DTOs, mayor latencia y complejidad operativa.
- **Decisión:** Se consolida el backend en **FastAPI (Python 3.12)** con SQLAlchemy 2.0 Async, Pydantic v2 y Alembic. La IA local se maneja como módulo interno comunicándose por red privada con un contenedor de inferencia LFM3-1.7B.

## ADR 002: Inmutabilidad Criptográfica en PostgreSQL sin Blockchain
- **Fecha:** 2026-11-11
- **Estado:** Aceptado
- **Contexto:** Se evaluó el uso de redes blockchain (Hyperledger Fabric o Ethereum), pero acarrean sobrecarga de infraestructura, transacciones lentas y costos.
- **Decisión:** La inmutabilidad y verificabilidad se implementan mediante:
  1. Restricciones a nivel de base de datos (`UNIQUE`, checks de cronograma).
  2. Nullifiers calculados con `HMAC-SHA256(NULLIFIER_SECRET, voter_id:constituency_id)`.
  3. Desvinculación de identidad: la tabla `vote` carece por diseño de `voter_id` (Invariante #9).
  4. Triggers en PostgreSQL que hacen la tabla `audit_log` estrictamente *append-only*.
  5. Cadenas de hashes y árboles de Merkle en PostgreSQL.

## ADR 003: Autoridad del Tiempo Electoral (DatabaseTimeProvider)
- **Fecha:** 2026-11-11
- **Estado:** Aceptado
- **Contexto:** La hora de las máquinas cliente o los servidores de aplicación en clústeres desincronizados puede dar lugar a condiciones de carrera o fraude en ventanas de votación.
- **Decisión:** La hora oficial siempre se consulta de PostgreSQL mediante `SELECT now()` encapsulado en `DatabaseTimeProvider`. Para la suite de pruebas automatizadas se provee un `FakeTimeProvider` inyectable (`FrozenClock`) para manipular el avance del tiempo de forma determinista.

## ADR 004: Máquina de Estados del Cronograma y Reglas de Edición Auditadas
- **Fecha:** 2026-11-11
- **Estado:** Aceptado
- **Contexto:** Los procesos electorales requieren ajustes imprevistos (ej. ampliación de plazo por fallas de conectividad), pero cambios arbitrarios destruyen la confianza cívica.
- **Decisión:** El cronograma es editable bajo reglas matemáticas estrictas:
  - Orden estricto: `reg_open < reg_close <= vote_open < vote_close`.
  - Fases pasadas o en curso no pueden alterar su inicio.
  - El fin de una fase en curso solo puede ampliarse o acortarse fijándolo al menos a 5 minutos en el futuro respecto a la hora del servidor.
  - Todo cambio fuera de borrador exige motivo (`reason >= 10 chars`) y genera un registro inmutable en `schedule_change`.

## ADR 005: Scheduler Autónomo con Bloqueo Transaccional
- **Fecha:** 2026-11-11
- **Estado:** Aceptado
- **Contexto:** Las transiciones de fase deben ocurrir exactamente al cumplirse los plazos sin intervención manual. Si la API corre en múltiples réplicas (o concurrencia con worker), múltiples procesos no deben colisionar.
- **Decisión:** Se utiliza `APScheduler` ejecutando `run_scheduler_tick` cada 10 segundos, protegido con `SELECT pg_try_advisory_xact_lock(849201)`. Las consultas emplean `SELECT ... FOR UPDATE SKIP LOCKED`.

## ADR 006: Materialized Paths para Jerarquías Electorales y Alcance de Delegados
- **Fecha:** 2026-11-11
- **Estado:** Aceptado
- **Contexto:** Las organizaciones (ej. universidades, cooperativas, colegios profesionales) tienen estructuras de niveles arbitrarios (Universidad -> Facultad -> Carrera -> Mención) que cambian por institución.
- **Decisión:** Se implementa un modelo de jerarquía dinámica en `structure.py`:
  1. `VoterGroup` define los estamentos electorales (ej. Docentes, Estudiantes).
  2. `HierarchyLevel` define los peldaños escalonados ordenados por `depth` incremental (1, 2, 3...).
  3. `UnitNode` implementa una ruta materializada canónica (`path` indexada) con formato `/{PARENT_PATH}{CODE}/`.
  4. Permite validación de alcance de circunscripciones y delegaciones `ADMIN_SEGMENT` con consultas directas `LIKE :path%`, eliminando la sobrecarga de consultas recursivas (CTE) en tiempo real.

## ADR 007: Congelamiento Estructural y Hash Determinista RFC 8785 (config_hash)
- **Fecha:** 2026-11-11
- **Estado:** Aceptado
- **Contexto:** Tras la convocatoria oficial y registro de candidatos, alterar los cargos, circunscripciones o candidatos constituiría manipulación electoral.
- **Decisión:** 
  1. Al invocar `POST /elections/{id}/publish`, se valida una suite de 6 reglas de consistencia de integridad.
  2. La estructura completa (elección, grupos, niveles, nodos, cargos, circunscripciones y candidatos) se normaliza y serializa en formato canónico determinista **RFC 8785** (orden léxico de claves, normalización de cadenas Unicode y números).
  3. Se genera el `config_hash` mediante `SHA-256(canonical_json)`.
  4. La guardia `require_election_draft` bloquea cualquier mutación posterior en grupos, niveles, nodos, cargos o candidatos devolviendo `409 Conflict`.

## ADR 008: Detección Híbrida de Duplicados en Padrón (IA-L2a) con Arbitraje Soberano
- **Fecha:** 2026-11-11
- **Estado:** Aceptado
- **Contexto:** Durante la importación de padrones masivos (ej. decenas de miles de estudiantes o socios) ocurren errores tipográficos en nombres o intentos de doble empadronamiento con documentos alterados.
- **Decisión:**
  1. Se implementa un detector en `app/modules/voters/duplicate_detector.py` que combina similitud trigram (`similarity >= 0.40`) y distancia Levenshtein (`levenshtein <= 3`).
  2. En PostgreSQL se aprovechan las extensiones nativas `pg_trgm` y `fuzzystrmatch`.
  3. Se implementa un fallback puro en memoria para SQLite (utilizado en la suite de pruebas unitarias/CI).
  4. Principio de Soberanía Cívica: Ningún votante es descartado automáticamente por el algoritmo. Se genera una alerta de advertencia en `import_issue` y se pone a disposición del tribunal en la bandeja de dictamen humano (`CONFIRM_DISTINCT`, `BLOCK_NEW`, `REMOVE_NEW`).

## ADR 009: Activación Pública por Enlace y Congelamiento Determinista de Padrón (roll_hash)
- **Fecha:** 2026-11-11
- **Estado:** Aceptado
- **Contexto:** En el modelo de auto-registro ciudadano o invitación institucional, los votantes deben poder activar su registro sin requerir cuentas de usuario ni contraseñas permanentes. Al cerrarse el registro, el padrón debe ser congelado sin posibilidad de añadir o retirar votantes.
- **Decisión:**
  1. Los enlaces de registro (`RegistrationLink`) se emiten con tokens URL-safe de alta entropía y se guardan con su hash SHA-256 (`token_hash`).
  2. En `/register/:token`, el ciudadano verifica su CI y pertenencia al grupo/nodo del enlace para transicionar de `IMPORTED`/`INVITED` a `ACTIVE`.
  3. Al expirar el plazo de registro (`REGISTRATION_CLOSED`), se ejecuta `freeze_roll_hash`: se ordenan todos los votantes `ACTIVE` por `document_id`, se serializan bajo RFC 8785 y se calcula `roll_hash = SHA-256(canonical_voters)`.
  4. A partir de este instante, cualquier intento de mutación del padrón electoral es rechazado con `409 Conflict`.

## ADR 010: Papeleta Automática, Voto Ciego con Nullifiers y Desvinculación Total
- **Fecha:** 2026-11-11
- **Estado:** Aceptado
- **Contexto:** Para garantizar el secreto inviolable del sufragio e impedir la coacción o compra de votos, no debe existir ningún enlace en la base de datos entre la identidad del votante y su papeleta depositada.
- **Decisión:**
  1. Al abrirse la votación (`VOTING_OPEN`), se emiten credenciales personales de votación de un solo uso (`VS-XXXX-XXXX-XXXX`), almacenadas con `token_hash = sha256(code)`.
  2. El votante inicia sesión mediante su CI y credencial, obteniendo un JWT efímero con alcance `VOTER_SESSION`.
  3. La papeleta se resuelve dinámicamente mediante el **Algoritmo 3.2**: seleccionando únicamente los cargos de su `group_id` cuya circunscripción territorial coincida con un prefijo de su `node.path`.
  4. La emisión atómica (**Algoritmo 3.3**) inserta votos en la tabla `vote`, la cual por diseño estricto (**Invariante #9**) carece de la columna `voter_id` o cualquier clave foránea hacia el elector.
  5. Para prevenir el doble voto sin correlacionar la identidad, se utiliza un `nullifier = HMAC-SHA256(SECRET, voter_id:constituency_id)` único por circunscripción (**Invariante #8**).
  6. Se registra la concurrencia en `voter_participation` de forma desacoplada y se trunca la marca temporal al minuto (**Invariante #17**) para mitigar ataques de análisis de tráfico.
  7. El votante recibe un recibo criptográfico auditable (`receipt_hash`).

## ADR 011: Escrutinio con k-Anonimato y Resultados Sellados (Invariantes #11 y #12)
- **Fecha:** 2026-11-11
- **Estado:** Aceptado
- **Contexto:** Durante la jornada electoral, la visualización de resultados parciales distorsiona la competencia democrática. Asimismo, en desgloses muy pequeños (ej. carreras con 2 o 3 estudiantes), revelar el conteo individual rompe el secreto del voto si todos votaron por la misma opción o si se cruzan datos externos.
- **Decisión:**
  1. **Invariante #11:** Cualquier consulta a `GET /elections/{id}/results` antes de que la elección se encuentre formalmente en `VOTING_CLOSED` o `TALLIED` es rechazada inmediatamente con código HTTP **403 Forbidden**.
  2. Tras la clausura de urnas, se realiza el cómputo oficial verificando matemáticamente que `candidates_total + blank_count + null_count == total_cast` en cada circunscripción.
  3. **Invariante #12 ($k$-anonimato):** En cualquier celda de desglose jerárquico o por filtro donde el total de votos sea estrictamente menor al umbral de la elección ($k$, configurado por defecto en 5), el conteo detallado por candidato se suprime (`redacted_by_k_anonymity = True`, `candidates = None`) mostrando un aviso de resguardo de privacidad.

## ADR 012: Sembrado Demostrativo Autónomo e Idempotente (seed:demo)
- **Fecha:** 2026-11-11
- **Estado:** Aceptado
- **Contexto:** Para la evaluación académica y despliegues de prueba en Render y Cloudflare Pages (donde no se dispone de servidores SMTP externos configurados), es indispensable contar con datos realistas, homónimos para probar IA-L2a, enlaces de activación y credenciales operativas listas para usar.
- **Decisión:**
  1. Se implementa `seed_demo.py`, ejecutable por CLI (`python -m app.db.seed_demo`) o mediante el endpoint protegido de `PLATFORM_ADMIN` (`POST /api/v1/platform/seed-demo`).
  2. Crea de forma completamente idempotente la **Universidad EL GRAN ESTUDIO** (con 36 votantes, par de homónimos `José Rodríguez` vs `Jose Rodriguez S.`, 4 cargos, enlaces de registro y credenciales) y las **Elecciones Nacionales Ecuador** (4 niveles territoriales y binomio presidencial).
  3. Habilita el inspector de credenciales (`DEMO_CREDENTIAL_INSPECTOR_ENABLED=True`) para permitir la prueba fluida de la cabina de votación sin requerir el envío forzoso de correos externos.


## ADR 013: Cadenas de Hashes en Votos y Bitácora de Auditoría (Invariantes #19 y #20)
- **Fecha:** 2026-11-11
- **Estado:** Aceptado
- **Contexto:** La base de datos relacional debe proporcionar garantías matemáticas de no repudio y detección de manipulación física en SQL.
- **Decisión:**
  1. Cada registro en `vote` incorpora `chain_index`, `prev_hash` y `vote_hash = SHA-256(chain_index || prev_hash || nullifier || choice_type || candidate_id || minute_timestamp)`.
  2. La cadena inicia con un bloque génesis único por elección ligado a su `config_hash`.
  3. Durante la emisión del voto, se ejecuta un bloqueo atómico `FOR UPDATE` sobre `election` para serializar la cadena.
  4. La bitácora `audit_log` implementa idéntico encadenamiento con triggers `trg_audit_log_immutable`.
  5. Los endpoints `/integrity/votes` y `/integrity/audit` permiten auditar de punta a punta la integridad criptográfica.

## ADR 014: Árbol de Merkle para Pruebas Criptográficas de Inclusión en el Padrón (Invariante #18)
- **Fecha:** 2026-11-11
- **Estado:** Aceptado
- **Contexto:** Los votantes requieren comprobar que su registro forma parte del censo electoral oficial sin que el tribunal tenga que publicar la lista completa con los datos de todos los empadronados.
- **Decisión:**
  1. Al pasar a `REGISTRATION_CLOSED`, se ordenan canónicamente los votantes activos y se construye un Árbol de Merkle binario balanceado en `app/crypto/merkle.py`.
  2. La raíz `merkle_root` se estampa en la entidad `election`.
  3. El endpoint `GET /elections/{id}/merkle/proof/{ci}` calcula el camino de hashes hermanos de orden $O(\log_2 N)$.
  4. El endpoint público `POST /elections/{id}/merkle/verify` permite a cualquier ciudadano reconstruir matemáticamente la raíz demostrando su inclusión en el padrón fidedigno.

## ADR 015: Arquitectura de Inferencia Local LFM3-1.7B con Fallback Determinista y Zero-PII (Invariante #14)
- **Fecha:** 2026-11-11
- **Estado:** Aceptado
- **Contexto:** Los modelos de IA no deben depender de proveedores externos privativos en elecciones soberanas ni filtrar datos de votantes, y el sistema no debe fallar con HTTP 500 si el motor LLM sufre sobrecarga o no está desplegado en entornos livianos (como Render Free).
- **Decisión:**
  1. Se configura un microservicio Docker con `LiquidAI/LFM3-1.7B` cuantizado en GGUF Q4_K_M con `llama-server`.
  2. El cliente `LocalLlmEngine` utiliza HTTP asíncrono con timeout de 8.0 segundos, temperatura de 0.05 y validación JSON con esquemas estrictos de Pydantic v2.
  3. Salvaguarda de Modo Degradado: Si el LLM está apagado o responde fuera de tiempo, se dispara un fallback determinista puro devolviendo un resultado analítico válido con el metadato `source: DETERMINISTIC_FALLBACK`.
  4. Salvaguarda de Privacidad: Se invoca `log_ai_call()` registrando en `ai_call_log` y en la cadena de auditoría la llamada libre de identificadores personales (CIs, nombres, votos).

## ADR 016: Extracción OCR de Cédula sin Persistencia de Imágenes (Invariante #15)
- **Fecha:** 2026-11-11
- **Estado:** Aceptado
- **Contexto:** Almacenar fotografías de documentos de identidad en el servidor viola normativas de protección de datos personales y expone al sistema a riesgos de filtración masiva de biometría.
- **Decisión:**
  1. El escaneo OCR de la cédula se procesa localmente en el navegador o en la aplicación móvil.
  2. Se extrae el texto bruto y se transmite al endpoint `POST /api/v1/ai/id-card/extract`.
  3. El backend limpia cualquier encabezado data-URI en memoria y extrae `{ci, nombres, apellidos, fecha_nacimiento}` con regex y validación de seguridad.
  4. En ningún momento se escribe la imagen en disco, base de datos ni almacenamiento en la nube.

## ADR 017: Accesibilidad por Voz Determinista 100% On-Device (Sección 7.3)
- **Fecha:** 2026-11-11
- **Estado:** Aceptado
- **Contexto:** Los votantes con discapacidad visual o dificultades motoras requieren votar de manera autónoma sin que sus instrucciones hablen por la red revelando el sentido de su sufragio.
- **Decisión:**
  1. La síntesis de voz (TTS) y el reconocimiento de comandos (STT) se interpretan en el dispositivo cliente mediante una gramática determinista pura (`voice-ballot-grammar.ts`).
  2. No se envía ningún paquete de audio, transcripción o comando intermedio a través de la red hacia el backend ni hacia ningún servicio de IA generativa.
  3. El voto se envía únicamente en el instante final al confirmar la emisión mediante la misma API ciega atómica `POST /ballot/cast`.

## ADR 018: RAG Oficial Neutral para Asistente Electoral con Desmontaje en Cabina (IA-L5)
- **Fecha:** 2026-11-11
- **Estado:** Aceptado
- **Contexto:** Un chatbot electoral puede inducir sesgos o alucinar reglas que confundan al votante, o distraerlo durante el momento del sufragio.
- **Decisión:**
  1. El asistente `POST /api/v1/ai/assistant/ask` se ancla a una base de conocimiento curada de 12 documentos oficiales (`DOC-01` a `DOC-12`).
  2. Se aplica un filtro estricto de neutralidad política que rechaza preguntas de preferencia partidaria o candidaturas.
  3. Si la base no cubre la consulta, responde con honestidad "No dispongo de esa información" y deriva a soporte humano.
  4. En la cabina de votación Web y Móvil, el widget del asistente se desmonta obligatoriamente durante el paso de selección de candidatos.

## ADR 019: Aplicación Móvil en React Native + Expo con Deep Linking Universal (S2-01)
- **Fecha:** 2026-11-11
- **Estado:** Aceptado
- **Contexto:** Los votantes requieren una experiencia móvil nativa en smartphones para activarse mediante enlaces en mensajes, escanear su cédula y votar de manera accesible.
- **Decisión:**
  1. Se implementa `apps/mobile` con React Native 0.74, Expo 51 y TypeScript consumiendo el paquete central `@votoseguro/api-client`.
  2. Soporta el esquema de Deep Link `votoseguro://register/:token` y `votoseguro://receipt/:hash`.
  3. Comparte exactamente los mismos contratos, lógica de negocio y endpoints `/api/v1` que el cliente web, garantizando paridad total de características y soberanía criptográfica.
