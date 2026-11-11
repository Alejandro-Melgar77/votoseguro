"""
Pruebas de Invariantes: Cadenas de Hashes de Votos, Bitácora y Detección de Adulteración (S2-02, S2-03, S2-05)
"""
import uuid
from datetime import datetime, timedelta, timezone
import pytest
from httpx import AsyncClient
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.time import FakeTimeProvider
from app.db.models.election import Election, ElectionStatus
from app.db.models.structure import Candidate, Constituency, Contest, HierarchyLevel, UnitNode, VoterGroup
from app.db.models.voter import Voter, VoterStatus
from app.db.models.voting import Vote, VoteChoiceType, VotingCredential


@pytest.mark.asyncio
async def test_vote_and_audit_hash_chains_tamper_detection(
    test_db: AsyncSession,
    client: AsyncClient,
    org1_setup,
    fake_time: FakeTimeProvider,
):
    org, admin, admin_token = org1_setup
    now = datetime(2026, 11, 25, 12, 0, 0, tzinfo=timezone.utc)
    fake_time.set_time(now)

    auth_headers = {"Authorization": f"Bearer {admin_token}"}

    # 1. Crear Elección en VOTING_OPEN
    election = Election(
        organization_id=org.id,
        name="Elección Cadena Criptográfica S2-02",
        timezone="America/La_Paz",
        registration_opens_at=now - timedelta(days=2),
        registration_closes_at=now - timedelta(hours=2),
        voting_opens_at=now - timedelta(hours=1),
        voting_closes_at=now + timedelta(hours=5),
        status=ElectionStatus.VOTING_OPEN,
        config_hash="CONFIG_HASH_CANONICAL_2026",
        created_by=admin.id,
    )
    test_db.add(election)
    await test_db.flush()

    # Estructura electoral
    grp = VoterGroup(organization_id=org.id, election_id=election.id, name="General", code="GEN")
    test_db.add(grp)
    await test_db.flush()

    lvl = HierarchyLevel(group_id=grp.id, depth=1, name="Nivel General")
    test_db.add(lvl)
    await test_db.flush()

    node = UnitNode(group_id=grp.id, level_id=lvl.id, parent_id=None, name="Sede Central", code="SC", path="/SC/", depth=1)
    test_db.add(node)
    await test_db.flush()

    contest = Contest(group_id=grp.id, scope_level_id=lvl.id, name="Presidencia", display_order=1, allow_blank=True, allow_null=True)
    test_db.add(contest)
    await test_db.flush()

    constituency = Constituency(contest_id=contest.id, node_id=node.id)
    test_db.add(constituency)
    await test_db.flush()

    cand1 = Candidate(constituency_id=constituency.id, name="Candidato Alfa", ballot_order=1)
    cand2 = Candidate(constituency_id=constituency.id, name="Candidato Beta", ballot_order=2)
    test_db.add_all([cand1, cand2])
    await test_db.flush()

    # Crear 3 votantes y sus credenciales
    voters = []
    tokens = []
    for i in range(1, 4):
        v = Voter(
            organization_id=org.id,
            election_id=election.id,
            group_id=grp.id,
            node_id=node.id,
            document_id=f"CI-{i}000",
            full_name=f"Votante {i}",
            status=VoterStatus.ACTIVE,
            attributes={},
        )
        test_db.add(v)
        await test_db.flush()
        voters.append(v)

        raw_cred = f"VS-TEST-CRED-{i:04d}"
        from app.crypto.hashing import sha256_hex
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

    receipt_hashes = []

    # 2. Votante 1 y 2 emiten sufragio
    for i in range(2):
        login_res = await client.post("/voter/login", json={"document_id": f"CI-{i+1}000", "credential_code": tokens[i]})
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
        receipt_hashes.append(cast_res.json()["receipt_hash"])

    # 3. Verificar que la cadena de votos esté 100% íntegra (S2-02)
    res_integrity = await client.get(f"/elections/{election.id}/integrity/votes", headers=auth_headers)
    assert res_integrity.status_code == 200
    int_data = res_integrity.json()
    assert int_data["valid"] is True
    assert int_data["total_blocks"] == 2
    assert int_data["verified_blocks"] == 2
    assert int_data["broken_at_index"] is None

    # 4. Verificar integridad de la bitácora de auditoría (S2-05)
    res_audit_int = await client.get(f"/elections/{election.id}/integrity/audit", headers=auth_headers)
    assert res_audit_int.status_code == 200
    audit_data = res_audit_int.json()
    assert audit_data["valid"] is True
    assert audit_data["total_entries"] >= 2

    # 5. Verificación de Comprobante por el Votante (S2-03)
    rec_res = await client.get(f"/receipts/{receipt_hashes[0]}")
    assert rec_res.status_code == 200
    rec_data = rec_res.json()
    assert rec_data["found"] is True
    assert rec_data["chain_intact"] is True
    assert len(rec_data["chain_proof"]) == 1
    assert "candidate_id" not in rec_data  # Invariante #9
    assert "choice_type" not in rec_data   # Invariante #9

    # 6. PRUEBA DE DETECCIÓN DE ADULTERACIÓN (TAMPER DETECTION)
    # Alterar fraudulentamente el primer voto en SQL (cambiar candidato)
    stmt_v1 = select(Vote).where(Vote.election_id == election.id, Vote.chain_index == 1)
    v1 = (await test_db.execute(stmt_v1)).scalar_one()
    v1.candidate_id = cand2.id  # Modificación no autorizada en BD
    await test_db.commit()

    # 7. La auditoría criptográfica DEBE detectar inmediatamente la adulteración
    res_tampered = await client.get(f"/elections/{election.id}/integrity/votes", headers=auth_headers)
    assert res_tampered.status_code == 200
    tampered_data = res_tampered.json()
    assert tampered_data["valid"] is False
    assert tampered_data["broken_at_index"] == 1
    assert "Alteración o adulteración de datos detectada" in tampered_data["error_detail"]
