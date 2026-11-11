"""
Entrypoint principal de FastAPI para VotoSeguro v1.0
"""
import logging
from contextlib import asynccontextmanager
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, text

from app.core.config import settings
from app.core.security import get_password_hash
from app.core.time import default_time_provider
from app.db.models.user import User, UserRole, UserStatus
from app.db.session import async_session_factory
from app.modules.admins.router import router as admins_router
from app.modules.audit.router import router as audit_router
from app.modules.auth.router import router as auth_router
from app.modules.elections.router import router as elections_router
from app.modules.organizations.router import router as organizations_router
from app.modules.scheduler.transition_service import run_scheduler_tick

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [VOTOSEGURO-API] %(message)s",
)
logger = logging.getLogger("votoseguro.api")


async def ensure_platform_admin():
    """Crea de forma idempotente al superadministrador de plataforma (PLATFORM_ADMIN) al arrancar."""
    async with async_session_factory() as session:
        stmt = select(User).where(User.email.ilike(settings.PLATFORM_ADMIN_EMAIL))
        existing_admin = (await session.execute(stmt)).scalar_one_or_none()
        if not existing_admin:
            logger.info(f"Creando usuario PLATFORM_ADMIN inicial: {settings.PLATFORM_ADMIN_EMAIL}")
            admin = User(
                organization_id=None,
                email=settings.PLATFORM_ADMIN_EMAIL.strip().lower(),
                full_name="Operador Central de Plataforma",
                password_hash=get_password_hash(settings.PLATFORM_ADMIN_PASSWORD),
                role=UserRole.PLATFORM_ADMIN,
                status=UserStatus.ACTIVE,
            )
            session.add(admin)
            await session.commit()
            logger.info("PLATFORM_ADMIN inicial aprovisionado exitosamente.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Tareas de inicio
    logger.info("Iniciando VotoSeguro API v1.0...")
    await ensure_platform_admin()

    # 2. Iniciar scheduler embebido si está habilitado
    scheduler = None
    if settings.RUN_EMBEDDED_SCHEDULER:
        logger.info("Iniciando APScheduler embebido protegido con pg_advisory_lock...")
        scheduler = AsyncIOScheduler()

        async def scheduled_tick():
            async with async_session_factory() as session:
                try:
                    events = await run_scheduler_tick(session, default_time_provider)
                    for ev in events:
                        logger.info(f"[EMBEDDED-SCHEDULER] {ev}")
                except Exception as exc:
                    logger.error(f"[EMBEDDED-SCHEDULER] Error en ciclo de transición: {exc}", exc_info=True)

        scheduler.add_job(
            scheduled_tick,
            "interval",
            seconds=settings.SCHEDULER_INTERVAL_SECONDS,
            id="embedded_scheduler_tick",
            max_instances=1,
            coalesce=True,
        )
        scheduler.start()

    yield

    # 3. Tareas de apagado
    if scheduler and scheduler.running:
        logger.info("Deteniendo APScheduler embebido...")
        scheduler.shutdown()
    logger.info("VotoSeguro API apagada correctamente.")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Plataforma SaaS Multi-Institución de Votación Electrónica Segura y Auditada",
    lifespan=lifespan,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    openapi_url="/openapi.json",
)

# Configuración de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registro de Routers versionados (/api/v1)
api_v1_prefix = "/api/v1"
app.include_router(auth_router, prefix=api_v1_prefix)
app.include_router(organizations_router, prefix=api_v1_prefix)
app.include_router(elections_router, prefix=api_v1_prefix)
app.include_router(admins_router, prefix=api_v1_prefix)
app.include_router(audit_router, prefix=api_v1_prefix)


@app.get("/api/v1/health", status_code=status.HTTP_200_OK, tags=["Salud"])
async def health_check():
    """Endpoint de comprobación de salud del servicio y de la conexión a la base de datos."""
    db_status = "unhealthy"
    try:
        async with async_session_factory() as session:
            await session.execute(text("SELECT 1"))
            db_status = "healthy"
    except Exception as e:
        logger.error(f"Falla de salud en base de datos: {e}")

    return {
        "status": "online" if db_status == "healthy" else "degraded",
        "database": db_status,
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
    }
