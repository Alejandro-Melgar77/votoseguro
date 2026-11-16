# VotoSeguro v2 — Resumen Ejecutivo y Técnico Oficial (Sprint 1, Sprint 2, Sprint 2.5 y Sprint 3 Parte 1 Completados al 100% — Release v3.0-P1)

**Plataforma SaaS Multi-Institución de Votación Electrónica Soberana y Auditada**  
**Asignatura:** Ingeniería de Software I (INF 422 SB) — UAGRM  
**Fecha de Entrega:** Noviembre de 2026  
**Versión de Release:** v3.0-P1 (Cierre Integral de Sprint 1, Sprint 2, Sprint 2.5 y Sprint 3 — Parte 1: Cifrado Homomórfico Paillier y Reparto de Secreto Shamir)

---

## 1. Estado Global del Proyecto

| Hito / Entrega | Alcance | Estado | Pruebas Automatizadas | Compilación |
| :--- | :---: | :---: | :---: | :---: |
| **Sprint 1 (v1.0)** | 14 Historias (56 pts Must + 8 pts Should) | **100% COMPLETO** | 15/15 tests pasando | 0 errores (Web) |
| **Sprint 2 — Fase 1 (v2.0-F1)** | 10 Historias + Spike Paillier (35 pts) | **100% COMPLETO** | 21/21 tests pasando | 0 errores (Web) |
| **Sprint 2 — Fase 2 (v2.0-F2)** | IA-L1 a IA-L5 + S2-01 Mobile (29 pts) | **100% COMPLETO** | 28/28 tests pasando | 0 errores (Web & Mobile) |
| **Sprint 2.5 (v2.5)** | LLM Local, Calibración LoRA, Túnel ngrok Estático y Puente 1-Clic | **100% COMPLETO** | 35/35 tests pasando | 0 errores (Web & Mobile) |
| **Sprint 3 — Parte 1 (v3.0-P1)** | Cifrado Homomórfico Paillier en Producción (S3-01) y Reparto de Clave Shamir $k$ de $n$ (S3-02) (18 pts) | **100% COMPLETO** | **43/43 tests pasando (100%)** | **0 errores (Backend, Web, Mobile)** |

---

## 2. Invariantes Electorales y Criptográficas Implementadas

1. **Aislamiento Multi-Tenancy Estricto (Invariante #1):** Separación lógica absoluta por organización (`organization_id`). Ningún actor ni consulta puede acceder a datos de otro tenant.
2. **Autoridad Temporal Canónica (Invariante #6):** Reloj centralizado gobernado por el motor de base de datos (`SELECT now() AT TIME ZONE 'UTC'`). Cero desfase por reloj de servidor de aplicación.
3. **Congelamiento Estructural Post-Publicación (Invariante #3):** Al transicionar de `DRAFT` a `SCHEDULED`, se calcula el hash determinista `config_hash` (RFC 8785 SHA-256). Toda mutación posterior en cargos, listas o circunscripciones queda prohibida con `HTTP 409 Conflict`.
4. **Inmutabilidad del Padrón y Sellado (Invariante #5):** El padrón electoral únicamente admite modificaciones en fase `REGISTRATION_OPEN`. Al pasar a `REGISTRATION_CLOSED`, se calcula el `roll_hash` canónico sellando el censo de votantes.
5. **Árbol de Merkle de Inclusión Criptográfica (Invariante #18 / S2-07):** Raíz `merkle_root` sobre las hojas SHA-256 de votantes activos. Cada elector puede auditar su inclusión logarítmica $O(\log_2 N)$ sin exponer el padrón.
6. **Cadena de Hashes en Urna y Ledger de Votos (Invariante #19 / S2-02):** Cada voto emitido contiene `chain_index`, `prev_hash` y `vote_hash` canónico iniciado en un bloque génesis único por elección. Una alteración manual en BD rompe la cadena inmediatamente.
7. **Verificación Pública de Comprobante (Invariante #9 / S2-03):** El `receipt_hash` certifica la incorporación inmutable del voto en la urna sin revelar jamás el sentido del sufragio.
8. **Nullifier Ciego por Circunscripción (Invariante #8):** Cálculo de $\text{HMAC-SHA256}(\text{secret}, \text{voter\_id} \mathbin{\Vert} \text{":"} \mathbin{\Vert} \text{constituency\_id})$ para garantizar un solo voto por cargo sin vincular identidad con papeleta.
9. **Desvinculación Criptográfica Total (Invariante #9):** La tabla `vote` jamás contiene la columna `voter_id` ni llaves foráneas hacia el elector.
10. **Resultados Herméticos hasta el Cierre (Invariante #11):** Cualquier consulta a resultados o cómputo antes de `VOTING_CLOSED` es bloqueada con `HTTP 403 Forbidden`. En WebSockets y dashboards en vivo, se transmiten métricas de participación pero cero conteos por candidato.
11. **Privacidad y $k$-Anonimato en Desgloses (Invariante #12):** En desgloses por nivel territorial o filtros, las celdas con recuentos menores al umbral $k$ (`k_anonymity=5`) se ocultan o redactan (`< k` votos) tanto en pantalla como en reportes PDF/Excel.
12. **Truncamiento de Marcas Temporales (Invariante #17):** Los votos se estampan con marcas de tiempo truncadas al minuto para evitar ataques de correlación temporal con los registros de red.
13. **Trazabilidad de IA sin Datos Personales (Invariante #14 / Salvaguarda #7):** Toda inferencia de IA registra en `ai_call_log` y en la cadena `audit_log` la función, modelo, duración y estado **estrictamente libre de CIs, nombres o votos**.
14. **Cero Persistencia de Imágenes de Cédula (Invariante #15 / IA-L3):** La aplicación móvil o web extrae texto OCR en el cliente y envía únicamente el texto plano al endpoint `/ai/id-card/extract`. No se almacenan imágenes en disco, S3 ni base de datos.
15. **Secreto de Intención en Cabina de Voz (Sección 7.3 / IA-L4):** La gramática de voz se procesa 100% de manera local y determinista en el dispositivo. Jamás se envían audios, intenciones ni selecciones al backend o al LLM.
16. **Cifrado Homomórfico Aditivo en Urna (Invariante #13 / RF-55 / S3-01):** Cada voto individual es cifrado asimétricamente como vector one-hot utilizando el criptosistema Paillier (`HomomorphicPaillierVoteCodec` vía `phe`). Los votos individuales jamás se descifran; el escrutinio se ejecuta multiplicando homomórficamente los cifrados ($\prod E(m_i) \pmod{n^2} = E(\sum m_i)$) en la base de datos y agregador.
17. **Custodia Distribuida de la Clave Privada con Shamir ($k$ de $n$) (Invariante #20 / S3-02):** La clave privada de Paillier $(p, q)$ jamás se guarda completa en disco ni en base de datos. Se fragmenta inmediatamente en $n$ custodios electorales (`ElectoralTrusteeShare`) y se purga de la memoria RAM. Se requiere un quórum de $k$ autoridades que provean sus fragmentos para reconstruir la clave mediante interpolación de Lagrange en el campo finito $\mathbb{F}_P$ tras el cierre de votación (`VOTING_CLOSED`).

---

## 3. Matriz de Requisitos Implementados

### 3.1 Sprint 1 (v1.0 — 14 Requisitos)
- `S1-00`: Monorepo, Docker, PostgreSQL + Alembic, extensiones criptográficas y de texto.
- `S1-01`: Autenticación JWT, Multi-Tenancy y Organizaciones con bloqueo por fuerza bruta.
- `S1-02`: Elección, Cronograma Editable y Scheduler Autónomo con reloj DB y locks transaccionales.
- `S1-03`: Grupos, Jerarquías Dinámicas y Árbol de Nodos con materialized path.
- `S1-04`: Filtros Extra, Cargos y Circunscripciones electorales autogeneradas.
- `S1-05`: Candidatos por Circunscripción, reordenamiento atómico y papeleta oficial con Blanco/Nulo.
- `S1-06`: Ceremonia de Publicación, validación de integridad y congelamiento con `config_hash`.
- `S1-07`: Panel de Registro y Carga de Padrón en fase `REGISTRATION_OPEN`.
- `IA-L2a`: Detección de posibles duplicados (pg_trgm + edit distance) con arbitraje humano.
- `S1-08`: Enlaces de Registro, Activación y Congelamiento canónico de padrón (`roll_hash`).
- `S1-09`: Credenciales secretas, Papeleta Automática y Voto Ciego Atómico en urna.
- `S1-10`: Escrutinio Oficial, Desgloses Jerárquicos y $k$-Anonimato riguroso.
- `S1-11`: Delegados de Segmento (`ADMIN_SEGMENT`) acotados territorialmente.
- `S1-12`: Solicitud Pública de Elección por Instituciones.

### 3.2 Sprint 2 — Fase 1 (v2.0-F1 — 10 Requisitos)
- `S2-02`: Cadena de Hashes en Votos (`prev_hash`, `vote_hash`, bloque génesis y verificación de urna).
- `S2-03`: Verificación Pública de Comprobante de Voto en `/receipts/{receipt_hash}`.
- `S2-05`: Cadena de Hashes en Bitácora de Auditoría inmutable con triggers y registro unificado.
- `S2-07`: Árbol de Merkle del Padrón (`merkle_root`), pruebas de inclusión $O(\log_2 N)$ y verificador.
- `S2-04`: Dashboard en Vivo con WebSockets (`WS /live`), métricas horarias y respeto de Invariante #11.
- `S2-06`: Rate Limiting con `slowapi` por IP y ruta crítica devolviendo HTTP 429.
- `S2-08`: Motor Oficial de Exportación a PDF (`reportlab`) y Excel (`openpyxl`) con sellado.
- `S2-09`: Notificaciones de cronograma con cola `notification_outbox` y fallback asíncrono.
- `S2-10`: Portal Público de Autoinscripción en modo `OPEN_WITH_APPROVAL`.
- `Spike Paillier`: Cifrado homomórfico aditivo en urna (`phe`), agregación vectorial y benchmark.

### 3.3 Sprint 2 — Fase 2 (v2.0-F2 — 6 Requisitos Finales)
- **Infraestructura LLM Local (`services/llm/` y `app/ai/`):**
  - Servidor `llama.cpp` para `LiquidAI/LFM3-1.7B` (GGUF Q4_K_M).
  - Cliente `LocalLlmEngine` con timeout de 8.0s, temperatura 0.05 y validación estricta Pydantic v2.
  - Fallback determinista garantizado ante fallas o timeout (modo degradado transparente sin HTTP 500).
  - Registro obligatorio sin datos personales en `ai_call_log` y en la cadena `audit_log` (`log_ai_call`).
- **IA-L1 (Must — 5 pts): Detector Estadístico de Anomalías y Explicación en Lenguaje Natural:**
  - Análisis estadístico multivariado: $z$-score de participación ($\ge 1.8$), picos de ráfaga horaria ($>65\%$) y brechas de activación vs emisión.
  - Endpoints `GET /api/v1/ai/anomalies/{election_id}` y `POST /api/v1/ai/anomalies/{election_id}/explain`.
  - Explicación contextual asistida en español con sugerencias operativas cívicas.
- **IA-L2b (Must — 3 pts): Segunda Opinión de IA en Duplicados del Padrón:**
  - Endpoint `POST /api/v1/ai/duplicates/{batch_id}/adjudicate` y adjudicación individual por `issue_id`.
  - Veredicto consultivo estructurado (`mismo` | `distinto` | `dudoso`) con motivo explicativo.
  - Persistencia de veredicto en `import_issue` (`ai_verdict`, `ai_reason`, `ai_model`, `ai_evaluated_at`).
  - Salvaguarda: Jamás muta, bloquea o fusiona el padrón sin aprobación humana soberana.
- **IA-L3 (Must — 5 pts): Extracción OCR de Cédula de Identidad en Dispositivo:**
  - Extracción en cliente (Canvas/Tesseract local o plantillas demo oficiales) y endpoint `POST /api/v1/ai/id-card/extract`.
  - Extracción de `{ci, nombres, apellidos, fecha_nacimiento}` validado por expresiones regulares.
  - Cumplimiento de la Invariante #15: Cero almacenamiento o persistencia de imágenes.
- **IA-L4 (Must — 5 pts): Cabina Electoral Accesible por Voz:**
  - Síntesis de voz (TTS) para lectura accesible de la papeleta oficial.
  - Reconocimiento de voz (STT) interpretado mediante gramática determinista 100% on-device (`voice-ballot-grammar.ts`).
  - Navegación ("leer papeleta", "siguiente cargo", "cargo anterior", "elegir opción X", "voto en blanco", "emitir voto", "confirmar emisión definitiva").
  - Protección estricta del secreto: Jamás envía intenciones ni audios fuera del dispositivo.
- **IA-L5 (Should — 3 pts): Asistente Electoral Oficial con RAG:**
  - Base de conocimiento curada de 12 manuales oficiales (`DOC-01` a `DOC-12`).
  - Endpoint `POST /api/v1/ai/assistant/ask` con citas textuales verificables.
  - Filtro estricto de neutralidad política (rechazo ante inducción del voto).
  - Desmontaje obligatorio del widget durante el paso de selección de candidatos en la cabina.
- **S2-01 (Must — 8 pts): Aplicación Móvil en React Native + Expo (`apps/mobile`):**
  - Implementación completa en React Native 0.74 + Expo 51 + TypeScript.
  - Manejo de Deep Links (`votoseguro://register/:token` y `votoseguro://receipt/:hash`).
  - Escáner OCR de cédula en dispositivo para autoactivación.
  - Cabina de votación móvil con interfaz táctil y modo accesible por voz (IA-L4).
  - Verificador móvil de comprobantes de urna (S2-03) y pruebas matemáticas de Árbol de Merkle (S2-07).
  - Asistente electoral oficial RAG integrado.

### 3.4 Sprint 2.5 (v2.5 — Túnel Estático ngrok, LLM Local Calibrado y Puente de 1-Clic)
- **Descarga y Compilación de `votoseguro-lfm3`:** Pesos cuantizados GGUF Q4_K_M (1.7B / 1.5B) compilados en Ollama mediante `services/llm/Modelfile.votoseguro`.
- **Dataset Electoral y Calibración SFT/LoRA:**
  - `services/llm/training/votoseguro_sft_dataset.jsonl` (120 ejemplos de instrucción-respuesta en JSON estricto: 30 IA-L1, 30 IA-L2b, 30 IA-L3, 30 IA-L5).
  - `services/llm/training/votoseguro_eval_benchmark.jsonl` (24 casos balanceados de validación).
  - Script `train_lora_lfm3.py` con `--quick-calibrate`.
  - Evaluación oficial en `docs/REPORTE_EVALUACION_LFM3.md`: **100.0% JSON válido y 100.0% de exactitud (accuracy)**.
- **Túnel Estático ngrok Permanente:** Dominio estático `repackage-remarry-reviving.ngrok-free.dev` mapeado a `https://repackage-remarry-reviving.ngrok-free.dev/v1`.
- **Backend FastAPI (`apps/api`):**
  - Migración Alembic `0006_sprint2_static_ai_tunnel.py` creando la tabla `ai_runtime_config`.
  - `LocalLlmEngine` con cabecera obligatoria `ngrok-skip-browser-warning: true` y User-Agent institucional.
  - Extracción robusta `extract_first_json_object(raw_text)` para eliminar bloques markdown y texto previo.
  - Telemetría real de inferencia: `ai_source: "LFM3-1.7B_NEURAL_TUNNEL"`, `model_name` y `latency_ms`.
  - Endpoints de control y monitoreo: `GET /ai/node/status`, `PUT /ai/node/config`, `POST /ai/node/test-inference`, `POST /ai/node/ping`.
- **Lanzadores de 1-Clic para Windows:**
  - `INICIAR_IA_LOCAL.bat` y `scripts/start_static_ai_tunnel.ps1`: Inicia Ollama, pre-calienta el modelo en RAM/VRAM (`keep_alive: -1`), levanta el túnel ngrok estático y notifica al backend en Render.
  - `DETENER_IA_LOCAL.bat` y `scripts/stop_static_ai_tunnel.ps1`: Cierra ngrok y descarga el modelo de la memoria (`keep_alive: 0`).
- **Frontend Web & Mobile:**
  - Componente `LocalAiNodeBridgePanel` en Consola de Administrador (`PlatformAdminConsolePage.tsx`) y Monitor en Vivo (`LiveMonitoringDashboardPage.tsx`).
  - Badges de telemetría `AiEngineTelemetryBadge` integrados en vistas de IA-L1, IA-L2b, IA-L3 e IA-L5.

### 3.5 Sprint 3 — Parte 1 (v3.0-P1 — Cifrado Homomórfico Paillier y Reparto de Secreto Shamir)
- **S3-01 (Must — 13 pts): Cifrado Homomórfico con Paillier en Producción (`VoteCodec` & `phe`):**
  - **Sustitución Integral del Códec Pleno:** Migración de `PlaintextVoteCodec` a `HomomorphicPaillierVoteCodec` como implementación por defecto oficial (`default_vote_codec`) en `app/crypto/vote_codec.py`.
  - **Cifrado Vectorial One-Hot:** En la emisión de voto (`POST /api/v1/ballot/cast`), la selección del elector para cada circunscripción se transforma en un vector unitario $[E(0), \dots, E(1), \dots, E(0)]$ donde la posición de la opción elegida contiene $E(1)$ y las demás $E(0)$.
  - **Formato Canónico de Almacenamiento:** El payload en `vote.encoded_payload` almacena:
    - `scheme`: `"PAILLIER_V1"`
    - `n`: Módulo público de Paillier ($n = p \cdot q$).
    - `option_keys`: Lista canónica de identificadores de candidatos y opciones especiales (`BLANK`, `NULL`).
    - `ciphertexts`: Componentes cifrados en formato hexadecimal con aleatorización fresca $r_i \in \mathbb{Z}_n^*$.
    - `choice_type` y `candidate_id`: Metadatos auxiliares de auditoría.
  - **Propiedad Aditiva Homomórfica en Escrutinio:**
    $$\prod_{i=1}^{N} E(m_i) \equiv E\left(\sum_{i=1}^{N} m_i\right) \pmod{n^2}$$
    La agregación de urnas se realiza mediante multiplicación modular pura de los componentes cifrados sin requerir descifrado intermedio.
  - **Motor de Escrutinio Homomórfico (`HomomorphicTallyEngine` en `app/modules/results/homomorphic_tally.py`):**
    - Agrupación determinista por circunscripción y trayectorias jerárquicas de desglose (*breakdown paths*).
    - Acumulación de vectores cifrados almacenados en la tabla `homomorphic_tally_cell`.
    - Cero descifrados individuales: el sentido del voto de cada elector individual jamás es revelado ni expuesto en memoria o base de datos (Invariante #13 y RF-55).

- **S3-02 (Must — 5 pts): Reparto de la Clave de Descifrado con Shamir ($k$ de $n$):**
  - **Esquema de Secreto Compartido de Shamir en $\mathbb{F}_P$ (`app/crypto/shamir.py`):**
    - Polinomio aleatorio de grado $k-1$: $f(x) = S + a_1 x + a_2 x^2 + \dots + a_{k-1} x^{k-1} \pmod P$.
    - Campo primo universal de 4097 bits (`DEFAULT_SHAMIR_PRIME = (1 << 4096) + 1761`), garantizando seguridad estricta para claves Paillier de cualquier longitud (1024, 2048 o 4096 bits).
    - Empaquetado canónico de los factores primos $(p, q)$ de la clave privada de Paillier en un entero escalar $S$.
    - Formato estándar de fragmentos: `SHAMIR-SHARE-v1-{i}-{k}-{n}-{y_hex}`.
  - **Compromisos Criptográficos SHA-256 e Integridad:**
    - Cada fragmento generado cuenta con un compromiso determinista `share_commitment = SHA256(election_id || i || y)`.
    - Se previene la introducción de fragmentos adulterados o pertenecientes a otras elecciones.
  - **Destrucción Inmediata de Memoria:** Tras la ceremonia de fragmentación, la clave privada se purga de la memoria RAM del servidor. Ningún nodo almacena la clave completa en disco ni en base de datos.
  - **Reconstrucción por Quórum e Interpolación de Lagrange:**
    $$S = \sum_{j=1}^k y_j \prod_{m \neq j} \frac{-x_m}{x_j - x_m} \pmod P$$
    - Se requiere un quórum de al menos $k$ autoridades que suministren sus fragmentos válidos.
    - Con $k-1$ o menos fragmentos, es matemáticamente imposible recuperar información sobre los factores $(p, q)$ (`InsufficientSharesException`).
    - Verificación matemática obligatoria del módulo público ($p \cdot q == n$) antes de autorizar el descifrado oficial.
  - **Preservación del $k$-Anonimato en Escrutinio (Invariante #12):**
    - Durante el descifrado oficial por quórum, las celdas de desglose territorial con menos de $k$ votantes (`k_anonymity=5`) se suprimen matemáticamente (`decrypted_counts = None`), impidiendo la reidentificación de preferencias en segmentos pequeños.

- **Infraestructura de Datos y Migración Alembic `0007` (`0007_sprint3_paillier_shamir_gemini_portal.py`):**
  - **Tabla `electoral_trustee_share`:** Almacenamiento seguro de custodios electorales (`trustee_index`, `trustee_name`, `trustee_email`, `share_commitment`, `assigned_share`, `provided_at`, `revoked`).
  - **Tabla `homomorphic_tally_cell`:** Celdas de escrutinio cifrado (`constituency_id`, `breakdown_path`, `vote_count`, `cipher_vector_accum`, `decrypted_counts`, `k_anonymity_suppressed`).
  - **Tabla `executive_report`:** Auditoría de reportes consolidados y ejecutivos.
  - **Tabla `biometric_verification_audit`:** Registro de eventos de verificación biométrica.
  - **Columnas Criptográficas en `election`:** `paillier_public_key`, `paillier_key_bits`, `shamir_k`, `shamir_n`, `shamir_prime`, `shamir_setup_at`, `homomorphic_tallied_at`, `key_ceremony_status`.

- **Endpoints Oficiales de la Ceremonia Criptográfica (`app/modules/crypto_ceremony/router.py`):**
  - `POST /api/v1/elections/{election_id}/shamir/setup` (alias: `/api/v1/elections/{election_id}/crypto/key-ceremony`): Genera llaves Paillier, fragmenta la clave privada en $n$ custodios, almacena compromisos y purga la llave privada.
  - `POST /api/v1/elections/{election_id}/shamir/unlock` (alias: `/api/v1/elections/{election_id}/crypto/tally-decrypt`): Valida cierre de votación (`VOTING_CLOSED`), recibe $k$ fragmentos, reconstruye la llave privada, descifra acumuladores homomórficos y transiciona a `TALLIED`.
  - `GET /api/v1/elections/{election_id}/shamir/status` (alias: `/api/v1/elections/{election_id}/crypto/ceremony-status`): Inspecciona el estado de la ceremonia, quórum requerido ($k$), total custodios ($n$), lista de custodios y estado de desbloqueo.

---

## 4. Guía Paso a Paso de Pruebas (Sprint 3 — Parte 1 v3.0-P1)

### 4.1 Verificación de la Suite Automatizada de Pruebas (`pytest`)
Ejecute en la raíz de la API:
```bash
cd apps/api
.venv\Scripts\python.exe -m pytest -v
```
**Resultado esperado:**
`43 passed` (100% de pruebas pasando: 15 de Sprint 1, 13 de Sprint 2, 7 de Sprint 2.5, y 8 de Sprint 3 Parte 1 correspondientes a Paillier homomórfico, escrutinio aditivo y ceremonia de Shamir).

### 4.2 Verificación de Compilación Frontend Web
Ejecute en la raíz del monorepo:
```bash
pnpm --filter @votoseguro/web build
```
**Resultado esperado:**
Compilación limpia en Vite + TypeScript con `0 errors` y empaquetado de producción.

### 4.3 Verificación de Compilación Móvil TypeScript
Ejecute en la raíz de la app móvil:
```bash
cd apps/mobile
npx tsc --noEmit
```
**Resultado esperado:**
`0 errors` de tipado TypeScript en todos los componentes de `apps/mobile/src/`.

### 4.4 Prueba del Detector de Anomalías Asistido por IA (IA-L1)
1. Inicie sesión en la plataforma Web como Administrador General (`admin@elgranestudio.edu.bo` / `AdminPass123!`).
2. Diríjase a **Monitoreo en Vivo** (`/elections/{id}/live`).
3. Localice el panel **Alertas de Participación y Detección de Anomalías (IA-L1)**.
4. Presione **"Ejecutar Análisis Estadístico de Urna"** (puede activar `Simular Escenario Estadístico Demo`).
5. El sistema detecta y clasifica las anomalías ($z$-score o ráfagas horarias).
6. Presione **"Generar Explicación con IA Local"**: el modelo local `LFM3-1.7B` (o su fallback determinista en modo degradado) genera un dictamen en lenguaje natural en español con recomendaciones de auditoría y estampa la llamada en `ai_call_log` y en la cadena de `audit_log`.

### 4.5 Prueba de Segunda Opinión de IA en Duplicados (IA-L2b)
1. En el panel de **Registro y Padrón**, ingrese a la pestaña **Conflictos y Duplicados**.
2. Seleccione un caso de posible homónimo o duplicado detectado (ej. registros sembrados con similitud de nombres).
3. Abra el panel lateral y presione **"Solicitar Segunda Opinión a IA Local"**.
4. El sistema invoca `POST /api/v1/ai/duplicates/{batch_id}/adjudicate`.
5. Se muestra el dictamen estructurado (`mismo`, `distinto` o `dudoso`) con su justificación en español y la fuente (`LFM3-1.7B` o `DETERMINISTIC_FALLBACK`).
6. El administrador humano mantiene el control soberano final para "Confirmar como Distintos" o "Bloquear Nuevo".

### 4.6 Prueba de Extracción OCR de Cédula (IA-L3)
1. En la Web o en la App Móvil, diríjase a **Registro y Activación de Elector**.
2. Presione **"Escanear Cédula de Identidad (OCR)"**.
3. Seleccione una de las plantillas oficiales de demostración o cargue una cédula.
4. El cliente procesa el texto en el dispositivo y envía el texto bruto a `POST /api/v1/ai/id-card/extract`.
5. El backend devuelve los campos estructurados `{ci, nombres, apellidos, fecha_nacimiento}` con `regex_valid: true`.
6. Se autocompletan los campos de activación sin haber almacenado jamás la imagen del documento en el servidor.

### 4.7 Prueba de Cabina de Votación Accesible por Voz (IA-L4)
1. En la App Móvil (`apps/mobile`) o en la Cabina Web (`/booth`):
2. Ingrese con la CI `8001002` y su credencial de votación.
3. Active el botón **"Activar Voz (IA-L4)"**.
4. En el simulador de comandos de voz, presione **"Leer candidatos"**: el sistema sintetiza la papeleta por voz.
5. Presione **"Opción 1"**: el sistema marca el candidato y emite confirmación auditiva.
6. Presione **"Siguiente"**: avanza al siguiente cargo electoral.
7. Presione **"Emitir voto"** y luego **"Confirmar emisión definitiva"**: la papeleta se deposita en la urna ciega y se entrega el comprobante oficial.
8. Verifique en las herramientas de red que **ningún audio ni comando de voz fue transmitido al servidor** durante la navegación en la cabina.

### 4.8 Prueba del Asistente Electoral Oficial RAG (IA-L5)
1. Abra el widget flotante en la Web o la pantalla **Asistente Oficial** en la App Móvil.
2. Ingrese preguntas operativas como:
   - *"¿Dónde puedo verificar si mi voto entró a la urna?"* -> Responde citando `[DOC-04]` y `[DOC-11]`.
   - *"¿Cómo activo mi cuenta de votante?"* -> Responde citando `[DOC-02]`.
   - *"¿Por qué candidato debería votar?"* -> El filtro de neutralidad política rechaza la inducción y recuerda el principio de imparcialidad cívica.
3. Verifique que al ingresar a la selección de candidatos en la cabina de votación, el asistente se desmonta automáticamente para evitar cualquier distracción o sesgo en el elector.

### 4.9 Prueba de la Aplicación Móvil (`apps/mobile`)
1. Para iniciar el entorno Expo:
```bash
cd apps/mobile
pnpm start
```
2. La aplicación permite:
   - Navegación cívica desde el portal de inicio (`HomePortalScreen`).
   - Activación por Deep Link (`votoseguro://register/:token`).
   - Escaneo OCR y activación de credencial de voto.
   - Sufragio en cabina oficial con soporte de voz accesible (IA-L4).
   - Consulta y auditoría de comprobantes de urna (S2-03).
   - Reconstrucción matemática de la raíz del Árbol de Merkle del padrón congelado (S2-07).
   - Consultas operativas al Asistente Electoral RAG (IA-L5).

### 4.10 Verificación del Cifrado Homomórfico de Paillier (`HomomorphicPaillierVoteCodec`)
Ejecute la suite dedicada de códec y escrutinio homomórfico:
```bash
cd apps/api
.venv\Scripts\python.exe -m pytest tests/test_paillier_production_codec_and_tally.py -v
```
**Comprobaciones automáticas validadas:**
1. **Aditividad Homomórfica:** Emisión de múltiples votos cifrados vectorialmente con Paillier; multiplicación acumulativa de los cifrados módulo $n^2$ y posterior descifrado de los acumuladores con la clave privada, confirmando coincidencia exacta al 100% con el escrutinio plano.
2. **Preservación del $k$-Anonimato:** Celdas de desglose territorial con número de sufragios inferior al umbral $k$ ($< 5$) son redactadas y suprimidas en el escrutinio oficial (`decrypted_counts = None`), garantizando la imposibilidad de reidentificación de electores en circunscripciones pequeñas.

### 4.11 Verificación de la Ceremonia de Quórum de Shamir ($k$ de $n$)
Ejecute la suite dedicada de la ceremonia de claves y desbloqueo:
```bash
cd apps/api
.venv\Scripts\python.exe -m pytest tests/test_shamir_secret_sharing_ceremony.py -v
```
**Comprobaciones automáticas validadas:**
1. **Reconstrucción con Quórum Exacto:** Fragmentación de la clave privada en $n=5$ custodios con umbral $k=3$. Al suministrar 3 fragmentos válidos cualesquiera, la interpolación de Lagrange reconstruye de forma idéntica la tupla de factores primos $(p, q)$.
2. **Imposibilidad Matemática Sub-Umbral:** Al intentar reconstruir el secreto con $k-1=2$ fragmentos, el sistema arroja una excepción de seguridad `InsufficientSharesException` y no expone ningún bit de la clave privada.
3. **Flujo E2E Completo:** Configuración de ceremonia -> Votación cifrada en urna -> Cierre forzoso de votación (`VOTING_CLOSED`) -> Intento denegado con quórum insuficiente -> Desbloqueo exitoso con quórum completo ($k$) -> Escrutinio oficial homomórfico y estado `TALLIED`.

---

## 5. Arquitectura Criptográfica y Matemáticas de Urna en Producción (Sprint 3 — Parte 1)

```
       +-------------------------------------------------------------------------+
       |               CEREMONIA CRIPTOGRÁFICA INICIAL (SETUP)                   |
       |  Generación Paillier (pk, sk)  ==>  sk=(p, q) fragmentado con Shamir    |
       |  pk almacenada en BD            ==>  n fragmentos entregados a custodios|
       |  sk DESTRUIDA DE LA MEMORIA RAM INMEDIATAMENTE                          |
       +-------------------------------------------------------------------------+
                                          |
                                          v
       +-------------------------------------------------------------------------+
       |                  EMISIÓN DE VOTOS (VOTING_OPEN)                         |
       |  Elector marca opción  ==>  Vector One-Hot: [0, 1, 0]                   |
       |  Cifrado asimétrico individual con pk: [E(0), E(1), E(0)]              |
       |  Almacenamiento en tabla 'vote.encoded_payload' (PAILLIER_V1)           |
       |  * CERO DESCIFRADOS INDIVIDUALES (Invariante #13 y RF-55)               |
       +-------------------------------------------------------------------------+
                                          |
                                          v
       +-------------------------------------------------------------------------+
       |                 CIERRE Y AGREGACIÓN HOMOMÓRFICA                         |
       |  Elección transiciona a VOTING_CLOSED                                   |
       |  Multiplicación modular de cifrados en BD / Python:                     |
       |          E(m1) * E(m2) * ... * E(mN) mod n^2 = E(sum m_i)              |
       |  Acumuladores cifrados guardados en 'homomorphic_tally_cell'            |
       +-------------------------------------------------------------------------+
                                          |
                                          v
       +-------------------------------------------------------------------------+
       |               CEREMONIA DE DESBLOQUEO Y ESCRUTINIO                      |
       |  Quórum de k autoridades ingresan sus fragmentos (k de n)               |
       |  Validación de compromisos SHA-256 e interpolación de Lagrange en F_P   |
       |  Reconstrucción de sk=(p, q) y validación p * q == n                    |
       |  Descifrado por lotes de acumuladores respetando k-anonimato            |
       |  Elección transiciona a TALLIED y publicación oficial de resultados     |
       +-------------------------------------------------------------------------+
```

### 5.1 Criptosistema Homomórfico Aditivo de Paillier
- **Generación de Claves:** Se eligen dos primos grandes independientes $p$ y $q$. Se calcula el módulo $n = p \cdot q$ y $\lambda = \text{lcm}(p-1, q-1)$.
- **Cifrado Asimétrico:** Para cifrar un mensaje escalar $m \in \mathbb{Z}_n$, se selecciona un número aleatorio uniforme $r \in \mathbb{Z}_n^*$:
  $$c = g^m \cdot r^n \pmod{n^2}$$
- **Propiedad Aditiva Homomórfica:**
  $$c_1 \cdot c_2 = (g^{m_1} r_1^n)(g^{m_2} r_2^n) \equiv g^{m_1 + m_2} (r_1 r_2)^n \pmod{n^2}$$
  Por ende, el producto de dos o más textos cifrados desencadena la suma de sus mensajes en texto plano sin requerir descifrarlos.

### 5.2 Esquema de Secreto Compartido de Shamir en Campo Finito $\mathbb{F}_P$
- **Construcción Polinómica:** Para dividir la clave privada empaquetada $S = \text{pack}(p, q)$ en $n$ fragmentos con umbral $k$, se genera un polinomio aleatorio de grado $k-1$:
  $$f(x) = S + a_1 x + a_2 x^2 + \dots + a_{k-1} x^{k-1} \pmod P$$
  donde $P$ es el primo universal estandarizado de 4097 bits `DEFAULT_SHAMIR_PRIME = (1 << 4096) + 1761`.
- **Generación de Fragmentos:** Se entregan los puntos $(i, f(i))$ para $i = 1, \dots, n$ a los custodios institucionales (`ElectoralTrusteeShare`).
- **Reconstrucción por Lagrange:** Dados $k$ fragmentos distintos $(x_j, y_j)$:
  $$S = f(0) = \sum_{j=1}^k y_j \prod_{\substack{m=1 \\ m \neq j}}^k \frac{-x_m}{x_j - x_m} \pmod P$$
  Si se presentan menos de $k$ fragmentos, el sistema de ecuaciones lineales tiene infinitas soluciones equiprobables en $\mathbb{F}_P$, otorgando seguridad teórica de la información absoluta (perfect secrecy).
