"""
Detector Estadístico de Anomalías de Participación y Explicación Asistida con LFM3-1.7B (IA-L1).
Cumple estrictamente la Invariante #11 (CERO conteos por candidato antes del cierre) y la
Invariante #14 (Trazabilidad y explicaciones basadas únicamente en métricas agregadas).
"""
import math
import uuid
from datetime import datetime, timezone
from typing import Any, List, Optional, Tuple
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.client import LocalLlmEngine
from app.ai.fallbacks import fallback_explain_anomaly
from app.ai.schemas import AnomalyExplanationResponse, AnomalyScanResponse
from app.db.models.election import Election
from app.db.models.structure import UnitNode, VoterGroup
from app.db.models.voter import Voter, VoterStatus
from app.db.models.voting import VoterParticipation, Vote


async def scan_election_anomalies(
    db: AsyncSession,
    election: Election,
    simulate_if_clean: bool = False,
) -> AnomalyScanResponse:
    """
    Escanea la distribución de participación y series horarias de la elección.
    Detecta anomalías estadísticas y genera sus explicaciones con LFM3-1.7B (o fallback).
    """
    election_id = election.id
    org_id = election.organization_id

    # 1. Obtener total de votantes activos y total de votos emitidos
    stmt_active = select(func.count(Voter.id)).where(
        Voter.election_id == election_id,
        Voter.status == VoterStatus.ACTIVE,
    )
    total_active = (await db.execute(stmt_active)).scalar() or 0

    stmt_voted = select(func.count(VoterParticipation.id)).where(
        VoterParticipation.election_id == election_id
    )
    total_voted = (await db.execute(stmt_voted)).scalar() or 0

    part_rate_pct = round((total_voted / total_active * 100.0), 2) if total_active > 0 else 0.0

    raw_anomalies: List[dict[str, Any]] = []

    # 2. Análisis por Nodo Hoja (Anomalía Tipo 1: PARTICIPATION_ZSCORE_OUTLIER)
    # Agrupar votantes activos por nodo
    stmt_nodes = (
        select(
            UnitNode.id,
            UnitNode.name,
            UnitNode.path,
            func.count(Voter.id).label("active_count"),
        )
        .join(Voter, Voter.node_id == UnitNode.id)
        .where(
            Voter.election_id == election_id,
            Voter.status == VoterStatus.ACTIVE,
        )
        .group_by(UnitNode.id, UnitNode.name, UnitNode.path)
        .having(func.count(Voter.id) >= 3)
    )
    node_rows = (await db.execute(stmt_nodes)).all()

    if len(node_rows) >= 2:
        rates: List[Tuple[Any, str, float, int]] = []
        for n_id, n_name, n_path, n_active in node_rows:
            # Contar votos en ese nodo
            stmt_nv = (
                select(func.count(VoterParticipation.id))
                .join(Voter, Voter.id == VoterParticipation.voter_id)
                .where(
                    VoterParticipation.election_id == election_id,
                    Voter.node_id == n_id,
                )
            )
            n_voted = (await db.execute(stmt_nv)).scalar() or 0
            n_rate = (n_voted / n_active * 100.0) if n_active > 0 else 0.0
            rates.append((n_id, n_name, n_rate, n_active))

        all_pcts = [r[2] for r in rates]
        mean_pct = sum(all_pcts) / len(all_pcts)
        variance = sum((p - mean_pct) ** 2 for p in all_pcts) / len(all_pcts)
        std_dev = math.sqrt(variance)

        for n_id, n_name, n_rate, n_active in rates:
            z_score = ((n_rate - mean_pct) / std_dev) if std_dev > 0.001 else 0.0
            # Regla de detección: |z| >= 1.8 o tasa > 90% cuando el promedio general es < 30%
            if abs(z_score) >= 1.8 or (n_rate >= 90.0 and mean_pct < 30.0):
                severity = "HIGH" if (abs(z_score) >= 2.2 or n_rate >= 90.0) else "MEDIUM"
                raw_anomalies.append({
                    "anomaly_id": f"anom-z-{str(n_id)[:8]}",
                    "code": "PARTICIPATION_ZSCORE_OUTLIER",
                    "severity": severity,
                    "target_name": n_name,
                    "metric_value": round(z_score, 2),
                    "baseline_value": round(mean_pct, 1),
                    "sample_size": n_active,
                    "extra_data": {
                        "unit_rate_pct": round(n_rate, 1),
                        "std_dev": round(std_dev, 2),
                    },
                })

    # 3. Análisis de Velocidad Horaria (Anomalía Tipo 2: HOURLY_VELOCITY_SPIKE)
    # Analizar votos emitidos por hora de forma compatible con PostgreSQL y SQLite
    stmt_votes = select(Vote.created_at).where(Vote.election_id == election_id)
    vote_times = (await db.execute(stmt_votes)).scalars().all()

    hourly_counts: dict[str, int] = {}
    for vt in vote_times:
        if vt:
            b_key = vt.strftime("%Y-%m-%d %H:00")
            hourly_counts[b_key] = hourly_counts.get(b_key, 0) + 1

    if hourly_counts and total_voted >= 5:
        counts = list(hourly_counts.values())
        max_hour_count = max(counts)
        pct_in_max_hour = (max_hour_count / total_voted * 100.0)

        mean_hr = sum(counts) / len(counts)
        var_hr = sum((c - mean_hr) ** 2 for c in counts) / len(counts)
        std_hr = math.sqrt(var_hr)

        if pct_in_max_hour >= 65.0 or (max_hour_count > (mean_hr + 2 * std_hr) and max_hour_count >= 5):
            severity = "HIGH" if pct_in_max_hour >= 75.0 else "MEDIUM"
            raw_anomalies.append({
                "anomaly_id": "anom-hr-spike",
                "code": "HOURLY_VELOCITY_SPIKE",
                "severity": severity,
                "target_name": "Ventana Horaria de Concentración Máxima",
                "metric_value": round(pct_in_max_hour, 1),
                "baseline_value": round(mean_hr, 1),
                "sample_size": total_voted,
                "extra_data": {
                    "max_hour_ballots": max_hour_count,
                    "mean_hourly_ballots": round(mean_hr, 1),
                },
            })

    # 4. Asimetría Operativa (Anomalía Tipo 3: ACTIVATION_VS_CAST_GAP)
    if election.status in ("VOTING_OPEN", "VOTING_CLOSED", "TALLIED") and total_active >= 5:
        for n_id, n_name, n_path, n_active in node_rows:
            # Votantes activados
            stmt_act = select(func.count(Voter.id)).where(
                Voter.election_id == election_id,
                Voter.node_id == n_id,
                Voter.status == VoterStatus.ACTIVE,
                Voter.activated_at.is_not(None),
            )
            act_count = (await db.execute(stmt_act)).scalar() or 0
            act_rate = (act_count / n_active * 100.0) if n_active > 0 else 0.0

            stmt_cst = (
                select(func.count(VoterParticipation.id))
                .join(Voter, Voter.id == VoterParticipation.voter_id)
                .where(
                    VoterParticipation.election_id == election_id,
                    Voter.node_id == n_id,
                )
            )
            cst_count = (await db.execute(stmt_cst)).scalar() or 0

            if act_rate >= 80.0 and cst_count == 0:
                raw_anomalies.append({
                    "anomaly_id": f"anom-gap-{str(n_id)[:8]}",
                    "code": "ACTIVATION_VS_CAST_GAP",
                    "severity": "MEDIUM",
                    "target_name": n_name,
                    "metric_value": round(act_rate, 1),
                    "baseline_value": 0.0,
                    "sample_size": n_active,
                    "extra_data": {"activated_count": act_count, "voted_count": 0},
                })

    is_sim = False
    # 5. Escenario Sintético para demostración / pruebas
    if not raw_anomalies and simulate_if_clean:
        is_sim = True
        raw_anomalies.append({
            "anomaly_id": "anom-sim-test-01",
            "code": "PARTICIPATION_ZSCORE_OUTLIER",
            "severity": "HIGH",
            "target_name": "Facultad de Tecnología - Carrera de Redes [ESCENARIO DE PRUEBA ESTADÍSTICO]",
            "metric_value": 2.45,
            "baseline_value": 24.2,
            "sample_size": 150,
            "extra_data": {
                "unit_rate_pct": 88.0,
                "note": "Generado bajo simulación explícita para validación de explicaciones de IA",
            },
        })

    # 6. Generar Explicaciones Asistidas con LFM3-1.7B
    explained_anomalies: List[AnomalyExplanationResponse] = []

    for item in raw_anomalies:
        prompt_text = (
            f"Analiza la siguiente anomalía estadística de participación en una elección institucional:\n"
            f"- Tipo de anomalía: {item['code']}\n"
            f"- Unidad/Segmento: {item['target_name']}\n"
            f"- Métrica observada: {item['metric_value']}\n"
            f"- Valor base de referencia: {item.get('baseline_value')}\n"
            f"- Tamaño de muestra: {item['sample_size']} votantes\n\n"
            f"Genera un objeto JSON con los siguientes campos obligatorios:\n"
            f"- anomaly_id: \"{item['anomaly_id']}\"\n"
            f"- code: \"{item['code']}\"\n"
            f"- severity: \"{item['severity']}\"\n"
            f"- metrics_summary: objeto con las métricas recibidas\n"
            f"- explanation_es: explicación concisa en español (máx 300 caracteres) explicando qué significa la anomalía estadística para los administradores\n"
            f"- recommended_checks: lista de 2 a 3 verificaciones recomendadas a realizar por el administrador humano\n"
            f"- requires_human_decision: true"
        )

        res = await LocalLlmEngine.call_structured(
            prompt=prompt_text,
            schema_cls=AnomalyExplanationResponse,
            fallback_fn=lambda a=item: fallback_explain_anomaly(a),
            system_instruction=(
                "Eres el auditor estadístico asistido de VotoSeguro. "
                "Tu rol es explicar desviaciones en métricas de participación sin emitir juicios políticos "
                "y sugerir verificaciones humanas objetivas. Responde estrictamente en JSON."
            ),
            function_name="IA-L1_ANOMALY_EXPLAIN",
            organization_id=org_id,
            election_id=election_id,
            db=db,
            sanitized_summary=f"Explicación asistida de anomalía de participación ({item['code']})",
        )
        explained_anomalies.append(res)

    return AnomalyScanResponse(
        election_id=str(election_id),
        election_status=election.status,
        total_active_voters=total_active,
        total_ballots_cast=total_voted,
        participation_rate_pct=part_rate_pct,
        anomalies_found_count=len(explained_anomalies),
        anomalies=explained_anomalies,
        scanned_at_utc=datetime.now(timezone.utc).isoformat(),
        is_simulation=is_sim,
    )
