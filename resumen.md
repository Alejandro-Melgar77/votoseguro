# VotoSeguro v2 — Resumen Ejecutivo y Técnico Oficial (Sprint 1 y Sprint 2 Completados al 100% — Release v2.0)

**Plataforma SaaS Multi-Institución de Votación Electrónica Soberana y Auditada**  
**Asignatura:** Ingeniería de Software I (INF 422 SB) — UAGRM  
**Fecha de Entrega:** 11 de Noviembre de 2026  
**Versión de Release:** v2.0.0 (Cierre Integral de Sprint 1 y Sprint 2)

---

## 1. Estado Global del Proyecto

| Hito / Entrega | Alcance | Estado | Pruebas Automatizadas | Compilación |
| :--- | :---: | :---: | :---: | :---: |
| **Sprint 1 (v1.0)** | 14 Historias (56 pts Must + 8 pts Should) | **100% COMPLETO** | 15/15 tests pasando | 0 errores (Web) |
| **Sprint 2 — Fase 1 (v2.0-F1)** | 10 Historias + Spike Paillier (35 pts) | **100% COMPLETO** | 21/21 tests pasando | 0 errores (Web) |
| **Sprint 2 — Fase 2 (v2.0-F2)** | IA-L1 a IA-L5 + S2-01 Mobile (29 pts) | **100% COMPLETO** | **28/28 tests pasando (100%)** | **0 errores (Web & Mobile)** |

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

---

## 4. Guía Paso a Paso de Pruebas de la Fase 2 (Sprint 2 v2.0)

### 4.1 Verificación de la Suite Automatizada de Pruebas (`pytest`)
Ejecute en la raíz de la API:
```bash
cd apps/api
.venv\Scripts\python.exe -m pytest -v
```
**Resultado esperado:**
`28 passed` en ~27 segundos (100% de pruebas pasando, abarcando modelos de IA, invariantes, fallback determinista y criptografía).

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
