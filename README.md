# VotoSeguro v2

> **Plataforma SaaS Multi-Institución de Votación Electrónica Auditada**  
> *INF 422 SB — Ingeniería de Software I (UAGRM)*

---

## 🏛️ Arquitectura del Sistema

- **Backend:** FastAPI (Python 3.12) + SQLAlchemy 2.0 Async + PostgreSQL 17 (Supabase) + Alembic.
- **Frontend:** React 18 + TypeScript + Vite + Tailwind CSS (Sistema de diseño: *Soberanía Cívica Criptográfica*).
- **Seguridad e Invariantes:**
  - Multi-tenancy estricto por `organization_id`.
  - Desvinculación criptográfica total del votante: la tabla `vote` carece de `voter_id` (Invariante #9).
  - Autoridad temporal canónica gobernada por el reloj de la base de datos `SELECT now() AT TIME ZONE 'UTC'` (Invariante #6).
  - Bitácora inmutable append-only con trigger PostgreSQL (`prevent_audit_log_mutation()`).
  - Bloqueo por fuerza bruta tras 5 intentos fallidos durante 15 minutos (`Retry-After: 900`).
  - Scheduler autónomo e idempotente (`APScheduler` con `pg_try_advisory_xact_lock(849201)`).

---

## 🚀 Despliegue en Producción

- **API Backend:** Desplegado en [Render](https://render.com) (`https://votoseguro-api-plyu.onrender.com`).
- **Base de Datos:** PostgreSQL 17 alojado en [Supabase](https://supabase.com).
- **Frontend SPA:** Alojado en [Cloudflare Pages](https://pages.cloudflare.com).
