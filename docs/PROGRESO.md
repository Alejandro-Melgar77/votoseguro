# Registro de Progreso — Sprint 1 (v1.0)

## Estado General del Sprint 1
- **Periodo:** 25/11/2026 al 08/12/2026 (10 días hábiles)
- **Alcance Total:** 56 pts Must + 8 pts Should = 64 pts

| ID | Prioridad | Historia de Usuario | Estado | Fecha de Inicio | Fecha de Cierre | Notas Técnicas |
|---|---|---|---|---|---|---|
| **S1-00** | Must | Configuración del Monorepo, Docker, DB y CI | Completado (Iteración 1) | 11/11/2026 | 11/11/2026 | 20 tablas modeladas, migraciones Alembic y extensiones pgcrypto, trgm y fuzzystrmatch. Primitivas criptográficas VoteCodec y Nullifier. |
| **S1-01** | Must | Autenticación JWT, Multi-Tenancy y Organizaciones | Completado (Iteración 1) | 11/11/2026 | 11/11/2026 | Bloqueo por fuerza bruta (5 intentos -> 15 min lock), aislamiento por organization_id y audit_log inmutable con trigger. |
| **S1-02** | Must | Elección, Cronograma Editable y Scheduler | Completado (Iteración 1) | 11/11/2026 | 11/11/2026 | APScheduler con pg_advisory_lock y reloj DB, validador de matriz de edición, acción Abrir registro e historial schedule_change. |
| **S1-03** | Must | Grupos, Jerarquías y Árbol de Nodos | Completado (Iteración 2) | 11/11/2026 | 11/11/2026 | VoterGroup, HierarchyLevel (depth), UnitNode con materialized path `/PATH/`, importador CSV con ordenamiento topológico y árbol visual interactivo. |
| **S1-04** | Must | Cargos, Circunscripciones y Filtros Extra | Completado (Iteración 2) | 11/11/2026 | 11/11/2026 | Contests con alcance por nivel, filtros dinámicos JSONB, desgloses y autogeneración/sincronización de circunscripciones electorales. |
| **S1-05** | Must | Candidatos por Circunscripción | Completado (Iteración 2) | 11/11/2026 | 11/11/2026 | CRUD de candidatos por circunscripción, reordenamiento atómico en papeleta, validación de imagen (magic bytes) y previsualización de papeleta oficial con Blanco/Nulo. |
| **S1-06** | Must | Publicación y config_hash | Completado (Iteración 2) | 11/11/2026 | 11/11/2026 | Ceremonia de publicación `DRAFT -> SCHEDULED`, validador de 6 reglas de integridad, congelamiento estructural con 409 Conflict y cálculo canónico RFC 8785 SHA-256. |
| **S1-07** | Must | Panel de Registro y Carga de Padrón | Completado (Iteración 2) | 11/11/2026 | 11/11/2026 | Padrón solo mutable en `REGISTRATION_OPEN`, alta individual y masiva CSV con validación de profundidad de nodo, resumen de avance por grupo/nodo y control de inhabilitaciones. |
| **S1-08** | Must | Enlaces de Registro y roll_hash | Completado (Iteración 3) | 11/11/2026 | 11/11/2026 | Enlaces por grupo/nodo con token URL-safe, activación pública con CI en `/register/:token` y congelamiento de padrón con cálculo canónico determinista de `roll_hash` (RFC 8785 SHA-256). |
| **S1-09** | Must | Papeleta Automática y Voto Atómico | Completado (Iteración 3) | 11/11/2026 | 11/11/2026 | Emisión de credenciales personales de un solo uso (`VS-XXXX-XXXX-XXXX`), login de votante, papeleta automática según path nodal (Algoritmo 3.2), emisión atómica blind cast (Algoritmo 3.3) con nullifiers HMAC-SHA256, sin voter_id en tabla vote (Invariante #9), timestamp truncado al minuto (Invariante #17) y recibo criptográfico auditado. |
| **S1-10** | Must | Resultados y k-Anonimato | Completado (Iteración 3) | 11/11/2026 | 11/11/2026 | Resultados herméticamente bloqueados con 403 Forbidden antes del cierre (Invariante #11), total de circunscripción 100% exacto verificado, desgloses jerárquicos configurados y k-anonimato estricto (Invariante #12: redacción si votos < k=5). |
| **IA-L2a**| Should | Detección de Duplicados Asistida (Padrón) | Completado (Iteración 2) | 11/11/2026 | 11/11/2026 | Detección híbrida pg_trgm + fuzzystrmatch con fallback en memoria para tests, registro de import_issue y bandeja de dictamen humano soberano. |
| **S1-11** | Should | Delegados de Solo Lectura (ADMIN_SEGMENT) | Completado (Iteración 1) | 11/11/2026 | 11/11/2026 | Alcance acotado por grupo o nodo jerárquico. Endpoints y UI funcional. |
| **S1-12** | Should | Solicitud Pública de Elección | Completado (Iteración 1) | 11/11/2026 | 11/11/2026 | Flujo público, radicación y aprobación/rechazo por PLATFORM_ADMIN. |

---

## Métricas de Calidad de la Iteración 3 (Release Final Sprint 1 v1.0)
- **Cobertura de Historias:** 14 de 14 Historias de Usuario completadas al 100% (56 pts Must + 8 pts Should = 64 pts).
- **Tests Automatizados:** 15 suites de pruebas de integración y verificación de invariantes pasando al 100% en `apps/api/tests/` (pytest: 15 passed en ~4.0s).
- **Compilación Frontend:** TypeScript estricto y Vite build pasando con 0 errores (1646 módulos empaquetados en producción).
- **Base de Datos y Migraciones:** Alembic actualizado a `0003_iter3_voting` en PostgreSQL (Supabase) y SQLite en memoria.
- **Sembrador Demostrativo (`seed:demo`):** Ejecución idempotente exitosa tanto por CLI (`python -m app.db.seed_demo`) como mediante endpoint protegido `POST /api/v1/platform/seed-demo`, aprovisionando Universidad EL GRAN ESTUDIO (36 votantes, homónimos IA-L2a, enlaces y credenciales) y Elecciones Nacionales Ecuador.
