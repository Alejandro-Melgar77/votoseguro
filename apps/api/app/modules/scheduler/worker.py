"""
Worker Standalone del Scheduler Autónomo de VotoSeguro
Ejecutado como contenedor independiente o proceso en segundo plano.
"""
import asyncio
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.core.config import settings
from app.core.time import default_time_provider
from app.db.session import async_session_factory
from app.modules.scheduler.transition_service import run_scheduler_tick

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [SCHEDULER-WORKER] %(message)s",
)
logger = logging.getLogger("votoseguro.scheduler")


async def tick_job():
    async with async_session_factory() as session:
        try:
            events = await run_scheduler_tick(session, default_time_provider)
            for ev in events:
                logger.info(ev)
        except Exception as e:
            logger.error(f"Error procesando ciclo del scheduler: {e}", exc_info=True)


async def main():
    logger.info("Iniciando Worker Autónomo de Scheduler (APScheduler)...")
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        tick_job,
        "interval",
        seconds=settings.SCHEDULER_INTERVAL_SECONDS,
        id="electoral_schedule_tick",
        max_instances=1,
        coalesce=True,
    )
    scheduler.start()
    logger.info(
        f"Scheduler iniciado correctamente con frecuencia de {settings.SCHEDULER_INTERVAL_SECONDS} segundos."
    )

    try:
        while True:
            await asyncio.sleep(3600)
    except (KeyboardInterrupt, SystemExit):
        logger.info("Deteniendo scheduler worker...")
        scheduler.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
