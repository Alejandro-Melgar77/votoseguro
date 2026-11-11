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
