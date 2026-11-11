# VotoSeguro v2 — Resumen Ejecutivo de Implementación (Sprint 1 - Iteración 1)

**Plataforma SaaS Multi-Institución de Votación Electrónica Auditada**  
**Asignatura:** Ingeniería de Software I (INF 422 SB) — UAGRM  
**Fecha de corte:** 11 de Noviembre de 2026  
**Estado:** Iteración 1 del Sprint 1 (v1.0) completamente desarrollada, probada y commiteada.

---

## 1. Visión General del Proyecto

**VotoSeguro v2** es una solución de voto electrónico auditada orientada a instituciones educativas, colegios de profesionales, sindicatos y asociaciones intermedias de Bolivia y Latinoamérica. 
Su diseño arquitectónico garantiza la integridad inquebrantable del proceso mediante:
- **Aislamiento Multi-Tenancy estricto** por organización (`organization_id`).
- **Anonimato absoluto del votante (Invariante #9):** Desvinculación criptográfica total entre la identidad del sufragante y la papeleta depositada (`vote` nunca almacena `voter_id`).
- **Autoridad temporal canónica (Invariante #6):** Todas las decisiones y transiciones de estado del ciclo electoral dependen exclusivamente del reloj de base de datos (`SELECT now() AT TIME ZONE 'UTC'`).
- **Auditoría inmutable (Append-Only):** Bitácora transaccional blindada a nivel de PostgreSQL contra cualquier intento de modificación o eliminación (`prevent_audit_log_mutation()`).

---

## 2. Historias de Usuario Implementadas en la Iteración 1

| Historia | Prioridad | Denominación | Estado | Descripción Funcional y Técnica |
| :--- | :---: | :--- | :---: | :--- |
| **S1-00** | **Must** | Configuración de Monorepo, Docker, DB y CI | **100%** | Estructura de monorepo con `pnpm` workspaces y Python venv/uv. Orquestación de contenedores con `docker-compose.yml` (5 servicios: postgres, api, scheduler, web, mailpit), configuración para despliegue en Render (`render.yaml`), soporte SPA para Cloudflare Pages (`public/_redirects`), primitivas criptográficas (`VoteCodec`, `Nullifier`) y **el 100% de los modelos ORM de las 20 tablas** con su migración inicial Alembic (`0001_initial_sprint1_schema.py`). |
| **S1-01** | **Must** | Autenticación JWT, Multi-Tenancy y Organizaciones | **100%** | Creación y administración de instituciones (tenants) por `PLATFORM_ADMIN`. Autenticación con JWT (HMAC-SHA256) y hash de contraseñas con Argon2 (con fallback automático a bcrypt). Bloqueo de seguridad por fuerza bruta tras 5 intentos fallidos durante 15 minutos (retornando cabecera HTTP `Retry-After`). Bitácora inmutable de auditoría (`audit_log`) con trigger PostgreSQL. |
| **S1-02** | **Must** | Elección, Cronograma Editable y Scheduler Autónomo | **100%** | CRUD integral de Elecciones y motor de cronograma con soporte de zonas horarias IANA (`America/La_Paz`). Matriz de reglas de edición estricta con registro de motivo humano obligatorio (`schedule_change`). Acción de override `"Abrir registro ahora"`. **Scheduler autónomo idempotente** (`APScheduler` cada 10s) con lock distribuido transaccional (`pg_try_advisory_xact_lock(849201)`) y reloj de BD. |
| **S1-11** | **Should** | Delegación de Administradores de Solo Lectura (`ADMIN_SEGMENT`) | **100%** | Creación y gestión de usuarios administradores con alcance restringido a un grupo institucional (`group_id`) o a un nodo del árbol jerárquico (`node_id`). |
| **S1-12** | **Should** | Solicitud Pública de Elección por Instituciones | **100%** | Formulario público institucional en Landing Page para solicitar la provisión de una elección. Flujo de radicación y consola de revisión, aprobación y rechazo exclusivo para el `PLATFORM_ADMIN`. |

---

## 3. Estructura de Archivos del Proyecto

```text
votoseguro/
├── docker-compose.yml                      # Orquestación de desarrollo local (Postgres, API, Worker, Web, Mailpit)
├── render.yaml                             # Definición de infraestructura como código (IaC) para Render
├── pnpm-workspace.yaml                     # Configuración de workspaces frontend/paquetes
├── package.json                            # Scripts raíz y configuración global
├── .env.example                            # Plantilla documentada de variables de entorno
├── .gitignore                              # Reglas de exclusión para Python, Node, temporales y credenciales
├── docs/
│   ├── DECISIONES.md                       # Decisiones de Arquitectura de Software (ADR 001 - 005)
│   └── PROGRESO.md                         # Cuadro de mando y seguimiento de historias del Sprint 1
├── packages/
│   └── api-client/                         # Paquete compartido de tipos TypeScript y contratos DTO
│       ├── package.json
│       └── src/
│           └── index.ts
├── apps/
│   ├── api/                                # Backend en FastAPI + SQLAlchemy 2.0 + Alembic
│   │   ├── pyproject.toml / requirements.txt
│   │   ├── Dockerfile
│   │   ├── alembic.ini
│   │   ├── alembic/
│   │   │   ├── env.py
│   │   │   └── versions/
│   │   │       └── 0001_initial_sprint1_schema.py # Migración DDL de las 20 tablas + extensiones + triggers
│   │   ├── app/
│   │   │   ├── main.py                     # Entrypoint FastAPI, lifespan, CORS, seed idempotente
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
│   │   │   │       ├── user.py             # app_user, admin_delegation
│   │   │   │       ├── election.py         # election, schedule_change
│   │   │   │       ├── structure.py        # group, hierarchy_node, contest, contest_filter, candidate
│   │   │   │       ├── voter.py            # voter, voter_group, registration_link
│   │   │   │       ├── voting.py           # vote, ballot_nullifier, tally_result
│   │   │   │       └── audit.py            # audit_log, verification_token
│   │   │   ├── crypto/
│   │   │   │   ├── nullifier.py            # Nullifiers ciegos con HMAC-SHA256
│   │   │   │   ├── vote_codec.py           # Codec de votos (Plano / Paillier homomórfico)
│   │   │   │   └── hashing.py              # SHA-256 canónico y encadenamiento de hashes
│   │   │   └── modules/
│   │   │       ├── auth/                   # Login, perfil, bloqueo fuerza bruta
│   │   │       ├── audit/                  # Consulta y registro de bitácora
│   │   │       ├── organizations/          # Gestión de tenants y solicitudes de elección
│   │   │       ├── admins/                 # Delegación de ADMIN_SEGMENT
│   │   │       ├── elections/              # CRUD de elección, validador de fechas y cambios
│   │   │       └── scheduler/              # APScheduler worker con lock de PostgreSQL
│   │   └── tests/                          # Suite de pruebas automatizadas
│   │       ├── conftest.py                 # Fixtures async y Mock TimeProvider
│   │       ├── test_tenancy_isolation.py   # Verificación de aislamiento multi-tenant
│   │       ├── test_auth_lockout.py        # Verificación de bloqueo tras 5 intentos
│   │       ├── test_schedule_rules.py      # Verificación de reglas de edición de cronograma
│   │       └── test_scheduler_transitions.py # Transiciones temporales deterministas
│   └── web/                                # Frontend en React 18 + Vite + TypeScript + Tailwind
│       ├── package.json / vite.config.ts / tailwind.config.js / tsconfig.json
│       ├── public/
│       │   ├── _redirects                  # Configuración de rewrite para Cloudflare Pages
│       │   └── shield-check.svg            # Favicon e isotipo institucional
│       └── src/
│           ├── main.tsx / App.tsx / index.css
│           ├── lib/
│           │   ├── api.ts                  # Cliente HTTP Axios configurado con interceptores
│           │   ├── auth-store.ts           # Store reactivo de autenticación y sesión
│           │   └── timezone.ts             # Utilidades de conversión y formateo de fechas
│           ├── components/
│           │   ├── layout/
│           │   │   ├── TopSecurityBanner.tsx     # Barra superior criptográfica y de estado
│           │   │   └── InstitutionalShell.tsx    # Layout institucional con navegación por rol
│           │   └── electoral/
│           │       ├── ElectionStateStepper.tsx  # Línea de tiempo visual del ciclo de vida
│           │       ├── PhaseCountdownClock.tsx   # Cuenta regresiva sincronizada
│           │       ├── CryptographicHashBadge.tsx # Visualizador de hashes SHA-256 truncados/copiables
│           │       ├── SealStatusStamp.tsx       # Sellos digitales de cera según fase electoral
│           │       ├── ScheduleEditModal.tsx     # Modal con justificación obligatoria
│           │       └── ScheduleAuditTimeline.tsx # Registro histórico de alteraciones de fecha
│           └── pages/
│               ├── PublicLandingRequestPage.tsx  # Portal público con formulario institucional
│               ├── LoginPage.tsx                 # Login con contador de intentos y bloqueo
│               ├── PlatformAdminConsolePage.tsx  # Consola del Administrador de la Plataforma
│               ├── ElectionWorkspacePage.tsx     # Panel de gestión de elección
│               ├── ScheduleControlPanelPage.tsx  # Centro de control del cronograma electoral
│               └── DelegateAdminsPage.tsx        # Administración de administradores segmentados
```

---

## 4. Detalle Técnico de la Base de Datos

Se modelaron en SQLAlchemy 2.0 y migraron en Alembic (`0001_initial_sprint1_schema.py`) **las 20 tablas** requeridas para el Sprint 1:

1. **Extensiones habilitadas:** `pgcrypto`, `pg_trgm`, `fuzzystrmatch`.
2. **Tablas Nucleares:**
   - `organization`: Identificador de tenant, slug, nombre y metadatos.
   - `election_request`: Solicitudes públicas de instituciones con estados `PENDING`, `APPROVED`, `REJECTED`.
   - `app_user`: Usuarios de plataforma (`PLATFORM_ADMIN`, `ADMIN_GENERAL`, `ADMIN_SEGMENT`, `VOTER`) con contadores de fuerza bruta (`failed_attempts`, `locked_until`).
   - `admin_delegation`: Restricción de alcance de `ADMIN_SEGMENT` a un `group_id` o `node_id`.
   - `election`: Entidad central con máquina de 7 estados (`DRAFT`, `REGISTRATION_OPEN`, `REGISTRATION_CLOSED`, `VOTING_OPEN`, `VOTING_CLOSED`, `TALLYING`, `RESULTS_PUBLISHED`), 4 marcas de tiempo IANA (`registration_opens_at`, `registration_closes_at`, `voting_opens_at`, `voting_closes_at`), y sellos criptográficos (`config_hash`, `roll_hash`, `tally_hash`).
   - `schedule_change`: Bitácora obligatoria de mutaciones de fecha con motivo humano explícito y diffs JSON.
   - `group`: Agrupaciones de votantes por elección.
   - `hierarchy_node`: Árbol jerárquico organizacional con ruta materializada (`materialized_path`).
   - `contest`: Cargos en disputa por elección.
   - `contest_filter`: Filtros de elegibilidad por cargo (por grupo o nodo).
   - `candidate`: Candidatos postulados a cargos con orden de papeleta y foto.
   - `voter`: Padrón electoral con documento de identidad y token de activación.
   - `voter_group`: Relación muchos a muchos entre votantes y grupos.
   - `registration_link`: Enlaces seguros de registro público para auto-empadronamiento.
   - `vote` (**Invariante #9**): Depósito ciego de votos. **Carece estrictamente de columna `voter_id`**. Solo contiene `receipt_hash`, `encrypted_payload` y `created_at` truncado al minuto.
   - `ballot_nullifier`: Token derivado con HMAC-SHA256 para prevenir el doble voto sin revelar la papeleta.
   - `tally_result`: Resultados de escrutinio con soporte de anonimato $k$.
   - `audit_log`: Registro transaccional append-only blindado por trigger contra `UPDATE` o `DELETE`.
   - `verification_token`: Tokens de auditoría pública individual para comprobación de recepción de voto.
3. **Trigger de Inmutabilidad:**
   ```sql
   CREATE OR REPLACE FUNCTION prevent_audit_log_mutation()
   RETURNS TRIGGER AS $$
   BEGIN
       RAISE EXCEPTION 'audit_log es inmutable y estrictamente append-only.';
   END;
   $$ LANGUAGE plpgsql;

   CREATE TRIGGER trg_audit_log_immutable
   BEFORE UPDATE OR DELETE ON audit_log
   FOR EACH ROW EXECUTE FUNCTION prevent_audit_log_mutation();
   ```

---

## 5. Criptografía y Seguridad Implementada

1. **Protección de Credenciales:** Hasheo de contraseñas con **Argon2id** (mediante `pwdlib[argon2]`), con fallback automático y seguro a **bcrypt**.
2. **Prevención de Fuerza Bruta:** Bloqueo automático de cuentas tras **5 intentos fallidos consecutivos** durante un periodo de **15 minutos**. Las respuestas HTTP 403 incluyen la cabecera estándar `Retry-After: 900`.
3. **Blindaje de Voto (Invariante #9):**
   - La papeleta (`vote`) se desacopla por completo del votante.
   - El `Nullifier` se calcula como $\text{HMAC-SHA256}(\text{voter\_id}, \text{election\_salt})$, asegurando que un votante solo pueda sufragar una única vez sin revelar cuál voto le corresponde.
   - La fecha de depósito del voto se trunca al minuto (`date_trunc('minute', now())`) para evitar ataques de correlación temporal con los logs de acceso.
4. **Autoridad Temporal (Invariante #6):**
   - El reloj oficial del sistema reside en PostgreSQL (`DatabaseTimeProvider` con `SELECT now() AT TIME ZONE 'UTC'`). El servidor de aplicaciones nunca confía en el reloj de su propio sistema operativo.
   - En entorno de pruebas se utiliza `FakeTimeProvider` para adelantar o atrasar el tiempo de forma determinista y auditable.

---

## 6. Motor de Cronograma y Scheduler Autónomo

1. **Matriz de Reglas de Modificación (§5.3 y §5.4):**
   - Las 4 fechas deben cumplir la estricta precedencia cronológica:
     $$\text{registration\_opens\_at} < \text{registration\_closes\_at} \le \text{voting\_opens\_at} < \text{voting\_closes\_at}$$
   - En estado `DRAFT`: Todas las fechas pueden ser editadas libremente.
   - En estado `REGISTRATION_OPEN`: No se puede modificar `registration_opens_at`. Se pueden prorrogar las fechas futuras.
   - En estado `VOTING_OPEN`: **Únicamente** se permite modificar `voting_closes_at`, la cual debe ser mayor o igual a $now + 5\text{ minutos}$. Se rechaza cualquier intento de modificar las tres fechas previas.
   - En estados cerrados (`VOTING_CLOSED`, `TALLYING`, `RESULTS_PUBLISHED`): El cronograma queda estrictamente congelado.
   - Cualquier alteración requiere obligatoriamente un campo `reason` de al menos 10 caracteres y genera un registro inmutable en `schedule_change`.
2. **Acción "Abrir registro ahora":** Permite al administrador adelantar la apertura de registro al instante actual, respetando las demás restricciones.
3. **Scheduler Autónomo Idempotente:**
   - Servicio periódico (`APScheduler`) ejecutado cada 10 segundos.
   - Utiliza bloqueo consultivo transaccional de PostgreSQL (`pg_try_advisory_xact_lock(849201)`), lo que permite que múltiples instancias de la API o trabajadores coexistan sin generar condiciones de carrera (*race conditions*).
   - Realiza las transiciones de estado de forma atómica y audita cada cambio en `audit_log`.

---

## 7. Sistema de Diseño y Frontend

El frontend fue desarrollado bajo el concepto **"Soberanía Cívica Criptográfica"**, enfocado en transmitir la máxima autoridad formal, seriedad jurídica y transparencia matemática:

- **Tipografías:**
  - *Fraunces* (Serif display): Para títulos formales, encabezados de actas y nombres institucionales.
  - *Plus Jakarta Sans* (Sans-serif funcional): Para controles de formulario, tablas de datos y paneles de lectura ágil.
  - *JetBrains Mono* (Monoespaciada): Para hashes criptográficos SHA-256, tokens, nullifiers y marcas temporales.
- **Paleta de Colores Cívica:**
  - `civic-navy`: Azul profundo institucional de fondo y marcos de seguridad.
  - `ballot-ivory`: Fondo claro tipo papel de voto para contraste de alta legibilidad.
  - `seal-emerald`: Aprobaciones, fases abiertas y firmas válidas.
  - `seal-amber`: Fases de advertencia, conteo regresivo próximo y estados pendientes.
  - `seal-crimson`: Bloqueos, estados congelados y rechazos de auditoría.
- **Componentes Especializados:**
  - `TopSecurityBanner`: Muestra en todo momento el tenant activo, el reloj del servidor y el estado de la conexión segura.
  - `ElectionStateStepper`: Representación interactiva de las 7 fases del ciclo electoral.
  - `PhaseCountdownClock`: Cronómetro visual con advertencia de urgencia y cálculo de tiempo restante.
  - `CryptographicHashBadge`: Insignia que formatea y permite la copia rápida de hashes criptográficos.
  - `SealStatusStamp`: Sello digital tipo cera electoral con inclinación y borde dentado.
  - `ScheduleEditModal`: Diálogo con validación reactiva de fechas y obligatoriedad de justificación.
  - `ScheduleAuditTimeline`: Línea de tiempo histórica de modificaciones de cronograma.
- **Compilación Verificada:**
  - Construcción de producción ejecutada con éxito (`pnpm --filter @votoseguro/web build`) en **3.09s**, generando un bundle optimizado de 283.33 kB JS y 24.80 kB CSS.

---

## 8. Verificación y Pruebas Automatizadas

Se construyó una suite de pruebas de invariantes con `pytest` y `pytest-asyncio` en `apps/api/tests/`:

```bash
$env:PYTHONPATH="votoseguro/apps/api"
.\votoseguro\apps\api\.venv\Scripts\python -m pytest votoseguro/apps/api/tests
```

**Resultado de ejecución:**
```text
================================ 5 passed in 1.01s =================================
```

1. `test_tenancy_isolation.py`: Comprueba que un administrador de la Organización A no puede listar ni acceder a recursos o elecciones de la Organización B.
2. `test_auth_lockout.py`: Comprueba que tras 5 intentos fallidos con contraseña errónea, la cuenta se bloquea por 15 minutos rechazando el 6to intento con HTTP 403 y `Retry-After`.
3. `test_schedule_rules.py`: Comprueba el rechazo de órdenes de fechas inválidos y el rechazo estricto de modificación de fechas de registro una vez iniciada la votación (`VOTING_OPEN`).
4. `test_scheduler_transitions.py`: Comprueba que al avanzar el reloj con `FakeTimeProvider`, el servicio transiciona automáticamente de `DRAFT` a `REGISTRATION_OPEN` y registra la auditoría.

---

## 9. Control de Versiones

El código se encuentra resguardado en el repositorio Git local:
- **Directorio:** `c:\Users\Ale\Documents\SW1 2-2026\PROYECTO GRUPAL\votoseguro`
- **Commit Inicial:** `2025f4e`
- **Mensaje:** `feat: initial architecture sprint 1 v1.0 (s1-00, s1-01, s1-02, s1-11, s1-12)`
- **Archivos Rastreados:** 85 archivos fuente limpios (sin artefactos de compilación ni dependencias pesadas).

---

## 10. Hoja de Ruta Inmediata (Iteración 2 del Sprint 1)

Una vez provistas las credenciales de despliegue en la nube, se dará inicio a la **Iteración 2**:

1. **S1-03:** Grupos, jerarquías dinámicas y árbol de nodos con ruta materializada (`materialized_path`) e importador CSV.
2. **S1-04:** Cargos en disputa (`contest`), circunscripciones y filtros extra de elegibilidad con generación automática de combinaciones.
3. **S1-05:** Gestión de candidatos por circunscripción con orden de papeleta y subida/validación de fotografías.
4. **S1-06:** Publicación de estructura electoral, congelamiento inmutable y cálculo del `config_hash` SHA-256 canónico.
