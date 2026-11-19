"""
Suite de Pruebas Automatizadas de Invariantes: Cifrado Homomórfico Paillier y Secreto Compartido de Shamir
Cubre:
- S3-01: Cifrado Homomórfico con Paillier en Producción (VoteCodec y HomomorphicTallyEngine).
- S3-02: Reparto de la Clave de Descifrado con Shamir (k de n) y Ceremonia Criptográfica de la Corte Electoral.
- Invariantes #9 (Desvinculación), #11 (Hermetismo hasta cierre), #12 (k-Anonimato en celdas homomórficas) e #13 (VoteCodec seguro).
"""
import uuid
from datetime import datetime, timedelta, timezone
import pytest
from httpx import AsyncClient
import phe.paillier as paillier
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.time import FakeTimeProvider
from app.crypto.shamir import (
    DEFAULT_SHAMIR_PRIME,
    InsufficientSharesException,
    InvalidShareCommitmentException,
    ShamirSecurityException,
    combine_shares,
    compute_share_commitment,
    format_share,
    pack_paillier_private_key,
    parse_share,
    split_secret,
    unpack_paillier_private_key,
)
from app.crypto.vote_codec import HomomorphicPaillierVoteCodec, default_vote_codec
from app.db.models.election import (
    Election,
    ElectionStatus,
    ElectoralTrusteeShare,
    HomomorphicTallyCell,
)
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
from app.db.models.voter import Voter, VoterStatus
from app.db.models.voting import Vote, VoteChoiceType, VotingCredential
from app.modules.results.homomorphic_tally import HomomorphicTallyEngine


@pytest.mark.asyncio
async def test_paillier_vector_encryption_and_homomorphic_addition_exact_match():
    """
    S3-01: Valida que el cifrado asimétrico Paillier permita sumar votos homomórficamente
    E(m1) * E(m2) % n^2 = E(m1 + m2) y obtener el mismo resultado exacto que el conteo plano
    sin revelar el sentido de los votos individuales.
    """
    # 1. Generar par de claves Paillier de 1024 bits
    public_key, private_key = paillier.generate_paillier_keypair(n_length=1024)
    codec = HomomorphicPaillierVoteCodec(public_key=public_key, private_key=private_key)

    cand_a = uuid.uuid4()
    cand_b = uuid.uuid4()
    cand_c = uuid.uuid4()
    option_keys = [str(cand_a), str(cand_b), str(cand_c), "BLANK", "NULL"]
    num_options = len(option_keys)

    # 2. Cifrar una selección individual y verificar estructura JSON canónica
    codec_public_only = HomomorphicPaillierVoteCodec(public_key=public_key)
    payload_a = codec_public_only.encode("CANDIDATE", cand_a, public_key=public_key, option_keys=option_keys)
    decoded_without_sk = codec_public_only.decode(payload_a)
    assert decoded_without_sk["scheme"] == "PAILLIER_V1"
    assert "decrypted_vector" not in decoded_without_sk  # Invariante #13: No revela el voto sin private_key

    decoded_with_sk = codec.decode(payload_a, private_key=private_key)
    assert decoded_with_sk["decrypted_vector"] == [1, 0, 0, 0, 0]
    assert decoded_with_sk["decoded_selection"] == str(cand_a)

    # 3. Simular emisión de 20 votos diversos
    # Distribución esperada:
    # Cand A: 8 votos
    # Cand B: 5 votos
    # Cand C: 4 votos
    # BLANK:  2 votos
    # NULL:   1 voto
    vote_plan = (
        [("CANDIDATE", cand_a)] * 8
        + [("CANDIDATE", cand_b)] * 5
        + [("CANDIDATE", cand_c)] * 4
        + [("BLANK", None)] * 2
        + [("NULL", None)] * 1
    )
    expected_tallies = [8, 5, 4, 2, 1]

    # Acumulador homomórfico inicializado en 1 (identidad multiplicativa)
    n_sq = public_key.n * public_key.n
    homomorphic_accumulator = [1] * num_options

    for choice_type, c_id in vote_plan:
        enc_payload_str = codec.encode(
            choice_type=choice_type,
            candidate_id=c_id,
            public_key=public_key,
            option_keys=option_keys,
        )
        vote_data = codec.decode(enc_payload_str)
        cipher_ints = [int(h, 16) for h in vote_data["ciphertexts"]]

        # Suma homomórfica aditiva vía multiplicación modular
        for i in range(num_options):
            homomorphic_accumulator[i] = (homomorphic_accumulator[i] * cipher_ints[i]) % n_sq

    # 4. Descifrar ÚNICAMENTE el vector acumulado
    decrypted_final_tallies = []
    for i in range(num_options):
        enc_total = paillier.EncryptedNumber(public_key, homomorphic_accumulator[i], 0)
        decrypted_final_tallies.append(private_key.decrypt(enc_total))

    # 5. Comprobar equivalencia matemática 100% exacta
    assert decrypted_final_tallies == expected_tallies
    assert sum(decrypted_final_tallies) == 20


@pytest.mark.asyncio
async def test_shamir_threshold_reconstruction_and_sub_threshold_failure():
    """
    S3-02: Valida que el esquema de secreto compartido de Shamir permita reconstruir
    exactamente la clave privada Paillier con k de n fragmentos y que falle con k-1 fragmentos.
    """
    # 1. Generar clave privada Paillier
    pub, priv = paillier.generate_paillier_keypair(n_length=1024)
    secret_s = pack_paillier_private_key(priv.p, priv.q)

    # 2. Dividir secreto con k=3 y n=5
    k = 3
    n = 5
    shares = split_secret(secret_s, k=k, n=n)
    assert len(shares) == 5

    # 3. Comprobar reconstrucción exitosa con cualquier combinación de 3 fragmentos
    combinations_to_test = [
        [shares[0], shares[1], shares[2]],  # {1, 2, 3}
        [shares[0], shares[2], shares[4]],  # {1, 3, 5}
        [shares[1], shares[3], shares[4]],  # {2, 4, 5}
    ]

    for combo in combinations_to_test:
        recovered_s = combine_shares(combo, min_k=k)
        assert recovered_s == secret_s
        rec_p, rec_q = unpack_paillier_private_key(recovered_s)
        assert rec_p == priv.p
        assert rec_q == priv.q
        assert (rec_p * rec_q) == pub.n

    # 4. Comprobar que 4 o 5 fragmentos también reconstruyen el secreto
    assert combine_shares(shares[:4], min_k=k) == secret_s
    assert combine_shares(shares, min_k=k) == secret_s

    # 5. Comprobar fallo estricto con k-1 = 2 fragmentos (excepción de seguridad)
    with pytest.raises(InsufficientSharesException) as exc_info:
        combine_shares(shares[:2], min_k=k)
    assert "Se requieren al menos 3 fragmentos" in str(exc_info.value)

    # 6. Comprobar que interpolar 2 fragmentos sin control de umbral genera basura matemática
    # que es rechazada por unpack_paillier_private_key
    sub_threshold_raw = combine_shares(shares[:2])
    assert sub_threshold_raw != secret_s
    with pytest.raises(ShamirSecurityException):
        unpack_paillier_private_key(sub_threshold_raw)

    # 7. Comprobar compromisos criptográficos y detección de alteración
    election_uuid = uuid.uuid4()
    valid_commit = compute_share_commitment(election_uuid, 1, shares[0][1])
    tampered_commit = compute_share_commitment(election_uuid, 1, shares[0][1] + 1)
    assert valid_commit != tampered_commit


@pytest.mark.asyncio
async def test_e2e_ceremony_setup_voting_closed_and_shamir_unlock(
    test_db: AsyncSession,
    client: AsyncClient,
    org1_setup,
    fake_time: FakeTimeProvider,
):
    """
    Prueba End-to-End completa de integración API:
    1. POST /elections/{id}/shamir/setup genera claves y fragmentos Shamir.
    2. GET /elections/{id}/shamir/status refleja el estado completado.
    3. Emisión de votos en cabina con VoteCodec Paillier.
    4. Cierre de votación (VOTING_CLOSED).
    5. Intento de desbloqueo con k-1 fragmentos es rechazado con HTTP 422.
    6. Intento de desbloqueo con fragmento alterado es rechazado con HTTP 422.
    7. Desbloqueo exitoso con quórum k=3 en POST /elections/{id}/shamir/unlock.
    8. Verificación de resultados finales en GET /results/{id}.
    """
    org, admin, admin_token = org1_setup
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    now = datetime(2026, 11, 26, 9, 0, 0, tzinfo=timezone.utc)
    fake_time.set_time(now)

    # 1. Crear Elección en DRAFT con cifrado homomórfico Paillier
    election = Election(
        organization_id=org.id,
        name="Elección Universitaria con Paillier y Shamir S3",
        timezone="America/La_Paz",
        registration_opens_at=now - timedelta(days=2),
        registration_closes_at=now - timedelta(hours=2),
        voting_opens_at=now - timedelta(hours=1),
        voting_closes_at=now + timedelta(hours=8),
        status=ElectionStatus.DRAFT,
        k_anonymity=5,
        created_by=admin.id,
        encryption_scheme="PAILLIER_HOMOMORPHIC",
        paillier_key_size=1024,
        shamir_threshold_k=3,
        shamir_total_n=5,
    )
    test_db.add(election)
    await test_db.flush()

    # 2. Estructura: Grupo, Nivel, Nodo, Cargo y 2 Candidatos
    grp = VoterGroup(organization_id=org.id, election_id=election.id, name="ESTUDIANTES", code="EST")
    test_db.add(grp)
    await test_db.flush()

    lvl = HierarchyLevel(group_id=grp.id, depth=1, name="Universidad")
    test_db.add(lvl)
    await test_db.flush()

    node = UnitNode(group_id=grp.id, level_id=lvl.id, parent_id=None, name="Campus Central", code="CC", path="/CC/", depth=1)
    test_db.add(node)
    await test_db.flush()

    contest = Contest(
        group_id=grp.id,
        scope_level_id=lvl.id,
        name="Presidente Federación",
        display_order=1,
        allow_blank=True,
        allow_null=True,
    )
    test_db.add(contest)
    await test_db.flush()

    constituency = Constituency(contest_id=contest.id, node_id=node.id)
    test_db.add(constituency)
    await test_db.flush()

    cand_1 = Candidate(constituency_id=constituency.id, name="Candidato Alpha", ballot_order=1)
    cand_2 = Candidate(constituency_id=constituency.id, name="Candidato Beta", ballot_order=2)
    test_db.add_all([cand_1, cand_2])
    await test_db.flush()

    # 3. Ejecutar Ceremonia de Claves de Shamir: POST /api/v1/elections/{id}/shamir/setup
    res_setup = await client.post(
        f"/elections/{election.id}/shamir/setup",
        headers=admin_headers,
        json={"key_size": 1024, "threshold_k": 3, "total_n": 5},
    )
    assert res_setup.status_code == 201
    setup_data = res_setup.json()
    assert setup_data["encryption_scheme"] == "PAILLIER_HOMOMORPHIC"
    assert setup_data["threshold_k"] == 3
    assert setup_data["total_n"] == 5
    assert len(setup_data["key_ceremony_hash"]) == 64
    assert len(setup_data["trustees"]) == 5

    trustee_tokens = [t["share_token"] for t in setup_data["trustees"]]
    assert all(t.startswith("VS-SHARE-") for t in trustee_tokens)

    # 4. Consultar Estado de Ceremonia: GET /api/v1/elections/{id}/shamir/status
    res_status = await client.get(
        f"/elections/{election.id}/shamir/status",
        headers=admin_headers,
    )
    assert res_status.status_code == 200
    status_data = res_status.json()
    assert status_data["key_ceremony_completed"] is True
    assert status_data["tally_ceremony_completed"] is False

    # 5. Registrar 4 votantes y emitir credenciales
    voters = []
    for i in range(4):
        v = Voter(
            organization_id=org.id,
            election_id=election.id,
            group_id=grp.id,
            node_id=node.id,
            document_id=f"CI-PAILLIER-{i+1}",
            full_name=f"Votante Cifrado {i+1}",
            status=VoterStatus.ACTIVE,
        )
        test_db.add(v)
        voters.append(v)
    await test_db.flush()

    # Abrir votación y emitir credenciales
    res_open = await client.post(
        f"/elections/{election.id}/voting/open-now",
        headers=admin_headers,
    )
    assert res_open.status_code == 200

    # Obtener credenciales de despacho
    res_disp = await client.get(
        f"/elections/{election.id}/voting/credentials-dispatch",
        headers=admin_headers,
    )
    dispatch = res_disp.json()

    # 6. Emitir votos en cabina:
    # Votante 1: Vota por Candidato Alpha
    # Votante 2: Vota por Candidato Alpha
    # Votante 3: Vota por Candidato Beta
    # Votante 4: Vota en BLANCO
    vote_choices = [
        ("CI-PAILLIER-1", "CANDIDATE", str(cand_1.id)),
        ("CI-PAILLIER-2", "CANDIDATE", str(cand_1.id)),
        ("CI-PAILLIER-3", "CANDIDATE", str(cand_2.id)),
        ("CI-PAILLIER-4", "BLANK", None),
    ]

    for doc_id, c_type, c_id in vote_choices:
        cred_code = next(item["credential_code"] for item in dispatch if item["document_id"] == doc_id)
        res_log = await client.post(
            "/voter/login",
            json={"document_id": doc_id, "credential_code": cred_code},
        )
        assert res_log.status_code == 200
        v_token = res_log.json()["access_token"]

        cast_res = await client.post(
            "/ballot/cast",
            headers={"Authorization": f"Bearer {v_token}"},
            json={
                "selections": [
                    {
                        "contest_id": str(contest.id),
                        "constituency_id": str(constituency.id),
                        "choice_type": c_type,
                        "candidate_id": c_id,
                    }
                ]
            },
        )
        assert cast_res.status_code == 201

    # Invariante #13: Verificar que los votos registrados en BD contienen ciphertexts de Paillier
    stmt_v = select(Vote).where(Vote.election_id == election.id)
    saved_votes = (await test_db.execute(stmt_v)).scalars().all()
    assert len(saved_votes) == 4
    for sv in saved_votes:
        assert '"scheme":"PAILLIER_V1"' in sv.encoded_payload
        assert '"ciphertexts":[' in sv.encoded_payload

    # 7. Pasar a VOTING_CLOSED
    fake_time.set_time(now + timedelta(hours=9))
    res_close = await client.post(
        f"/elections/{election.id}/voting/close-now",
        headers=admin_headers,
        json={"reason": "Cierre oficial de mesas de sufragio para inicio de escrutinio"},
    )
    assert res_close.status_code == 200

    # 8. Intento de desbloqueo con k-1 = 2 fragmentos -> 422 Unprocessable Entity
    res_sub_unlock = await client.post(
        f"/elections/{election.id}/shamir/unlock",
        headers=admin_headers,
        json={"shares": trustee_tokens[:2]},
    )
    assert res_sub_unlock.status_code == 422
    assert "al menos 3 fragmentos" in res_sub_unlock.json()["detail"].lower()

    # 9. Intento de desbloqueo con fragmento alterado -> 422 Unprocessable Entity
    tampered_token = trustee_tokens[0][:-4] + "DEAD"
    res_tampered = await client.post(
        f"/elections/{election.id}/shamir/unlock",
        headers=admin_headers,
        json={"shares": [tampered_token, trustee_tokens[1], trustee_tokens[2]]},
    )
    assert res_tampered.status_code == 422
    assert "no coincide con el compromiso criptográfico" in res_tampered.json()["detail"]

    # 10. Desbloqueo oficial exitoso con quórum k=3: POST /api/v1/elections/{id}/shamir/unlock
    res_unlock_success = await client.post(
        f"/elections/{election.id}/shamir/unlock",
        headers=admin_headers,
        json={"shares": [trustee_tokens[0], trustee_tokens[2], trustee_tokens[4]]},
    )
    assert res_unlock_success.status_code == 200
    unlock_data = res_unlock_success.json()
    assert unlock_data["status"] == "TALLIED"
    assert len(unlock_data["tally_ceremony_hash"]) == 64
    assert unlock_data["total_ballots_tallied"] == 4

    # 11. Consultar Resultados Oficiales Escrutados: GET /api/v1/elections/{id}/results
    res_results = await client.get(
        f"/elections/{election.id}/results",
        headers=admin_headers,
    )
    assert res_results.status_code == 200
    res_json = res_results.json()
    group_res = res_json["groups"][0]
    contest_res = group_res["contests"][0]
    const_res = contest_res["constituencies"][0]

    # Verificar concordancia exacta con los votos emitidos
    assert const_res["total_cast"] == 4
    assert const_res["blank_count"] == 1
    assert const_res["null_count"] == 0

    cands_summary = {c["candidate_id"]: c["votes_count"] for c in const_res["candidates"]}
    assert cands_summary[str(cand_1.id)] == 2  # Alpha: 2 votos
    assert cands_summary[str(cand_2.id)] == 1  # Beta: 1 voto


@pytest.mark.asyncio
async def test_homomorphic_tally_engine_k_anonymity_suppression(
    test_db: AsyncSession,
    client: AsyncClient,
    org1_setup,
):
    """
    S3-01 e Invariante #12: Valida que en desgloses jerárquicos, las celdas con menos
    de k votos permanezcan suprimidas y jamás se descifren (decrypted_counts = None),
    mientras que las celdas con >= k votos se descifren con exactitud.
    """
    org, admin, admin_token = org1_setup
    now = datetime(2026, 11, 26, 10, 0, 0, tzinfo=timezone.utc)

    # Elección con k_anonymity = 5
    election = Election(
        organization_id=org.id,
        name="Elección con k-Anonimato Homomórfico",
        timezone="America/La_Paz",
        registration_opens_at=now - timedelta(days=2),
        registration_closes_at=now - timedelta(hours=2),
        voting_opens_at=now - timedelta(hours=1),
        voting_closes_at=now + timedelta(hours=4),
        status=ElectionStatus.VOTING_CLOSED,
        k_anonymity=5,
        created_by=admin.id,
        encryption_scheme="PAILLIER_HOMOMORPHIC",
        paillier_key_size=1024,
    )
    test_db.add(election)
    await test_db.flush()

    # Generar claves Paillier
    pub, priv = paillier.generate_paillier_keypair(n_length=1024)
    election.paillier_public_n = str(pub.n)
    election.paillier_public_key = str(pub.n)
    await test_db.flush()

    # Estructura: Nivel Facultad y 2 Carreras
    grp = VoterGroup(organization_id=org.id, election_id=election.id, name="ESTUDIANTES", code="EST")
    test_db.add(grp)
    await test_db.flush()

    lvl_fac = HierarchyLevel(group_id=grp.id, depth=1, name="Facultad")
    lvl_car = HierarchyLevel(group_id=grp.id, depth=2, name="Carrera")
    test_db.add_all([lvl_fac, lvl_car])
    await test_db.flush()

    node_fac = UnitNode(group_id=grp.id, level_id=lvl_fac.id, parent_id=None, name="FICCT", code="FICCT", path="/FICCT/", depth=1)
    test_db.add(node_fac)
    await test_db.flush()

    node_sis = UnitNode(group_id=grp.id, level_id=lvl_car.id, parent_id=node_fac.id, name="Sistemas", code="SIS", path="/FICCT/SIS/", depth=2)
    node_red = UnitNode(group_id=grp.id, level_id=lvl_car.id, parent_id=node_fac.id, name="Redes", code="RED", path="/FICCT/RED/", depth=2)
    test_db.add_all([node_sis, node_red])
    await test_db.flush()

    contest = Contest(group_id=grp.id, scope_level_id=lvl_fac.id, name="Decano", display_order=1)
    test_db.add(contest)
    await test_db.flush()

    # Desglose a nivel Carrera
    breakdown = ContestBreakdown(contest_id=contest.id, kind=BreakdownKind.LEVEL, level_id=lvl_car.id, label="Por Carrera")
    test_db.add(breakdown)
    await test_db.flush()

    constituency = Constituency(contest_id=contest.id, node_id=node_fac.id)
    test_db.add(constituency)
    await test_db.flush()

    cand_dec1 = Candidate(constituency_id=constituency.id, name="Ing. Candidato 1", ballot_order=1)
    cand_dec2 = Candidate(constituency_id=constituency.id, name="Ing. Candidato 2", ballot_order=2)
    test_db.add_all([cand_dec1, cand_dec2])
    await test_db.flush()

    codec = HomomorphicPaillierVoteCodec(public_key=pub, private_key=priv)
    option_keys = [str(cand_dec1.id), str(cand_dec2.id), "BLANK", "NULL"]

    # Simular votos:
    # Carrera SIS: 6 votos (>= k=5, NO debe suprimirse)
    # Carrera RED: 2 votos (< k=5, DEBE suprimirse por k-anonimato)
    for i in range(6):
        payload = codec.encode("CANDIDATE", cand_dec1.id, public_key=pub, option_keys=option_keys)
        test_db.add(Vote(
            election_id=election.id,
            constituency_id=constituency.id,
            choice_type=VoteChoiceType.CANDIDATE,
            candidate_id=cand_dec1.id,
            encoded_payload=payload,
            segment_path="/FICCT/SIS/",
            nullifier=f"nullifier-sis-{i}",
            receipt_hash=f"receipt-sis-{i}",
            created_at=now,
        ))

    for i in range(2):
        payload = codec.encode("CANDIDATE", cand_dec2.id, public_key=pub, option_keys=option_keys)
        test_db.add(Vote(
            election_id=election.id,
            constituency_id=constituency.id,
            choice_type=VoteChoiceType.CANDIDATE,
            candidate_id=cand_dec2.id,
            encoded_payload=payload,
            segment_path="/FICCT/RED/",
            nullifier=f"nullifier-red-{i}",
            receipt_hash=f"receipt-red-{i}",
            created_at=now,
        ))
    await test_db.flush()

    # 1. Agregación homomórfica previa
    cells = await HomomorphicTallyEngine.aggregate_votes_for_election(test_db, election)
    assert len(cells) >= 3  # TOTAL, SIS, RED

    cell_sis = next(c for c in cells if c.cell_key == "/FICCT/SIS/")
    cell_red = next(c for c in cells if c.cell_key == "/FICCT/RED/")

    assert cell_sis.ballots_aggregated == 6
    assert cell_sis.suppressed_by_k_anonymity is False

    assert cell_red.ballots_aggregated == 2
    assert cell_red.suppressed_by_k_anonymity is True  # Invariante #12

    # 2. Descifrado oficial del escrutinio con la clave privada Paillier
    tally_summary = await HomomorphicTallyEngine.decrypt_election_tally(test_db, election, priv)

    assert tally_summary["suppressed_cells_count"] >= 1
    assert cell_sis.decrypted_counts is not None
    assert cell_sis.decrypted_counts[str(cand_dec1.id)] == 6

    # Invariante #12: La celda de Redes permanece con decrypted_counts = None
    assert cell_red.decrypted_counts is None
