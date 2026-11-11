"""
Servicio de Despacho y Registro de Notificaciones por Correo (S2-09)
Notifica a votantes registrados ante cambios de cronograma electoral.
"""
import logging
import uuid
from datetime import datetime, timezone
from email.message import EmailMessage
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models.election import Election, ScheduleChange
from app.db.models.notification import NotificationOutbox
from app.db.models.voter import Voter, VoterStatus

logger = logging.getLogger("votoseguro.notifications")


class NotificationService:
    @staticmethod
    async def dispatch_schedule_notifications(
        db: AsyncSession,
        election: Election,
        schedule_changes: list[ScheduleChange],
        reason_text: str,
        db_now: datetime,
    ) -> int:
        """
        S2-09: Notifica por correo electrónico a todos los votantes ACTIVE o INVITED
        cuando ocurre una modificación en el cronograma electoral.
        """
        stmt = select(Voter).where(
            Voter.election_id == election.id,
            Voter.status.in_([VoterStatus.ACTIVE, VoterStatus.INVITED]),
            Voter.email.isnot(None),
            Voter.email != "",
        )
        voters = (await db.execute(stmt)).scalars().all()
        if not voters:
            return 0

        # Construir resumen de cambios de fechas
        adjustments = []
        for sc in schedule_changes:
            old_str = sc.old_value.strftime("%Y-%m-%d %H:%M UTC") if hasattr(sc.old_value, "strftime") else str(sc.old_value)
            new_str = sc.new_value.strftime("%Y-%m-%d %H:%M UTC") if hasattr(sc.new_value, "strftime") else str(sc.new_value)
            adjustments.append(f"- {sc.field_name}: Anterior: {old_str} -> Nuevo: {new_str}")
        adjustments_text = "\n".join(adjustments)

        subject = f"Aviso de Modificación de Cronograma: {election.name}"

        dispatched_count = 0
        for voter in voters:
            body = (
                f"Estimado(a) {voter.full_name}:\n\n"
                f"Le informamos que el cronograma oficial de la elección '{election.name}' ha sido modificado.\n\n"
                f"Motivo formal declarado por la autoridad electoral:\n"
                f"\"{reason_text}\"\n\n"
                f"Ajustes realizados en el calendario:\n"
                f"{adjustments_text}\n\n"
                f"Por favor revise sus fechas hábiles de registro y sufragio ingresando a la plataforma.\n\n"
                f"Atentamente,\n"
                f"Comité Electoral — VotoSeguro v2.0"
            )

            status = "STORED_DEMO_OUTBOX"
            if settings.SMTP_HOST:
                try:
                    import aiosmtplib
                    msg = EmailMessage()
                    msg["From"] = settings.SMTP_FROM_EMAIL
                    msg["To"] = voter.email
                    msg["Subject"] = subject
                    msg.set_content(body)

                    await aiosmtplib.send(
                        msg,
                        hostname=settings.SMTP_HOST,
                        port=settings.SMTP_PORT,
                        username=settings.SMTP_USER,
                        password=settings.SMTP_PASSWORD,
                        start_tls=True if settings.SMTP_PORT == 587 else False,
                    )
                    status = "SENT_SMTP"
                except Exception as exc:
                    logger.warning(f"Error enviando correo SMTP a {voter.email}: {exc}")
                    status = "FAILED"

            outbox_entry = NotificationOutbox(
                organization_id=election.organization_id,
                election_id=election.id,
                schedule_change_id=schedule_changes[0].id if schedule_changes else None,
                recipient_email=voter.email,
                recipient_name=voter.full_name,
                subject=subject,
                body_text=body,
                delivery_status=status,
                created_at=db_now,
            )
            db.add(outbox_entry)
            dispatched_count += 1

        return dispatched_count

    @staticmethod
    async def list_outbox(
        db: AsyncSession,
        election_id: uuid.UUID,
        limit: int = 100,
        offset: int = 0,
    ) -> list[NotificationOutbox]:
        stmt = (
            select(NotificationOutbox)
            .where(NotificationOutbox.election_id == election_id)
            .order_by(NotificationOutbox.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list((await db.execute(stmt)).scalars().all())
