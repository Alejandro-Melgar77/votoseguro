# VotoSeguro v2 — Resumen Ejecutivo de Implementación (Sprint 1 Completo & Sprint 2 Fase 1 Completa)

**Plataforma SaaS Multi-Institución de Votación Electrónica Auditada**  
**Asignatura:** Ingeniería de Software I (INF 422 SB) — UAGRM  
**Fecha de corte:** 11 de Noviembre de 2026  
**Estado:**
- **Sprint 1 (100% Completo — 14/14 historias de usuario):** Infraestructura, Tenancy, Jerarquías Dinámicas, Papeleta, Voto Ciego Atómico, Nullifiers Ciegos, Escrutinio con $k$-Anonimato y Sembrador Demo.
- **Sprint 2 — Fase 1 de 2 (100% Completo — 10/10 requisitos y Spike Criptográfico):**
  - **S2-02 (Must — 5 pts):** Cadena de Hashes en Votos (`prev_hash`, `vote_hash`, bloque génesis por elección y verificación integral de urna).
  - **S2-03 (Must — 3 pts):** Verificación Pública de Comprobante de Voto con prueba de posición en cadena y secreto absoluto.
  - **S2-05 (Must — 3 pts):** Cadena de Hashes en Bitácora de Auditoría y registro unificado de eventos de IA (`log_ai_call`).
  - **S2-07 (Should — 5 pts):** Árbol de Merkle del Padrón Electoral (`merkle_root`), generación de pruebas logarítmicas de inclusión y verificador criptográfico sin exponer el censo.
  - **S2-04 (Must — 5 pts):** Dashboard de Monitoreo en Tiempo Real con WebSockets (`/live`), métricas por hora, participación segmentada y respeto estricto de la Invariante #11.
  - **S2-06 (Must — 3 pts):** Rate Limiting por IP y ruta crítica contra fuerza bruta y DoS con `slowapi` (HTTP 429).
  - **S2-08 (Should — 3 pts):** Motor Oficial de Exportación a PDF (`reportlab`) y Excel (`openpyxl`) para Resultados ($k$-anonimato), Participación y Auditoría.
  - **S2-09 (Should — 2 pts):** Notificación por Correo de Reprogramaciones de Cronograma con bandeja de salida `notification_outbox` y fallback `aiosmtplib`.
  - **S2-10 (Could — 3 pts):** Portal Público de Autoinscripción (`OPEN_WITH_APPROVAL`) con bandeja de aprobación/rechazo para el Administrador General.
  - **Spike Paillier (Obligatorio Sprint 2):** Motor funcional de Cifrado Homomórfico Aditivo (`phe`) con adición homomórfica en urna agrupada por circunscripción/segmento y benchmark de rendimiento.
- **Calidad y Verificación:** **21 de 21 pruebas automatizadas pasando en `pytest` (100% de éxito)** y compilación de producción en Vite + TypeScript con **0 errores**.

---

## 1. Visión General del Proyecto

**VotoSeguro v2** es una plataforma integral de voto electrónico verificable, transparente y auditada, diseñada para instituciones de educación superior, colegios de profesionales, cooperativas y asociaciones civiles de Bolivia y Latinoamérica.

Su diseño arquitectónico garantiza la integridad soberana del proceso electoral mediante **Invariantes Electorales Criptográficas y de Dominio**:
- **Aislamiento Multi-Tenancy estricto** por organización (`organization_id`).
- **Anonimato absoluto del votante (Invariante #9):** Desvinculación criptográfica total entre la identidad del sufragante y la papeleta depositada (`vote` nunca almacena `voter_id`).
- **Nullifier Ciego por Circunscripción (Invariante #8):** Cálculo de $\text{HMAC-SHA256}(\text{secret}, \text{voter\_id} \mathbin{\Vert} \text{":"} \mathbin{\Vert} \text{constituency\_id})$ para garantizar un solo voto por cargo sin revelar identidad.
- **Congelamiento Estructural Post-Publicación (Invariante #3):** Una vez publicada solemnemente la elección (`DRAFT -> SCHEDULED`) y emitido el `config_hash` determinista (RFC 8785), cualquier mutación estructural es bloqueada con `HTTP 409 Conflict`.
- **Inmutabilidad Temporal del Padrón y Sellado Canónico (Invariante #5):** El padrón electoral únicamente admite modificaciones durante `REGISTRATION_OPEN`. Al cerrarse la fase, se calcula el `roll_hash` determinista (SHA-256) congelando el censo de votantes.
- **Árbol de Merkle de Inclusión Criptográfica (Invariante #18):** Al congelar el padrón, se calcula la raíz `merkle_root` sobre las hojas SHA-256 de los votantes habilitados. Cualquier ciudadano puede comprobar su inclusión mediante una prueba matemática $O(\log_2 N)$ sin exponer datos de otros electores.
- **Cadena de Hashes en Urna y Ledger de Votos (Invariante #19):** Cada voto emitido contiene `chain_index`, `prev_hash` y `vote_hash` canónico iniciado en un bloque génesis único por elección. Una alteración manual en BD rompe la cadena inmediatamente.
- **Cadena de Hashes en Bitácora de Auditoría (Invariante #20):** La bitácora transaccional es append-only mediante trigger de PostgreSQL (`trg_audit_log_immutable`) y encadena cada evento con SHA-256 (`entry_hash`).
- **Resultados Sellados hasta el Cierre (Invariante #11):** Cualquier consulta a resultados o cómputo antes de `VOTING_CLOSED` es bloqueada con `HTTP 403 Forbidden`. En WebSockets y dashboards en vivo, se transmiten métricas de participación pero cero conteos por candidato.
- **Privacidad y $k$-Anonimato en Desgloses (Invariante #12):** En desgloses por nivel territorial o filtros, las celdas con recuentos menores al umbral $k$ (`k_anonymity=5`) se ocultan o redactan (`< k` votos) tanto en pantalla como en reportes PDF/Excel.
- **Serialización Canónica del Voto (Invariante #13):** Uso de `VoteCodec` determinista tanto en voto plano como en homomórfico.
- **Truncamiento de Marcas Temporales (Invariante #17):** Los votos se estampan con marcas de tiempo truncadas al minuto para evitar ataques de correlación temporal con los registros de red.
- **Autoridad temporal canónica (Invariante #6):** Todas las decisiones y transiciones de estado dependen exclusivamente del reloj de base de datos (`SELECT now() AT TIME ZONE 'UTC'`).

---

## 2. Historias de Usuario Implementadas

### Sprint 1: Infraestructura, Estructura, Padrón, Voto Ciego y Escrutinio (14/14 — 100%)
- **S1-00 (Must — 5 pts):** Configuración de Monorepo, Docker, DB y CI.
- **S1-01 (Must — 8 pts):** Autenticación JWT, Multi-Tenancy y Organizaciones.
- **S1-02 (Must — 8 pts):** Elección, Cronograma Editable y Scheduler Autónomo.
- **S1-11 (Should — 3 pts):** Delegación de Administradores de Segmento (`ADMIN_SEGMENT`).
- **S1-12 (Should — 3 pts):** Solicitud Pública de Elección por Instituciones.
- **S1-03 (Must — 8 pts):** Grupos, Jerarquías Dinámicas y Árbol de Nodos.
- **S1-04 (Must — 5 pts):** Filtros Extra, Cargos y Circunscripciones.
- **S1-05 (Must — 5 pts):** Candidatos por Circunscripción y Estudio de Papeleta.
- **S1-06 (Must — 5 pts):** Ceremonia de Publicación y `config_hash` SHA-256 (RFC 8785).
- **S1-07 (Must — 8 pts):** Panel de Registro y Carga de Padrón Electoral.
- **IA-L2a (Should — 5 pts):** Detección de Duplicados y Arbitraje Humano.
- **S1-08 (Must — 6 pts):** Enlaces de Registro, Activación y `roll_hash`.
- **S1-09 (Must — 8 pts):** Credenciales, Papeleta Automática y Voto Ciego Atómico.
- **S1-10 (Must — 5 pts):** Escrutinio Oficial, Desgloses y $k$-Anonimato.
- **`seed:demo` (Must):** Sembrador autónomo de Universidad EL GRAN ESTUDIO y Elecciones Ecuador.

### Sprint 2 (Fase 1 de 2): Integridad Criptográfica, Merkle, WebSockets, Exportaciones & Spike Paillier (10/10 — 100%)
| Historia | Prioridad | Denominación | Puntos | Estado | Descripción Funcional y Técnica |
| :--- | :---: | :--- | :---: | :---: | :--- |
| **S2-02** | **Must** | Cadena de Hashes en Votos y Verificación Integral de Urna | 5 pts | **100%** | Cada voto en `vote` incorpora `chain_index`, `prev_hash` y `vote_hash` canónico. Bloque génesis calculado con SHA-256 ligado al `config_hash` de la elección. Bloqueo atómico `FOR UPDATE` sobre `election` durante la emisión. Endpoint `GET /api/v1/elections/{id}/integrity/votes` que audita bloque por bloque y detecta cualquier alteración en base de datos. |
| **S2-03** | **Must** | Verificación Pública Mejorada de Comprobante | 3 pts | **100%** | Endpoint público `GET /api/v1/receipts/{receipt_hash}` y página web `/verify-receipt` que certifica la incorporación del voto en la urna, su posición `chain_index`, `prev_hash` y `vote_hash` en la cadena, garantizando el secreto del sufragio sin revelar jamás la opción o candidato votado. |
| **S2-05** | **Must** | Cadena de Hashes en Bitácora y Registro Unificado de IA | 3 pts | **100%** | Encadenamiento SHA-256 en `audit_log` (`chain_index`, `prev_hash`, `entry_hash`) protegido por trigger PostgreSQL. Método `log_ai_call()` para registrar inferencias de IA en la tabla `ai_call_log` y en la bitácora inmutable. Endpoint de verificación `GET /api/v1/elections/{id}/integrity/audit`. |
| **S2-07** | **Should** | Árbol de Merkle del Padrón y Pruebas de Inclusión | 5 pts | **100%** | Módulo criptográfico `app/crypto/merkle.py`. Al pasar a `REGISTRATION_CLOSED`, se calcula `merkle_root` sobre las hojas canónicas de votantes activos. Endpoint `GET /api/v1/elections/{id}/merkle/proof/{document_id}` genera el camino de hermanos $O(\log_2 N)$. Endpoint `POST /api/v1/elections/{id}/merkle/verify` valida matemáticamente la inclusión del elector sin exponer el padrón. |
| **S2-04** | **Must** | Dashboard en Vivo con WebSockets y Métricas por Hora | 5 pts | **100%** | Conexión WebSocket `WS /api/v1/elections/{id}/live` con fallback a `GET /live-metrics`. Monitoreo en tiempo real de avance del registro, participación por estamento/segmento jerárquico y curva de votos por hora (`hourly_votes_series`). Respeta estrictamente el alcance de `ADMIN_SEGMENT` y la **Invariante #11** (cero conteos parciales por opción). |
| **S2-06** | **Must** | Rate Limiting contra Fuerza Bruta y DoS | 3 pts | **100%** | Integración de `slowapi` con límites estrictos por IP en rutas críticas (login: 5/min, emisión de voto: 30/min, generación de pruebas Merkle: 60/min). Retorna HTTP 429 con cabecera `Retry-After` y registra excesos en la bitácora de auditoría. |
| **S2-08** | **Should** | Motor Oficial de Exportación a PDF y Excel | 3 pts | **100%** | Módulo `app/modules/exports/` con generación de documentos en memoria (`BytesIO`). Exportación en PDF profesional (`reportlab`) y hojas de cálculo Excel (`openpyxl`) para: 1) Acta Oficial de Resultados con sellos criptográficos y $k$-anonimato; 2) Padrón y Participación Electoral; 3) Bitácora Completa de Auditoría. |
| **S2-09** | **Should** | Notificación por Correo de Reprogramaciones y Outbox | 2 pts | **100%** | Al modificar el cronograma (`PUT /elections/{id}/schedule`), se despacha automáticamente una notificación por correo a todos los votantes registrados en estado `ACTIVE`. Soporte de envío SMTP (`aiosmtplib`) y almacenamiento en bandeja persistente `notification_outbox` (`delivery_status: SENT_SMTP | STORED_DEMO_OUTBOX | FAILED`) consultable desde la UI. |
| **S2-10** | **Could** | Autoinscripción Ciudadana con Aprobación Administrativa | 3 pts | **100%** | Soporte de modo de elección `OPEN_WITH_APPROVAL`. Endpoint público `POST /api/v1/public/elections/{id}/self-register` que registra votantes en estado `PENDING_APPROVAL`. Bandeja de gestión para el `ADMIN_GENERAL` con aprobación (`POST /voters/{id}/approve`) y rechazo con causal formal (`POST /voters/{id}/reject`). |
| **Spike Paillier** | **Obligatorio** | Spike de Cifrado Homomórfico Aditivo (Paillier) | — | **100%** | Motor `app/crypto/paillier_spike.py` basado en `phe`. Cifrado asimétrico de papeletas vectoriales, suma homomórfica de cifrados en urna agrupada por circunscripción y prefijo de segmento, y descifrado final verificado. Endpoint de benchmark `POST /api/v1/crypto/paillier-spike-benchmark` con medición de latencias y confirmación de equivalencia matemática: $\text{Decrypt}(\prod E(v_i)) = \sum v_i$. |

---

## 3. Estructura de Archivos del Proyecto

```text
votoseguro/
├── README.md                               # Documentación general del repositorio
├── resumen.md                              # Resumen ejecutivo de implementación sincronizado
├── docker-compose.yml                      # Orquestación de contenedores locales
├── render.yaml                             # IaC para Render (FastAPI + Worker)
├── pnpm-workspace.yaml                     # Workspaces frontend y contratos
├── package.json                            # Scripts raíz
├── packages/
│   └── api-client/                         # Paquete de contratos TypeScript y DTOs
│       ├── package.json / tsconfig.json
│       └── src/index.ts                    # DTOs de Integridad, Merkle, Realtime, Exportaciones y Paillier
├── apps/
│   ├── api/                                # Backend en FastAPI + SQLAlchemy + Alembic
│   │   ├── alembic/
│   │   │   └── versions/
│   │   │       ├── 0001_initial_sprint1_schema.py
│   │   │       ├── 0002_iter2_reconcile.py
│   │   │       ├── 0003_iter3_voting.py
│   │   │       └── 0004_sprint2_integrity_realtime_exports.py # Migración Sprint 2 (Merkle, Chains, Outbox)
│   │   ├── app/
│   │   │   ├── core/
│   │   │   │   ├── rate_limit.py           # SlowAPI Limiter, middleware y manejadores 429
│   │   │   │   ├── config.py / security.py / dependencies.py
│   │   │   ├── crypto/
│   │   │   │   ├── merkle.py               # Árbol de Merkle determinista y pruebas de inclusión
│   │   │   │   ├── paillier_spike.py       # Motor de Cifrado Homomórfico Paillier y Benchmark
│   │   │   │   ├── hashing.py / nullifier.py / vote_codec.py
│   │   │   ├── db/models/
│   │   │   │   ├── election.py             # merkle_root, registration_mode, votes_chain_head
│   │   │   │   ├── voter.py                # PENDING_APPROVAL, rejection_reason, reviewed_by
│   │   │   │   ├── voting.py               # chain_index, prev_hash, vote_hash
│   │   │   │   ├── audit.py                # chain_index, prev_hash, entry_hash
│   │   │   │   └── notification.py         # notification_outbox (S2-09)
│   │   │   └── modules/
│   │   │       ├── integrity/              # Verificación de cadenas de votos, auditoría, Merkle y Paillier
│   │   │       ├── realtime/               # WebSockets (/live), métricas en vivo y series por hora
│   │   │       ├── exports/                # Generador en memoria de PDF (ReportLab) y Excel (OpenPyXL)
│   │   │       ├── notifications/          # Despachador de correos de cronograma y bandeja outbox
│   │   │       ├── registration/           # Autoinscripción pública y aprobación/rechazo
│   │   │       └── ballots/ / results/ / scheduler/ / structure/ / voters/
│   │   └── tests/                          # Suite completa de pruebas (21 tests automatizados)
│   │       ├── test_vote_and_audit_hash_chains.py          # Verificación de cadenas y detección de manipulación
│   │       ├── test_merkle_tree_and_inclusion_proof.py      # Árbol de Merkle, prueba de inclusión y validación
│   │       ├── test_realtime_dashboard_and_exports.py       # WebSockets, métricas en vivo, Invariante #11 y exports
│   │       ├── test_rate_limiting_notifications_and_self_reg.py # SlowAPI, correos y autoinscripción con aprobación
│   │       ├── test_paillier_homomorphic_spike.py           # Equivalencia homomórfica y benchmark Paillier
│   │       └── [15 tests automatizados del Sprint 1]
│   └── web/                                # Frontend React 18 + Vite + TypeScript + Tailwind
│       └── src/
│           ├── pages/
│           │   ├── LiveMonitoringDashboardPage.tsx       # Monitoreo en vivo WebSockets + gráfico de votos/hora
│           │   ├── CryptographicIntegrityCenterPage.tsx  # Centro de Cadenas de Hash, Árbol Merkle y Spike Paillier
│           │   ├── PublicReceiptVerifierPage.tsx         # Verificador público de comprobantes electorales
│           │   ├── PublicSelfRegistrationPage.tsx        # Portal público de autoinscripción ciudadana
│           │   ├── VoterRollRegistrationPanelPage.tsx    # Padrón + bandeja de aprobación de autoinscripciones
│           │   ├── ScheduleControlPanelPage.tsx          # Cronograma + bandeja outbox de correos
│           │   ├── ElectionResultsTallyPage.tsx          # Cómputo oficial + descargas de PDF y Excel
│           │   └── [Otras páginas del workspace institucional]
│           └── components/layout/InstitutionalShell.tsx  # Enlaces de navegación con Centro de Integridad y Live
```

---

## 4. Detalle de Pruebas Automatizadas (21 de 21 Pasando — 100%)

La suite completa de pruebas se ejecuta mediante `pytest` sobre SQLite en memoria y PostgreSQL:

```powershell
cd votoseguro/apps/api
.\.venv\Scripts\python.exe -m pytest
```

**Resultado de ejecución:**
```text
============================= test session starts =============================
platform win32 -- Python 3.14.0, pytest-9.2.0, pluggy-1.7.0
rootdir: C:\Users\Ale\Documents\SW1 2-2026\PROYECTO GRUPAL\votoseguro\apps\api
configfile: pyproject.toml
testpaths: tests
plugins: anyio-4.16.0, asyncio-1.4.1.post1
collected 21 items

tests\test_auth_lockout.py .                                             [  4%]
tests\test_automatic_ballot_and_atomic_cast.py .                         [  9%]
tests\test_hierarchy_and_contests.py ..                                  [ 19%]
tests\test_merkle_tree_and_inclusion_proof.py .                          [ 23%]
tests\test_paillier_homomorphic_spike.py ..                              [ 33%]
tests\test_publication_and_immutability.py .                             [ 38%]
tests\test_rate_limiting_notifications_and_self_reg.py .                 [ 42%]
tests\test_realtime_dashboard_and_exports.py .                           [ 47%]
tests\test_registration_links_and_roll_hash.py .                         [ 52%]
tests\test_results_and_k_anonymity.py .                                  [ 57%]
tests\test_schedule_rules.py ..                                          [ 66%]
tests\test_scheduler_transitions.py .                                    [ 71%]
tests\test_seed_demo.py ..                                               [ 80%]
tests\test_tenancy_isolation.py .                                        [ 85%]
tests\test_vote_and_audit_hash_chains.py .                               [ 90%]
tests\test_voter_roll_and_duplicates.py ..                               [100%]
======================= 21 passed, 13 warnings in 4.90s =======================
```

---

## 5. Compilación del Frontend en Producción

El frontend web se compila sin errores de tipos TypeScript ni advertencias bloqueantes:

```powershell
cd votoseguro/apps/web
pnpm --filter @votoseguro/web build
```

**Resultado de ejecución:**
```text
$ tsc && vite build
vite v5.4.21 building for production...
transforming...
✓ 1650 modules transformed.
rendering chunks...
computing gzip size...
dist/index.html                   1.09 kB │ gzip:   0.62 kB
dist/assets/index-DL2ifWvO.css   43.92 kB │ gzip:   7.64 kB
dist/assets/index-CotvPEhp.js   543.17 kB │ gzip: 128.15 kB
✓ built in 2.92s
```

---

## 6. Control de Versiones e Historial de Commits

El repositorio se encuentra alojado en GitHub:
- **URL:** [https://github.com/Alejandro-Melgar77/votoseguro](https://github.com/Alejandro-Melgar77/votoseguro)
- **Rama:** `main`

### Historial de Commits Principales:
1. `2025f4e`: `feat: initial architecture sprint 1 v1.0 (s1-00, s1-01, s1-02, s1-11, s1-12)`
2. `e95e25a`: `feat(sprint-1): complete iteration 2 - electoral structure, candidate ballot studio, publication config hash, voter roll and duplicate detection`
3. `e575e80`: `fase 2 sprint 1`
4. `a9b1c0e`: `feat(sprint-1): complete phase 3 v1.0 - voter activation links, automatic ballot, atomic blind voting, k-anonymity tally and seed demo`
5. `feat(sprint-2): complete phase 1 v2.0 - vote & audit hash chains, merkle tree proofs, live websocket dashboard, pdf/xlsx exports, rate limiting, schedule notifications and paillier spike`

---

## 7. Guía de Demostración y Verificación de Nuevas Capacidades (Sprint 2 Fase 1)

1. **Centro de Integridad Criptográfica (`/elections/:id/integrity`):**
   - **Cadena de Votos:** Presionar *"Ejecutar Verificación Completa"*. Comprueba que todos los votos emitidos forman una cadena ininterrumpida de hashes SHA-256 desde el bloque génesis. Si se altera un voto directamente en base de datos, el verificador marca la urna como comprometida indicando el índice exacto de ruptura.
   - **Cadena de Auditoría:** Verifica la bitácora inmutable encadenada de eventos de auditoría y llamadas a IA.
   - **Explorador del Árbol de Merkle:** Ingresar una cédula de identidad (CI) de un votante activo. El sistema genera la prueba de inclusión logarítmica y permite verificar con un clic la coincidencia matemática contra la raíz oficial (`merkle_root`) sin divulgar el resto del padrón.
   - **Laboratorio Homomórfico Paillier:** Seleccionar tamaño de clave (1024 o 2048 bits) y número de votos simulados. Ejecutar el benchmark y comprobar la insignia de equivalencia matemática exacta: $\text{Decrypt}(\prod E(v_i)) = \sum v_i$, junto con la tabla de tiempos de cifrado y adición homomórfica.
2. **Dashboard de Monitoreo en Tiempo Real (`/elections/:id/live`):**
   - Conectar mediante WebSockets para observar la actualización en tiempo real de participación ciudadana, desglose por estamentos/nodos y curva de votos por hora sin vulnerar la Invariante #11 (urnas selladas).
3. **Descarga de Reportes Oficiales en PDF y Excel:**
   - En `/elections/:id/results` o en el panel de monitoreo, presionar *"Acta Oficial PDF"* y *"Escrutinio Excel"*. El sistema genera y descarga al instante los documentos institucionales sellados criptográficamente y protegidos por $k$-anonimato.
4. **Verificación Universal de Comprobantes (`/verify-receipt`):**
   - Ingresar el hash de un recibo emitido al votar. El verificador demuestra de forma pública que el voto reside íntegro en la urna criptográfica sin divulgar la opción sufragada.
5. **Autoinscripción Pública con Aprobación (`/elections/:id/self-register`):**
   - En una elección configurada con modo `OPEN_WITH_APPROVAL`, un ciudadano envía su formulario de registro quedando en estado `PENDING_APPROVAL`.
   - El Administrador General accede a la pestaña *"Autoinscripciones S2-10"* en el padrón para aprobar o rechazar la solicitud con causal debidamente auditada.
