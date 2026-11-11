"""
Servicio de Negocio para Candidatos, Orden en Papeleta y Validación de Fotografía (S1-05)
"""
import base64
import uuid
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import (
    NotFoundException,
    UnprocessableEntityException,
)
from app.db.models.structure import Candidate, Constituency, Contest
from app.modules.candidates.schemas import (
    CandidateCreate,
    CandidateReorderRequest,
    CandidateResponse,
    CandidateUpdate,
    PhotoUploadResponse,
)
from app.modules.structure.guards import require_group_draft


class CandidateService:

    @staticmethod
    async def _require_constituency_draft(db: AsyncSession, constituency_id: uuid.UUID) -> tuple[Constituency, Contest]:
        stmt = (
            select(Constituency)
            .where(Constituency.id == constituency_id)
            .options(selectinload(Constituency.contest))
        )
        constituency = (await db.execute(stmt)).scalar_one_or_none()
        if not constituency:
            raise NotFoundException("Circunscripción no encontrada.")

        await require_group_draft(db, constituency.contest.group_id)
        return constituency, constituency.contest

    @staticmethod
    async def create_candidate(
        db: AsyncSession, constituency_id: uuid.UUID, payload: CandidateCreate
    ) -> CandidateResponse:
        constituency, _ = await CandidateService._require_constituency_draft(db, constituency_id)

        # Determinar orden en papeleta
        if payload.ballot_order is not None:
            ballot_order = payload.ballot_order
            # Verificar si ya está ocupado
            stmt_order = select(Candidate).where(
                Candidate.constituency_id == constituency_id, Candidate.ballot_order == ballot_order
            )
            if (await db.execute(stmt_order)).scalar_one_or_none():
                raise UnprocessableEntityException(
                    f"La posición {ballot_order} en la papeleta ya está asignada a otro candidato en esta circunscripción."
                )
        else:
            stmt_max = select(func.max(Candidate.ballot_order)).where(
                Candidate.constituency_id == constituency_id
            )
            max_order = (await db.execute(stmt_max)).scalar() or 0
            ballot_order = max_order + 1

        candidate = Candidate(
            constituency_id=constituency_id,
            name=payload.name.strip(),
            party_or_front=payload.party_or_front.strip() if payload.party_or_front else None,
            photo_url=payload.photo_url.strip() if payload.photo_url else None,
            ballot_order=ballot_order,
        )
        db.add(candidate)
        await db.commit()
        await db.refresh(candidate)
        return CandidateResponse.model_validate(candidate)

    @staticmethod
    async def list_candidates(db: AsyncSession, constituency_id: uuid.UUID) -> list[CandidateResponse]:
        stmt = (
            select(Candidate)
            .where(Candidate.constituency_id == constituency_id)
            .order_by(Candidate.ballot_order.asc())
        )
        candidates = (await db.execute(stmt)).scalars().all()
        return [CandidateResponse.model_validate(c) for c in candidates]

    @staticmethod
    async def update_candidate(
        db: AsyncSession, candidate_id: uuid.UUID, payload: CandidateUpdate
    ) -> CandidateResponse:
        stmt = select(Candidate).where(Candidate.id == candidate_id)
        candidate = (await db.execute(stmt)).scalar_one_or_none()
        if not candidate:
            raise NotFoundException("Candidato no encontrado.")

        await CandidateService._require_constituency_draft(db, candidate.constituency_id)

        if payload.name:
            candidate.name = payload.name.strip()
        if payload.party_or_front is not None:
            candidate.party_or_front = payload.party_or_front.strip() if payload.party_or_front else None
        if payload.photo_url is not None:
            candidate.photo_url = payload.photo_url.strip() if payload.photo_url else None

        if payload.ballot_order is not None and payload.ballot_order != candidate.ballot_order:
            stmt_dup = select(Candidate).where(
                Candidate.constituency_id == candidate.constituency_id,
                Candidate.id != candidate.id,
                Candidate.ballot_order == payload.ballot_order,
            )
            if (await db.execute(stmt_dup)).scalar_one_or_none():
                raise UnprocessableEntityException(
                    f"La posición {payload.ballot_order} en la papeleta ya está ocupada."
                )
            candidate.ballot_order = payload.ballot_order

        await db.commit()
        await db.refresh(candidate)
        return CandidateResponse.model_validate(candidate)

    @staticmethod
    async def delete_candidate(db: AsyncSession, candidate_id: uuid.UUID) -> None:
        stmt = select(Candidate).where(Candidate.id == candidate_id)
        candidate = (await db.execute(stmt)).scalar_one_or_none()
        if not candidate:
            raise NotFoundException("Candidato no encontrado.")

        await CandidateService._require_constituency_draft(db, candidate.constituency_id)
        await db.delete(candidate)
        await db.commit()

    @staticmethod
    async def reorder_candidates(
        db: AsyncSession, constituency_id: uuid.UUID, payload: CandidateReorderRequest
    ) -> list[CandidateResponse]:
        await CandidateService._require_constituency_draft(db, constituency_id)

        stmt = select(Candidate).where(Candidate.constituency_id == constituency_id)
        candidates = {c.id: c for c in (await db.execute(stmt)).scalars().all()}

        if set(payload.ordered_candidate_ids) != set(candidates.keys()):
            raise UnprocessableEntityException(
                "La lista ordenada debe incluir exactamente a todos los candidatos de esta circunscripción."
            )

        # Reasignar orden temporal para evitar violar uq_candidate_constituency_order durante updates intermedios
        for idx, cid in enumerate(payload.ordered_candidate_ids, start=1000):
            candidates[cid].ballot_order = idx
        await db.flush()

        for idx, cid in enumerate(payload.ordered_candidate_ids, start=1):
            candidates[cid].ballot_order = idx

        await db.commit()
        return await CandidateService.list_candidates(db, constituency_id)

    @staticmethod
    def validate_and_process_photo(image_bytes: bytes, filename: str) -> str:
        """
        Valida tamaño (<= 2MB) y magic bytes (JPEG, PNG, WEBP), retornando un Data URI.
        """
        max_size = 2 * 1024 * 1024  # 2MB
        if len(image_bytes) > max_size:
            raise UnprocessableEntityException("La fotografía excede el tamaño máximo permitido de 2 MB.")

        mime_type = None
        if image_bytes.startswith(b"\xff\xd8\xff"):
            mime_type = "image/jpeg"
        elif image_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
            mime_type = "image/png"
        elif image_bytes.startswith(b"RIFF") and len(image_bytes) >= 12 and image_bytes[8:12] == b"WEBP":
            mime_type = "image/webp"

        if not mime_type:
            raise UnprocessableEntityException(
                "Formato de imagen no admitido. Únicamente se permiten archivos JPEG, PNG o WEBP válidos."
            )

        b64 = base64.b64encode(image_bytes).decode("ascii")
        return f"data:{mime_type};base64,{b64}"
