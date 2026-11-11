"""
Pruebas de Invariante: Papeleta Automática y Emisión Atómica Ciega del Sufragio (S1-09)
Valida:
- Invariante #6: Autoridad temporal y rechazo de votos fuera de ventana.
- Invariante #7: Únicamente votantes ACTIVE reciben credencial y pueden votar.
- Invariante #8: Nullifier HMAC-SHA256 y un voto por persona y cargo.
- Invariante #9: Tabla 'vote' desvinculada físicamente de voter_id.
- Invariante #13: Codificación de voto (VoteCodec).
- Invariante #17: Marca temporal truncada al minuto exacto.
"""
from datetime import datetime, timedelta, timezone
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.time import FakeTimeProvider
from app.db.models.election import Election, ElectionStatus
from app.db.models.structure import Candidate, Constituency, Contest, HierarchyLevel, UnitNode, VoterGroup
from app.db.models.voter import Voter, VoterStatus
from app.db.models.voting import Vote, VoteChoiceType, VoterParticipation, VotingCredential


@pytest.mark.asyncio
async def test_automatic_ballot_and_atomic_cast(
    test_db: AsyncSession,
    client: AsyncClient,
    org1_setup,
    fake_time: FakeTimeProvider,
):
    org, admin, admin_token = org1_setup
    now = datetime(2026, 11, 25, 8, 0, 0, tzinfo=timezone.utc)
    fake_time.set_time(now)

    t_reg_open = now - timedelta(days=2)
    t_reg_close = now - timedelta(hours=1)
    t_vote_open = now
    t_vote_close = now + timedelta(hours=10)

    # 1. Crear Elección en REGISTRATION_CLOSED
    election = Election(
        organization_id=org.id,
        name="Elección General Universitaria S1-09",
        timezone="America/La_Paz",
        registration_opens_at=t_reg_open,
        registration_closes_at=t_reg_close,
        voting_opens_at=t_vote_open,
        voting_closes_at=t_vote_close,
        status=ElectionStatus.REGISTRATION_CLOSED,
        k_anonymity=5,
        created_by=admin.id,
    )
    test_db.add(election)
    await test_db.flush()

    # 2. Grupo Estudiantes (3 niveles: Universidad -> Facultad -> Carrera)
    grp_est = VoterGroup(organization_id=org.id, election_id=election.id, name="ESTUDIANTES", code="EST")
    grp_doc = VoterGroup(organization_id=org.id, election_id=election.id, name="DOCENTES", code="DOC")
    test_db.add_all([grp_est, grp_doc])
    await test_db.flush()

    lvl_univ = HierarchyLevel(group_id=grp_est.id, depth=1, name="Universidad")
    lvl_fac = HierarchyLevel(group_id=grp_est.id, depth=2, name="Facultad")
    lvl_car = HierarchyLevel(group_id=grp_est.id, depth=3, name="Carrera")
    test_db.add_all([lvl_univ, lvl_fac, lvl_car])
    await test_db.flush()

    node_univ = UnitNode(group_id=grp_est.id, level_id=lvl_univ.id, parent_id=None, name="UNIV", code="UNIV", path="/UNIV/", depth=1)
    test_db.add(node_univ)
    await test_db.flush()

    node_ficct = UnitNode(group_id=grp_est.id, level_id=lvl_fac.id, parent_id=node_univ.id, name="FICCT", code="FICCT", path="/UNIV/FICCT/", depth=2)
    test_db.add(node_ficct)
    await test_db.flush()

    node_inf = UnitNode(group_id=grp_est.id, level_id=lvl_car.id, parent_id=node_ficct.id, name="INF", code="INF", path="/UNIV/FICCT/INF/", depth=3)
    test_db.add(node_inf)
    await test_db.flush()

    # 3 Cargos Estudiantes
    # 1. Rector (Nivel 1)
    c_rector = Contest(group_id=grp_est.id, scope_level_id=lvl_univ.id, name="Rector", display_order=1, allow_blank=True, allow_null=True)
    # 2. Decano (Nivel 2)
    c_decano = Contest(group_id=grp_est.id, scope_level_id=lvl_fac.id, name="Decano FICCT", display_order=2, allow_blank=True, allow_null=True)
    # 3. Encargado Carrera (Nivel 3)
    c_carrera = Contest(group_id=grp_est.id, scope_level_id=lvl_car.id, name="Director INF", display_order=3, allow_blank=True, allow_null=True)
    test_db.add_all([c_rector, c_decano, c_carrera])
    await test_db.flush()

    # Circunscripciones y Candidatos
    const_rec = Constituency(contest_id=c_rector.id, node_id=node_univ.id)
    const_dec = Constituency(contest_id=c_decano.id, node_id=node_ficct.id)
    const_car = Constituency(contest_id=c_carrera.id, node_id=node_inf.id)
    test_db.add_all([const_rec, const_dec, const_car])
    await test_db.flush()

    cand_rec1 = Candidate(constituency_id=const_rec.id, name="Dr. Rector Uno", ballot_order=1)
    cand_rec2 = Candidate(constituency_id=const_rec.id, name="Dra. Rectora Dos", ballot_order=2)
    cand_dec1 = Candidate(constituency_id=const_dec.id, name="Ing. Decano Uno", ballot_order=1)
    cand_car1 = Candidate(constituency_id=const_car.id, name="Ing. Director Uno", ballot_order=1)
    test_db.add_all([cand_rec1, cand_rec2, cand_dec1, cand_car1])
    await test_db.flush()

    # Grupo Docentes (Nivel 1 con su propio cargo)
    lvl_doc = HierarchyLevel(group_id=grp_doc.id, depth=1, name="Universidad")
    test_db.add(lvl_doc)
    await test_db.flush()

    node_udoc = UnitNode(group_id=grp_doc.id, level_id=lvl_doc.id, parent_id=None, name="UNIV-DOC", code="UDOC", path="/UDOC/", depth=1)
    test_db.add(node_udoc)
    await test_db.flush()

    c_rdoc = Contest(group_id=grp_doc.id, scope_level_id=lvl_doc.id, name="Rector Claustro Docente", display_order=1, allow_blank=True, allow_null=True)
    test_db.add(c_rdoc)
    await test_db.flush()

    const_rdoc = Constituency(contest_id=c_rdoc.id, node_id=node_udoc.id)
    test_db.add(const_rdoc)
    await test_db.flush()

    cand_rdoc1 = Candidate(constituency_id=const_rdoc.id, name="Dr. Docente Candidato", ballot_order=1)
    test_db.add(cand_rdoc1)
    await test_db.flush()

    # 3. Votantes:
    # Votante 1: Estudiante Informática ACTIVE
    voter_est_active = Voter(
        organization_id=org.id,
        election_id=election.id,
        group_id=grp_est.id,
        node_id=node_inf.id,
        document_id="CI-EST-ACTIVE",
        full_name="Estudiante Activo Inf",
        status=VoterStatus.ACTIVE,
    )
    # Votante 2: Estudiante IMPORTED (No debe recibir credencial)
    voter_est_imported = Voter(
        organization_id=org.id,
        election_id=election.id,
        group_id=grp_est.id,
        node_id=node_inf.id,
        document_id="CI-EST-IMPORTED",
        full_name="Estudiante Importado No Activo",
        status=VoterStatus.IMPORTED,
    )
    # Votante 3: Docente ACTIVE
    voter_doc_active = Voter(
        organization_id=org.id,
        election_id=election.id,
        group_id=grp_doc.id,
        node_id=node_udoc.id,
        document_id="CI-DOC-ACTIVE",
        full_name="Docente Activo",
        status=VoterStatus.ACTIVE,
    )
    test_db.add_all([voter_est_active, voter_est_imported, voter_doc_active])
    await test_db.commit()

    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # 4. Abrir la votación (VOTING_OPEN) y emitir credenciales
    res_open = await client.post(
        f"/elections/{election.id}/voting/open-now",
        headers=admin_headers,
    )
    assert res_open.status_code == 200
    assert res_open.json()["credentials_issued"] == 2  # voter_est_active y voter_doc_active

    # Invariante #7: Verificar que voter_est_imported NO recibió credencial
    stmt_cred_imp = select(VotingCredential).where(VotingCredential.voter_id == voter_est_imported.id)
    assert (await test_db.execute(stmt_cred_imp)).scalar_one_or_none() is None

    # Consultar credenciales desde el despacho
    res_dispatch = await client.get(
        f"/elections/{election.id}/voting/credentials-dispatch",
        headers=admin_headers,
    )
    assert res_dispatch.status_code == 200
    dispatch_list = res_dispatch.json()
    assert len(dispatch_list) == 2

    est_cred_code = next(item["credential_code"] for item in dispatch_list if item["document_id"] == "CI-EST-ACTIVE")
    doc_cred_code = next(item["credential_code"] for item in dispatch_list if item["document_id"] == "CI-DOC-ACTIVE")

    # 5. Login de votante en cabina oficial (/voter/login)
    # Intentar login con votante IMPORTED con código inventado -> 401
    res_login_bad = await client.post(
        "/voter/login",
        json={"document_id": "CI-EST-IMPORTED", "credential_code": "VS-FAKE-CODE-1234"},
    )
    assert res_login_bad.status_code == 401

    # Login exitoso de Estudiante
    res_login_est = await client.post(
        "/voter/login",
        json={"document_id": "CI-EST-ACTIVE", "credential_code": est_cred_code},
    )
    assert res_login_est.status_code == 200
    est_token = res_login_est.json()["access_token"]
    est_headers = {"Authorization": f"Bearer {est_token}"}

    # Login exitoso de Docente
    res_login_doc = await client.post(
        "/voter/login",
        json={"document_id": "CI-DOC-ACTIVE", "credential_code": doc_cred_code},
    )
    assert res_login_doc.status_code == 200
    doc_token = res_login_doc.json()["access_token"]
    doc_headers = {"Authorization": f"Bearer {doc_token}"}

    # 6. Algoritmo 3.2: Consultar Papeleta Automática (GET /ballot)
    # Para Estudiante de INF: debe recibir EXACTAMENTE 3 cargos (Rector, Decano FICCT, Director INF)
    res_ballot_est = await client.get("/ballot", headers=est_headers)
    assert res_ballot_est.status_code == 200
    ballot_est = res_ballot_est.json()
    assert len(ballot_est["contests"]) == 3
    contest_names_est = [c["contest_name"] for c in ballot_est["contests"]]
    assert contest_names_est == ["Rector", "Decano FICCT", "Director INF"]
    assert ballot_est["voter_profile"]["node_path"] == "/UNIV/FICCT/INF/"

    # Para Docente: debe recibir ÚNICAMENTE los cargos de su grupo (1 cargo: Rector Claustro Docente)
    res_ballot_doc = await client.get("/ballot", headers=doc_headers)
    assert res_ballot_doc.status_code == 200
    ballot_doc = res_ballot_doc.json()
    assert len(ballot_doc["contests"]) == 1
    assert ballot_doc["contests"][0]["contest_name"] == "Rector Claustro Docente"

    # 7. Invariantes #8, #9, #13, #17: Emisión Atómica Ciega (POST /ballot/cast)
    selections_payload = [
        {
            "contest_id": str(c_rector.id),
            "constituency_id": str(const_rec.id),
            "choice_type": "CANDIDATE",
            "candidate_id": str(cand_rec1.id),
        },
        {
            "contest_id": str(c_decano.id),
            "constituency_id": str(const_dec.id),
            "choice_type": "BLANK",
            "candidate_id": None,
        },
        {
            "contest_id": str(c_carrera.id),
            "constituency_id": str(const_car.id),
            "choice_type": "NULL",
            "candidate_id": None,
        },
    ]

    res_cast = await client.post(
        "/ballot/cast",
        headers=est_headers,
        json={"selections": selections_payload},
    )
    assert res_cast.status_code == 201
    cast_data = res_cast.json()
    receipt_hash = cast_data["receipt_hash"]
    assert receipt_hash is not None
    assert len(receipt_hash) == 64
    assert cast_data["contests_count"] == 3

    # Invariante #9: Verificar que la tabla 'vote' NO CONTIENE voter_id
    stmt_votes = select(Vote).where(Vote.receipt_hash == receipt_hash)
    inserted_votes = (await test_db.execute(stmt_votes)).scalars().all()
    assert len(inserted_votes) == 3

    for v in inserted_votes:
        # Verificar que la entidad Vote carece de cualquier campo voter_id
        assert not hasattr(v, "voter_id")
        # Invariante #17: Marca temporal truncada al minuto
        assert v.created_at.second == 0
        assert v.created_at.microsecond == 0
        # Invariante #8: Nullifier HMAC-SHA256 no vacío
        assert len(v.nullifier) == 64
        # Invariante #13: Payload codificado
        assert len(v.encoded_payload) > 0

    # Invariante #8: Intentar votar de nuevo con el mismo token o credencial -> 409 Conflict
    res_double_vote = await client.post(
        "/ballot/cast",
        headers=est_headers,
        json={"selections": selections_payload},
    )
    assert res_double_vote.status_code == 409

    # Verificar constancia en voter_participation
    stmt_part = select(VoterParticipation).where(
        VoterParticipation.election_id == election.id,
        VoterParticipation.voter_id == voter_est_active.id,
    )
    part_entry = (await test_db.execute(stmt_part)).scalar_one_or_none()
    assert part_entry is not None

    # 8. Verificación pública de comprobante (GET /receipts/{receipt_hash})
    res_receipt = await client.get(f"/receipts/{receipt_hash}")
    assert res_receipt.status_code == 200
    receipt_info = res_receipt.json()
    assert receipt_info["found"] is True
    assert receipt_info["contests_recorded"] == 3
    assert receipt_info["status"] == "RECORDED_IN_BALLOT_BOX"
    # Jamás debe revelar candidatos en la respuesta del comprobante
    assert "candidate" not in str(receipt_info).lower()

    # 9. Invariante #6: Avanzar el reloj más allá de voting_closes_at y verificar que un votante con sesión JWT activa recibe 403
    fake_time.set_time(t_vote_close + timedelta(minutes=5))

    doc_selections = [
        {
            "contest_id": str(c_rdoc.id),
            "constituency_id": str(const_rdoc.id),
            "choice_type": "CANDIDATE",
            "candidate_id": str(cand_rdoc1.id),
        }
    ]
    res_expired_cast = await client.post(
        "/ballot/cast",
        headers=doc_headers,
        json={"selections": doc_selections},
    )
    assert res_expired_cast.status_code == 403
    assert "concluido" in res_expired_cast.json()["detail"].lower()
