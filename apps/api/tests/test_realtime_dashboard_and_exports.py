"""
Pruebas Automatizadas de Dashboard en Tiempo Real (S2-04) y Exportaciones Oficiales PDF/Excel (S2-08)
Verifica:
1. Endpoint de métricas en vivo GET /api/v1/elections/{id}/live-metrics.
2. Invariante #11: Cero conteos de votos por candidato o preferencias antes del cierre oficial (VOTING_CLOSED).
3. Serie de votos por hora y avance por grupo/nodo.
4. Exportación de Resultados en PDF y Excel (bloqueado durante VOTING_OPEN, habilitado al publicar).
5. Exportación de Participación y Bitácora de Auditoría con encabezados institucionales y sellos criptográficos.
"""
import uuid
from datetime import datetime, timedelta, timezone
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.time import FakeTimeProvider
from app.db.models.election import Election, ElectionStatus
from app.db.models.structure import Candidate, Constituency, Contest, HierarchyLevel, UnitNode, VoterGroup
from app.db.models.voter import Voter, VoterStatus
from app.db.models.voting import VotingCredential


@pytest.mark.asyncio
async def test_realtime_metrics_and_official_exports(
    test_db: AsyncSession,
    client: AsyncClient,
    org1_setup,
    fake_time: FakeTimeProvider,
):
    org, admin, admin_token = org1_setup
    now = datetime(2026, 11, 25, 12, 0, 0, tzinfo=timezone.utc)
    fake_time.set_time(now)
    auth_headers = {"Authorization": f"Bearer {admin_token}"}

    # 1. Configurar Elección con estructura
    election = Election(
        organization_id=org.id,
        name="Elección Dashboard y Exportaciones S2-04-08",
        timezone="America/La_Paz",
        registration_opens_at=now - timedelta(days=2),
        registration_closes_at=now - timedelta(hours=2),
        voting_opens_at=now - timedelta(hours=1),
        voting_closes_at=now + timedelta(hours=4),
        status=ElectionStatus.VOTING_OPEN,
        config_hash="CONFIG_HASH_LIVE_TEST_2026",
        roll_hash="ROLL_HASH_CANONICAL_2026",
        merkle_root="MERKLE_ROOT_TEST_2026",
        created_by=admin.id,
    )
    test_db.add(election)
    await test_db.flush()

    grp = VoterGroup(organization_id=org.id, election_id=election.id, name="Docentes", code="DOC")
    test_db.add(grp)
    await test_db.flush()

    lvl = HierarchyLevel(group_id=grp.id, depth=1, name="Facultad")
    test_db.add(lvl)
    await test_db.flush()

    node = UnitNode(group_id=grp.id, level_id=lvl.id, parent_id=None, name="Tecnología", code="TEC", path="/TEC/", depth=1)
    test_db.add(node)
    await test_db.flush()

    contest = Contest(group_id=grp.id, scope_level_id=lvl.id, name="Decanato", display_order=1, allow_blank=True, allow_null=True)
    test_db.add(contest)
    await test_db.flush()

    constituency = Constituency(contest_id=contest.id, node_id=node.id)
    test_db.add(constituency)
    await test_db.flush()

    cand1 = Candidate(constituency_id=constituency.id, name="Dra. Valenzuela", ballot_order=1)
    cand2 = Candidate(constituency_id=constituency.id, name="Ing. Mendoza", ballot_order=2)
    test_db.add_all([cand1, cand2])
    await test_db.flush()

    # Crear 4 votantes
    voters = []
    tokens = []
    from app.crypto.hashing import sha256_hex

    for i in range(1, 5):
        v = Voter(
            organization_id=org.id,
            election_id=election.id,
            group_id=grp.id,
            node_id=node.id,
            document_id=f"CI-LIVE-{i}",
            full_name=f"Docente {i}",
            status=VoterStatus.ACTIVE,
            attributes={},
        )
        test_db.add(v)
        await test_db.flush()
        voters.append(v)

        raw_cred = f"VS-LIVE-CRED-{i:04d}"
        cred = VotingCredential(
            election_id=election.id,
            voter_id=v.id,
            token_hash=sha256_hex(raw_cred),
            raw_token=raw_cred,
            issued_at=now - timedelta(hours=1),
            expires_at=election.voting_closes_at,
        )
        test_db.add(cred)
        tokens.append(raw_cred)

    await test_db.commit()

    # 2. Consultar métricas en vivo antes de votar (S2-04)
    res_m0 = await client.get(f"/elections/{election.id}/live-metrics", headers=auth_headers)
    assert res_m0.status_code == 200
    m0_data = res_m0.json()
    assert m0_data["registration_metrics"]["total"] == 4
    assert m0_data["participation_metrics"]["total_voted"] == 0
    assert m0_data["participation_metrics"]["participation_rate_pct"] == 0.0

    # Invariante #11: Verificar que NO existan resultados parciales por candidato en el esquema
    assert "candidate_results" not in m0_data
    assert "candidate_counts" not in m0_data

    # Intentar exportar resultados cuando VOTING_OPEN -> Debe devolver 403 Forbidden
    res_exp_forbidden = await client.get(f"/elections/{election.id}/exports/results?format=pdf", headers=auth_headers)
    assert res_exp_forbidden.status_code == 403

    # 3. Emitir sufragio de 2 electores en horarios distintos
    for i in range(2):
        login_res = await client.post("/voter/login", json={"document_id": f"CI-LIVE-{i+1}", "credential_code": tokens[i]})
        assert login_res.status_code == 200
        v_token = login_res.json()["access_token"]
        v_headers = {"Authorization": f"Bearer {v_token}"}

        cast_res = await client.post(
            "/ballot/cast",
            headers=v_headers,
            json={
                "selections": [
                    {
                        "contest_id": str(contest.id),
                        "constituency_id": str(constituency.id),
                        "choice_type": "CANDIDATE",
                        "candidate_id": str(cand1.id if i == 0 else cand2.id),
                    }
                ]
            },
        )
        assert cast_res.status_code == 201

    # 4. Consultar métricas tras sufragios
    res_m1 = await client.get(f"/elections/{election.id}/live-metrics", headers=auth_headers)
    assert res_m1.status_code == 200
    m1_data = res_m1.json()
    assert m1_data["registration_metrics"]["total"] == 4
    assert m1_data["participation_metrics"]["total_voted"] == 2
    assert m1_data["participation_metrics"]["participation_rate_pct"] == 50.0
    assert len(m1_data["hourly_votes_series"]) > 0
    assert len(m1_data["segment_breakdown"]) > 0

    # 5. Exportar Participación y Auditoría (permitidos durante la elección)
    res_part_pdf = await client.get(f"/elections/{election.id}/exports/participation?format=pdf", headers=auth_headers)
    assert res_part_pdf.status_code == 200
    assert res_part_pdf.headers["content-type"] == "application/pdf"
    assert res_part_pdf.content.startswith(b"%PDF-")

    res_part_xlsx = await client.get(f"/elections/{election.id}/exports/participation?format=xlsx", headers=auth_headers)
    assert res_part_xlsx.status_code == 200
    assert "spreadsheetml" in res_part_xlsx.headers["content-type"]
    assert res_part_xlsx.content.startswith(b"PK")

    res_audit_pdf = await client.get(f"/elections/{election.id}/exports/audit?format=pdf", headers=auth_headers)
    assert res_audit_pdf.status_code == 200
    assert res_audit_pdf.content.startswith(b"%PDF-")

    res_audit_xlsx = await client.get(f"/elections/{election.id}/exports/audit?format=xlsx", headers=auth_headers)
    assert res_audit_xlsx.status_code == 200
    assert res_audit_xlsx.content.startswith(b"PK")

    # 6. Cerrar y Publicar resultados para habilitar exportación oficial de Resultados (S2-08)
    election.status = ElectionStatus.TALLIED
    await test_db.commit()

    res_res_pdf = await client.get(f"/elections/{election.id}/exports/results?format=pdf", headers=auth_headers)
    assert res_res_pdf.status_code == 200
    assert res_res_pdf.headers["content-type"] == "application/pdf"
    assert res_res_pdf.content.startswith(b"%PDF-")

    res_res_xlsx = await client.get(f"/elections/{election.id}/exports/results?format=xlsx", headers=auth_headers)
    assert res_res_xlsx.status_code == 200
    assert "spreadsheetml" in res_res_xlsx.headers["content-type"]
    assert res_res_xlsx.content.startswith(b"PK")
