# VotoSeguro v2 — Resumen Ejecutivo de Implementación (Sprint 1 — Fases 1 y 2)

**Plataforma SaaS Multi-Institución de Votación Electrónica Auditada**  
**Asignatura:** Ingeniería de Software I (INF 422 SB) — UAGRM  
**Fecha de corte:** 11 de Noviembre de 2026  
**Estado:** Iteración 1 e Iteración 2 (Fase 2) del Sprint 1 (v1.0) completamente desarrolladas, verificadas con suite de 10 pruebas automatizadas en `pytest`, frontend compilado en producción (Vite + TypeScript), infraestructura en la nube desplegada (Supabase + Render + Cloudflare Pages) y versionada en GitHub.

---

## 1. Visión General del Proyecto

**VotoSeguro v2** es una solución integral de voto electrónico auditada y verificable orientada a universidades, colegios de profesionales, cooperativas y asociaciones intermedias de Bolivia y Latinoamérica. 
Su diseño arquitectónico garantiza la integridad soberana del proceso electoral mediante:
- **Aislamiento Multi-Tenancy estricto** por organización (`organization_id`).
- **Anonimato absoluto del votante (Invariante #9):** Desvinculación criptográfica total entre la identidad del sufragante y la papeleta depositada (`vote` nunca almacena `voter_id`).
- **Congelamiento Estructural Post-Publicación (Invariante #3):** Una vez publicada solemnemente la elección (`DRAFT -> SCHEDULED`) y emitido el `config_hash` determinista, cualquier mutación sobre grupos, niveles, nodos, filtros, cargos o candidatos es bloqueada con `HTTP 409 Conflict`.
- **Inmutabilidad Temporal del Padrón (Invariante #5):** El padrón electoral únicamente admite altas, bajas, bloqueos o importaciones durante la fase oficial `REGISTRATION_OPEN`.
- **Autoridad temporal canónica (Invariante #6):** Todas las decisiones y transiciones de estado del ciclo electoral dependen exclusivamente del reloj de base de datos (`SELECT now() AT TIME ZONE 'UTC'`).
- **Auditoría inmutable (Append-Only):** Bitácora transaccional blindada a nivel de PostgreSQL contra cualquier intento de modificación o eliminación (`prevent_audit_log_mutation()`).

---

## 2. Historias de Usuario Implementadas (Sprint 1 — Fases 1 y 2)

### Fase 1 (Infraestructura, Tenancy, Cronograma y Scheduler)
| Historia | Prioridad | Denominación | Estado | Descripción Funcional y Técnica |
| :--- | :---: | :--- | :---: | :--- |
| **S1-00** | **Must** | Configuración de Monorepo, Docker, DB y CI | **100%** | Monorepo con `pnpm` workspaces y Python venv/uv. Orquestación de contenedores con `docker-compose.yml` (5 servicios: postgres, api, scheduler, web, mailpit), configuración para despliegue en Render (`render.yaml`), soporte SPA para Cloudflare Pages (`public/_redirects`), primitivas criptográficas (`VoteCodec`, `Nullifier`) y **el 100% de los modelos ORM de las 20 tablas** con su migración inicial Alembic (`0001_initial_sprint1_schema.py`). |
| **S1-01** | **Must** | Autenticación JWT, Multi-Tenancy y Organizaciones | **100%** | Creación y administración de instituciones (tenants) por `PLATFORM_ADMIN`. Autenticación con JWT (HMAC-SHA256) y hash de contraseñas con Argon2 (con fallback automático a bcrypt). Bloqueo de seguridad por fuerza bruta tras 5 intentos fallidos durante 15 minutos (retornando cabecera HTTP `Retry-After: 900`). Bitácora inmutable de auditoría (`audit_log`) con trigger PostgreSQL. |
| **S1-02** | **Must** | Elección, Cronograma Editable y Scheduler Autónomo | **100%** | CRUD integral de Elecciones y motor de cronograma con soporte de zonas horarias IANA (`America/La_Paz`). Matriz de reglas de edición estricta con registro de motivo humano obligatorio (`schedule_change`). Acción de override `"Abrir registro ahora"`. **Scheduler autónomo idempotente** (`APScheduler` cada 10s) con lock distribuido transaccional (`pg_try_advisory_xact_lock(849201)`) y reloj de BD. |
| **S1-11** | **Should** | Delegación de Administradores de Solo Lectura (`ADMIN_SEGMENT`) | **100%** | Creación y gestión de usuarios administradores con alcance territorial o de estamento restringido a un grupo institucional (`group_id`) o a un nodo del árbol jerárquico (`node_id`). |
| **S1-12** | **Should** | Solicitud Pública de Elección por Instituciones | **100%** | Formulario público institucional en Landing Page para solicitar la provisión de una elección. Flujo de radicación y consola de revisión, aprobación y rechazo exclusivo para el `PLATFORM_ADMIN`. |

### Fase 2 (Estructura Jerárquica, Candidatos, Publicación con Hash y Padrón con IA)
| Historia | Prioridad | Denominación | Estado | Descripción Funcional y Técnica |
| :--- | :---: | :--- | :---: | :--- |
| **S1-03** | **Must** | Grupos, Jerarquías Dinámicas y Árbol de Nodos | **100%** | Gestión de `VoterGroup`, escalera de niveles `HierarchyLevel` ordenados por `depth >= 1` y árbol organizacional `UnitNode` con ruta materializada (`path` indexada, ej. `/UAGRM/FICCT/INF/`). Importador masivo CSV de nodos con ordenamiento topológico padre-hijo y cálculo de paths. |
| **S1-04** | **Must** | Filtros Extra, Cargos y Autogeneración de Circunscripciones | **100%** | Filtros dinámicos JSONB (`FilterDefinition`), definición de cargos (`Contest`) con nivel de alcance (`scope_level_id`), desgloses (`ContestBreakdown` por `LEVEL` o `FILTER`) y **sincronización/autogeneración automática de circunscripciones** (`Constituency`) para cada nodo del nivel respectivo. |
| **S1-05** | **Must** | Candidatos por Circunscripción y Estudio de Papeleta | **100%** | CRUD completo de candidatos (`Candidate`) por circunscripción, reordenamiento atómico de papeleta (`ballot_order`), validación de fotografías binarias mediante Magic Bytes (JPEG/PNG) y previsualización en vivo de papeleta oficial en papel marfil con opciones solemnes de **Blanco** y **Nulo**. |
| **S1-06** | **Must** | Ceremonia de Publicación y `config_hash` SHA-256 | **100%** | Transición solemne `DRAFT -> SCHEDULED` mediante `POST /elections/{id}/publish`, validador de integridad de **6 reglas obligatorias**, serialización canónica determinista **RFC 8785**, emisión de `config_hash` SHA-256 y congelamiento estructural irreversible con `HTTP 409 Conflict`. |
| **S1-07** | **Must** | Panel de Registro y Carga de Padrón Electoral | **100%** | Gestión de votantes restringida estrictamente a `REGISTRATION_OPEN`. Alta individual e importador masivo CSV resiliente fila por fila (`ImportBatch` / `ImportIssue`) con validación de profundidad de nodo y unicidad de CI. Bloqueo/desbloqueo/retiro de votantes y resumen estadístico respetando el alcance de `ADMIN_SEGMENT`. |
| **IA-L2a** | **Should** | Detección de Duplicados y Arbitraje Humano | **100%** | Detección automática de posibles duplicados y homonimias usando `pg_trgm` (`similarity >= 0.40`) y `fuzzystrmatch` (`levenshtein <= 3`), con fallback en memoria para SQLite. Bandeja de arbitraje humano con comparativa lado a lado (`CONFIRM_DISTINCT`, `BLOCK_NEW`, `REMOVE_NEW`). |

---

## 3. Estructura de Archivos del Proyecto

```text
votoseguro/
├── README.md                               # Documentación principal del repositorio en GitHub
├── resumen.md                              # Resumen ejecutivo sincronizado
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
│           └── index.ts                    # Interfaces de Dominio (Elecciones, Estructura, Candidatos, Padrón, IA-L2a)
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
│   │   │   ├── main.py                     # Entrypoint FastAPI, lifespan, CORS, registro de routers y seed
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
│   │   │   │   ├── nullifier.py            # Nullifiers ciegos: HMAC-SHA256(voter_id:constituency_id)
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
│           │   │   └── InstitutionalShell.tsx    # Layout institucional con navegación completa
│           │   └── electoral/
│           │       ├── ElectionStateStepper.tsx       # Línea de tiempo visual del ciclo de vida
│           │       ├── PhaseCountdownClock.tsx        # Cuenta regresiva sincronizada
│           │       ├── CryptographicHashBadge.tsx     # Visualizador de hashes SHA-256
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
│               ├── ElectionWorkspacePage.tsx          # Panel de gestión con accesos directos
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
   - `organization` & `election_request`: Multi-tenancy institucional y radicación pública de solicitudes.
   - `user` & `admin_assignment`: RBAC institucional (`PLATFORM_ADMIN`, `ADMIN_GENERAL`, `ADMIN_SEGMENT`, `OBSERVER`) con bloqueo de fuerza bruta y alcance por `group_id` o `node_id`.
   - `election` & `schedule_change`: Ciclo de vida con máquina de 7 estados, marcas de tiempo IANA y sellos criptográficos (`config_hash`, `roll_hash`, `tally_hash`).
   - `voter_group`, `hierarchy_level` & `unit_node`: Grupos de votantes, niveles jerárquicos ordenados por `depth` y nodos con ruta materializada `path` indexada (`/{PARENT_PATH}{CODE}/`).
   - `filter_definition`, `contest`, `contest_breakdown`, `constituency` & `candidate`: Filtros extra JSONB, cargos con nivel de alcance, desgloses, circunscripciones autogeneradas y candidatos con orden en papeleta.
   - `voter`, `import_batch` & `import_issue`: Padrón electoral con restricción de unicidad `(election_id, document_id)`, trazabilidad de lotes CSV, errores de validación e incidentes de duplicidad (`candidate_voter_id`, `matched_voter_id`, `similarity_score`, `edit_distance`, `resolution`, `resolved_by`, `resolved_at`).
   - `registration_link`, `vote`, `voting_credential` & `voter_participation`: Infraestructura para activación y depósito ciego de votos (**Invariante #9**: `vote` carece por diseño de `voter_id`).
   - `audit_log` & `ai_call_log`: Bitácora estrictamente *append-only* protegida por el trigger `trg_audit_log_immutable`.
3. **Trigger de Inmutabilidad:**
   ```sql
   CREATE OR REPLACE FUNCTION prevent_audit_log_mutation() RETURNS trigger AS $$
   BEGIN
       RAISE EXCEPTION 'audit_log is append-only. UPDATE and DELETE operations are forbidden.';
   END;
   $$ LANGUAGE plpgsql;

   CREATE TRIGGER trg_audit_log_immutable
   BEFORE UPDATE OR DELETE ON audit_log
   FOR EACH ROW EXECUTE FUNCTION prevent_audit_log_mutation();
   ```

---

## 5. Criptografía, Inmutabilidad y Seguridad Implementada

1. **Protección de Credenciales:** Hasheo de contraseñas con **Argon2id** (`argon2-cffi`), con fallback automático y seguro a **bcrypt**.
2. **Prevención de Fuerza Bruta:** Bloqueo automático de cuentas tras **5 intentos fallidos consecutivos** durante un periodo de **15 minutos** (`Retry-After: 900`).
3. **Blindaje de Voto y Nullifier por Circunscripción (Invariante #9):**
   - `compute_nullifier(voter_id, constituency_id, secret)` calcula:
     $$\text{nullifier} = \text{HMAC-SHA256}(\text{secret}, \text{voter\_id} \mathbin{\Vert} \text{":"} \mathbin{\Vert} \text{constituency\_id})$$
     permitiendo exactamente un voto por persona **por cada cargo/circunscripción** de su papeleta sin vincular jamás `voter_id` a la tabla `vote`.
4. **Publicación Canónica RFC 8785 y `config_hash` (Invariante #3):**
   - Al ejecutar `POST /api/v1/elections/{id}/publish`, se serializa la estructura electoral completa bajo formato JSON canónico determinista (claves ordenadas léxicamente, sin espacios residuales, cadenas UTF-8) y se calcula `SHA-256`.
   - La guardia `require_election_draft` rechaza automáticamente con `HTTP 409 Conflict` cualquier intento posterior de modificar grupos, niveles, nodos, filtros, cargos o candidatos.
5. **Inmutabilidad Temporal del Padrón (Invariante #5):**
   - Toda inserción individual, importación masiva o alteración de estado sobre el padrón electoral es rechazada con error de dominio si la elección no se encuentra en `REGISTRATION_OPEN`.
6. **Autoridad Temporal (Invariante #6):**
   - El reloj oficial del sistema reside en PostgreSQL (`DatabaseTimeProvider` con `SELECT now() AT TIME ZONE 'UTC'`), con inyección de `FakeTimeProvider` para pruebas deterministas.

---

## 6. Motor de Estructura Electoral, Padrón y Detección IA-L2a (Fase 2)

1. **Rutas Materializadas y Árbol Nodal (S1-03):**
   - El modelo `UnitNode` implementa rutas jerárquicas formateadas como `/{PARENT_PATH}{CODE}/` (ej. `/UAGRM/FICCT/INF/`), permitiendo verificar la pertenencia de un votante o el alcance de un `ADMIN_SEGMENT` en tiempo $O(1)$ mediante operadores `LIKE :path%`.
   - El importador CSV procesa los nodos en orden topológico por niveles, resolviendo padres antes que hijos y validando códigos únicos.
2. **Autogeneración de Circunscripciones (S1-04):**
   - Al crear o modificar un cargo (`Contest`) con un nivel de alcance (`scope_level_id`), el backend sincroniza automáticamente una circunscripción electoral (`Constituency`) para cada nodo existente en ese nivel dentro del grupo.
3. **Validación de Candidatos y Papeleta (S1-05):**
   - Validación binaria estricta de imágenes mediante Magic Bytes (`\xFF\xD8\xFF` para JPEG y `\x89PNG\r\n\x1a\n` para PNG), rechazando extensiones o contenidos falsificados.
   - Reordenamiento atómico de posiciones en papeleta (`ballot_order`) mediante desplazamiento temporal para evitar infracciones de la restricción `UniqueConstraint("constituency_id", "ballot_order")`.
4. **Ceremonia de Publicación con 6 Reglas (S1-06):**
   - Verifica exhaustivamente:
     1. Al menos un grupo de votantes configurado.
     2. Al menos un nivel jerárquico por grupo.
     3. Al menos un nodo hoja por grupo.
     4. Al menos un cargo electoral definido.
     5. Cada cargo tiene al menos una circunscripción asociada.
     6. Cada circunscripción tiene al menos 1 candidato registrado.
   - Transiciona de `DRAFT` a `SCHEDULED` (o a `REGISTRATION_OPEN` si la hora de apertura ya transcurrió) y emite el `config_hash`.
5. **Padrón Electoral Resiliente (S1-07):**
   - Carga masiva CSV fila por fila tolerante a fallos: almacena el lote en `import_batch` y registra fallos individuales en `import_issue` sin detener el procesamiento de filas válidas.
   - Comprueba que el nodo seleccionado corresponda al nivel más profundo requerido por los cargos del grupo.
6. **Detector Híbrido de Duplicados IA-L2a:**
   - En PostgreSQL aprovecha `pg_trgm` (`similarity >= 0.40`) y `fuzzystrmatch` (`levenshtein <= 3`).
   - En SQLite (entornos de test/CI) ejecuta un fallback en memoria de n-gramas trigram y distancia Levenshtein pura.
   - Somete las sospechas a arbitraje humano en `DuplicateAdjudicationDrawer` (`CONFIRM_DISTINCT`, `BLOCK_NEW`, `REMOVE_NEW`).

---

## 7. Sistema de Diseño y Frontend (`apps/web`)

Desarrollado bajo el concepto **"Soberanía Cívica Criptográfica"** (*Fraunces* + *Plus Jakarta Sans* + *JetBrains Mono* sobre paleta *civic-navy*, *ballot-ivory*, *seal-emerald*, *seal-amber*, *seal-crimson*):

- **Nuevos Componentes Electorales (Fase 2):**
  - `HierarchyTreeExplorer`: Explorador de árbol jerárquico con sangría visual, insignias de ruta materializada, alta manual de nodos hijos e importador CSV interactivo.
  - `OfficialBallotPreviewCard`: Simulador de papeleta oficial en papel marfil con tarjetas de candidatos, opción de Voto en Blanco y Voto Nulo.
  - `PublicationCeremonyModal`: Modal solemne de publicación con checklist de las 6 reglas, advertencia de congelamiento irreversible y presentación copiable del `config_hash`.
  - `DuplicateAdjudicationDrawer`: Panel lateral comparativo de duplicados IA-L2a con indicador porcentual de similitud, distancia Levenshtein y formulario de dictamen humano auditado.
- **Nuevas Páginas y Rutas Integradas:**
  - `/elections/:electionId/structure` (`StructureArchitectPage`)
  - `/elections/:electionId/candidates` (`CandidatesBallotStudioPage`)
  - `/elections/:electionId/voters` (`VoterRollRegistrationPanelPage`)
  - Navegación lateral unificada en `InstitutionalShell` y accesos rápidos en `ElectionWorkspacePage`.
- **Compilación Verificada:**
  - Construcción de producción ejecutada con éxito (`pnpm --filter @votoseguro/web build`) transformando **1643 módulos** con 0 errores de TypeScript (`tsc && vite build`), generando bundle optimizado de **391.18 kB JS** y **36.88 kB CSS**.

---

## 8. Verificación y Pruebas Automatizadas

La suite completa de pruebas de invariantes con `pytest` y `pytest-asyncio` en `apps/api/tests/` pasó al 100%:

```powershell
cd votoseguro/apps/api
$env:PYTHONPATH="."
.\.venv\Scripts\python -m pytest tests
```

**Resultado de ejecución:**
```text
======================= 10 passed, 8 warnings in 2.75s ========================
```

1. `test_tenancy_isolation.py`: Comprueba que un administrador de la Organización A no puede acceder a elecciones o recursos de la Organización B.
2. `test_auth_lockout.py`: Comprueba que tras 5 intentos fallidos con contraseña errónea, la cuenta se bloquea por 15 minutos rechazando el 6to intento con HTTP 403 y `Retry-After: 900`.
3. `test_schedule_rules.py`: Comprueba el rechazo de órdenes cronológicos inválidos y el rechazo estricto de edición de fechas de registro una vez iniciada la votación (`VOTING_OPEN`).
4. `test_scheduler_transitions.py`: Comprueba que al avanzar el reloj con `FakeTimeProvider`, el scheduler transiciona automáticamente de `DRAFT` a `REGISTRATION_OPEN` y registra la auditoría.
5. `test_hierarchy_and_contests.py`: Comprueba la jerarquía de niveles, árbol de nodos con ruta materializada `/PATH/`, importación CSV topológica, filtros JSONB y autogeneración de circunscripciones.
6. `test_publication_and_immutability.py`: Comprueba la validación de 6 reglas de cobertura, el cálculo determinista de `config_hash` mediante RFC 8785 y el bloqueo estructural `409 Conflict` post-publicación.
7. `test_voter_roll_and_duplicates.py`: Comprueba la guardia de fase `REGISTRATION_OPEN`, validación de profundidad de nodo, importador CSV tolerante a fallos, detector IA-L2a y resolución de duplicados.

---

## 9. Despliegue en la Nube e Infraestructura en Producción

Toda la plataforma opera sobre una arquitectura cloud de tres capas:

### Capa 1: Base de Datos PostgreSQL 17 (Supabase)
- **Instancia:** Aprovisionada en AWS (`sa-east-1` / `us-west-2`).
- **Connection Pooler (IPv4):** `aws-1-us-west-2.pooler.supabase.com:5432` *(Resuelve la incompatibilidad IPv6 de entornos cloud).*
- **Migraciones Alembic:** `0001_initial_sprint1_schema` y `0002_sprint1_iteration2_reconciliation`.
- **Auditoría Blindada:** Trigger PostgreSQL `trg_audit_log_immutable` activo impidiendo `UPDATE` y `DELETE`.

### Capa 2: Backend API & Scheduler Autónomo (Render)
- **Servicio:** Web Service en Render (`votoseguro-api`).
- **URL Pública:** `https://votoseguro-api-plyu.onrender.com`
- **Estado de Salud:** `Live` (`GET /api/v1/health` $\rightarrow$ `status: online`, `database: healthy`).
- **Superadmin Inicial:** `admin@votoseguro.org` inicializado de manera idempotente durante el ciclo de vida del contenedor.
- **Worker Autónomo:** APScheduler embebido activo con `pg_advisory_lock(849201)` ejecutando ciclos de evaluación cada 10 segundos.

### Capa 3: Frontend Web SPA (Cloudflare Pages)
- **Proyecto:** `votoseguro` en Cloudflare Pages conectado a la rama `main` de GitHub.
- **URL Base de la API:** `VITE_API_BASE_URL=https://votoseguro-api-plyu.onrender.com/api/v1`.
- **Enrutamiento:** Redirección SPA configurada en `_redirects` (`/* /index.html 200`).

---

## 10. Modificaciones Técnicas y Ajustes de Producción

Durante el proceso de despliegue se realizaron las siguientes correcciones críticas:

1. **Protocolo Alembic con asyncpg:** Se dividió la migración en dos llamadas `op.execute()` separadas para la función y el trigger de PostgreSQL.
2. **Dependencias Asíncronas en Docker (Render):** Se añadieron explícitamente `greenlet>=3.1.1` y `sqlalchemy[asyncio]>=2.0.35` a `requirements.txt` y `pyproject.toml`.
3. **Puerto Dinámico en Render:** Se configuró `--port ${PORT:-8000}` en el comando de arranque del Dockerfile.
4. **Conectividad IPv4 Render $\rightarrow$ Supabase:** Se configuró el Connection Pooler de Supabase (`aws-1-us-west-2.pooler.supabase.com:5432`), garantizando resolución IPv4 limpia.
5. **Corrección de `.gitignore` en Frontend:** Se ancló la regla de Python a `/lib/` para evitar ignorar `apps/web/src/lib/`.
6. **Permisos de Build para esbuild en pnpm v10:** Se añadió `"pnpm": { "onlyBuiltDependencies": ["esbuild"] }` en `package.json`.

---

## 11. Control de Versiones e Historial de Commits

El repositorio se encuentra alojado y sincronizado en:
- **URL:** [https://github.com/Alejandro-Melgar77/votoseguro](https://github.com/Alejandro-Melgar77/votoseguro)
- **Rama:** `main`

### Historial Canónico de Commits:
1. `2025f4e`: `feat: initial architecture sprint 1 v1.0 (s1-00, s1-01, s1-02, s1-11, s1-12)`
2. `787b5c1`: `docs: add executive implementation summary resumen.md`
3. `6d78d70`: `fix(db): separate trigger DDL statements for asyncpg compatibility`
4. `03a3056`: `chore(infra): configure render.yaml with Supabase PostgreSQL connection`
5. `d5f0db0`: `chore(infra): add plan free to render.yaml`
6. `ec1feba`: `fix(api): add greenlet dependency and support dynamic PORT in Dockerfile`
7. `d3b828a`: `chore(infra): update render.yaml with IPv4 pooler connection string`
8. `0c21caf`: `fix(web): unignore and track src/lib files and allow esbuild build script`
9. `083f0f5`: `docs: add project README.md and trigger deployment`
10. `bc4013c`: `docs: update resumen.md with cloud deployments and infrastructure fixes`
11. `e95e25a`: `feat(sprint-1): complete iteration 2 - electoral structure, candidate ballot studio, publication config hash, voter roll and duplicate detection`
12. `e575e80`: `fase 2 sprint 1`

---

## 12. Hoja de Ruta Inmediata (Iteración 3 del Sprint 1)

Con las Fases 1 y 2 100% implementadas y verificadas, el cierre del Sprint 1 se enfocará en la **Iteración 3**:

1. **S1-08 (Enlaces Públicos de Registro y `roll_hash`):** Activación de votantes mediante enlace firmado y sellado definitivo del padrón electoral (`roll_hash`).
2. **S1-09 (Papeleta Automática y Voto Atómico):** Generación dinámica de la papeleta según el nodo del votante, depósito ciego de votos con nullifiers por circunscripción (sin `voter_id` en `vote`) y emisión de recibo verificable.
3. **S1-10 (Escrutinio y $k$-Anonimato):** Tabulación oficial de resultados con supresión de celdas por debajo del umbral $k$ (`k_anonymity`) y verificación de actas.
4. **Script `seed:demo`:** Sembrado integral de un proceso electoral universitario de demostración para evaluación y auditoría académica.
