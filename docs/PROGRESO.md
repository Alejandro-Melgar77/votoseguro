# Registro de Progreso — Sprint 1 (v1.0) & Sprint 2 (v2.0)

## Estado General del Proyecto
- **Periodo:** 11 de Noviembre de 2026
- **Estado Global:** Sprint 1 y Sprint 2 completados al 100% (Release Oficial v2.0).
- **Pruebas Automatizadas:** **28 de 28 pruebas unitarias y de integración pasando al 100% en `pytest`**.
- **Compilación de Producción:** Web (Vite + TypeScript) con **0 errores**; Mobile (`apps/mobile` con React Native + Expo) con **0 errores** en TypeScript (`tsc --noEmit`).

---

## 1. Sprint 1: Infraestructura, Jerarquías, Padrón, Voto Ciego y Escrutinio (100% Completo — 64 pts)

| ID | Prioridad | Historia de Usuario | Estado | Fecha de Cierre | Notas Técnicas |
|---|---|---|---|---|---|
| **S1-00** | Must | Configuración del Monorepo, Docker, DB y CI | Completado | 11/11/2026 | 20 tablas modeladas, migraciones Alembic y extensiones pgcrypto, trgm y fuzzystrmatch. Primitivas criptográficas VoteCodec y Nullifier. |
| **S1-01** | Must | Autenticación JWT, Multi-Tenancy y Organizaciones | Completado | 11/11/2026 | Bloqueo por fuerza bruta (5 intentos -> 15 min lock), aislamiento por organization_id y audit_log inmutable con trigger. |
| **S1-02** | Must | Elección, Cronograma Editable y Scheduler | Completado | 11/11/2026 | APScheduler con pg_advisory_lock y reloj DB, validador de matriz de edición, acción Abrir registro e historial schedule_change. |
| **S1-03** | Must | Grupos, Jerarquías y Árbol de Nodos | Completado | 11/11/2026 | VoterGroup, HierarchyLevel (depth), UnitNode con materialized path `/PATH/`, importador CSV con ordenamiento topológico y árbol visual interactivo. |
| **S1-04** | Must | Cargos, Circunscripciones y Filtros Extra | Completado | 11/11/2026 | Contests con alcance por nivel, filtros dinámicos JSONB, desgloses y autogeneración/sincronización de circunscripciones electorales. |
| **S1-05** | Must | Candidatos por Circunscripción | Completado | 11/11/2026 | CRUD de candidatos por circunscripción, reordenamiento atómico en papeleta, validación de imagen (magic bytes) y previsualización de papeleta oficial con Blanco/Nulo. |
| **S1-06** | Must | Publicación y config_hash | Completado | 11/11/2026 | Ceremonia de publicación `DRAFT -> SCHEDULED`, validador de 6 reglas de integridad, congelamiento estructural con 409 Conflict y cálculo canónico RFC 8785 SHA-256. |
| **S1-07** | Must | Panel de Registro y Carga de Padrón | Completado | 11/11/2026 | Padrón solo mutable en `REGISTRATION_OPEN`, alta individual y masiva CSV con validación de profundidad de nodo, resumen de avance por grupo/nodo y control de inhabilitaciones. |
| **S1-08** | Must | Enlaces de Registro y roll_hash | Completado | 11/11/2026 | Enlaces por grupo/nodo con token URL-safe, activación pública con CI en `/register/:token` y congelamiento de padrón con cálculo canónico determinista de `roll_hash` (RFC 8785 SHA-256). |
| **S1-09** | Must | Papeleta Automática y Voto Atómico | Completado | 11/11/2026 | Emisión de credenciales personales de un solo uso (`VS-XXXX-XXXX-XXXX`), login de votante, papeleta automática según path nodal (Algoritmo 3.2), emisión atómica blind cast (Algoritmo 3.3) con nullifiers HMAC-SHA256, sin voter_id en tabla vote (Invariante #9), timestamp truncado al minuto (Invariante #17) y recibo criptográfico auditado. |
| **S1-10** | Must | Resultados y k-Anonimato | Completado | 11/11/2026 | Resultados herméticamente bloqueados con 403 Forbidden antes del cierre (Invariante #11), total de circunscripción 100% exacto verificado, desgloses jerárquicos configurados y k-anonimato estricto (Invariante #12: redacción si votos < k=5). |
| **IA-L2a**| Should | Detección de Duplicados Asistida (Padrón) | Completado | 11/11/2026 | Detección híbrida pg_trgm + fuzzystrmatch con fallback en memoria para tests, registro de import_issue y bandeja de dictamen humano soberano. |
| **S1-11** | Should | Delegados de Solo Lectura (ADMIN_SEGMENT) | Completado | 11/11/2026 | Alcance acotado por grupo o nodo jerárquico. Endpoints y UI funcional. |
| **S1-12** | Should | Solicitud Pública de Elección | Completado | 11/11/2026 | Flujo público, radicación y aprobación/rechazo por PLATFORM_ADMIN. |

---

## 2. Sprint 2 — Fase 1: Integridad Criptográfica, Merkle, WebSockets, Exportaciones & Spike Paillier (100% Completo)

| ID | Prioridad | Historia de Usuario | Puntos | Estado | Notas Técnicas |
|---|---|---|---|---|---|
| **S2-02** | Must | Cadena de Hashes en Votos y Urna | 5 pts | Completado | `prev_hash`, `vote_hash`, bloque génesis por elección y auditoría integral de urna bloque por bloque (`/integrity/votes`). |
| **S2-03** | Must | Verificación Pública de Comprobante | 3 pts | Completado | Verificador público `/receipts/{receipt_hash}` que certifica posición en cadena e inmutabilidad sin revelar el voto (Invariante #9). |
| **S2-05** | Must | Cadena de Hashes en Bitácora y Registro IA | 3 pts | Completado | `audit_log` con encadenamiento SHA-256 e integración con `log_ai_call` para registrar todas las inferencias en `ai_call_log`. |
| **S2-07** | Should | Árbol de Merkle del Padrón | 5 pts | Completado | `merkle_root` sobre padrón congelado, pruebas de inclusión logarítmicas (`/merkle/proof/{ci}`) y verificador matemático (`/merkle/verify`). |
| **S2-04** | Must | Dashboard en Vivo con WebSockets | 5 pts | Completado | Conexión WebSocket `WS /live` con fallback polling. Curva horaria y participación respetando estrictamente la Invariante #11. |
| **S2-06** | Must | Rate Limiting por IP y Ruta Crítica | 3 pts | Completado | Protección contra DoS y fuerza bruta con `slowapi` devolviendo HTTP 429. |
| **S2-08** | Should | Motor de Exportación PDF y Excel | 3 pts | Completado | Generación de actas PDF con firma canónica y planillas Excel respetando $k$-anonimato. |
| **S2-09** | Should | Notificación de Cronograma | 2 pts | Completado | Cola de salida `notification_outbox` y fallback asíncrono `aiosmtplib`. |
| **S2-10** | Could | Portal Público de Autoinscripción | 3 pts | Completado | Modo `OPEN_WITH_APPROVAL` con bandeja de aprobación/rechazo para el Administrador General. |
| **Spike Paillier** | Obligatorio | Spike de Cifrado Homomórfico | — | Completado | Adición homomórfica en urna (`phe`), agregación vectorial por circunscripción y benchmark de latencia. |

---

## 3. Sprint 2 — Fase 2: IA Local LFM3-1.7B, Accesibilidad por Voz & App Móvil (100% Completo — Release v2.0)

| ID | Prioridad | Denominación y Módulo | Puntos | Estado | Notas Técnicas y Salvaguardas |
|---|---|---|---|---|---|
| **Infraestructura LLM** | Must | Servidor y Cliente `LFM3-1.7B` | 5 pts | Completado | `services/llm/Dockerfile` (llama.cpp server GGUF Q4_K_M). Cliente `app/ai/client.py` con timeout de 8.0s, temperatura 0.05, validación Pydantic estricta y fallback determinista garantizado en modo degradado. Trazabilidad sin PII en `ai_call_log` y `audit_log`. |
| **IA-L1** | Must | Detector de Anomalías y Explicación | 5 pts | Completado | Detección estadística ($z$-score $\ge 1.8$, picos horarios $>65\%$, brechas activación vs voto). Endpoint `POST /api/v1/ai/anomalies/{id}/explain` con explicación en español y recomendaciones cívicas. Respeta Invariante #11. |
| **IA-L2b** | Must | Segunda Opinión de IA en Duplicados | 3 pts | Completado | Veredicto consultivo (`mismo`, `distinto`, `dudoso`) con motivo explicativo vía `POST /api/v1/ai/duplicates/{batch_id}/adjudicate`. Persistencia en `import_issue` mediante migración `0005_sprint2_phase2_ai_local.py`. Jamás muta ni bloquea automáticamente. |
| **IA-L3** | Must | Extracción OCR de Cédula de Identidad | 5 pts | Completado | Extracción OCR en el dispositivo cliente y endpoint `POST /api/v1/ai/id-card/extract`. Validación por expresiones regulares bolivianas/latinoamericanas. **Cero persistencia de imágenes ni buffers (Invariante #15)**. |
| **IA-L4** | Must | Cabina Electoral Accesible por Voz | 5 pts | Completado | Lectura hablada de la papeleta (TTS) y comandos de voz (STT). **Gramática determinista 100% on-device (`voice-ballot-grammar.ts`)**. Jamás envía audios ni intenciones fuera del dispositivo (Invariante Sección 7.3). |
| **IA-L5** | Should | Asistente Electoral Oficial con RAG | 3 pts | Completado | Base de conocimiento curada de 12 manuales oficiales (`DOC-01` a `DOC-12`). Endpoint `POST /api/v1/ai/assistant/ask` con citas textuales verificables, filtro estricto de neutralidad política y derivación a soporte. Desmontado en votación. |
| **S2-01** | Must | Aplicación Móvil React Native + Expo | 8 pts | Completado | App en `apps/mobile/` consumiendo `/api/v1`. Deep Linking (`votoseguro://register/:token`), escáner OCR de cédula, login CI + credencial, papeleta automática con modo voz (IA-L4), emisión atómica ciega, verificador de comprobante y árbol de Merkle. |

---

## 4. Métricas de Calidad Globales del Release v2.0
- **Suites de Pruebas Backend (`pytest`):** 28 de 28 pruebas pasando (100% éxito) en 27.88s.
- **Compilación Web (`@votoseguro/web`):** Vite 5 + React 18 + TypeScript compilado con **0 errores**.
- **Compilación Móvil (`@votoseguro/mobile`):** React Native 0.74 + Expo 51 + TypeScript compilado con **0 errores**.
- **Librería de Contratos (`@votoseguro/api-client`):** TypeScript compilado con **0 errores**.
- **Seguridad e Invariantes:** Cumplimiento total de Invariantes #1 al #20 (Aislamiento, Nullifiers HMAC, Voto Ciego, Congelamiento Canónico, Merkle Tree, Cadenas de Hashes, Zero PII y Zero Image Storage).
