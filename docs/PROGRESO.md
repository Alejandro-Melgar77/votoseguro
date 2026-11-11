# Registro de Progreso — Sprint 1 (v1.0)

## Estado General del Sprint 1
- **Periodo:** 25/11/2026 al 08/12/2026 (10 días hábiles)
- **Alcance Total:** 56 pts Must + 8 pts Should = 64 pts

| ID | Prioridad | Historia de Usuario | Estado | Fecha de Inicio | Fecha de Cierre | Notas Técnicas |
|---|---|---|---|---|---|---|
| **S1-00** | Must | Configuración del Monorepo, Docker, DB y CI | Completado (Iteración 1) | 11/11/2026 | 11/11/2026 | 20 tablas modeladas, migraciones Alembic y extensiones pgcrypto, trgm y fuzzystrmatch. Primitivas criptográficas VoteCodec y Nullifier. |
| **S1-01** | Must | Autenticación JWT, Multi-Tenancy y Organizaciones | Completado (Iteración 1) | 11/11/2026 | 11/11/2026 | Bloqueo por fuerza bruta (5 intentos -> 15 min lock), aislamiento por organization_id y audit_log inmutable con trigger. |
| **S1-02** | Must | Elección, Cronograma Editable y Scheduler | Completado (Iteración 1) | 11/11/2026 | 11/11/2026 | APScheduler con pg_advisory_lock y reloj DB, validador de matriz de edición, acción Abrir registro e historial schedule_change. |
| **S1-03** | Must | Grupos, Jerarquías y Árbol de Nodos | Pendiente | | | Materialized path para jerarquías dinámicas (Iteración 2) |
| **S1-04** | Must | Cargos, Circunscripciones y Filtros Extra | Pendiente | | | Generación automática de circunscripciones (Iteración 2) |
| **S1-05** | Must | Candidatos por Circunscripción | Pendiente | | | Validación de fotos y orden en papeleta (Iteración 2) |
| **S1-06** | Must | Publicación y config_hash | Pendiente | | | Congelamiento de estructura y cálculo SHA-256 (Iteración 2) |
| **S1-07** | Must | Panel de Registro y Carga de Padrón | Pendiente | | | Solo en REGISTRATION_OPEN, importación CSV (Iteración 3) |
| **S1-08** | Must | Enlaces de Registro y roll_hash | Pendiente | | | Activación pública y padrón congelado (Iteración 3) |
| **S1-09** | Must | Papeleta Automática y Voto Atómico | Pendiente | | | Nullifiers con HMAC-SHA256, sin voter_id (Iteración 3) |
| **S1-10** | Must | Resultados y k-Anonimato | Pendiente | | | Supresión de celdas menores a k votos (Iteración 3) |
| **IA-L2a**| Should | Detección de Duplicados Clásica | Pendiente | | | pg_trgm + fuzzystrmatch (Iteración 3) |
| **S1-11** | Should | Delegados de Solo Lectura (ADMIN_SEGMENT) | Completado (Iteración 1) | 11/11/2026 | 11/11/2026 | Alcance acotado por grupo o nodo jerárquico. Endpoints y UI funcional. |
| **S1-12** | Should | Solicitud Pública de Elección | Completado (Iteración 1) | 11/11/2026 | 11/11/2026 | Flujo público, radicación y aprobación/rechazo por PLATFORM_ADMIN. |
