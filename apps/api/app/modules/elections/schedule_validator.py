"""
Motor de Validación de Cronograma Electoral y Reglas de Edición Auditada (Secciones 5.3 y 5.4)
"""
from datetime import datetime, timedelta, timezone
from app.core.exceptions import ConflictException, UnprocessableEntityException
from app.db.models.election import Election, ElectionStatus
from app.modules.elections.schemas import ScheduleDiff, ScheduleUpdateRequest


def ensure_utc(dt: datetime) -> datetime:
    """Normaliza un datetime asegurando que contenga zona horaria UTC."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def validate_and_diff_schedule_update(
    election: Election,
    payload: ScheduleUpdateRequest,
    db_now: datetime,
) -> list[ScheduleDiff]:
    """
    Valida la matriz de mutabilidad y el orden cronológico del cronograma.
    Retorna la lista de campos modificados para persistir en schedule_change y audit_log.
    """
    db_now = ensure_utc(db_now)

    new_reg_open = ensure_utc(payload.registration_opens_at)
    new_reg_close = ensure_utc(payload.registration_closes_at)
    new_vote_open = ensure_utc(payload.voting_opens_at)
    new_vote_close = ensure_utc(payload.voting_closes_at)

    old_reg_open = ensure_utc(election.registration_opens_at)
    old_reg_close = ensure_utc(election.registration_closes_at)
    old_vote_open = ensure_utc(election.voting_opens_at)
    old_vote_close = ensure_utc(election.voting_closes_at)

    # 1. Validación de Orden Cronológico Invariante (Sección 5.3)
    # new_reg_open < new_reg_close <= new_vote_open < new_vote_close
    if not (new_reg_open < new_reg_close):
        raise UnprocessableEntityException(
            "El inicio del registro debe ser estrictamente anterior al cierre del registro."
        )

    if not (new_reg_close <= new_vote_open):
        raise UnprocessableEntityException(
            "El orden cronológico es inválido: el registro debe cerrar antes o al mismo instante en que abre la votación."
        )

    if not (new_vote_open < new_vote_close):
        raise UnprocessableEntityException(
            "El inicio de la votación debe ser estrictamente anterior al cierre de la misma."
        )

    # Detectar campos efectivamente modificados
    diffs: list[ScheduleDiff] = []
    if new_reg_open != old_reg_open:
        diffs.append(ScheduleDiff("registration_opens_at", old_reg_open, new_reg_open))
    if new_reg_close != old_reg_close:
        diffs.append(ScheduleDiff("registration_closes_at", old_reg_close, new_reg_close))
    if new_vote_open != old_vote_open:
        diffs.append(ScheduleDiff("voting_opens_at", old_vote_open, new_vote_open))
    if new_vote_close != old_vote_close:
        diffs.append(ScheduleDiff("voting_closes_at", old_vote_close, new_vote_close))

    # Si no hubo cambios, retornar lista vacía
    if not diffs:
        return []

    # 2. Matriz de Estados Invariantes (Sección 5.4)
    status = election.status

    # Bloqueo total tras el fin de la elección
    if status in (ElectionStatus.VOTING_CLOSED, ElectionStatus.TALLIED, ElectionStatus.CANCELLED):
        raise ConflictException(
            "No se permite modificar el cronograma de una elección cerrada, finalizada o cancelada."
        )

    # Exigir motivo obligatorio fuera de DRAFT
    if status != ElectionStatus.DRAFT:
        if not payload.reason or len(payload.reason.strip()) < 10:
            raise UnprocessableEntityException(
                "Debe proporcionar un motivo formal de al menos 10 caracteres para modificar el cronograma de una elección publicada."
            )

    # Reglas específicas por estado
    for diff in diffs:
        field = diff.field_name
        new_val = diff.new_value

        # A. Si la elección está en VOTING_OPEN
        if status == ElectionStatus.VOTING_OPEN:
            if field != "voting_closes_at":
                raise ConflictException(
                    "Durante la fase de votación abierta (VOTING_OPEN) únicamente se permite modificar la hora de cierre de la votación."
                )
            if new_val < db_now + timedelta(minutes=5):
                raise UnprocessableEntityException(
                    "El cierre de la votación en curso debe fijarse al menos a 5 minutos en el futuro respecto a la hora del servidor."
                )

        # B. Si la elección está en REGISTRATION_OPEN
        elif status == ElectionStatus.REGISTRATION_OPEN:
            if field == "registration_opens_at":
                raise ConflictException(
                    "No se puede modificar la fecha de inicio de una fase de registro que ya se encuentra en curso."
                )
            if field == "registration_closes_at":
                if new_val < db_now + timedelta(minutes=5):
                    raise UnprocessableEntityException(
                        "El cierre de una fase en curso debe fijarse al menos a 5 minutos en el futuro respecto a la hora del servidor."
                    )
            if field in ("voting_opens_at", "voting_closes_at"):
                if new_val < db_now + timedelta(minutes=1):
                    raise UnprocessableEntityException(
                        "Las fechas de fases futuras deben fijarse en un instante posterior a la hora actual."
                    )

        # C. Si la elección está en REGISTRATION_CLOSED (esperando inicio de votación)
        elif status == ElectionStatus.REGISTRATION_CLOSED:
            if field in ("registration_opens_at", "registration_closes_at"):
                raise ConflictException(
                    "La fase de registro ya ha finalizado y el padrón electoral está congelado; no se pueden alterar sus fechas."
                )
            if field in ("voting_opens_at", "voting_closes_at"):
                if new_val < db_now + timedelta(minutes=1):
                    raise UnprocessableEntityException(
                        "La fecha de apertura de votación debe fijarse al menos 1 minuto a futuro respecto a la hora del servidor."
                    )

        # D. Si la elección está en SCHEDULED (publicada, esperando apertura de registro)
        elif status == ElectionStatus.SCHEDULED:
            if new_val < db_now + timedelta(minutes=1):
                raise UnprocessableEntityException(
                    "Las fechas del cronograma de una elección programada deben fijarse en el futuro."
                )

        # E. Si la elección está en DRAFT
        elif status == ElectionStatus.DRAFT:
            # En borrador se pueden editar libremente
            pass

    return diffs
