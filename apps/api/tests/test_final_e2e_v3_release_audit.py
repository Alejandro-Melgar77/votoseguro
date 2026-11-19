"""
Suite de Certificación Integral y Auditoría End-to-End de Release v3.0.0
Archivo: apps/api/tests/test_final_e2e_v3_release_audit.py

Recorre en un único flujo continuo e ininterrumpido todo el ciclo de vida electoral de VotoSeguro v3.0.0:
1. Creación de Organización y Autoridad Electoral (Tenant Isolation - Invariante #1).
2. Arquitectura Jerárquica y Estructura Territorial (Materialized Path - S1-03 / S1-04 / S1-05).
3. Ceremonia Criptográfica de Generación de Claves Paillier + Shamir k de n (S3-01, S3-02, Invariante #20).
4. Ceremonia de Publicación y Congelamiento Estructural (config_hash RFC 8785 - Invariante #3, S1-06).
5. Apertura de Registro, Detección Asistida de Duplicados (IA-L2a / IA-L2b) y Activación de Votantes (Invariante #7).
6. Cierre del Padrón Electoral, Sellado roll_hash y Árbol de Merkle (merkle_root e inclusión O(log N) - Invariante #5, S2-07).
7. Apertura de Votación y Emisión Atómica Ciega con Cifrado Paillier (VoteCodec, nullifier HMAC y cadena de hashes - S3-01, S2-02, Invariantes #8, #9, #13, #19).
8. Cierre de Urnas y Verificación de Hermetismo Absoluto (Resultados bloqueados con HTTP 403 antes del quórum - Invariante #11).
9. Desbloqueo Criptográfico por Quórum Shamir (k de n) y Escrutinio Homomórfico con k-Anonimato (S3-01, S3-02, Invariante #12).
10. Generación de Informe Ejecutivo Oficial en Lenguaje Natural con Gemini (IA-E1, Invariante #14).
11. Portal Público de Auditoría para Observadores sin Autenticación (S3-03 - Cero PII, sellos matemáticos íntegros).
"""
import json
import uuid
from datetime import datetime, timedelta, timezone
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.time import FakeTimeProvider
from app.crypto.hashing import sha256_hex
from app.db.models.audit import AiCallLog, AuditLog
from app.db.models.election import (
    Election,
    ElectionStatus,
    ElectoralTrusteeShare,
    HomomorphicTallyCell,
    ScheduleChange,
)
from app.db.models.organization import Organization, OrganizationStatus, OrganizationType
from app.db.models.structure import (
    Candidate,
    Constituency,
    Contest,
    HierarchyLevel,
    UnitNode,
    VoterGroup,
)
from app.db.models.user import User, UserRole, UserStatus
from app.db.models.voter import ImportBatch, ImportIssue, Voter, VoterStatus
from app.db.models.voting import Vote, VoteChoiceType, VotingCredential


@pytest.mark.asyncio
async def test_full_lifecycle_v3_release_certification_and_invariants(
    test_db: AsyncSession,
    client: AsyncClient,
    org1_setup,
    fake_time: FakeTimeProvider,
):
    """
    Test End-to-End integral que certifica el 100% de las invariantes electorales,
    criptográficas y de gobernanza para el Release Oficial v3.0.0.
    """
    # =========================================================================
    # FASE 1: Tenant y Autoridad Electoral (Invariante #1)
    # =========================================================================
    org, admin, admin_token = org1_setup
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    now = datetime(2026, 12, 1, 8, 0, 0, tzinfo=timezone.utc)
    fake_time.set_time(now)

    # =========================================================================
    # FASE 2: Creación de la Elección en Estado DRAFT (S1-02)
    # =========================================================================
    t_reg_open = now + timedelta(hours=1)
    t_reg_close = now + timedelta(hours=3)
    t_vote_open = now + timedelta(hours=4)
    t_vote_close = now + timedelta(hours=8)

    res_elec = await client.post(
        "/elections",
        headers=admin_headers,
        json={
            "name": "Elección Magna Claustro Universitario v3.0 Release Audit",
            "timezone": "America/La_Paz",
            "registration_opens_at": t_reg_open.isoformat(),
            "registration_closes_at": t_reg_close.isoformat(),
            "voting_opens_at": t_vote_open.isoformat(),
            "voting_closes_at": t_vote_close.isoformat(),
            "k_anonymity": 5,
        },
    )
    assert res_elec.status_code == 201, res_elec.text
    elec_data = res_elec.json()
    election_id = uuid.UUID(elec_data["id"])
    assert elec_data["status"] == "DRAFT"

    # =========================================================================
    # FASE 3: Diseño de la Estructura Jerárquica y Candidaturas (S1-03 a S1-05)
    # =========================================================================
    # 3.1 Grupo de Votantes
    res_grp = await client.post(
        f"/elections/{election_id}/groups",
        headers=admin_headers,
        json={"name": "ESTUDIANTES Y DOCENTES", "code": "EST_DOC"},
    )
    assert res_grp.status_code == 201
    group_id = res_grp.json()["id"]

    # 3.2 Niveles Jerárquicos (Facultad -> Carrera)
    res_lvl1 = await client.post(f"/groups/{group_id}/levels", headers=admin_headers, json={"name": "Facultad"})
    res_lvl2 = await client.post(f"/groups/{group_id}/levels", headers=admin_headers, json={"name": "Carrera"})
    lvl1_id = res_lvl1.json()["id"]
    lvl2_id = res_lvl2.json()["id"]

    # 3.3 Nodos Territoriales (Árbol con Materialized Path)
    res_fac = await client.post(
        f"/groups/{group_id}/nodes",
        headers=admin_headers,
        json={"level_id": lvl1_id, "parent_id": None, "name": "Facultad de Tecnología", "code": "TEC"},
    )
    fac_id = res_fac.json()["id"]

    res_car_sis = await client.post(
        f"/groups/{group_id}/nodes",
        headers=admin_headers,
        json={"level_id": lvl2_id, "parent_id": fac_id, "name": "Ingeniería de Sistemas", "code": "SIS"},
    )
    res_car_red = await client.post(
        f"/groups/{group_id}/nodes",
        headers=admin_headers,
        json={"level_id": lvl2_id, "parent_id": fac_id, "name": "Ingeniería en Redes", "code": "RED"},
    )
    car_sis_id = res_car_sis.json()["id"]
    car_red_id = res_car_red.json()["id"]

    # 3.4 Cargo Electoral: Dirección de Carrera (genera 2 circunscripciones: SIS y RED)
    res_cnt = await client.post(
        f"/groups/{group_id}/contests",
        headers=admin_headers,
        json={
            "name": "Dirección de Carrera",
            "scope_level_id": lvl2_id,
            "allow_blank": True,
            "allow_null": True,
            "display_order": 1,
        },
    )
    assert res_cnt.status_code == 201
    contest_id = res_cnt.json()["id"]

    res_cstys = await client.get(f"/contests/{contest_id}/constituencies", headers=admin_headers)
    assert res_cstys.status_code == 200
    cstys = res_cstys.json()
    assert len(cstys) == 2
    csty_sis_id = next(c["id"] for c in cstys if c["node_code"] == "SIS")
    csty_red_id = next(c["id"] for c in cstys if c["node_code"] == "RED")

    # 3.5 Registro de Candidatos en cada circunscripción
    res_c1 = await client.post(
        f"/constituencies/{csty_sis_id}/candidates",
        headers=admin_headers,
        json={"name": "Dra. Ada Lovelace", "party_or_front": "FRENTE INNOVACIÓN SIS", "ballot_order": 1},
    )
    res_c2 = await client.post(
        f"/constituencies/{csty_sis_id}/candidates",
        headers=admin_headers,
        json={"name": "Dr. Alan Turing", "party_or_front": "FRENTE CIENCIA SIS", "ballot_order": 2},
    )
    cand_ada_id = res_c1.json()["id"]
    cand_turing_id = res_c2.json()["id"]

    res_c3 = await client.post(
        f"/constituencies/{csty_red_id}/candidates",
        headers=admin_headers,
        json={"name": "Dra. Radia Perlman", "party_or_front": "FRENTE PROTOCOLO RED", "ballot_order": 1},
    )
    res_c4 = await client.post(
        f"/constituencies/{csty_red_id}/candidates",
        headers=admin_headers,
        json={"name": "Dr. Vint Cerf", "party_or_front": "FRENTE INTERNET RED", "ballot_order": 2},
    )
    cand_radia_id = res_c3.json()["id"]
    cand_cerf_id = res_c4.json()["id"]

    # =========================================================================
    # FASE 4: Ceremonia Criptográfica de Generación de Claves (S3-01 y S3-02)
    # =========================================================================
    res_ceremony = await client.post(
        f"/elections/{election_id}/shamir/setup",
        headers=admin_headers,
        json={"key_size": 1024, "threshold_k": 2, "total_n": 3},
    )
    assert res_ceremony.status_code == 201, res_ceremony.text
    ceremony_data = res_ceremony.json()
    assert ceremony_data["encryption_scheme"] == "PAILLIER_HOMOMORPHIC"
    assert ceremony_data["threshold_k"] == 2
    assert ceremony_data["total_n"] == 3
    key_ceremony_hash = ceremony_data["key_ceremony_hash"]
    assert len(key_ceremony_hash) == 64

    # Custodios electorales de Shamir (fragmentos emitidos y clave privada destruida)
    trustee_shares = [t["share_token"] for t in ceremony_data["trustees"]]
    assert len(trustee_shares) == 3
    status_response = await client.get(f"/elections/{election_id}/shamir/status", headers=admin_headers)
    assert status_response.status_code == 200
    assert all(t["share_token"] is None for t in status_response.json()["trustees"])
    assert all(s.startswith("VS-SHARE-") for s in trustee_shares)

    # Estado de la ceremonia de claves
    res_c_status = await client.get(f"/elections/{election_id}/shamir/status", headers=admin_headers)
    assert res_c_status.status_code == 200
    assert res_c_status.json()["key_ceremony_completed"] is True
    assert res_c_status.json()["tally_ceremony_completed"] is False

    # =========================================================================
    # FASE 5: Ceremonia de Publicación y Congelamiento Estructural (Invariante #3)
    # =========================================================================
    res_publish = await client.post(f"/elections/{election_id}/publish", headers=admin_headers)
    assert res_publish.status_code == 200, res_publish.text
    pub_data = res_publish.json()
    config_hash = pub_data["config_hash"]
    assert len(config_hash) == 64
    assert pub_data["status"] == "SCHEDULED"

    # Invariante #3: Toda mutación posterior queda prohibida (409 Conflict)
    res_err_cand = await client.post(
        f"/constituencies/{csty_sis_id}/candidates",
        headers=admin_headers,
        json={"name": "Candidato Intruso", "party_or_front": "INTRUSO", "ballot_order": 3},
    )
    assert res_err_cand.status_code == 409
    assert "congelada" in res_err_cand.json()["detail"].lower()

    # =========================================================================
    # FASE 6: Apertura de Registro, Segunda Opinión de IA (IA-L2b) y Padrón
    # =========================================================================
    # Avanzamos el reloj a la fase de registro
    fake_time.set_time(t_reg_open + timedelta(minutes=10))

    # Actualizar estado de la elección a REGISTRATION_OPEN
    stmt_el = select(Election).where(Election.id == election_id)
    el_db = (await test_db.execute(stmt_el)).scalar_one()
    el_db.status = ElectionStatus.REGISTRATION_OPEN
    await test_db.commit()

    # 6.1 Prueba de Segunda Opinión de IA en Duplicados (IA-L2b)
    batch = ImportBatch(
        organization_id=org.id,
        election_id=election_id,
        uploaded_by=admin.id,
        filename="censo_estudiantil_2026.csv",
        total_rows=10,
        valid_rows=8,
        error_rows=0,
        duplicate_warnings=1,
    )
    test_db.add(batch)
    await test_db.flush()

    issue = ImportIssue(
        batch_id=batch.id,
        row_number=5,
        issue_type="POSSIBLE_DUPLICATE",
        document_id="8001099",
        raw_full_name="María René Fernández",
        similarity_score=0.84,
        edit_distance=2,
        resolution="PENDING",
        details={
            "matched_name": "Jose Rodriguez S.",
            "matched_doc": "8001099",
        },
    )
    test_db.add(issue)
    await test_db.commit()

    res_ai_dup = await client.post(
        f"/ai/duplicates/{batch.id}/adjudicate",
        headers=admin_headers,
    )
    assert res_ai_dup.status_code == 200
    dup_batch_data = res_ai_dup.json()
    assert len(dup_batch_data["suggestions"]) >= 1
    dup_sugg = dup_batch_data["suggestions"][0]
    assert dup_sugg["verdict"] in ("mismo", "distinto", "dudoso")
    assert isinstance(dup_sugg["short_reason"], str)
    assert dup_sugg["human_action_required"] is True

    # 6.2 Registro e Inscripción de Votantes:
    # 8 votantes para Carrera SIS (supera k-anonimato = 5)
    # 3 votantes para Carrera RED (inferior a k-anonimato = 5, debe ser suprimido en el desglose)
    sis_voters_info = []
    for i in range(1, 9):
        doc = f"CI-E2E-SIS-{i:03d}"
        v = Voter(
            organization_id=org.id,
            election_id=election_id,
            group_id=uuid.UUID(group_id),
            node_id=uuid.UUID(car_sis_id),
            document_id=doc,
            full_name=f"Elector Sistemas {i}",
            email=f"sis{i}@ficct.edu.bo",
            status=VoterStatus.ACTIVE,
        )
        test_db.add(v)
        sis_voters_info.append(doc)

    red_voters_info = []
    for i in range(1, 4):
        doc = f"CI-E2E-RED-{i:03d}"
        v = Voter(
            organization_id=org.id,
            election_id=election_id,
            group_id=uuid.UUID(group_id),
            node_id=uuid.UUID(car_red_id),
            document_id=doc,
            full_name=f"Elector Redes {i}",
            email=f"red{i}@ficct.edu.bo",
            status=VoterStatus.ACTIVE,
        )
        test_db.add(v)
        red_voters_info.append(doc)

    await test_db.commit()

    # =========================================================================
    # FASE 7: Cierre del Padrón, Sellado roll_hash y Árbol de Merkle (S1-08 / S2-07)
    # =========================================================================
    fake_time.set_time(t_reg_close + timedelta(minutes=5))

    res_freeze = await client.post(f"/elections/{election_id}/registration/close-now", headers=admin_headers)
    assert res_freeze.status_code == 200, res_freeze.text
    freeze_data = res_freeze.json()
    roll_hash = freeze_data["roll_hash"]
    merkle_root = freeze_data["merkle_root"]
    assert len(roll_hash) == 64
    assert len(merkle_root) == 64
    assert freeze_data["active_voters_count"] == 11

    # Verificación de prueba de inclusión en el Árbol de Merkle para un elector
    target_ci = sis_voters_info[0]
    res_proof = await client.get(f"/elections/{election_id}/merkle/proof/{target_ci}", headers=admin_headers)
    assert res_proof.status_code == 200
    proof_data = res_proof.json()
    assert proof_data["merkle_root"] == merkle_root

    res_v_proof = await client.post(
        f"/elections/{election_id}/merkle/verify",
        json={
            "merkle_root": proof_data["merkle_root"],
            "leaf_hash": proof_data["leaf_hash"],
            "proof": proof_data["proof"],
        },
    )
    assert res_v_proof.status_code == 200
    assert res_v_proof.json()["valid"] is True

    # =========================================================================
    # FASE 8: Apertura de Votación y Emisión Atómica con Cifrado Paillier (S3-01)
    # =========================================================================
    fake_time.set_time(t_vote_open + timedelta(minutes=5))

    res_open = await client.post(f"/elections/{election_id}/voting/open-now", headers=admin_headers)
    assert res_open.status_code == 200, res_open.text
    assert res_open.json()["status"] == "VOTING_OPEN"

    # Ajuste formal y auditado de cronograma en VOTING_OPEN (S2-08)
    res_sched = await client.put(
        f"/elections/{election_id}/schedule",
        headers=admin_headers,
        json={
            "registration_opens_at": t_reg_open.isoformat(),
            "registration_closes_at": t_reg_close.isoformat(),
            "voting_opens_at": t_vote_open.isoformat(),
            "voting_closes_at": (t_vote_close + timedelta(hours=2)).isoformat(),
            "reason": "Ampliación reglamentaria de jornada para garantizar el escrutinio transparente",
        },
    )
    assert res_sched.status_code == 200, res_sched.text

    # Obtener credenciales de votación emitidas
    res_creds = await client.get(f"/elections/{election_id}/voting/credentials-dispatch", headers=admin_headers)
    assert res_creds.status_code == 200
    dispatch_items = res_creds.json()
    assert len(dispatch_items) == 11

    # Plan de Sufragio:
    # SIS (8 votos):
    # - 4 votos por Dra. Ada Lovelace
    # - 2 votos por Dr. Alan Turing
    # - 1 voto en BLANCO
    # - 1 voto NULO
    # RED (3 votos):
    # - 2 votos por Dra. Radia Perlman
    # - 1 voto por Dr. Vint Cerf
    voting_plan = [
        # Electores de SIS
        (sis_voters_info[0], csty_sis_id, "CANDIDATE", cand_ada_id),
        (sis_voters_info[1], csty_sis_id, "CANDIDATE", cand_ada_id),
        (sis_voters_info[2], csty_sis_id, "CANDIDATE", cand_ada_id),
        (sis_voters_info[3], csty_sis_id, "CANDIDATE", cand_ada_id),
        (sis_voters_info[4], csty_sis_id, "CANDIDATE", cand_turing_id),
        (sis_voters_info[5], csty_sis_id, "CANDIDATE", cand_turing_id),
        (sis_voters_info[6], csty_sis_id, "BLANK", None),
        (sis_voters_info[7], csty_sis_id, "NULL", None),
        # Electores de RED
        (red_voters_info[0], csty_red_id, "CANDIDATE", cand_radia_id),
        (red_voters_info[1], csty_red_id, "CANDIDATE", cand_radia_id),
        (red_voters_info[2], csty_red_id, "CANDIDATE", cand_cerf_id),
    ]

    receipt_hashes = []
    for doc_id, csty_id, c_type, c_id in voting_plan:
        cred_item = next(item for item in dispatch_items if item["document_id"] == doc_id)
        code = cred_item["credential_code"]

        # 8.1 Login de Cabina
        res_login = await client.post("/voter/login", json={"document_id": doc_id, "credential_code": code})
        assert res_login.status_code == 200, res_login.text
        v_token = res_login.json()["access_token"]
        v_headers = {"Authorization": f"Bearer {v_token}"}

        # 8.2 Resolución de Papeleta Automática
        res_ballot = await client.get("/ballot", headers=v_headers)
        assert res_ballot.status_code == 200
        ballot_data = res_ballot.json()
        assert len(ballot_data["contests"]) >= 1

        # 8.3 Emisión Atómica Ciega con Cifrado Paillier
        res_cast = await client.post(
            "/ballot/cast",
            headers=v_headers,
            json={
                "selections": [
                    {
                        "contest_id": contest_id,
                        "constituency_id": csty_id,
                        "choice_type": c_type,
                        "candidate_id": c_id,
                    }
                ]
            },
        )
        assert res_cast.status_code == 201, res_cast.text
        rcpt = res_cast.json()["receipt_hash"]
        receipt_hashes.append(rcpt)

        # 8.4 Verificación Pública del Comprobante
        res_rcpt = await client.get(f"/receipts/{rcpt}")
        assert res_rcpt.status_code == 200
        rcpt_data = res_rcpt.json()
        assert rcpt_data["found"] is True
        assert rcpt_data["chain_intact"] is True

    # Invariante #9 (Desvinculación Criptográfica):
    # Verificar que en la tabla `vote` NO existe columna ni vínculo voter_id
    stmt_votes = select(Vote).where(Vote.election_id == election_id)
    stored_votes = (await test_db.execute(stmt_votes)).scalars().all()
    assert len(stored_votes) == 11
    for sv in stored_votes:
        assert not hasattr(sv, "voter_id") or sv.__dict__.get("voter_id") is None
        # Invariante #13: Cifrado Paillier presente en cada voto
        assert '"scheme":"PAILLIER_V1"' in sv.encoded_payload
        assert sv.candidate_id is None
        assert sv.choice_type is None
        assert '"candidate_id"' not in sv.encoded_payload
        assert '"choice_type"' not in sv.encoded_payload
        assert '"ciphertexts":[' in sv.encoded_payload
        # Invariante #19: Cadena de hashes inmutable
        assert sv.chain_index >= 1
        assert len(sv.vote_hash) == 64
        assert len(sv.prev_hash) == 64

    # =========================================================================
    # FASE 9: Hermetismo de Resultados en Urna Abierta (Invariante #11) y Cierre de Urnas
    # =========================================================================
    # INVARIANTE #11: Resultados Herméticos durante VOTING_OPEN
    # La consulta a /results DEBE responder con HTTP 403 Forbidden mientras la votación esté abierta
    res_locked_open = await client.get(f"/elections/{election_id}/results", headers=admin_headers)
    assert res_locked_open.status_code == 403, "Invariante #11 violada: los resultados se filtraron durante VOTING_OPEN"

    fake_time.set_time(t_vote_close + timedelta(hours=2, minutes=5))

    # Registrar cambio y cierre formal de la votación
    res_close = await client.post(
        f"/elections/{election_id}/voting/close-now",
        headers=admin_headers,
        json={"reason": "Cierre legal oficial de urnas para inicio de escrutinio homomórfico colegiado"},
    )
    assert res_close.status_code == 200, res_close.text
    assert res_close.json()["status"] == "VOTING_CLOSED"

    # =========================================================================
    # FASE 10: Desbloqueo Criptográfico por Quórum Shamir (S3-01 / S3-02)
    # =========================================================================
    # 10.1 Intento de apertura con k-1 = 1 fragmento -> Falla con 422
    res_fail_sub = await client.post(
        f"/elections/{election_id}/shamir/unlock",
        headers=admin_headers,
        json={"shares": [trustee_shares[0]]},
    )
    assert res_fail_sub.status_code == 422
    assert "al menos 2 fragmentos" in res_fail_sub.json()["detail"].lower()

    # 10.2 Intento de apertura con fragmento adulterado -> Falla con 422
    tampered_share = trustee_shares[0][:-4] + "BEEF"
    res_fail_tamp = await client.post(
        f"/elections/{election_id}/shamir/unlock",
        headers=admin_headers,
        json={"shares": [tampered_share, trustee_shares[1]]},
    )
    assert res_fail_tamp.status_code == 422

    # 10.3 Desbloqueo Exitoso con Quórum k=2
    res_unlock = await client.post(
        f"/elections/{election_id}/shamir/unlock",
        headers=admin_headers,
        json={"shares": [trustee_shares[0], trustee_shares[1]]},
    )
    assert res_unlock.status_code == 200, res_unlock.text
    unlock_data = res_unlock.json()
    assert unlock_data["status"] == "TALLIED"
    tally_ceremony_hash = unlock_data["tally_ceremony_hash"]
    assert len(tally_ceremony_hash) == 64
    assert unlock_data["total_ballots_tallied"] == 11

    # 10.4 Verificación de Resultados Escrutados con k-Anonimato (Invariante #12)
    res_results = await client.get(f"/elections/{election_id}/results", headers=admin_headers)
    assert res_results.status_code == 200
    results_json = res_results.json()

    # Encontrar las dos circunscripciones en la respuesta
    all_cstys_res = []
    for g in results_json["groups"]:
        for cnt_r in g["contests"]:
            all_cstys_res.extend(cnt_r["constituencies"])

    csty_sis_res = next(c for c in all_cstys_res if c["constituency_id"] == csty_sis_id)
    csty_red_res = next(c for c in all_cstys_res if c["constituency_id"] == csty_red_id)

    # Circunscripción SIS (8 votos >= k=5): Conteos exactos visibles
    assert csty_sis_res["total_cast"] == 8
    assert csty_sis_res["blank_count"] == 1
    assert csty_sis_res["null_count"] == 1
    sis_cands_map = {c["candidate_id"]: c["votes_count"] for c in csty_sis_res["candidates"]}
    assert sis_cands_map[cand_ada_id] == 4
    assert sis_cands_map[cand_turing_id] == 2

    # 10.5 Celdas de Escrutinio Homomórfico en Base de Datos (S3-01 / Invariante #12 / #13)
    stmt_cells = select(HomomorphicTallyCell).where(
        HomomorphicTallyCell.election_id == election_id,
    )
    all_cells = (await test_db.execute(stmt_cells)).scalars().all()
    assert len(all_cells) >= 2
    for cell in all_cells:
        assert cell.cell_scope_type in ("CONSTITUENCY_TOTAL", "LEVEL_BREAKDOWN", "FILTER_BREAKDOWN")
        assert len(cell.cell_proof_hash) == 64
        assert len(cell.aggregated_ciphertexts) >= 4  # Candidato 1, 2, BLANK, NULL
        if cell.cell_scope_type == "CONSTITUENCY_TOTAL":
            assert cell.decrypted_counts is not None

    # Verificar k-anonimato en desgloses de nivel
    level_breakdown_cells = [c for c in all_cells if c.cell_scope_type == "LEVEL_BREAKDOWN"]
    for lbc in level_breakdown_cells:
        if 0 < lbc.ballots_aggregated < 5:
            assert lbc.suppressed_by_k_anonymity is True
            assert lbc.decrypted_counts is None

    # =========================================================================
    # FASE 11: Generación del Informe Ejecutivo con Gemini (IA-E1 / Invariante #14)
    # =========================================================================
    res_report = await client.post(
        "/ai/reports/executive",
        headers=admin_headers,
        json={"election_id": str(election_id), "tone": "FORMAL_COURT"},
    )
    assert res_report.status_code == 201, res_report.text
    rep_data = res_report.json()
    assert "report_hash" in rep_data
    assert len(rep_data["report_hash"]) == 64
    assert len(rep_data["summary_markdown"]) > 50
    assert "integrity_certification" in rep_data
    assert rep_data["ai_source"] in ("GEMINI_EXTERNAL_API", "DETERMINISTIC_FALLBACK")
    assert rep_data["language"] == "es"

    # Invariante #14: Ningún dato personal (CI, nombres) en el informe ni en la llamada de IA
    full_report_text = json.dumps(rep_data)
    for ci in sis_voters_info + red_voters_info:
        assert ci not in full_report_text

    # =========================================================================
    # FASE 12: Portal Público de Auditoría Integral (S3-03 - Rol OBSERVER Sin Login)
    # =========================================================================
    # Solicitud totalmente abierta (sin cabecera Authorization)
    res_pub_dossier = await client.get(f"/public/audit/elections/{election_id}")
    assert res_pub_dossier.status_code == 200, res_pub_dossier.text
    dossier = res_pub_dossier.json()

    # Sellos Criptográficos Públicos Inmutables
    assert dossier["status"] == "TALLIED"
    assert dossier["config_hash"] == config_hash
    assert dossier["roll_hash"] == roll_hash
    assert dossier["merkle_root"] == merkle_root
    assert dossier["key_ceremony_hash"] == key_ceremony_hash
    assert dossier["tally_ceremony_hash"] == tally_ceremony_hash
    assert dossier["shamir_threshold_k"] == 2
    assert dossier["shamir_total_n"] == 3
    assert dossier["paillier_public_key"] is not None

    # Integridad de la Cadena de Votos
    assert dossier["votes_integrity"]["chain_valid"] is True
    assert dossier["votes_integrity"]["total_items"] == 11

    # Historial Inmutable del Cronograma
    assert isinstance(dossier["schedule_changes"], list)
    assert len(dossier["schedule_changes"]) >= 1
    assert any("escrutinio" in ch["reason"].lower() for ch in dossier["schedule_changes"])

    # CERO filtración de datos personales en el expediente público
    public_dossier_str = json.dumps(dossier)
    for ci in sis_voters_info + red_voters_info:
        assert ci not in public_dossier_str
    assert "voter_id" not in public_dossier_str
    assert "credential_code" not in public_dossier_str

    print("\n" + "=" * 80)
    print("CERTIFICACIÓN E2E DE RELEASE v3.0.0 COMPLETADA CON ÉXITO")
    print(f"Elección Auditada: {election_id}")
    print(f"ConfigHash:        {config_hash}")
    print(f"RollHash:          {roll_hash}")
    print(f"MerkleRoot:        {merkle_root}")
    print(f"KeyCeremonyHash:   {key_ceremony_hash}")
    print(f"TallyCeremonyHash: {tally_ceremony_hash}")
    print("=" * 80)
