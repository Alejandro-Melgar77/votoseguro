"""
Pruebas de Invariantes para Cómputo de Resultados, Desgloses y k-Anonimato (S1-10)
- Invariante #11: Resultados sellados y bloqueados estrictamente con 403 Forbidden antes de VOTING_CLOSED.
- Invariante #12: Aplicación estricta de k-anonimato en desgloses jerárquicos (redacción si votos < k).
- Cómputo exacto de circunscripción y conciliación matemática 100% verificada.
"""
from datetime import datetime, timedelta, timezone
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.time import FakeTimeProvider
from app.db.models.election import Election, ElectionStatus
from app.db.models.structure import (
    BreakdownKind,
    Candidate,
    Constituency,
    Contest,
    ContestBreakdown,
    HierarchyLevel,
    UnitNode,
    VoterGroup,
)
from app.db.models.voting import Vote, VoteChoiceType


@pytest.mark.asyncio
async def test_results_sealed_before_closing_and_k_anonymity(
    test_db: AsyncSession,
    client: AsyncClient,
    org1_setup,
    fake_time: FakeTimeProvider,
):
    org, admin, admin_token = org1_setup
    now = datetime(2026, 11, 25, 12, 0, 0, tzinfo=timezone.utc)
    fake_time.set_time(now)

    t_reg_open = now - timedelta(days=5)
    t_reg_close = now - timedelta(days=2)
    t_vote_open = now - timedelta(hours=4)
    t_vote_close = now + timedelta(hours=4)

    # 1. Crear Elección en VOTING_OPEN con k=5
    election = Election(
        organization_id=org.id,
        name="Elección General con k-Anonimato S1-10",
        timezone="America/La_Paz",
        registration_opens_at=t_reg_open,
        registration_closes_at=t_reg_close,
        voting_opens_at=t_vote_open,
        voting_closes_at=t_vote_close,
        status=ElectionStatus.VOTING_OPEN,
        k_anonymity=5,
        created_by=admin.id,
    )
    test_db.add(election)
    await test_db.flush()

    # 2. Grupo Estudiantes con 3 niveles jerárquicos
    grp = VoterGroup(organization_id=org.id, election_id=election.id, name="ESTUDIANTES", code="EST")
    test_db.add(grp)
    await test_db.flush()

    lvl_univ = HierarchyLevel(group_id=grp.id, depth=1, name="Universidad")
    lvl_fac = HierarchyLevel(group_id=grp.id, depth=2, name="Facultad")
    lvl_car = HierarchyLevel(group_id=grp.id, depth=3, name="Carrera")
    test_db.add_all([lvl_univ, lvl_fac, lvl_car])
    await test_db.flush()

    node_univ = UnitNode(group_id=grp.id, level_id=lvl_univ.id, parent_id=None, name="Universidad Central", code="UC", path="/UC/", depth=1)
    test_db.add(node_univ)
    await test_db.flush()

    node_ficct = UnitNode(group_id=grp.id, level_id=lvl_fac.id, parent_id=node_univ.id, name="Facultad de Tecnología", code="TEC", path="/UC/TEC/", depth=2)
    test_db.add(node_ficct)
    await test_db.flush()

    node_inf = UnitNode(group_id=grp.id, level_id=lvl_car.id, parent_id=node_ficct.id, name="Ingeniería de Sistemas", code="SIS", path="/UC/TEC/SIS/", depth=3)
    node_civ = UnitNode(group_id=grp.id, level_id=lvl_car.id, parent_id=node_ficct.id, name="Ingeniería Civil", code="CIV", path="/UC/TEC/CIV/", depth=3)
    test_db.add_all([node_inf, node_civ])
    await test_db.flush()

    # 3. Cargo Rectorado con desglose configurado a nivel Carrera
    c_rector = Contest(
        group_id=grp.id,
        scope_level_id=lvl_univ.id,
        name="Rectorado Universitario",
        display_order=1,
        allow_blank=True,
        allow_null=True,
    )
    test_db.add(c_rector)
    await test_db.flush()

    bd_carrera = ContestBreakdown(
        contest_id=c_rector.id,
        kind=BreakdownKind.LEVEL,
        level_id=lvl_car.id,
        label="Por Carrera",
    )
    test_db.add(bd_carrera)
    await test_db.flush()

    const_rec = Constituency(contest_id=c_rector.id, node_id=node_univ.id)
    test_db.add(const_rec)
    await test_db.flush()

    cand1 = Candidate(constituency_id=const_rec.id, name="Dra. María Paz", party_or_front="Frente Renovación", ballot_order=1)
    cand2 = Candidate(constituency_id=const_rec.id, name="Dr. Carlos Roca", party_or_front="Frente Autonomía", ballot_order=2)
    test_db.add_all([cand1, cand2])
    await test_db.flush()

    # 4. Sembrar votos directamente en la urna (tabla vote):
    # - En SIS: 6 votos (>= k=5) -> 4 para cand1, 2 para cand2
    # - En CIV: 2 votos (< k=5)  -> 1 para cand1, 1 para cand2
    # Total de la circunscripción: 8 votos (5 para cand1, 3 para cand2)
    import hashlib
    votes_to_insert = []
    # 4 votos cand1 en SIS
    for i in range(4):
        votes_to_insert.append(
            Vote(
                election_id=election.id,
                constituency_id=const_rec.id,
                choice_type=VoteChoiceType.CANDIDATE,
                candidate_id=cand1.id,
                encoded_payload="ENCODED",
                segment_path="/UC/TEC/SIS/",
                filters_snapshot={},
                nullifier=hashlib.sha256(f"nullifier_sis_c1_{i}".encode()).hexdigest(),
                receipt_hash=hashlib.sha256(f"receipt_sis_c1_{i}".encode()).hexdigest(),
                created_at=now,
            )
        )
    # 2 votos cand2 en SIS
    for i in range(2):
        votes_to_insert.append(
            Vote(
                election_id=election.id,
                constituency_id=const_rec.id,
                choice_type=VoteChoiceType.CANDIDATE,
                candidate_id=cand2.id,
                encoded_payload="ENCODED",
                segment_path="/UC/TEC/SIS/",
                filters_snapshot={},
                nullifier=hashlib.sha256(f"nullifier_sis_c2_{i}".encode()).hexdigest(),
                receipt_hash=hashlib.sha256(f"receipt_sis_c2_{i}".encode()).hexdigest(),
                created_at=now,
            )
        )
    # 1 voto cand1 en CIV
    votes_to_insert.append(
        Vote(
            election_id=election.id,
            constituency_id=const_rec.id,
            choice_type=VoteChoiceType.CANDIDATE,
            candidate_id=cand1.id,
            encoded_payload="ENCODED",
            segment_path="/UC/TEC/CIV/",
            filters_snapshot={},
            nullifier=hashlib.sha256(b"nullifier_civ_c1").hexdigest(),
            receipt_hash=hashlib.sha256(b"receipt_civ_c1").hexdigest(),
            created_at=now,
        )
    )
    # 1 voto cand2 en CIV
    votes_to_insert.append(
        Vote(
            election_id=election.id,
            constituency_id=const_rec.id,
            choice_type=VoteChoiceType.CANDIDATE,
            candidate_id=cand2.id,
            encoded_payload="ENCODED",
            segment_path="/UC/TEC/CIV/",
            filters_snapshot={},
            nullifier=hashlib.sha256(b"nullifier_civ_c2").hexdigest(),
            receipt_hash=hashlib.sha256(b"receipt_civ_c2").hexdigest(),
            created_at=now,
        )
    )
    test_db.add_all(votes_to_insert)
    await test_db.commit()

    headers = {"Authorization": f"Bearer {admin_token}"}

    # =========================================================================
    # INVARIANTE #11: Resultados sellados antes del cierre (VOTING_OPEN)
    # =========================================================================
    res_open = await client.get(f"/elections/{election.id}/results", headers=headers)
    assert res_open.status_code == 403
    assert "bloqueados" in res_open.json()["detail"] or "VOTING_CLOSED" in res_open.json()["detail"]

    # =========================================================================
    # Cierre oficial de la votación
    # =========================================================================
    res_close = await client.post(
        f"/elections/{election.id}/voting/close-now",
        headers=headers,
        json={"reason": "Cierre formal de urna para cómputo oficial."},
    )
    assert res_close.status_code == 200
    assert res_close.json()["status"] == "VOTING_CLOSED"

    # =========================================================================
    # Cómputo de Resultados Oficiales y Conciliación
    # =========================================================================
    res_results = await client.get(f"/elections/{election.id}/results", headers=headers)
    assert res_results.status_code == 200
    results_data = res_results.json()

    assert results_data["election_id"] == str(election.id)
    assert results_data["k_anonymity"] == 5

    group_data = results_data["groups"][0]
    contest_data = group_data["contests"][0]
    const_data = contest_data["constituencies"][0]

    # Verificación total de circunscripción
    assert const_data["total_cast"] == 8
    assert const_data["exact_match_verified"] is True
    assert const_data["blank_count"] == 0
    assert const_data["null_count"] == 0

    cands_res = const_data["candidates"]
    c1_res = next(c for c in cands_res if c["candidate_id"] == str(cand1.id))
    c2_res = next(c for c in cands_res if c["candidate_id"] == str(cand2.id))

    assert c1_res["votes_count"] == 5
    assert c1_res["percentage"] == 62.5
    assert c2_res["votes_count"] == 3
    assert c2_res["percentage"] == 37.5

    # =========================================================================
    # INVARIANTE #12: Verificación de k-Anonimato en Desgloses
    # =========================================================================
    breakdowns = const_data["breakdowns"]
    assert len(breakdowns) == 1
    bd_carreras = breakdowns[0]
    assert bd_carreras["label"] == "Por Carrera"

    cells = bd_carreras["cells"]
    assert len(cells) == 2

    # Celda SIS: 6 votos >= k=5 -> NO redactada
    cell_sis = next(c for c in cells if c["cell_code"] == "SIS")
    assert cell_sis["total_votes"] == 6
    assert cell_sis["redacted_by_k_anonymity"] is False
    assert cell_sis["candidates"] is not None
    assert len(cell_sis["candidates"]) == 2
    sis_c1 = next(c for c in cell_sis["candidates"] if c["candidate_id"] == str(cand1.id))
    sis_c2 = next(c for c in cell_sis["candidates"] if c["candidate_id"] == str(cand2.id))
    assert sis_c1["votes_count"] == 4
    assert sis_c2["votes_count"] == 2

    # Celda CIV: 2 votos < k=5 -> REDACTADA por k-anonimato
    cell_civ = next(c for c in cells if c["cell_code"] == "CIV")
    assert cell_civ["total_votes"] == 2
    assert cell_civ["redacted_by_k_anonymity"] is True
    assert cell_civ["k_threshold"] == 5
    assert cell_civ["candidates"] is None
    assert cell_civ["blank_count"] is None
    assert cell_civ["null_count"] is None
    assert "< 5 votos" in cell_civ["k_anonymity_message"]

    # =========================================================================
    # Métricas de Participación
    # =========================================================================
    res_part = await client.get(f"/elections/{election.id}/participation", headers=headers)
    assert res_part.status_code == 200
    part_data = res_part.json()
    assert part_data["election_id"] == str(election.id)
    assert "by_group" in part_data
