"""
Servicio de Publicación, Validación de Consistencia de 6 Reglas y Cálculo de ConfigHash (S1-06)
"""
import hashlib
import json
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import (
    ConflictException,
    NotFoundException,
    UnprocessableEntityException,
)
from app.core.time import TimeProvider
from app.db.models.audit import AuditLog
from app.db.models.election import Election, ElectionStatus
from app.db.models.structure import (
    Candidate,
    Constituency,
    Contest,
    ContestBreakdown,
    FilterDefinition,
    HierarchyLevel,
    UnitNode,
    VoterGroup,
)
from app.db.models.user import User
from app.db.models.voter import Voter
from datetime import datetime, timezone


def ensure_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


class PublicationService:

    @staticmethod
    async def publish_election(
        db: AsyncSession,
        election_id: uuid.UUID,
        actor: User,
        time_provider: TimeProvider,
        client_ip: str | None = None,
    ) -> Election:
        """
        Ejecuta la validación de 6 reglas de consistencia electoral,
        genera el JSON canónico determinista RFC 8785, calcula el config_hash SHA-256,
        congela la estructura y transiciona el estado de DRAFT a SCHEDULED (o REGISTRATION_OPEN).
        """
        stmt = (
            select(Election)
            .where(Election.id == election_id)
            .options(
                selectinload(Election.groups).selectinload(VoterGroup.levels),
                selectinload(Election.groups).selectinload(VoterGroup.nodes),
                selectinload(Election.groups).selectinload(VoterGroup.filters),
                selectinload(Election.groups)
                .selectinload(VoterGroup.contests)
                .selectinload(Contest.scope_level),
                selectinload(Election.groups)
                .selectinload(VoterGroup.contests)
                .selectinload(Contest.breakdowns),
                selectinload(Election.groups)
                .selectinload(VoterGroup.contests)
                .selectinload(Contest.constituencies)
                .selectinload(Constituency.node),
                selectinload(Election.groups)
                .selectinload(VoterGroup.contests)
                .selectinload(Contest.constituencies)
                .selectinload(Constituency.candidates),
            )
        )
        election = (await db.execute(stmt)).scalar_one_or_none()
        if not election:
            raise NotFoundException("Elección no encontrada.")

        db_now = ensure_utc(await time_provider.now(db))
        reg_open = ensure_utc(election.registration_opens_at)
        reg_close = ensure_utc(election.registration_closes_at)
        vote_open = ensure_utc(election.voting_opens_at)
        vote_close = ensure_utc(election.voting_closes_at)
        errors: list[str] = []

        # =====================================================================
        # Regla 1 (Estado): Debe encontrarse estrictamente en DRAFT
        # =====================================================================
        if election.status != ElectionStatus.DRAFT:
            raise ConflictException(
                f"La elección se encuentra en estado '{election.status.value}'. Solo una elección en borrador (DRAFT) puede ser publicada."
            )

        # =====================================================================
        # Regla 2 (Cronograma vigente): Precedencia y fechas futuras
        # =====================================================================
        if not (reg_open < reg_close <= vote_open < vote_close):
            errors.append(
                "El cronograma no cumple la precedencia cronológica: registration_opens_at < registration_closes_at <= voting_opens_at < voting_closes_at."
            )

        if reg_close <= db_now:
            errors.append(
                f"El cierre de registro ({reg_close.isoformat()}) debe ser posterior al instante actual ({db_now.isoformat()})."
            )

        # =====================================================================
        # Regla 3 (Grupos y Jerarquías): Al menos 1 grupo, y cada grupo con nivel y nodo
        # =====================================================================
        if not election.groups:
            errors.append("La elección debe contener al menos un Grupo de Votantes.")
        else:
            for g in election.groups:
                if not g.levels:
                    errors.append(f"El grupo '{g.name}' no tiene ningún nivel jerárquico configurado.")
                if not g.nodes:
                    errors.append(f"El grupo '{g.name}' no tiene ningún nodo territorial/organizacional creado.")

        # =====================================================================
        # Regla 4 (Cargos): Cada grupo debe tener al menos 1 Contest
        # =====================================================================
        for g in election.groups:
            if not g.contests:
                errors.append(f"El grupo '{g.name}' debe tener al menos un cargo en disputa (Contest).")

        # =====================================================================
        # Regla 5 (Cobertura de Circunscripciones y Candidatos)
        # =====================================================================
        for g in election.groups:
            for c in g.contests:
                if not c.constituencies:
                    errors.append(
                        f"El cargo '{c.name}' del grupo '{g.name}' no tiene circunscripciones generadas."
                    )
                for const in c.constituencies:
                    node_name = const.node.name if const.node else str(const.node_id)
                    if not const.candidates:
                        errors.append(
                            f"La circunscripción '{node_name}' para el cargo '{c.name}' (Grupo: {g.name}) no tiene candidatos registrados."
                        )

        # =====================================================================
        # Regla 6 (Consistencia de Profundidad de Padrón Pre-cargado)
        # =====================================================================
        stmt_voters = (
            select(Voter)
            .where(Voter.election_id == election_id)
            .options(selectinload(Voter.node), selectinload(Voter.group))
        )
        existing_voters = (await db.execute(stmt_voters)).scalars().all()
        if existing_voters:
            for v in existing_voters:
                # Buscar máximo depth de los contests de su grupo
                group_contests = [c for g in election.groups if g.id == v.group_id for c in g.contests]
                if group_contests:
                    max_depth_required = max(c.scope_level.depth for c in group_contests if c.scope_level)
                    if v.node.depth < max_depth_required:
                        errors.append(
                            f"El votante '{v.full_name}' (CI: {v.document_id}) asignado al nodo '{v.node.name}' (nivel {v.node.depth}) no cumple con el nivel mínimo requerido ({max_depth_required}) para los cargos de su grupo."
                        )

        # Si alguna regla falló, devolver 422 con detalle explícito
        if errors:
            raise UnprocessableEntityException(
                "La elección no cumple con los requisitos de consistencia para ser publicada: "
                + " | ".join(errors)
            )

        # =====================================================================
        # Cálculo Determinista de config_hash (RFC 8785)
        # =====================================================================
        canonical_groups = []
        total_contests = 0
        total_constituencies = 0
        total_candidates = 0

        for group in sorted(election.groups, key=lambda g: g.code):
            sorted_levels = [
                {"depth": lvl.depth, "name": lvl.name}
                for lvl in sorted(group.levels, key=lambda l: l.depth)
            ]
            sorted_nodes = [
                {"code": n.code, "name": n.name, "path": n.path, "depth": n.depth}
                for n in sorted(group.nodes, key=lambda n: n.path)
            ]
            sorted_filters = [
                {
                    "key": f.key,
                    "label": f.label,
                    "allowed_values": sorted(f.allowed_values),
                    "is_required": f.is_required,
                }
                for f in sorted(group.filters, key=lambda f: f.key)
            ]

            sorted_contests = []
            for c in sorted(group.contests, key=lambda ct: (ct.display_order, ct.name)):
                total_contests += 1
                sorted_breakdowns = [
                    {"kind": b.kind.value, "label": b.label}
                    for b in sorted(c.breakdowns, key=lambda b: (b.kind.value, b.label))
                ]
                sorted_constituencies = []
                for const in sorted(c.constituencies, key=lambda ct: ct.node.path if ct.node else ""):
                    total_constituencies += 1
                    sorted_cands = [
                        {
                            "name": cd.name,
                            "party_or_front": cd.party_or_front or "",
                            "ballot_order": cd.ballot_order,
                        }
                        for cd in sorted(const.candidates, key=lambda cd: cd.ballot_order)
                    ]
                    total_candidates += len(sorted_cands)
                    sorted_constituencies.append({
                        "node_path": const.node.path if const.node else "",
                        "candidates": sorted_cands,
                    })

                sorted_contests.append({
                    "name": c.name,
                    "allow_blank": c.allow_blank,
                    "allow_null": c.allow_null,
                    "display_order": c.display_order,
                    "scope_level_depth": c.scope_level.depth if c.scope_level else 1,
                    "breakdowns": sorted_breakdowns,
                    "constituencies": sorted_constituencies,
                })

            canonical_groups.append({
                "code": group.code,
                "name": group.name,
                "levels": sorted_levels,
                "nodes": sorted_nodes,
                "filters": sorted_filters,
                "contests": sorted_contests,
            })

        canonical_payload = {
            "schema_version": "votoseguro.config.v1",
            "election_id": str(election.id),
            "organization_id": str(election.organization_id),
            "name": election.name,
            "timezone": election.timezone,
            "k_anonymity": election.k_anonymity,
            "groups": canonical_groups,
        }

        canonical_bytes = json.dumps(
            canonical_payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")
        config_hash = hashlib.sha256(canonical_bytes).hexdigest()

        # =====================================================================
        # Congelamiento y Transición de Estado
        # =====================================================================
        election.config_hash = config_hash
        election.published_at = db_now

        if db_now >= reg_open:
            election.status = ElectionStatus.REGISTRATION_OPEN
        else:
            election.status = ElectionStatus.SCHEDULED

        # Registro en Bitácora Inmutable de Auditoría
        audit_entry = AuditLog(
            organization_id=election.organization_id,
            election_id=election.id,
            actor_id=actor.id,
            actor_role=actor.role.value,
            action="ELECTION_PUBLISHED",
            entity_type="election",
            entity_id=str(election.id),
            payload={
                "config_hash": config_hash,
                "status_after_publication": election.status.value,
                "published_at": db_now.isoformat(),
                "groups_count": len(canonical_groups),
                "contests_count": total_contests,
                "constituencies_count": total_constituencies,
                "candidates_count": total_candidates,
            },
            ip_address=client_ip,
        )
        db.add(audit_entry)

        await db.commit()
        await db.refresh(election)
        return election
