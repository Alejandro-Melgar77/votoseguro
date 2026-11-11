# VotoSeguro v2 — Resumen Ejecutivo de Implementación (Sprint 1 Completo — Final Release v1.0)

**Plataforma SaaS Multi-Institución de Votación Electrónica Auditada**  
**Asignatura:** Ingeniería de Software I (INF 422 SB) — UAGRM  
**Fecha de corte:** 11 de Noviembre de 2026  
**Estado:** **100% de Historias de Usuario del Sprint 1 (14/14 historias)** desarrolladas, verificadas con suite de 15 pruebas automatizadas en `pytest` (100% de éxito), frontend compilado en producción (Vite + TypeScript con 0 errores), base de datos Supabase migrada a la última versión (`0003_iter3_voting`), dataset institucional sembrado (`seed:demo`), e infraestructura cloud activa (Supabase + Render + Cloudflare Pages).

---

## 1. Visión General del Proyecto

**VotoSeguro v2** es una plataforma integral de voto electrónico verificable, transparente y auditada, diseñada para instituciones de educación superior, colegios de profesionales, cooperativas y asociaciones civiles de Bolivia y Latinoamérica.

Su diseño arquitectónico garantiza la integridad soberana del proceso electoral mediante **17 Invariantes Electorales Criptográficas y de Dominio**:
- **Aislamiento Multi-Tenancy estricto** por organización (`organization_id`).
- **Anonimato absoluto del votante (Invariante #9):** Desvinculación criptográfica total entre la identidad del sufragante y la papeleta depositada (`vote` nunca almacena `voter_id`).
- **Nullifier Ciego por Circunscripción (Invariante #8):** Cálculo de $\text{HMAC-SHA256}(\text{secret}, \text{voter\_id} \mathbin{\Vert} \text{":"} \mathbin{\Vert} \text{constituency\_id})$ para garantizar un solo voto por cargo sin revelar identidad.
- **Congelamiento Estructural Post-Publicación (Invariante #3):** Una vez publicada solemnemente la elección (`DRAFT -> SCHEDULED`) y emitido el `config_hash` determinista (RFC 8785), cualquier mutación sobre grupos, niveles, nodos, filtros, cargos o candidatos es bloqueada con `HTTP 409 Conflict`.
- **Inmutabilidad Temporal del Padrón y Sellado Canónico (Invariante #5):** El padrón electoral únicamente admite modificaciones durante `REGISTRATION_OPEN`. Al cerrarse la fase, se calcula el `roll_hash` determinista (SHA-256) congelando el censo de votantes.
- **Credenciales Exclusivas para Votantes Activos (Invariante #7):** Solo los votantes en estado `ACTIVE` reciben credenciales personales de un solo uso (`VS-XXXX-XXXX-XXXX`).
- **Resultados Sellados hasta el Cierre (Invariante #11):** Cualquier consulta a resultados o cómputo antes de `VOTING_CLOSED` es bloqueada con `HTTP 403 Forbidden`.
- **Privacidad y $k$-Anonimato en Desgloses (Invariante #12):** En desgloses por nivel territorial o filtros, las celdas con recuentos menores al umbral $k$ (`k_anonymity=5`) se ocultan o redactan (`< k` votos) para impedir la reidentificación del votante.
- **Serialización Canónica del Voto (Invariante #13):** Uso de `VoteCodec` determinista tanto en voto plano como en homomórfico.
- **Truncamiento de Marcas Temporales (Invariante #17):** Los votos se estampan con marcas de tiempo truncadas al minuto para evitar ataques de correlación temporal con los registros de red.
- **Autoridad temporal canónica (Invariante #6):** Todas las decisiones y transiciones de estado dependen exclusivamente del reloj de base de datos (`SELECT now() AT TIME ZONE 'UTC'`).
- **Auditoría inmutable (Append-Only):** Bitácora transaccional blindada a nivel de PostgreSQL contra cualquier intento de modificación o eliminación (`prevent_audit_log_mutation()`).

---

## 2. Historias de Usuario Implementadas (14 de 14 — 100% Sprint 1)

### Fase 1: Infraestructura, Tenancy, Cronograma y Scheduler
| Historia | Prioridad | Denominación | Puntos | Estado | Descripción Funcional y Técnica |
| :--- | :---: | :--- | :---: | :---: | :--- |
| **S1-00** | **Must** | Configuración de Monorepo, Docker, DB y CI | 5 pts | **100%** | Monorepo con `pnpm` workspaces y Python venv/uv. Contenedores con `docker-compose.yml`, configuración IaC para Render (`render.yaml`), soporte SPA para Cloudflare Pages (`public/_redirects`), primitivas criptográficas (`VoteCodec`, `Nullifier`) y modelos ORM de las 20 tablas con su migración inicial Alembic (`0001_initial_sprint1_schema.py`). |
| **S1-01** | **Must** | Autenticación JWT, Multi-Tenancy y Organizaciones | 8 pts | **100%** | Creación y administración de instituciones (tenants) por `PLATFORM_ADMIN`. Autenticación con JWT (HMAC-SHA256) y hash de contraseñas con Argon2 (con fallback automático a bcrypt). Bloqueo de seguridad por fuerza bruta tras 5 intentos fallidos durante 15 minutos (`Retry-After: 900`). Bitácora inmutable de auditoría (`audit_log`) con trigger PostgreSQL. |
| **S1-02** | **Must** | Elección, Cronograma Editable y Scheduler Autónomo | 8 pts | **100%** | CRUD integral de Elecciones y motor de cronograma con soporte de zonas horarias IANA (`America/La_Paz`). Matriz de reglas de edición estricta con registro de motivo obligatorio (`schedule_change`). Acción de override *"Abrir registro ahora"*. Scheduler autónomo idempotente (`APScheduler` cada 10s) con lock distribuido transaccional (`pg_try_advisory_xact_lock(849201)`) y reloj de BD. |
| **S1-11** | **Should** | Delegación de Administradores de Solo Lectura (`ADMIN_SEGMENT`) | 3 pts | **100%** | Creación y gestión de administradores con alcance territorial o de estamento restringido a un grupo institucional (`group_id`) o a un nodo del árbol jerárquico (`node_id`). |
| **S1-12** | **Should** | Solicitud Pública de Elección por Instituciones | 3 pts | **100%** | Formulario público institucional en Landing Page para solicitar la provisión de una elección. Flujo de radicación y consola de revisión, aprobación y rechazo exclusivo para el `PLATFORM_ADMIN`. |

### Fase 2: Estructura Jerárquica, Candidatos, Publicación y Padrón con IA
| Historia | Prioridad | Denominación | Puntos | Estado | Descripción Funcional y Técnica |
| :--- | :---: | :--- | :---: | :---: | :--- |
| **S1-03** | **Must** | Grupos, Jerarquías Dinámicas y Árbol de Nodos | 8 pts | **100%** | Gestión de `VoterGroup`, escalera de niveles `HierarchyLevel` ordenados por `depth >= 1` y árbol organizacional `UnitNode` con ruta materializada (`path` indexada, ej. `/UAGRM/FICCT/INF/`). Importador masivo CSV de nodos con ordenamiento topológico padre-hijo y cálculo de paths. |
| **S1-04** | **Must** | Filtros Extra, Cargos y Circunscripciones | 5 pts | **100%** | Filtros dinámicos JSONB (`FilterDefinition`), definición de cargos (`Contest`) con nivel de alcance (`scope_level_id`), desgloses (`ContestBreakdown` por `LEVEL` o `FILTER`) y sincronización/autogeneración automática de circunscripciones (`Constituency`) para cada nodo del nivel respectivo. |
| **S1-05** | **Must** | Candidatos por Circunscripción y Estudio de Papeleta | 5 pts | **100%** | CRUD completo de candidatos (`Candidate`) por circunscripción, reordenamiento atómico de papeleta (`ballot_order`), validación de fotografías binarias mediante Magic Bytes (JPEG/PNG) y previsualización en vivo de papeleta oficial en papel marfil con opciones solemnes de Blanco y Nulo. |
| **S1-06** | **Must** | Ceremonia de Publicación y `config_hash` SHA-256 | 5 pts | **100%** | Transición solemne `DRAFT -> SCHEDULED` mediante `POST /elections/{id}/publish`, validador de integridad de 6 reglas obligatorias, serialización canónica determinista **RFC 8785**, emisión de `config_hash` SHA-256 y congelamiento estructural irreversible con `HTTP 409 Conflict`. |
| **S1-07** | **Must** | Panel de Registro y Carga de Padrón Electoral | 8 pts | **100%** | Gestión de votantes restringida estrictamente a `REGISTRATION_OPEN`. Alta individual e importador masivo CSV resiliente fila por fila (`ImportBatch` / `ImportIssue`) con validación de profundidad de nodo y unicidad de CI. Bloqueo/desbloqueo/retiro de votantes y resumen estadístico respetando el alcance de `ADMIN_SEGMENT`. |
| **IA-L2a** | **Should** | Detección de Duplicados y Arbitraje Humano | 5 pts | **100%** | Detección automática de posibles duplicados y homonimias usando `pg_trgm` (`similarity >= 0.40`) y `fuzzystrmatch` (`levenshtein <= 3`), con fallback en memoria para SQLite. Bandeja de arbitraje humano con comparativa lado a lado (`CONFIRM_DISTINCT`, `BLOCK_NEW`, `REMOVE_NEW`). |

### Fase 3: Activación, Papeleta Automática, Voto Ciego Atómico, Escrutinio y Demo
| Historia | Prioridad | Denominación | Puntos | Estado | Descripción Funcional y Técnica |
| :--- | :---: | :--- | :---: | :---: | :--- |
| **S1-08** | **Must** | Enlaces de Registro, Activación y `roll_hash` | 6 pts | **100%** | Generación de enlaces de activación por grupo o nodo (`registration_link`), portal público de activación (`/register/:token`) validando CI del votante dentro de `REGISTRATION_OPEN`. Despacho de invitaciones y sellado automático/administrativo del padrón al cierre con cálculo determinista de `roll_hash` SHA-256 (RFC 8785). |
| **S1-09** | **Must** | Credenciales, Papeleta Automática y Voto Ciego | 8 pts | **100%** | Emisión de credenciales personales de un solo uso (`VS-XXXX-XXXX-XXXX`) para votantes `ACTIVE`. Login de votante (`/voter/login`), resolución dinámica de papeleta automática según `group_id` y `node.path` (`GET /api/v1/ballot`), depósito atómico transaccional de votos (`POST /api/v1/ballot/cast`) con nullifiers HMAC-SHA256 por circunscripción, tabla `vote` sin `voter_id` (Invariante #9), timestamp truncado al minuto (Invariante #17), `VoteCodec` (Invariante #13), emisión de recibo criptográfico (`receipt_hash`) descargable y verificación pública de recibo. |
| **S1-10** | **Must** | Escrutinio Oficial, Desgloses y $k$-Anonimato | 5 pts | **100%** | Cómputo de resultados tras el cierre (`VOTING_CLOSED`), sellado con `HTTP 403 Forbidden` durante la votación (Invariante #11). Conteos totales exactos por candidato, blanco y nulo, desgloses configurados (`ContestBreakdown` por jerarquía `segment_path` y filtros `filters_snapshot`), y aplicación estricta de **$k$-anonimato (Invariante #12)** ocultando o redactando celdas con $< k$ votos ($k=5$). |
| **`seed:demo`** | **Must** | Sembrado de Datos Demo Idempotente | — | **100%** | Sembrador autónomo de dos elecciones completas: **Universidad EL GRAN ESTUDIO** (Estudiantes y Docentes, 3 facultades, 4 carreras, cargos de Rector, Decano, Director, candidatos y 36+ votantes con casos de homonimia) y **Elecciones Nacionales Ecuador** (4 niveles territoriales: País, Provincias, Cantones, Parroquias con Presidente y Gobernadores). Ejecutable vía CLI (`python -m app.db.seed_demo`) y por endpoint administrativo (`POST /api/v1/platform/seed-demo`). |

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
│   ├── DECISIONES.md                       # Decisiones de Arquitectura de Software (ADR 001 - 012)
│   └── PROGRESO.md                         # Cuadro de mando y seguimiento de historias (14/14 completadas)
├── packages/
│   └── api-client/                         # Paquete compartido de tipos TypeScript y contratos DTO
│       ├── package.json
│       └── src/
│           └── index.ts                    # Tipos de Dominio (Elecciones, Candidatos, Padrón, Enlaces, Papeleta, Resultados)
├── apps/
│   ├── api/                                # Backend en FastAPI + SQLAlchemy 2.0 + Alembic
│   │   ├── pyproject.toml / requirements.txt
│   │   ├── Dockerfile
│   │   ├── alembic.ini
│   │   ├── alembic/
│   │   │   ├── env.py
│   │   │   └── versions/
│   │   │       ├── 0001_initial_sprint1_schema.py              # DDL de las 20 tablas + extensiones + triggers
│   │   │       ├── 0002_sprint1_iteration2_reconciliation.py   # Reconciliación de columnas para Iteración 2
│   │   │       └── 0003_sprint1_iteration3_voting_reconciliation.py # Reconciliación de enlaces y credenciales (Fase 3)
│   │   ├── app/
│   │   │   ├── main.py                     # Entrypoint FastAPI, lifespan, CORS, registro de routers y seed
│   │   │   ├── core/
│   │   │   │   ├── config.py               # Configuración con Pydantic Settings
│   │   │   │   ├── security.py             # Hasheo Argon2 / bcrypt, firma y verificación JWT (User y VoterSession)
│   │   │   │   ├── time.py                 # Abstracción de reloj canónico (Database / Fake)
│   │   │   │   ├── exceptions.py           # Jerarquía de errores de dominio y mapeo HTTP
│   │   │   │   └── dependencies.py         # Extracción de contexto tenant, voter session y guardias RBAC
│   │   │   ├── db/
│   │   │   │   ├── base.py                 # DeclarativeBase y tipos comunes
│   │   │   │   ├── session.py              # Generador de sesiones async (asyncpg / aiosqlite)
│   │   │   │   ├── seed_demo.py            # Sembrador CLI / programático de datos demo
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
│   │   │       ├── auth/                   # Login de usuarios y administradores, perfil, bloqueo fuerza bruta
│   │   │       ├── audit/                  # Consulta y registro de bitácora
│   │   │       ├── organizations/          # Gestión de tenants, solicitudes y endpoint platform/seed-demo
│   │   │       ├── admins/                 # Delegación de ADMIN_SEGMENT
│   │   │       ├── elections/              # CRUD de elección, validador de fechas y publicación (S1-06)
│   │   │       ├── structure/              # S1-03 y S1-04: jerarquías, nodos, filtros y cargos
│   │   │       ├── candidates/             # S1-05: candidatos y papeleta
│   │   │       ├── voters/                 # S1-07 e IA-L2a: padrón, carga CSV y detector de duplicados
│   │   │       ├── registration/           # S1-08: enlaces de registro, activación pública y roll_hash
│   │   │       ├── ballots/                # S1-09: credenciales de votación, login votante, papeleta automática y voto ciego
│   │   │       ├── results/                # S1-10: cómputo oficial, desgloses jerárquicos y k-anonimato
│   │   │       └── scheduler/              # APScheduler worker con lock de PostgreSQL y congelamiento de roll_hash
│   │   └── tests/                          # Suite de pruebas automatizadas (15 tests en 11 archivos)
│   │       ├── conftest.py                 # Fixtures async y Mock TimeProvider
│   │       ├── test_tenancy_isolation.py   # Verificación de aislamiento multi-tenant
│   │       ├── test_auth_lockout.py        # Verificación de bloqueo tras 5 intentos
│   │       ├── test_schedule_rules.py      # Verificación de reglas de edición de cronograma
│   │       ├── test_scheduler_transitions.py # Transiciones temporales deterministas
│   │       ├── test_hierarchy_and_contests.py # Jerarquías, paths, importador CSV y circunscripciones
│   │       ├── test_publication_and_immutability.py # Validación de 6 reglas, RFC 8785 config_hash y 409 Conflict
│   │       ├── test_voter_roll_and_duplicates.py # Guardia de fase, profundidad de nodo e IA-L2a
│   │       ├── test_registration_links_and_roll_hash.py # Enlaces de registro, activación y sellado de padrón
│   │       ├── test_automatic_ballot_and_atomic_cast.py # Login votante, papeleta automática, voto ciego y recibo
│   │       ├── test_results_and_k_anonymity.py # Bloqueo 403 antes del cierre y k-anonimato en desgloses
│   │       └── test_seed_demo.py           # Idempotencia y completitud del sembrador demo
│   └── web/                                # Frontend en React 18 + Vite + TypeScript + Tailwind
│       ├── package.json / vite.config.ts / tailwind.config.js / tsconfig.json
│       ├── public/
│       │   ├── _redirects                  # Configuración de rewrite para Cloudflare Pages
│       │   └── shield-check.svg            # Favicon e isotipo institucional
│       └── src/
│           ├── main.tsx / App.tsx / index.css
│           ├── lib/
│           │   ├── api.ts                  # Cliente HTTP Fetch tipado (JSON y multipart FormData)
│           │   ├── auth-store.ts           # Store reactivo de autenticación administrativa y sesión de votante
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
│               ├── PlatformAdminConsolePage.tsx       # Consola de Superadmin con botón Sembrar Datos Demo
│               ├── ElectionWorkspacePage.tsx          # Panel de gestión electoral
│               ├── StructureArchitectPage.tsx         # Arquitecto de grupos, niveles, nodos, cargos y filtros
│               ├── CandidatesBallotStudioPage.tsx     # Estudio de candidatos y previsualización de papeleta
│               ├── VoterRollRegistrationPanelPage.tsx # Panel de padrón, CSV, IA-L2a, Enlaces S1-08 y Credenciales S1-09
│               ├── ScheduleControlPanelPage.tsx       # Centro de control del cronograma electoral
│               ├── DelegateAdminsPage.tsx             # Administración de administradores segmentados
│               ├── PublicVoterRegistrationPage.tsx    # Portal público de activación de votantes (/register/:token)
│               ├── VoterBallotBoothPage.tsx           # Cabina oficial de votación (/vote) con papeleta y recibo
│               └── ElectionResultsTallyPage.tsx       # Centro de cómputo y resultados oficiales (/results)
```

---

## 4. Detalle Técnico de Base de Datos y Migraciones

La base de datos cuenta con **20 tablas modeladas**, extensiones criptográficas y de texto, y triggers de seguridad ejecutados sobre PostgreSQL 17 (Supabase):

1. **Extensiones activadas:** `pgcrypto`, `pg_trgm`, `fuzzystrmatch`.
2. **Historial de Migraciones Alembic:**
   - `0001_initial_sprint1_schema.py`: Creación integral de las 20 tablas, relaciones, claves foráneas, índices de unicidad y trigger inmutable.
   - `0002_iter2_reconcile.py`: Ajuste de compatibilidad para identificadores de versión Alembic (`VARCHAR(128)`) y conciliación de columnas estructurales.
   - `0003_iter3_voting.py`: Adición de soporte para tokens previsualizables de demostración en `registration_link` (`raw_token`) y `voting_credential` (`demo_code`) para facilitar la auditoría sin requerir SMTP externo obligatorio.
3. **Trigger de Inmutabilidad de Auditoría:**
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

## 5. Arquitectura de Seguridad e Invariantes Criptográficas

1. **Protección de Credenciales de Usuario:** Hasheo con **Argon2id** (`argon2-cffi`), con fallback automático a **bcrypt**.
2. **Defensa contra Ataques de Fuerza Bruta:** Bloqueo automático de cuentas de usuario tras **5 intentos fallidos consecutivos** durante un periodo de **15 minutos** (`Retry-After: 900`).
3. **Blindaje de Voto Ciego y Nullifiers (Invariante #9 y #8):**
   - La tabla `vote` **no contiene la columna `voter_id`**.
   - Para impedir el doble voto sin romper el anonimato, se utiliza un *nullifier* criptográfico:
     $$\text{nullifier} = \text{HMAC-SHA256}(\text{election.secret\_key}, \text{voter\_id} \mathbin{\Vert} \text{":"} \mathbin{\Vert} \text{constituency\_id})$$
   - El *nullifier* es único por votante y circunscripción, registrándose en `voter_participation` y en el registro del voto, garantizando matemáticamente que ningún votante pueda emitir más de un voto por cargo.
4. **Papeleta Automática Resuelta por Jerarquía:**
   - Al autenticarse el votante en `/voter/login`, el backend localiza su grupo (`group_id`) y su nodo territorial (`unit_node.path`).
   - Para cada cargo (`Contest`) del grupo, se busca la circunscripción (`Constituency`) cuyo nodo ancestro coincide con el `path` del votante.
   - El votante recibe exclusivamente los cargos que le corresponden según su ubicación o estamento.
5. **Depósito Atómico Transaccional y Recibo Criptográfico:**
   - La emisión del voto se ejecuta en una transacción única ACID (`POST /api/v1/ballot/cast`):
     1. Valida que la credencial esté activa y no haya sido utilizada (`used_at IS NULL`).
     2. Verifica que ninguno de los nullifiers haya sido previamente depositado.
     3. Inserta los votos codificados en la tabla `vote` con timestamp truncado al minuto (**Invariante #17**).
     4. Calcula el hash acumulado del recibo:
        $$\text{receipt\_hash} = \text{SHA-256}(\text{election\_id} \mathbin{\Vert} \text{timestamp} \mathbin{\Vert} \text{nullifiers\_hash})$$
     5. Marca la credencial como usada (`used_at = now`) y registra la participación en `voter_participation`.
   - El votante recibe su recibo descargable para verificación posterior en `GET /api/v1/receipts/{receipt_hash}`.
6. **Escrutinio Sellado y $k$-Anonimato (Invariantes #11 y #12):**
   - Durante la votación (`VOTING_OPEN`), el endpoint `/elections/{id}/results` retorna estrictamente `HTTP 403 Forbidden` (*"Los resultados solo pueden consultarse una vez cerrada la votación"*).
   - Al cerrarse la votación (`VOTING_CLOSED`), se calcula la tabulación oficial exacta de votos totales por candidato, blanco y nulo.
   - En los desgloses configurados (`ContestBreakdown` por jerarquía o filtros), cualquier celda que contenga menos de $k$ votos ($k=5$ por defecto) se redacta con `is_redacted = true` y `vote_count = null`, impidiendo la reidentificación de votantes en segmentos pequeños.
7. **Congelamiento de Padrón y `roll_hash` (Invariante #5):**
   - Al finalizar el registro, el sistema genera la lista canónica de votantes activos ordenada deterministamente por `document_id` y emite el `roll_hash` (SHA-256 RFC 8785), sellando el padrón para siempre.

---

## 6. Verificación y Suite de Pruebas Automatizadas

La suite completa de pruebas automatizadas con `pytest` y `pytest-asyncio` en `apps/api/tests/` ejecutó **15 suites con 100% de éxito**:

```powershell
cd votoseguro/apps/api
$env:PYTHONPATH="."
.\.venv\Scripts\python -m pytest tests
```

**Resultado de ejecución:**
```text
======================= 15 passed, 8 warnings in 4.01s ========================
```

### Detalle de las 15 Pruebas Automatizadas:
1. `test_tenancy_isolation.py`: Comprueba que un administrador de la Organización A no puede acceder a elecciones o recursos de la Organización B.
2. `test_auth_lockout.py`: Comprueba que tras 5 intentos fallidos con contraseña errónea, la cuenta se bloquea por 15 minutos rechazando el 6to intento con HTTP 403 y `Retry-After: 900`.
3. `test_schedule_rules.py`: Comprueba el rechazo de órdenes cronológicos inválidos y el rechazo estricto de edición de fechas de registro una vez iniciada la votación (`VOTING_OPEN`).
4. `test_scheduler_transitions.py`: Comprueba que al avanzar el reloj con `FakeTimeProvider`, el scheduler transiciona automáticamente de `DRAFT` a `REGISTRATION_OPEN` y registra la auditoría.
5. `test_hierarchy_and_contests.py`: Comprueba la jerarquía de niveles, árbol de nodos con ruta materializada `/PATH/`, importación CSV topológica, filtros JSONB y autogeneración de circunscripciones.
6. `test_publication_and_immutability.py`: Comprueba la validación de 6 reglas de cobertura, el cálculo determinista de `config_hash` mediante RFC 8785 y el bloqueo estructural `409 Conflict` post-publicación.
7. `test_voter_roll_and_duplicates.py`: Comprueba la guardia de fase `REGISTRATION_OPEN`, validación de profundidad de nodo, importador CSV tolerante a fallos, detector IA-L2a y resolución de duplicados.
8. `test_registration_links_and_roll_hash.py`: Comprueba la creación de enlaces de registro por grupo/nodo, la activación pública mediante CI en `/register/:token`, el despacho de invitaciones y el cálculo canónico de `roll_hash` al cerrar el registro.
9. `test_automatic_ballot_and_atomic_cast.py`: Comprueba la emisión de credenciales para votantes activos, login de votante (`VOTER_SESSION`), resolución dinámica de papeleta según nodo jerárquico, emisión atómica de votos con nullifiers, ausencia de `voter_id` en `vote` (Invariante #9), timestamp truncado al minuto (Invariante #17) y verificación pública de recibo.
10. `test_results_and_k_anonymity.py`: Comprueba el bloqueo `403 Forbidden` de resultados antes de `VOTING_CLOSED` (Invariante #11), el cómputo exacto de votos tras el cierre y la aplicación estricta de $k$-anonimato ($k=5$) en desgloses jerárquicos (Invariante #12).
11. `test_seed_demo.py`: Comprueba la idempotencia del script `seed:demo`, el sembrado completo de la Universidad EL GRAN ESTUDIO y Elecciones Nacionales Ecuador, los votantes con casos de homonimia y la ejecución exitosa del endpoint `POST /api/v1/platform/seed-demo`.

---

## 7. Despliegue en la Nube e Infraestructura en Producción

Toda la plataforma opera sobre una arquitectura cloud de tres capas en producción:

### Capa 1: Base de Datos PostgreSQL 17 (Supabase)
- **Instancia:** Aprovisionada en AWS (`aws-1-us-west-2.pooler.supabase.com:5432`).
- **Migraciones Aplicadas:** `0001_initial_sprint1_schema`, `0002_iter2_reconcile` y `0003_iter3_voting`.
- **Auditoría Blindada:** Trigger PostgreSQL `trg_audit_log_immutable` activo impidiendo mutaciones en la bitácora.
- **Datos Sembrados:** Ejecutado `seed:demo` con organizaciones de prueba activas.

### Capa 2: Backend API & Scheduler Autónomo (Render)
- **Servicio:** Web Service en Render (`votoseguro-api`).
- **URL Pública:** `https://votoseguro-api-plyu.onrender.com`
- **Monitoreo:** `GET /api/v1/health` $\rightarrow$ `status: online`, `database: healthy`.
- **Superadmin:** `admin@votoseguro.org` inicializado de manera idempotente.
- **Worker Autónomo:** APScheduler embebido activo con `pg_advisory_lock(849201)` ejecutando ciclos de evaluación cada 10 segundos.

### Capa 3: Frontend Web SPA (Cloudflare Pages)
- **Proyecto:** `votoseguro` en Cloudflare Pages conectado a la rama `main` de GitHub.
- **URL Base de la API:** `VITE_API_BASE_URL=https://votoseguro-api-plyu.onrender.com/api/v1`.
- **Enrutamiento:** Redirección SPA configurada en `_redirects` (`/* /index.html 200`).
- **Compilación de Producción:** Verificada con `pnpm --filter @votoseguro/web build` (0 errores TypeScript).

---

## 8. Control de Versiones e Historial de Commits

El repositorio se encuentra alojado y sincronizado en:
- **URL:** [https://github.com/Alejandro-Melgar77/votoseguro](https://github.com/Alejandro-Melgar77/votoseguro)
- **Rama:** `main`

### Historial de Commits del Sprint 1:
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
13. `a9b1c0e` *(por publicar)*: `feat(sprint-1): complete phase 3 v1.0 - voter activation links, automatic ballot, atomic blind voting, k-anonymity tally and seed demo`

---

## 9. Manual Rápido de Validación y Flujo de Demostración

Para evaluar y auditar la plataforma de forma integral de extremo a extremo:

1. **Sembrado Demo:**
   - Iniciar sesión como `admin@votoseguro.org` (clave `Admin1234!*`) en `/login`.
   - Entrar a la Consola de Plataforma (`/platform/console`) y presionar el botón **"Sembrar Datos Demo (seed:demo)"**.
2. **Activación de Votantes por Enlace (S1-08):**
   - Entrar a la elección *"Elecciones Rectorales 2026"* $\rightarrow$ Pestaña **"Padrón Electoral"** (`/elections/:id/voters`).
   - Ir a la sub-pestaña **"Enlaces de Registro (S1-08)"**, crear un enlace o copiar un enlace existente (`/register/:token`).
   - Abrir el enlace en una ventana de incógnito, ingresar el CI de un votante importado (ej. `CI-EST-001`), verificar la emisión de su Certificado Digital de Registro y constatar que su estado cambia a `ACTIVE`.
3. **Congelamiento de Padrón y Despacho de Credenciales (S1-09):**
   - En la pestaña de padrón, presionar **"Congelar Padrón (roll_hash)"** para sellar el censo electoral con hash determinista.
   - Ir a la sub-pestaña **"Credenciales Demo (S1-09)"** para inspeccionar las credenciales personales generadas (`VS-XXXX-XXXX-XXXX`).
   - Presionar **"Abrir Votación Ahora"** para cambiar el estado de la elección a `VOTING_OPEN`.
4. **Cabina de Votación y Depósito Ciego (S1-09):**
   - Navegar a `/vote` en una ventana de incógnito.
   - Ingresar el CI (ej. `CI-EST-001`) y el código de credencial copiado.
   - Constatar la **Papeleta Automática** personalizada (cargos de Rector, Decano FICCT y Director de Carrera Informática).
   - Seleccionar candidatos (o Voto en Blanco / Voto Nulo) y presionar **"Confirmar y Depositar Voto Ciego"**.
   - Descargar el Recibo Criptográfico con el `receipt_hash` y verificar su presencia pública en el verificador de actas.
5. **Comprobación de Bóveda Sellada (Invariante #11):**
   - Con la elección aún en `VOTING_OPEN`, ingresar al Centro de Cómputo (`/elections/:id/results`).
   - Constatar la advertencia de Bóveda Criptográfica Sellada con el candado digital y el indicador de participación en tiempo real (los resultados parciales están estrictamente ocultos).
6. **Cierre de Votación y Escrutinio con $k$-Anonimato (S1-10):**
   - Como Administrador General, presionar **"Cerrar Votación Oficialmente"**.
   - El sistema calcula el escrutinio total exacto y desbloquea el acta digital de resultados.
   - En la sección de desgloses jerárquicos y por filtros, verificar la aplicación del **$k$-anonimato**: los nodos con menos de 5 votos aparecen redactados con la insignia *"Protegido por k-anonimato (< 5 votos)"*.
