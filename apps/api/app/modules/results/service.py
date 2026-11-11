"""
Servicio de Negocio para Cómputo de Resultados Oficiales, Desgloses y k-Anonimato (S1-10)
"""
import uuid
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.dependencies import TenantContext
from app.core.exceptions import (
    ConflictException,
    ForbiddenException,
    NotFoundException,
)
from app.core.time import TimeProvider
from app.db.models.election import Election, ElectionStatus
from app.db.models.structure import (
    BreakdownKind,
    Candidate,
    Constituency,
    Contest,
    ContestBreakdown,
    FilterDefinition,
    HierarchyLevel,
    UnitNode,
    VoterGroup,
)
from app.db.models.voter import Voter, VoterStatus
from app.db.models.voting import Vote, VoteChoiceType, VoterParticipation
from app.modules.audit.service import AuditService
from app.modules.results.schemas import (
    BreakdownCellResult,
    CandidateResultItem,
    ConstituencyResult,
    ContestBreakdownResult,
    ContestResult,
    ElectionResultsResponse,
    GroupParticipationItem,
    GroupResult,
    NodeParticipationItem,
    ParticipationMetricsResponse,
)


class ResultsService:
    @staticmethod
    async def close_voting_now(
        db: AsyncSession,
        election_id: uuid.UUID,
        reason: str,
        tenant: TenantContext,
        time_provider: TimeProvider,
    ) -> dict[str, str]:
        """Cierra la votación manualmente (exclusivo ADMIN_GENERAL) para iniciar el escrutinio."""
        db_now = await time_provider.now(db)

        stmt = select(Election).where(
            Election.id == election_id,
            Election.organization_id == tenant.organization_id,
        )
        election = (await db.execute(stmt)).scalar_one_or_none()
        if not election:
            raise NotFoundException("Elección no encontrada en su institución.")

        if election.status not in (ElectionStatus.VOTING_OPEN, ElectionStatus.REGISTRATION_CLOSED):
            raise ConflictException(
                "La elección únicamente puede cerrarse si se encuentra en VOTING_OPEN o REGISTRATION_CLOSED."
            )

        election.status = ElectionStatus.VOTING_CLOSED
        election.voting_closed_at = db_now
        election.updated_at = db_now

        await AuditService.log_event(
            db=db,
            action="ELECTION_VOTING_CLOSED",
            entity_type="election",
            entity_id=str(election.id),
            actor_role=tenant.user.role.value,
            actor_id=tenant.user.id,
            organization_id=tenant.organization_id,
            election_id=election.id,
            payload={"reason": reason, "timestamp": db_now.isoformat()},
        )
        await db.commit()

        return {
            "message": "Votación cerrada oficialmente. Urnas clausuradas para cómputo definitivo.",
            "status": election.status.value,
        }

    @staticmethod
    async def get_participation_metrics(
        db: AsyncSession,
        election_id: uuid.UUID,
        tenant: TenantContext,
    ) -> ParticipationMetricsResponse:
        """Calcula las métricas de participación ciudadana en tiempo real."""
        stmt_el = select(Election).where(
            Election.id == election_id,
            Election.organization_id == tenant.organization_id,
        )
        election = (await db.execute(stmt_el)).scalar_one_or_none()
        if not election:
            raise NotFoundException("Elección no encontrada en su institución.")

        # Cargar grupos de la elección
        stmt_groups = (
            select(VoterGroup)
            .where(VoterGroup.election_id == election_id)
            .order_by(VoterGroup.name.asc())
        )
        groups = (await db.execute(stmt_groups)).scalars().all()

        # Filtrar si es ADMIN_SEGMENT
        if tenant.is_segment_admin() and tenant.assignments:
            allowed_group_ids = {a.group_id for a in tenant.assignments}
            groups = [g for g in groups if g.id in allowed_group_ids]

        # Cargar votantes activos y participaciones
        stmt_voters = select(Voter).where(
            Voter.election_id == election_id,
            Voter.status == VoterStatus.ACTIVE,
        )
        active_voters = (await db.execute(stmt_voters)).scalars().all()

        stmt_part = select(VoterParticipation).where(
            VoterParticipation.election_id == election_id
        )
        participations = (await db.execute(stmt_part)).scalars().all()
        participated_voter_ids = {p.voter_id for p in participations}

        total_active = len(active_voters)
        total_voted = len(participated_voter_ids)
        overall_pct = round((total_voted / total_active * 100), 2) if total_active > 0 else 0.0

        group_items: list[GroupParticipationItem] = []
        for g in groups:
            g_active = [v for v in active_voters if v.group_id == g.id]
            g_voted = [v for v in g_active if v.id in participated_voter_ids]

            g_active_cnt = len(g_active)
            g_voted_cnt = len(g_voted)
            g_pct = round((g_voted_cnt / g_active_cnt * 100), 2) if g_active_cnt > 0 else 0.0

            # Nodos del grupo
            stmt_nodes = (
                select(UnitNode)
                .where(UnitNode.group_id == g.id)
                .order_by(UnitNode.depth.asc(), UnitNode.path.asc())
            )
            nodes = (await db.execute(stmt_nodes)).scalars().all()

            node_items: list[NodeParticipationItem] = []
            for n in nodes:
                # Si es ADMIN_SEGMENT, filtrar nodos fuera de su asignación
                if tenant.is_segment_admin() and tenant.assignments:
                    allowed = False
                    for a in tenant.assignments:
                        if a.group_id == g.id:
                            if not a.node_id:
                                allowed = True
                                break
                            elif a.node and n.path.startswith(a.node.path):
                                allowed = True
                                break
                    if not allowed:
                        continue

                n_active = [v for v in g_active if v.node and v.node.path.startswith(n.path)]
                n_voted = [v for v in n_active if v.id in participated_voter_ids]
                n_act_cnt = len(n_active)
                n_vot_cnt = len(n_voted)
                n_pct = round((n_vot_cnt / n_act_cnt * 100), 2) if n_act_cnt > 0 else 0.0

                node_items.append(
                    NodeParticipationItem(
                        node_id=n.id,
                        node_name=n.name,
                        node_code=n.code,
                        node_path=n.path,
                        depth=n.depth,
                        active_voters=n_act_cnt,
                        voted_count=n_vot_cnt,
                        participation_rate_pct=n_pct,
                    )
                )

            group_items.append(
                GroupParticipationItem(
                    group_id=g.id,
                    group_name=g.name,
                    group_code=g.code,
                    active_voters=g_active_cnt,
                    voted_count=g_voted_cnt,
                    participation_rate_pct=g_pct,
                    nodes=node_items,
                )
            )

        return ParticipationMetricsResponse(
            election_id=election.id,
            election_name=election.name,
            total_active_voters=total_active,
            total_voted=total_voted,
            participation_rate_pct=overall_pct,
            by_group=group_items,
        )

    @staticmethod
    async def compute_election_results(
        db: AsyncSession,
        election_id: uuid.UUID,
        tenant: TenantContext,
    ) -> ElectionResultsResponse:
        """
        Invariante #11 y #12: Escrutinio Oficial, Desgloses Jerárquicos y k-Anonimato.
        - Rechaza con 403 Forbidden antes del cierre (VOTING_CLOSED).
        - Total de circunscripción 100% exacto y matemáticamente verificado.
        - Celdas de desgloses con menos de k votos se redactan para preservar el secreto del voto.
        """
        # 1. Cargar elección
        stmt_el = select(Election).where(
            Election.id == election_id,
            Election.organization_id == tenant.organization_id,
        )
        election = (await db.execute(stmt_el)).scalar_one_or_none()
        if not election:
            raise NotFoundException("Elección no encontrada en su institución.")

        # Invariante #11: Bloqueo estricto antes del cierre de urnas
        if election.status not in (ElectionStatus.VOTING_CLOSED, ElectionStatus.TALLIED):
            raise ForbiddenException(
                "Los resultados por candidato están estrictamente bloqueados hasta el cierre oficial "
                "de la votación (VOTING_CLOSED)."
            )

        k = election.k_anonymity

        # 2. Cargar todos los votos de la elección
        stmt_votes = select(Vote).where(Vote.election_id == election_id)
        all_votes = (await db.execute(stmt_votes)).scalars().all()

        # Agrupar votos por circunscripción
        votes_by_constituency: dict[uuid.UUID, list[Vote]] = {}
        for v in all_votes:
            votes_by_constituency.setdefault(v.constituency_id, []).append(v)

        # 3. Cargar estructura: Grupos, Niveles, Cargos, Desgloses, Circunscripciones, Candidatos
        stmt_groups = (
            select(VoterGroup)
            .where(VoterGroup.election_id == election_id)
            .order_by(VoterGroup.name.asc())
        )
        groups = (await db.execute(stmt_groups)).scalars().all()

        # Filtrar si es ADMIN_SEGMENT
        if tenant.is_segment_admin() and tenant.assignments:
            allowed_group_ids = {a.group_id for a in tenant.assignments}
            groups = [g for g in groups if g.id in allowed_group_ids]

        group_results: list[GroupResult] = []

        for group in groups:
            # Cargar niveles del grupo
            stmt_levels = select(HierarchyLevel).where(HierarchyLevel.group_id == group.id)
            levels_map = {l.id: l for l in (await db.execute(stmt_levels)).scalars().all()}

            # Cargar filtros extra del grupo
            stmt_filters = select(FilterDefinition).where(FilterDefinition.group_id == group.id)
            filters_map = {f.id: f for f in (await db.execute(stmt_filters)).scalars().all()}

            # Cargar cargos del grupo con desgloses
            stmt_contests = (
                select(Contest)
                .options(selectinload(Contest.breakdowns))
                .where(Contest.group_id == group.id)
                .order_by(Contest.display_order.asc(), Contest.name.asc())
            )
            contests = (await db.execute(stmt_contests)).scalars().all()

            contest_results: list[ContestResult] = []

            for contest in contests:
                scope_level = levels_map.get(contest.scope_level_id)
                scope_level_name = scope_level.name if scope_level else "General"

                # Cargar circunscripciones del cargo con nodo
                stmt_const = (
                    select(Constituency)
                    .options(
                        selectinload(Constituency.node),
                        selectinload(Constituency.candidates),
                    )
                    .where(Constituency.contest_id == contest.id)
                    .order_by(Constituency.id.asc())
                )
                constituencies = (await db.execute(stmt_const)).scalars().all()

                const_results: list[ConstituencyResult] = []

                for const in constituencies:
                    c_node = const.node
                    if not c_node:
                        continue

                    # Filtrar si es ADMIN_SEGMENT
                    if tenant.is_segment_admin() and tenant.assignments:
                        allowed = False
                        for a in tenant.assignments:
                            if a.group_id == group.id:
                                if not a.node_id:
                                    allowed = True
                                    break
                                elif a.node and c_node.path.startswith(a.node.path):
                                    allowed = True
                                    break
                        if not allowed:
                            continue

                    const_votes = votes_by_constituency.get(const.id, [])
                    total_cast = len(const_votes)

                    # Contar candidatos, blancos, nulos
                    cand_counts: dict[uuid.UUID, int] = {c.id: 0 for c in const.candidates}
                    blank_count = 0
                    null_count = 0

                    for v in const_votes:
                        if v.choice_type == VoteChoiceType.CANDIDATE and v.candidate_id:
                            cand_counts[v.candidate_id] = cand_counts.get(v.candidate_id, 0) + 1
                        elif v.choice_type == VoteChoiceType.BLANK:
                            blank_count += 1
                        elif v.choice_type == VoteChoiceType.NULL:
                            null_count += 1

                    candidates_total = sum(cand_counts.values())
                    exact_match = (candidates_total + blank_count + null_count == total_cast)

                    # Candidatos ordenados por cantidad de votos desc, luego por ballot_order
                    candidates_dtos: list[CandidateResultItem] = []
                    sorted_cands = sorted(
                        const.candidates,
                        key=lambda c: (-cand_counts.get(c.id, 0), c.ballot_order),
                    )
                    for c in sorted_cands:
                        v_cnt = cand_counts.get(c.id, 0)
                        pct = round((v_cnt / total_cast * 100), 2) if total_cast > 0 else 0.0
                        candidates_dtos.append(
                            CandidateResultItem(
                                candidate_id=c.id,
                                full_name=getattr(c, "name", "") or getattr(c, "full_name", ""),
                                ballot_number=getattr(c, "ballot_order", 1),
                                ballot_order=c.ballot_order,
                                party_affiliation=getattr(c, "party_or_front", None),
                                party_color=getattr(c, "party_color", None),
                                photo_url=c.photo_url,
                                votes_count=v_cnt,
                                percentage=pct,
                            )
                        )

                    # -------------------------------------------------------------
                    # Desgloses Configurados (ContestBreakdown) + k-Anonimato
                    # -------------------------------------------------------------
                    breakdown_results: list[ContestBreakdownResult] = []

                    for bd in contest.breakdowns:
                        cells: list[BreakdownCellResult] = []

                        if bd.kind == BreakdownKind.LEVEL and bd.level_id:
                            target_level = levels_map.get(bd.level_id)
                            # Cargar nodos del nivel que sean descendientes del nodo de la circunscripción
                            stmt_subnodes = (
                                select(UnitNode)
                                .where(
                                    UnitNode.group_id == group.id,
                                    UnitNode.level_id == bd.level_id,
                                )
                                .order_by(UnitNode.name.asc())
                            )
                            sub_nodes = (await db.execute(stmt_subnodes)).scalars().all()
                            matching_nodes = [
                                sn for sn in sub_nodes if sn.path.startswith(c_node.path)
                            ]

                            for sn in matching_nodes:
                                cell_votes = [
                                    v for v in const_votes if v.segment_path.startswith(sn.path)
                                ]
                                n_cell = len(cell_votes)

                                # Invariante #12: k-anonimato
                                if 0 < n_cell < k:
                                    cells.append(
                                        BreakdownCellResult(
                                            cell_id=str(sn.id),
                                            cell_name=sn.name,
                                            cell_code=sn.code,
                                            cell_path=sn.path,
                                            total_votes=n_cell,
                                            redacted_by_k_anonymity=True,
                                            k_threshold=k,
                                            k_anonymity_message=(
                                                f"< {k} votos (Protegido por k-anonimato para resguardar el secreto del sufragio)"
                                            ),
                                            candidates=None,
                                            blank_count=None,
                                            null_count=None,
                                        )
                                    )
                                else:
                                    # Desglose normal
                                    cell_cand_counts = {c.id: 0 for c in const.candidates}
                                    cell_blank = 0
                                    cell_null = 0
                                    for cv in cell_votes:
                                        if cv.choice_type == VoteChoiceType.CANDIDATE and cv.candidate_id:
                                            cell_cand_counts[cv.candidate_id] = (
                                                cell_cand_counts.get(cv.candidate_id, 0) + 1
                                            )
                                        elif cv.choice_type == VoteChoiceType.BLANK:
                                            cell_blank += 1
                                        elif cv.choice_type == VoteChoiceType.NULL:
                                            cell_null += 1

                                    cell_cands_dto: list[CandidateResultItem] = []
                                    for c in sorted_cands:
                                        cv_cnt = cell_cand_counts.get(c.id, 0)
                                        c_pct = round((cv_cnt / n_cell * 100), 2) if n_cell > 0 else 0.0
                                        cell_cands_dto.append(
                                            CandidateResultItem(
                                                candidate_id=c.id,
                                                full_name=getattr(c, "name", "") or getattr(c, "full_name", ""),
                                                ballot_number=getattr(c, "ballot_order", 1),
                                                ballot_order=c.ballot_order,
                                                party_affiliation=getattr(c, "party_or_front", None),
                                                party_color=getattr(c, "party_color", None),
                                                photo_url=c.photo_url,
                                                votes_count=cv_cnt,
                                                percentage=c_pct,
                                            )
                                        )

                                    cells.append(
                                        BreakdownCellResult(
                                            cell_id=str(sn.id),
                                            cell_name=sn.name,
                                            cell_code=sn.code,
                                            cell_path=sn.path,
                                            total_votes=n_cell,
                                            redacted_by_k_anonymity=False,
                                            k_threshold=k,
                                            k_anonymity_message=None,
                                            candidates=cell_cands_dto,
                                            blank_count=cell_blank,
                                            null_count=cell_null,
                                        )
                                    )

                            breakdown_results.append(
                                ContestBreakdownResult(
                                    breakdown_id=bd.id,
                                    kind=bd.kind.value,
                                    label=bd.label,
                                    level_id=bd.level_id,
                                    level_name=target_level.name if target_level else None,
                                    filter_id=None,
                                    filter_key=None,
                                    cells=cells,
                                )
                            )

                        elif bd.kind == BreakdownKind.FILTER and bd.filter_id:
                            target_filter = filters_map.get(bd.filter_id)
                            allowed_values = target_filter.allowed_values if target_filter else []
                            filter_key = target_filter.key if target_filter else "filtro"

                            for val in allowed_values:
                                cell_votes = [
                                    v
                                    for v in const_votes
                                    if v.filters_snapshot and v.filters_snapshot.get(filter_key) == val
                                ]
                                n_cell = len(cell_votes)

                                if 0 < n_cell < k:
                                    cells.append(
                                        BreakdownCellResult(
                                            cell_id=f"{filter_key}:{val}",
                                            cell_name=str(val),
                                            cell_code=None,
                                            cell_path=None,
                                            total_votes=n_cell,
                                            redacted_by_k_anonymity=True,
                                            k_threshold=k,
                                            k_anonymity_message=(
                                                f"< {k} votos (Protegido por k-anonimato)"
                                            ),
                                            candidates=None,
                                            blank_count=None,
                                            null_count=None,
                                        )
                                    )
                                else:
                                    cell_cand_counts = {c.id: 0 for c in const.candidates}
                                    cell_blank = 0
                                    cell_null = 0
                                    for cv in cell_votes:
                                        if cv.choice_type == VoteChoiceType.CANDIDATE and cv.candidate_id:
                                            cell_cand_counts[cv.candidate_id] = (
                                                cell_cand_counts.get(cv.candidate_id, 0) + 1
                                            )
                                        elif cv.choice_type == VoteChoiceType.BLANK:
                                            cell_blank += 1
                                        elif cv.choice_type == VoteChoiceType.NULL:
                                            cell_null += 1

                                    cell_cands_dto = [
                                        CandidateResultItem(
                                            candidate_id=c.id,
                                            full_name=getattr(c, "name", "") or getattr(c, "full_name", ""),
                                            ballot_number=getattr(c, "ballot_order", 1),
                                            ballot_order=c.ballot_order,
                                            party_affiliation=getattr(c, "party_or_front", None),
                                            party_color=getattr(c, "party_color", None),
                                            photo_url=c.photo_url,
                                            votes_count=cell_cand_counts.get(c.id, 0),
                                            percentage=round((cell_cand_counts.get(c.id, 0) / n_cell * 100), 2)
                                            if n_cell > 0
                                            else 0.0,
                                        )
                                        for c in sorted_cands
                                    ]

                                    cells.append(
                                        BreakdownCellResult(
                                            cell_id=f"{filter_key}:{val}",
                                            cell_name=str(val),
                                            cell_code=None,
                                            cell_path=None,
                                            total_votes=n_cell,
                                            redacted_by_k_anonymity=False,
                                            k_threshold=k,
                                            k_anonymity_message=None,
                                            candidates=cell_cands_dto,
                                            blank_count=cell_blank,
                                            null_count=cell_null,
                                        )
                                    )

                            breakdown_results.append(
                                ContestBreakdownResult(
                                    breakdown_id=bd.id,
                                    kind=bd.kind.value,
                                    label=bd.label,
                                    level_id=None,
                                    level_name=None,
                                    filter_id=bd.filter_id,
                                    filter_key=filter_key,
                                    cells=cells,
                                )
                            )

                    const_results.append(
                        ConstituencyResult(
                            constituency_id=const.id,
                            node_id=c_node.id,
                            node_name=c_node.name,
                            node_code=c_node.code,
                            node_path=c_node.path,
                            total_cast=total_cast,
                            candidates_total=candidates_total,
                            blank_count=blank_count,
                            null_count=null_count,
                            exact_match_verified=exact_match,
                            candidates=candidates_dtos,
                            breakdowns=breakdown_results,
                        )
                    )

                contest_results.append(
                    ContestResult(
                        contest_id=contest.id,
                        contest_name=contest.name,
                        contest_code=getattr(contest, "code", None) or contest.name[:4].upper(),
                        description=contest.description,
                        scope_level_id=contest.scope_level_id,
                        scope_level_name=scope_level_name,
                        allow_blank=contest.allow_blank,
                        allow_null=contest.allow_null,
                        constituencies=const_results,
                    )
                )

            group_results.append(
                GroupResult(
                    group_id=group.id,
                    group_name=group.name,
                    group_code=group.code,
                    contests=contest_results,
                )
            )

        return ElectionResultsResponse(
            election_id=election.id,
            election_name=election.name,
            status=election.status.value,
            timezone=election.timezone,
            k_anonymity=election.k_anonymity,
            config_hash=election.config_hash,
            roll_hash=election.roll_hash,
            voting_closed_at=election.voting_closed_at,
            groups=group_results,
        )
