# VotoSeguro v2 — Resumen Ejecutivo de Implementación (Sprint 1 - Iteraciones 1 y 2)

**Plataforma SaaS Multi-Institución de Votación Electrónica Auditada**  
**Asignatura:** Ingeniería de Software I (INF 422 SB) — UAGRM  
**Fecha de corte:** 11 de Noviembre de 2026  
**Estado:** Iteración 1 e Iteración 2 (Fase 2) del Sprint 1 (v1.0) completamente desarrolladas, testeadas y versionadas en GitHub.

---

## 1. Visión General del Proyecto

**VotoSeguro v2** es una solución de voto electrónico auditada orientada a instituciones educativas, colegios de profesionales, sindicatos y asociaciones intermedias de Bolivia y Latinoamérica. 
Su diseño arquitectónico garantiza la integridad inquebrantable del proceso mediante:
- **Aislamiento Multi-Tenancy estricto** por organización (`organization_id`).
- **Anonimato absoluto del votante (Invariante #9):** Desvinculación criptográfica total entre la identidad del sufragante y la papeleta depositada (`vote` nunca almacena `voter_id`).
- **Congelamiento Estructural Post-Publicación (Invariante #3):** Una vez publicada la elección (`DRAFT -> SCHEDULED`) y emitido el `config_hash`, cualquier intento de mutación estructural sobre grupos, niveles, nodos, filtros, cargos o candidatos es rechazado con `HTTP 409 Conflict`.
- **Inmutabilidad Temporal del Padrón (Invariante #5):** El padrón electoral únicamente admite altas, bajas, bloqueos o importaciones durante la fase `REGISTRATION_OPEN`.
- **Autoridad temporal canónica (Invariante #6):** Todas las decisiones y transiciones de estado del ciclo electoral dependen exclusivamente del reloj de base de datos (`SELECT now() AT TIME ZONE 'UTC'`).
- **Auditoría inmutable (Append-Only):** Bitácora transaccional blindada a nivel de PostgreSQL contra cualquier intento de modificación o eliminación (`prevent_audit_log_mutation()`).

---

## 2. Historias de Usuario Implementadas (Sprint 1 — Iteraciones 1 y 2)

### Iteración 1 (Infraestructura, Tenancy y Cronograma)
| Historia | Prioridad | Denominación | Estado | Descripción Funcional y Técnica |
| :--- | :---: | :--- | :---: | :--- |
| **S1-00** | **Must** | Configuración de Monorepo, Docker, DB y CI | **100%** | Estructura de monorepo con `pnpm` workspaces y Python venv/uv. Orquestación de contenedores con `docker-compose.yml` (5 servicios: postgres, api, scheduler, web, mailpit), configuración para despliegue en Render (`render.yaml`), soporte SPA para Cloudflare Pages (`public/_redirects`), primitivas criptográficas (`VoteCodec`, `Nullifier`) y **el 100% de los modelos ORM de las 20 tablas** con su migración inicial Alembic (`0001_initial_sprint1_schema.py`). |
| **S1-01** | **Must** | Autenticación JWT, Multi-Tenancy y Organizaciones | **100%** | Creación y administración de instituciones (tenants) por `PLATFORM_ADMIN`. Autenticación con JWT (HMAC-SHA256) y hash de contraseñas con Argon2 (con fallback automático a bcrypt). Bloqueo de seguridad por fuerza bruta tras 5 intentos fallidos durante 15 minutos (retornando cabecera HTTP `Retry-After`). Bitácora inmutable de auditoría (`audit_log`) con trigger PostgreSQL. |
| **S1-02** | **Must** | Elección, Cronograma Editable y Scheduler Autónomo | **100%** | CRUD integral de Elecciones y motor de cronograma con soporte de zonas horarias IANA (`America/La_Paz`). Matriz de reglas de edición estricta con registro de motivo humano obligatorio (`schedule_change`). Acción de override `"Abrir registro ahora"`. **Scheduler autónomo idempotente** (`APScheduler` cada 10s) con lock distribuido transaccional (`pg_try_advisory_xact_lock(849201)`) y reloj de BD. |
| **S1-11** | **Should** | Delegación de Administradores de Solo Lectura (`ADMIN_SEGMENT`) | **100%** | Creación y gestión de usuarios administradores con alcance restringido a un grupo institucional (`group_id`) o a un nodo del árbol jerárquico (`node_id`). |
| **S1-12** | **Should** | Solicitud Pública de Elección por Instituciones | **100%** | Formulario público institucional en Landing Page para solicitar la provisión de una elección. Flujo de radicación y consola de revisión, aprobación y rechazo exclusivo para el `PLATFORM_ADMIN`. |

### Iteración 2 / Fase 2 (Estructura Electoral, Papeleta, Publicación y Padrón)
| Historia | Prioridad | Denominación | Estado | Descripción Funcional y Técnica |
| :--- | :---: | :--- | :---: | :--- |
| **S1-03** | **Must** | Grupos, Jerarquías Dinámicas y Árbol de Nodos | **100%** | Gestión de `VoterGroup`, peldaños de profundidad `HierarchyLevel` (`depth >= 1`) y árbol organizacional `UnitNode` con ruta materializada (`path`, ej. `/UAGRM/FICCT/INF/`). Importador masivo CSV de nodos con ordenamiento topológico padre-hijo. |
| **S1-04** | **Must** | Filtros Extra, Cargos y Autogeneración de Circunscripciones | **100%** | Filtros dinámicos JSONB (`FilterDefinition`), definición de cargos (`Contest`) con nivel de alcance (`scope_level_id`), desgloses (`ContestBreakdown` por `LEVEL` o `FILTER`) y **sincronización/autogeneración automática de circunscripciones** (`Constituency`) al crear o modificar nodos y cargos. |
| **S1-05** | **Must** | Candidatos por Circunscripción y Estudio de Papeleta | **100%** | CRUD completo de candidatos (`Candidate`) por circunscripción, reordenamiento atómico de papeleta (`ballot_order`), validación binaria de fotografías (Magic Bytes JPEG/PNG) y previsualización en vivo de papeleta oficial con opciones de **Blanco** y **Nulo**. |
| **S1-06** | **Must** | Ceremonia de Publicación y `config_hash` SHA-256 | **100%** | Transición oficial `DRAFT -> SCHEDULED` mediante `POST /elections/{id}/publish`, validador de integridad de **6 reglas obligatorias**, serialización canónica determinista **RFC 8785**, emisión de `config_hash` SHA-256 y congelamiento estructural irreversible (`HTTP 409 Conflict`). |
| **S1-07** | **Must** | Panel de Registro y Carga de Padrón Electoral | **100%** | Gestión de votantes restringida estrictamente a `REGISTRATION_OPEN`. Alta individual e importador masivo CSV resiliente fila por fila (`ImportBatch` / `ImportIssue`) con validación de profundidad de nodo y unicidad de CI. Bloqueo/desbloqueo/retiro de votantes y resumen estadístico respetando el alcance de `ADMIN_SEGMENT`. |
| **IA-L2a** | **Should** | Detección de Duplicados y Arbitraje Humano | **100%** | Detección automática de posibles duplicados y homonimias usando `pg_trgm` (`similarity >= 0.40`) y `fuzzystrmatch` (`levenshtein <= 3`), con fallback en memoria para SQLite. Bandeja de arbitraje humano con comparativa lado a lado (`CONFIRM_DISTINCT`, `BLOCK_NEW`, `REMOVE_NEW`). |

---

## 3. Estructura de Archivos del Proyecto

```text
votoseguro/
├── README.md                               # Documentación principal del repositorio en GitHub
├── resumen.md                              # Resumen ejecutivo de implementación (Iteraciones 1 y 2)
├── docker-compose.yml                      # Orquestación de desarrollo local (Postgres, API, Worker, Web, Mailpit)
├── render.yaml                             # Definición de infraestructura como código (IaC) para Render
├── pnpm-workspace.yaml                     # Configuración de workspaces frontend/paquetes
├── package.json                            # Scripts raíz, dependencias y configuración pnpm
├── .env.example                            # Plantilla documentada de variables de entorno
├── .gitignore                              # Reglas de exclusión para Python, Node, temporales y credenciales
├── docs/
│   ├── DECISIONES.md                       # Decisiones de Arquitectura de Software (ADR 001 - 008)
│   └── PROGRESO.md                         # Cuadro de mando y seguimiento de historias del Sprint 1
├── packages/
│   └── api-client/                         # Paquete compartido de tipos TypeScript y contratos DTO
│       ├── package.json
│       └── src/
│           └── index.ts                    # Interfaces completas (Elecciones, Estructura, Candidatos, Padrón, IA-L2a)
├── apps/
│   ├── api/                                # Backend en FastAPI + SQLAlchemy 2.0 + Alembic
│   │   ├── pyproject.toml / requirements.txt
│   │   ├── Dockerfile
│   │   ├── alembic.ini
│   │   ├── alembic/
│   │   │   ├── env.py
│   │   │   └── versions/
│   │   │       ├── 0001_initial_sprint1_schema.py              # Migración DDL de las 20 tablas + extensiones + triggers
│   │   │       └── 0002_sprint1_iteration2_reconciliation.py   # Reconciliación de columnas para Iteración 2
│   │   ├── app/
│   │   │   ├── main.py                     # Entrypoint FastAPI, lifespan, CORS, routers y seed idempotente
│   │   │   ├── core/
│   │   │   │   ├── config.py               # Configuración con Pydantic Settings
│   │   │   │   ├── security.py             # Hasheo Argon2 / bcrypt, firma y verificación JWT
│   │   │   │   ├── time.py                 # Abstracción de reloj canónico (Database / Fake)
│   │   │   │   ├── exceptions.py           # Jerarquía de errores de dominio y mapeo HTTP
│   │   │   │   └── dependencies.py         # Extracción de contexto tenant y guardias RBAC
│   │   │   ├── db/
│   │   │   │   ├── base.py                 # DeclarativeBase y tipos comunes
│   │   │   │   ├── session.py              # Generador de sesiones async (asyncpg / aiosqlite)
│   │   │   │   └── models/                 # Modelos ORM de las 20 tablas
│   │   │   │       ├── organization.py     # organization, election_request
│   │   │   │       ├── user.py             # user, admin_assignment
│   │   │   │       ├── election.py         # election, schedule_change
│   │   │   │       ├── structure.py        # voter_group, hierarchy_level, unit_node, filter_definition, contest, contest_breakdown, constituency, candidate
│   │   │   │       ├── voter.py            # voter, import_batch, import_issue, registration_link
│   │   │   │       ├── voting.py           # vote, voter_participation, voting_credential
│   │   │   │       └── audit.py            # audit_log, ai_call_log
│   │   │   ├── crypto/
│   │   │   │   ├── nullifier.py            # Nullifiers ciegos por circunscripción: HMAC-SHA256(voter_id:constituency_id)
│   │   │   │   ├── vote_codec.py           # Codec de votos (Plano / Paillier homomórfico)
│   │   │   │   └── hashing.py              # SHA-256 canónico y encadenamiento de hashes
│   │   │   └── modules/
│   │   │       ├── auth/                   # Login, perfil, bloqueo fuerza bruta
│   │   │       ├── audit/                  # Consulta y registro de bitácora
│   │   │       ├── organizations/          # Gestión de tenants y solicitudes de elección
│   │   │       ├── admins/                 # Delegación de ADMIN_SEGMENT
│   │   │       ├── elections/              # CRUD de elección, validador de fechas y publication_service.py (S1-06)
│   │   │       ├── structure/              # S1-03 y S1-04: guards.py, schemas.py, service.py, router.py
│   │   │       ├── candidates/             # S1-05: schemas.py, service.py, router.py
│   │   │       ├── voters/                 # S1-07 e IA-L2a: duplicate_detector.py, schemas.py, service.py, router.py
│   │   │       └── scheduler/              # APScheduler worker con lock de PostgreSQL
│   │   └── tests/                          # Suite de pruebas automatizadas (10 tests en 7 archivos)
│   │       ├── conftest.py                 # Fixtures async y Mock TimeProvider
│   │       ├── test_tenancy_isolation.py   # Verificación de aislamiento multi-tenant
│   │       ├── test_auth_lockout.py        # Verificación de bloqueo tras 5 intentos
│   │       ├── test_schedule_rules.py      # Verificación de reglas de edición de cronograma
│   │       ├── test_scheduler_transitions.py # Transiciones temporales deterministas
│   │       ├── test_hierarchy_and_contests.py # Jerarquías, paths, importador CSV y circunscripciones
│   │       ├── test_publication_and_immutability.py # Validación de 6 reglas, RFC 8785 config_hash y 409 Conflict
│   │       └── test_voter_roll_and_duplicates.py # Guardia de fase, profundidad de nodo e IA-L2a
│   └── web/                                # Frontend en React 18 + Vite + TypeScript + Tailwind
│       ├── package.json / vite.config.ts / tailwind.config.js / tsconfig.json
│       ├── public/
│       │   ├── _redirects                  # Configuración de rewrite para Cloudflare Pages
│       │   └── shield-check.svg            # Favicon e isotipo institucional
│       └── src/
│           ├── main.tsx / App.tsx / index.css
│           ├── lib/
│           │   ├── api.ts                  # Cliente HTTP Fetch tipado (JSON y multipart FormData)
│           │   ├── auth-store.ts           # Store reactivo de autenticación y sesión
│           │   └── timezone.ts             # Utilidades de conversión y formateo de fechas
│           ├── components/
│           │   ├── layout/
│           │   │   ├── TopSecurityBanner.tsx     # Barra superior criptográfica y de estado
│           │   │   └── InstitutionalShell.tsx    # Layout institucional con navegación electoral completa
│           │   └── electoral/
│           │       ├── ElectionStateStepper.tsx       # Línea de tiempo visual del ciclo de vida
│           │       ├── PhaseCountdownClock.tsx        # Cuenta regresiva sincronizada
│           │       ├── CryptographicHashBadge.tsx     # Visualizador de hashes SHA-256 truncados/copiables
│           │       ├── SealStatusStamp.tsx            # Sellos digitales de cera según fase electoral
│           │       ├── ScheduleEditModal.tsx          # Modal con justificación obligatoria
│           │       ├── ScheduleAuditTimeline.tsx      # Registro histórico de alteraciones de fecha
│           │       ├── HierarchyTreeExplorer.tsx      # Explorador de árbol organizacional + importador CSV
│           │       ├── OfficialBallotPreviewCard.tsx  # Simulador de papeleta en papel marfil con Blanco/Nulo
│           │       ├── PublicationCeremonyModal.tsx   # Ceremonia de publicación con checklist y config_hash
│           │       └── DuplicateAdjudicationDrawer.tsx # Drawer comparativo de arbitraje humano IA-L2a
│           └── pages/
│               ├── PublicLandingRequestPage.tsx       # Portal público con formulario institucional
│               ├── LoginPage.tsx                      # Login con contador de intentos y bloqueo
│               ├── PlatformAdminConsolePage.tsx       # Consola del Administrador de la Plataforma
│               ├── ElectionWorkspacePage.tsx          # Panel de gestión con accesos directos a todos los módulos
│               ├── StructureArchitectPage.tsx         # Arquitecto de grupos, niveles, nodos, cargos y filtros
│               ├── CandidatesBallotStudioPage.tsx     # Estudio de candidatos y previsualización de papeleta
│               ├── VoterRollRegistrationPanelPage.tsx # Panel de padrón, carga CSV, KPIs y bandeja IA-L2a
│               ├── ScheduleControlPanelPage.tsx       # Centro de control del cronograma electoral
│               └── DelegateAdminsPage.tsx             # Administración de administradores segmentados
```

---

## 4. Detalle Técnico de la Base de Datos

Se modelaron en SQLAlchemy 2.0 y migraron en Alembic (`0001_initial_sprint1_schema.py` y `0002_sprint1_iteration2_reconciliation.py`) **las 20 tablas** requeridas para el Sprint 1:

1. **Extensiones habilitadas:** `pgcrypto`, `pg_trgm`, `fuzzystrmatch`.
2. **Tablas Nucleares y Estructurales:**
   - `organization` & `election_request`: Multi-tenancy institucional y radicación pública.
   - `user` & `admin_assignment`: RBAC (`PLATFORM_ADMIN`, `ADMIN_GENERAL`, `ADMIN_SEGMENT`, `OBSERVER`) con bloqueo de fuerza bruta y alcance por `group_id` o `node_id`.
   - `election` & `schedule_change`: Máquina de estados (`DRAFT`, `SCHEDULED`, `REGISTRATION_OPEN`, `REGISTRATION_CLOSED`, `VOTING_OPEN`, `VOTING_CLOSED`, `TALLIED`, `CANCELLED`), ventanas IANA y sellos (`config_hash`, `roll_hash`, `tally_hash`).
   - `voter_group`, `hierarchy_level` & `unit_node`: Grupos de votantes, niveles jerárquicos ordenados por `depth` y nodos con ruta materializada `path` indexada (`/{PARENT_PATH}{CODE}/`).
   - `filter_definition`, `contest`, `contest_breakdown`, `constituency` & `candidate`: Filtros extra JSONB, cargos con nivel de alcance, desgloses, circunscripciones autogeneradas por nodo y candidatos con orden en papeleta.
   - `voter`, `import_batch` & `import_issue`: Padrón electoral con unicidad `(election_id, document_id)`, trazabilidad de lotes CSV, errores de validación e incidentes de duplicidad (`candidate_voter_id`, `matched_voter_id`, `similarity_score`, `edit_distance`, `resolution`, `resolved_by`, `resolved_at`).
   - `registration_link`, `vote`, `voting_credential` & `voter_participation`: Infraestructura para activación y depósito ciego de votos (Invariante #9: `vote` carece de `voter_id`).
   - `audit_log` & `ai_call_log`: Bitácora estrictamente *append-only* protegida por el trigger `trg_audit_log_immutable`.

---

## 5. Criptografía, Inmutabilidad y Seguridad Implementada

1. **Protección de Credenciales:** Hasheo de contraseñas con **Argon2id** (`argon2-cffi`), con fallback seguro a **bcrypt**.
2. **Prevención de Fuerza Bruta:** Bloqueo automático tras **5 intentos fallidos consecutivos** durante **15 minutos** (`Retry-After: 900`).
3. **Blindaje de Voto y Nullifier por Circunscripción (Invariante #9):**
   - `compute_nullifier(voter_id, constituency_id, secret)` calcula $\text{HMAC-SHA256}(\text{secret}, \text{voter\_id} \mathbin{\Vert} \text{":"} \mathbin{\Vert} \text{constituency\_id})$, garantizando 1 voto por votante **por cada cargo/circunscripción** de su papeleta sin vincular jamás `voter_id` a la tabla `vote`.
4. **Publicación Canónica RFC 8785 y `config_hash` (Invariante #3):**
   - Al ejecutar `POST /api/v1/elections/{id}/publish`, se serializa la estructura electoral completa (elección, grupos, niveles, nodos, filtros, cargos, circunscripciones y candidatos) bajo formato JSON canónico determinista (claves ordenadas léxicamente, sin espacios residuales, UTF-8) y se calcula `SHA-256`.
   - Cualquier mutación posterior sobre la estructura electoral es rechazada automáticamente por `require_election_draft` con `HTTP 409 Conflict`.
5. **Autoridad Temporal (Invariante #6):**
   - Reloj oficial en PostgreSQL (`DatabaseTimeProvider` con `SELECT now() AT TIME ZONE 'UTC'`), con inyección de `FakeTimeProvider` para pruebas deterministas.

---

## 6. Motor de Estructura Electoral, Padrón y Detección IA-L2a (Iteración 2)

1. **Árbol Jerárquico y Sincronización de Circunscripciones (S1-03 / S1-04):**
   - Importador CSV de nodos con ordenamiento topológico que garantiza la creación previa de nodos raíz antes de sus descendientes, validando códigos únicos por grupo y construyendo la ruta materializada `/CODE/`.
   - Al definir un `Contest` con `scope_level_id`, el servicio sincroniza automáticamente una `Constituency` por cada `UnitNode` ubicado en dicha profundidad.
2. **Validación Binaria de Candidatos y Papeleta (S1-05):**
   - Validación de fotografías por Magic Bytes (`JPEG` / `PNG`) y reordenamiento atómico de papeleta sin colisiones de `UniqueConstraint("constituency_id", "ballot_order")`.
3. **Ceremonia de Publicación de 6 Reglas (S1-06):**
   - Valida: existencia de grupos, niveles por grupo, nodos hoja, cargos, circunscripciones por cargo y al menos 1 candidato por circunscripción. Transiciona `DRAFT -> SCHEDULED` (o directamente a `REGISTRATION_OPEN` si la fecha de apertura ya fue alcanzada).
4. **Padrón Electoral y Carga Masiva Tolerante a Fallos (S1-07):**
   - Restricción estricta a `REGISTRATION_OPEN` (Invariante #5).
   - Validación de profundidad del nodo asignado frente al nivel más profundo requerido por los cargos del grupo.
   - Procesamiento CSV fila por fila registrando `ImportBatch` y `ImportIssue` sin abortar el lote completo por errores puntuales.
   - Visibilidad acotada por `path LIKE '{node_path}%'` para delegados `ADMIN_SEGMENT`.
5. **Detector Híbrido de Duplicados IA-L2a:**
   - En PostgreSQL ejecuta consultas de similitud trigram (`pg_trgm`) y distancia de edición (`fuzzystrmatch` Levenshtein).
   - En entornos SQLite de pruebas/CI conmuta automáticamente a un motor equivalente en memoria para garantizar paridad de comportamiento.
   - Somete toda colisión a arbitraje humano (`CONFIRM_DISTINCT`, `BLOCK_NEW`, `REMOVE_NEW`).

---

## 7. Sistema de Diseño y Frontend (`apps/web`)

Desarrollado bajo la línea visual **"Soberanía Cívica Criptográfica"** (*Fraunces* + *Plus Jakarta Sans* + *JetBrains Mono* sobre paleta *civic-navy*, *ballot-ivory*, *seal-emerald*, *seal-amber*, *seal-crimson*):

- **Nuevos Componentes Electorales (Iteración 2):**
  - `HierarchyTreeExplorer`: Árbol visual con sangría jerárquica, insignias de ruta materializada, alta manual de nodos hijos e importador CSV interactivo.
  - `OfficialBallotPreviewCard`: Tarjeta tipo papeleta oficial en papel marfil con tarjetas de candidatos, opción de Voto en Blanco y Voto Nulo.
  - `PublicationCeremonyModal`: Modal solemne de publicación con checklist de las 6 reglas, advertencia irreversible de congelamiento y presentación copiable del `config_hash`.
  - `DuplicateAdjudicationDrawer`: Panel lateral comparativo de duplicados IA-L2a con indicador porcentual de similitud, distancia Levenshtein y dictamen humano auditado.
- **Nuevas Páginas y Rutas Integradas:**
  - `/elections/:electionId/structure` (`StructureArchitectPage`)
  - `/elections/:electionId/candidates` (`CandidatesBallotStudioPage`)
  - `/elections/:electionId/voters` (`VoterRollRegistrationPanelPage`)
  - Navegación lateral unificada en `InstitutionalShell` y accesos rápidos en `ElectionWorkspacePage`.
- **Compilación Verificada:**
  - Construcción de producción ejecutada con éxito (`pnpm --filter @votoseguro/web build`) transformando **1643 módulos** con 0 errores de TypeScript (`tsc && vite build`), generando bundle de **391.18 kB JS** y **36.88 kB CSS**.

---

## 8. Verificación y Pruebas Automatizadas

La suite completa de invariantes con `pytest` y `pytest-asyncio` en `apps/api/tests/` pasó al 100%:

```powershell
cd votoseguro/apps/api
$env:PYTHONPATH="."
.\.venv\Scripts\python -m pytest tests
```

**Resultado de ejecución:**
```text
======================= 10 passed, 8 warnings in 2.75s ========================
```

1. `test_tenancy_isolation.py` (1 test): Aislamiento estricto multi-tenant entre organizaciones.
2. `test_auth_lockout.py` (1 test): Bloqueo de cuenta tras 5 intentos fallidos por 15 minutos con `Retry-After`.
3. `test_schedule_rules.py` (2 tests): Precedencia cronológica y reglas de edición por estado.
4. `test_scheduler_transitions.py` (1 test): Transición automática determinista con `FakeTimeProvider`.
5. `test_hierarchy_and_contests.py` (2 tests): Creación de niveles, árbol con rutas materializadas, importación CSV topológica, filtros JSONB y autogeneración de circunscripciones.
6. `test_publication_and_immutability.py` (1 test): Validación de cobertura de candidatos en publicación, cálculo determinista de `config_hash` SHA-256 y rechazo `409 Conflict` ante mutación post-publicación.
7. `test_voter_roll_and_duplicates.py` (2 tests): Guardia de fase `REGISTRATION_OPEN`, validación de profundidad de nodo, importación masiva CSV resiliente, detección IA-L2a y arbitraje humano.

---

## 9. Despliegue en la Nube e Infraestructura en Producción

La plataforma opera sobre una arquitectura cloud de tres capas:
- **Base de Datos PostgreSQL 17 (Supabase):** Connection Pooler IPv4 (`aws-1-us-west-2.pooler.supabase.com:5432`) con extensiones `pgcrypto`, `pg_trgm`, `fuzzystrmatch` y trigger `trg_audit_log_immutable`. *(Nota: ejecutar `alembic upgrade head` para aplicar `0002_sprint1_iteration2_reconciliation` en el entorno remoto).*
- **Backend API & Scheduler Autónomo (Render):** `https://votoseguro-api-plyu.onrender.com` con APScheduler embebido y lock consultivo `pg_try_advisory_xact_lock`.
- **Frontend Web SPA (Cloudflare Pages):** Conectado a la rama `main` con `VITE_API_BASE_URL` y enrutamiento SPA `_redirects`.

---

## 10. Control de Versiones e Historial de Commits

El repositorio se encuentra alojado y sincronizado en:
- **URL:** [https://github.com/Alejandro-Melgar77/votoseguro](https://github.com/Alejandro-Melgar77/votoseguro)
- **Rama:** `main`

### Historial Reciente de Commits:
1. `2025f4e`: `feat: initial architecture sprint 1 v1.0 (s1-00, s1-01, s1-02, s1-11, s1-12)`
2. `083f0f5`: `docs: add project README.md and trigger deployment`
3. `bc4013c`: `docs: update resumen.md with cloud deployments and infrastructure fixes`
4. `e95e25a`: `feat(sprint-1): complete iteration 2 - electoral structure, candidate ballot studio, publication config hash, voter roll and duplicate detection`
5. Commit actual (`fase 2 sprint 1`): Actualización integral de documentación (`resumen.md`) y sincronización final de la Fase 2 en GitHub.

---

## 11. Hoja de Ruta Inmediata (Iteración 3 de 3 del Sprint 1)

Con la estructura electoral, papeleta, publicación y padrón de votantes 100% implementados y verificados, el cierre del Sprint 1 se enfocará en la **Iteración 3**:

1. **S1-08 (Enlaces Públicos de Registro y `roll_hash`):** Activación de votantes por enlace institucional firmado y congelamiento criptográfico definitivo del padrón electoral (`roll_hash`).
2. **S1-09 (Papeleta Automática y Voto Atómico):** Generación dinámica de papeleta según ruta del votante, emisión atómica de voto con nullifiers por circunscripción (sin `voter_id` en `vote`) y emisión de recibo criptográfico verificable.
3. **S1-10 (Escrutinio y $k$-Anonimato):** Tabulación oficial de resultados con supresión automática de celdas por debajo del umbral $k$ (`k_anonymity`) y verificación integral de integridad.
4. **Script `seed:demo`:** Sembrado completo de elección universitaria realista de extremo a extremo para demostración académica y auditoría.
