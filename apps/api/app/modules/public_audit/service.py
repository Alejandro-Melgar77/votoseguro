"""
Servicio Oficial del Portal Público de Auditoría (S3-03 - RF-57).
Ofrece verificación ciudadana independiente y soberana sin requerir autenticación:
- Sellos criptográficos inmutables (config_hash, roll_hash, merkle_root, paillier_public_key).
- Verificación en vivo de la cadena de hashes de votos y bitácora de auditoría.
- Historial transparente de cambios del cronograma (schedule_changes) con motivo oficial.
- Resultados públicos post-cierre respetando estrictamente el k-anonimato.
- Cero exposición de datos personales (document_id, email, nombres) o votos individuales.
"""
import uuid
from typing import List
from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.audit import AuditLog
from app.db.models.election import (
    Election,
    ElectionStatus,
    HomomorphicTallyCell,
    ScheduleChange,
)
from app.db.models.organization import Organization
from app.db.models.voter import Voter, VoterStatus
from app.db.models.voting import Vote
from app.modules.public_audit.schemas import (
    ChainIntegrityStatus,
    ConstituencyResultPublic,
    PublicAuditDossierResponse,
    PublicElectionSummary,
    ScheduleChangePublicItem,
)


class PublicAuditService:
    """
    Motor de consolidación de evidencias públicas para el rol OBSERVER y ciudadanía general.
    """

    @classmethod
    async def list_public_elections(cls, db: AsyncSession) -> List[PublicElectionSummary]:
        """
        Lista todas las elecciones en curso o concluidas (excluyendo borradores DRAFT).
        """
        stmt = (
            select(Election, Organization.name.label("org_name"))
            .join(Organization, Election.organization_id == Organization.id)
            .where(Election.status != ElectionStatus.DRAFT)
            .order_by(Election.voting_opens_at.desc())
        )
        rows = (await db.execute(stmt)).all()

        summaries = []
        for election, org_name in rows:
            status_val = election.status.value if hasattr(election.status, "value") else str(election.status)
            summaries.append(
                PublicElectionSummary(
                    election_id=election.id,
                    name=election.name,
                    organization_name=org_name,
                    status=status_val,
                    config_hash=election.config_hash,
                    roll_hash=election.roll_hash,
                    merkle_root=election.merkle_root,
                    voting_opens_at=election.voting_opens_at,
                    voting_closes_at=election.voting_closes_at,
                )
            )
        return summaries

    @classmethod
    async def get_public_audit_dossier(
        cls,
        db: AsyncSession,
        election_id: uuid.UUID,
    ) -> PublicAuditDossierResponse:
        """
        Construye el expediente público de auditoría de la elección sin exponer datos sensibles.
        """
        # 1. Obtener la elección
        stmt_elec = (
            select(Election, Organization.name.label("org_name"))
            .join(Organization, Election.organization_id == Organization.id)
            .where(Election.id == election_id)
        )
        row = (await db.execute(stmt_elec)).first()
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Elección solicitada no encontrada.",
            )

        election, org_name = row

        # Prohibir inspección pública de borradores no publicados
        if election.status == ElectionStatus.DRAFT:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="La elección se encuentra en fase de borrador y no es pública.",
            )

        # 2. Historial público de cambios de cronograma
        stmt_changes = (
            select(ScheduleChange)
            .where(ScheduleChange.election_id == election_id)
            .order_by(ScheduleChange.changed_at.asc())
        )
        db_changes = list((await db.execute(stmt_changes)).scalars().all())
        schedule_items = [
            ScheduleChangePublicItem(
                id=c.id,
                field_name=c.field_name,
                old_value=c.old_value.isoformat() if hasattr(c.old_value, "isoformat") else str(c.old_value),
                new_value=c.new_value.isoformat() if hasattr(c.new_value, "isoformat") else str(c.new_value),
                reason=c.reason,
                changed_at=c.changed_at,
            )
            for c in db_changes
        ]

        # 3. Verificación en vivo de la cadena de hashes de votos (Ledger)
        stmt_votes = (
            select(Vote)
            .where(Vote.election_id == election_id)
            .order_by(Vote.chain_index.asc())
        )
        votes = list((await db.execute(stmt_votes)).scalars().all())

        total_votes = len(votes)
        votes_chain_valid = True
        head_vote_hash = "GENESIS"
        genesis_vote_hash = None

        if votes:
            genesis_vote_hash = votes[0].vote_hash
            head_vote_hash = votes[-1].vote_hash
            prev = None
            for v in votes:
                if prev and v.prev_hash != prev.vote_hash:
                    votes_chain_valid = False
                    break
                prev = v

        votes_integrity = ChainIntegrityStatus(
            total_items=total_votes,
            chain_valid=votes_chain_valid,
            head_hash=head_vote_hash,
            genesis_hash=genesis_vote_hash,
        )

        # 4. Verificación en vivo de la bitácora de auditoría
        stmt_audit = (
            select(AuditLog)
            .where(AuditLog.election_id == election_id)
            .order_by(AuditLog.chain_index.asc())
        )
        audit_entries = list((await db.execute(stmt_audit)).scalars().all())
        total_audit = len(audit_entries)
        audit_chain_valid = True
        head_audit_hash = "GENESIS"

        if audit_entries:
            head_audit_hash = audit_entries[-1].entry_hash
            prev_a = None
            for a in audit_entries:
                if prev_a and a.prev_hash != prev_a.entry_hash:
                    audit_chain_valid = False
                    break
                prev_a = a

        audit_integrity = ChainIntegrityStatus(
            total_items=total_audit,
            chain_valid=audit_chain_valid,
            head_hash=head_audit_hash,
        )

        # 5. Participación electoral
        stmt_census = select(func.count(Voter.id)).where(
            Voter.election_id == election_id,
            Voter.status == VoterStatus.ACTIVE,
        )
        total_census = (await db.execute(stmt_census)).scalar() or 0
        turnout_pct = round((total_votes / total_census * 100), 2) if total_census > 0 else 0.0

        # 6. Parámetros de clave pública
        pub_key = election.paillier_public_key or election.paillier_public_n or ""
        pub_key_trunc = f"{pub_key[:24]}...{pub_key[-24:]}" if len(pub_key) > 60 else pub_key

        # 7. Resultados públicos (Solo si cerrado o escrutado)
        status_str = election.status.value if hasattr(election.status, "value") else str(election.status)
        results_published = False
        public_results: List[ConstituencyResultPublic] = []
        results_notice = "Resultados herméticos hasta el cierre oficial de la votación (Invariante #11)."

        if election.status in (ElectionStatus.VOTING_CLOSED, ElectionStatus.TALLIED):
            results_published = True
            results_notice = "Resultados oficiales certificados conforme a cómputo homomórfico y k-anonimato."
            stmt_cells = select(HomomorphicTallyCell).where(
                HomomorphicTallyCell.election_id == election_id,
                HomomorphicTallyCell.cell_scope_type == "CONSTITUENCY_TOTAL",
            )
            cells = list((await db.execute(stmt_cells)).scalars().all())

            for c in cells:
                public_results.append(
                    ConstituencyResultPublic(
                        constituency_id=c.constituency_id,
                        constituency_label=c.cell_label,
                        ballots_aggregated=c.ballots_aggregated,
                        suppressed_by_k_anonymity=c.suppressed_by_k_anonymity,
                        results=c.decrypted_counts if not c.suppressed_by_k_anonymity else None,
                    )
                )

        return PublicAuditDossierResponse(
            election_id=election.id,
            name=election.name,
            organization_name=org_name,
            status=status_str,
            timezone=election.timezone,
            k_anonymity=election.k_anonymity,
            encryption_scheme=election.encryption_scheme or "PAILLIER_HOMOMORPHIC",
            config_hash=election.config_hash,
            roll_hash=election.roll_hash,
            merkle_root=election.merkle_root,
            key_ceremony_hash=election.key_ceremony_hash,
            tally_ceremony_hash=election.tally_ceremony_hash,
            paillier_public_n=election.paillier_public_n,
            paillier_public_key=pub_key,
            paillier_public_key_truncated=pub_key_trunc,
            shamir_threshold_k=election.shamir_threshold_k,
            shamir_total_n=election.shamir_total_n,
            key_ceremony_status="COMPLETADA" if election.key_ceremony_hash else "PENDIENTE",
            voting_opens_at=election.voting_opens_at,
            voting_closes_at=election.voting_closes_at,
            schedule_changes=schedule_items,
            votes_integrity=votes_integrity,
            audit_integrity=audit_integrity,
            total_registered_voters=total_census,
            total_votes_cast=total_votes,
            turnout_percentage=turnout_pct,
            results_published=results_published,
            results=public_results if results_published else None,
            results_notice=results_notice,
        )
