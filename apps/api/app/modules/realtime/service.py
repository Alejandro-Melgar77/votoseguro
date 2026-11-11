"""
Servicio de Métricas en Tiempo Real (S2-04)
INVARIANTE #11: Resultados sellados y protegidos durante el sufragio.
Solo calcula métricas agregadas de participación y empadronamiento.
Cero conteos por candidato o tendencias de ganadores.
"""
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import NotFoundException
from app.core.time import TimeProvider
from app.db.models.election import Election
from app.db.models.structure import UnitNode, VoterGroup
from app.db.models.user import AdminAssignment, User, UserRole
from app.db.models.voter import Voter, VoterStatus
from app.db.models.voting import VoterParticipation
from app.modules.realtime.schemas import (
    HourlyVotesBucketDTO,
    LiveDashboardSnapshot,
    ParticipationMetricsDTO,
    RegistrationMetricsDTO,
    SegmentBreakdownItemDTO,
)


class RealtimeMonitoringService:
    @staticmethod
    async def get_live_dashboard_snapshot(
        db: AsyncSession,
        election_id: uuid.UUID,
        user: User | None = None,
        time_provider: TimeProvider | None = None,
    ) -> LiveDashboardSnapshot:
        election = await db.get(Election, election_id)
        if not election:
            raise NotFoundException(f"Elección con ID {election_id} no encontrada.")

        now_utc = await time_provider.now(db) if time_provider else datetime.now(timezone.utc)

        # 1. Determinar filtros de alcance para ADMIN_SEGMENT
        segment_group_id: uuid.UUID | None = None
        segment_node_path: str | None = None

        if user and user.role == UserRole.ADMIN_SEGMENT:
            stmt_assign = select(AdminAssignment).where(
                AdminAssignment.user_id == user.id,
                AdminAssignment.organization_id == election.organization_id,
            )
            assignment = (await db.execute(stmt_assign)).scalar_one_or_none()
            if assignment:
                segment_group_id = assignment.group_id
                if assignment.node_id:
                    node = await db.get(UnitNode, assignment.node_id)
                    if node:
                        segment_node_path = node.path

        # 2. Métricas de Empadronamiento
        stmt_voters = select(Voter).options(selectinload(Voter.node)).where(Voter.election_id == election_id)
        if segment_group_id:
            stmt_voters = stmt_voters.where(Voter.group_id == segment_group_id)

        all_voters = (await db.execute(stmt_voters)).scalars().all()

        if segment_node_path:
            all_voters = [v for v in all_voters if v.node and v.node.path.startswith(segment_node_path)]

        counts: dict[str, int] = defaultdict(int)
        for v in all_voters:
            status_str = v.status.value if hasattr(v.status, "value") else str(v.status)
            counts[status_str] += 1

        total_voters = len(all_voters)
        active_count = counts.get("ACTIVE", 0)
        imported_count = counts.get("IMPORTED", 0)
        invited_count = counts.get("INVITED", 0)
        blocked_count = counts.get("BLOCKED", 0)
        pending_count = counts.get("PENDING_APPROVAL", 0)

        activation_rate = round((active_count / total_voters * 100), 2) if total_voters > 0 else 0.0

        registration_metrics = RegistrationMetricsDTO(
            imported=imported_count,
            invited=invited_count,
            active=active_count,
            blocked=blocked_count,
            pending_approval=pending_count,
            total=total_voters,
            activation_rate_pct=activation_rate,
        )

        # 3. Métricas de Participación
        stmt_parts = select(VoterParticipation).options(selectinload(VoterParticipation.node)).where(
            VoterParticipation.election_id == election_id
        )
        if segment_group_id:
            stmt_parts = stmt_parts.where(VoterParticipation.group_id == segment_group_id)

        all_parts = (await db.execute(stmt_parts)).scalars().all()
        if segment_node_path:
            all_parts = [p for p in all_parts if p.node and p.node.path.startswith(segment_node_path)]

        total_voted = len(all_parts)
        abstention = max(0, active_count - total_voted)
        part_rate = round((total_voted / active_count * 100), 2) if active_count > 0 else 0.0

        participation_metrics = ParticipationMetricsDTO(
            total_eligible_active=active_count,
            total_voted=total_voted,
            abstention_count=abstention,
            participation_rate_pct=part_rate,
        )

        # 4. Desglose Territorial por Segmento / Nodo
        # Agrupar votantes activos y participaciones por (group_id, node_id)
        voters_by_node: dict[tuple[uuid.UUID, uuid.UUID], int] = defaultdict(int)
        for v in all_voters:
            if (v.status.value if hasattr(v.status, "value") else str(v.status)) == "ACTIVE":
                voters_by_node[(v.group_id, v.node_id)] += 1

        voted_by_node: dict[tuple[uuid.UUID, uuid.UUID], int] = defaultdict(int)
        for p in all_parts:
            voted_by_node[(p.group_id, p.node_id)] += 1

        # Cargar grupos y nodos involucrados
        segment_items: list[SegmentBreakdownItemDTO] = []
        stmt_groups = select(VoterGroup).where(VoterGroup.election_id == election_id)
        groups = (await db.execute(stmt_groups)).scalars().all()
        groups_map = {g.id: g.name for g in groups}

        all_node_keys = set(voters_by_node.keys()) | set(voted_by_node.keys())
        for gid, nid in all_node_keys:
            node = await db.get(UnitNode, nid)
            g_name = groups_map.get(gid, "Grupo")
            n_name = node.name if node else "Nodo"
            n_path = node.path if node else "/"
            act = voters_by_node[(gid, nid)]
            vot = voted_by_node[(gid, nid)]
            pct = round((vot / act * 100), 2) if act > 0 else 0.0

            segment_items.append(
                SegmentBreakdownItemDTO(
                    group_id=str(gid),
                    group_name=g_name,
                    node_id=str(nid),
                    node_name=n_name,
                    node_path=n_path,
                    active_voters=act,
                    votes_cast=vot,
                    participation_pct=pct,
                )
            )

        segment_items.sort(key=lambda s: s.node_path)

        # 5. Serie Temporal de Votos por Hora
        hourly_counts: dict[str, int] = defaultdict(int)
        for p in all_parts:
            dt = p.completed_at
            bucket_key = dt.strftime("%Y-%m-%d %H:00")
            hourly_counts[bucket_key] += 1

        hourly_series: list[HourlyVotesBucketDTO] = []
        cumulative = 0
        sorted_buckets = sorted(hourly_counts.keys())
        for b in sorted_buckets:
            cast = hourly_counts[b]
            cumulative += cast
            # Formatear etiqueta local
            try:
                hour_part = b.split(" ")[1][:2]
                label = f"{hour_part}:00"
            except Exception:
                label = b

            hourly_series.append(
                HourlyVotesBucketDTO(
                    hour_bucket_utc=b,
                    hour_label_local=label,
                    ballots_cast=cast,
                    cumulative_ballots=cumulative,
                )
            )

        return LiveDashboardSnapshot(
            election_id=election.id,
            election_name=election.name,
            status=election.status.value,
            server_now_utc=now_utc,
            config_hash=election.config_hash,
            roll_hash=election.roll_hash,
            merkle_root=election.merkle_root,
            registration_metrics=registration_metrics,
            participation_metrics=participation_metrics,
            segment_breakdown=segment_items,
            hourly_votes_series=hourly_series,
        )
