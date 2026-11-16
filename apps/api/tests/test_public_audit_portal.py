"""
Pruebas de Invariantes para el Portal Público de Auditoría (S3-03 - RF-57):
- Acceso público abierto sin token JWT para observadores electorales y ciudadanía.
- Exposición de sellos inmutables (config_hash, roll_hash, merkle_root, paillier_public_key).
- Verificación en vivo de integridad de la cadena de votos y de auditoría.
- Historial completo e inmutable de cambios del cronograma (schedule_change) con motivo oficial.
- Resultados protegidos por hermetismo hasta el cierre y k-anonimato post-cierre.
- CERO filtración de datos personales (document_id, email, nombres) ni votos individuales.
"""
import json
import uuid
from datetime import datetime, timedelta, timezone
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.time import FakeTimeProvider
from app.db.models.election import (
    Election,
    ElectionStatus,
    HomomorphicTallyCell,
    ScheduleChange,
)
from app.db.models.organization import Organization, OrganizationStatus, OrganizationType
from app.db.models.structure import (
    Constituency,
    Contest,
    HierarchyLevel,
    UnitNode,
    VoterGroup,
)
from app.db.models.voter import Voter, VoterStatus
from app.db.models.voting import Vote, VoteChoiceType


@pytest.mark.asyncio
async def test_public_audit_elections_list_without_auth(
    test_db: AsyncSession,
    client: AsyncClient,
    org1_setup,
):
    """
    S3-03: Verifica que GET /api/v1/public/audit/elections sea público,
    liste elecciones publicadas y excluya borradores en estado DRAFT.
    """
    org, admin, _ = org1_setup
    now = datetime(2026, 11, 26, 12, 0, 0, tzinfo=timezone.utc)

    # 1. Elección en borrador (DRAFT) - NO debe aparecer
    elec_draft = Election(
        organization_id=org.id,
        name="Elección Borrador Interno",
        timezone="America/La_Paz",
        registration_opens_at=now + timedelta(days=1),
        registration_closes_at=now + timedelta(days=2),
        voting_opens_at=now + timedelta(days=3),
        voting_closes_at=now + timedelta(days=4),
        status=ElectionStatus.DRAFT,
        created_by=admin.id,
    )

    # 2. Elección publicada (REGISTRATION_OPEN) - Debe aparecer
    elec_pub = Election(
        organization_id=org.id,
        name="Elección Universitaria Activa",
        timezone="America/La_Paz",
        registration_opens_at=now - timedelta(days=1),
        registration_closes_at=now + timedelta(days=2),
        voting_opens_at=now + timedelta(days=3),
        voting_closes_at=now + timedelta(days=4),
        status=ElectionStatus.REGISTRATION_OPEN,
        config_hash="a" * 64,
        created_by=admin.id,
    )

    test_db.add_all([elec_draft, elec_pub])
    await test_db.commit()

    # Invocación sin token de autenticación
    res = await client.get("/public/audit/elections")
    assert res.status_code == 200, res.text
    data = res.json()

    assert isinstance(data, list)
    names = [e["name"] for e in data]
    assert "Elección Universitaria Activa" in names
    assert "Elección Borrador Interno" not in names


@pytest.mark.asyncio
async def test_public_audit_dossier_integrity_and_schedule_history_no_pii(
    test_db: AsyncSession,
    client: AsyncClient,
    org1_setup,
    fake_time: FakeTimeProvider,
):
    """
    S3-03 & Invariantes #11, #12, #14:
    Consulta el expediente público integral de una elección concluida.
    Verifica sellos, cadenas de bloques, historial de cronograma y supresión por k-anonimato
    sin exponer jamás CIs, correos o nombres de electores.
    """
    org, admin, _ = org1_setup
    now = datetime(2026, 11, 26, 20, 0, 0, tzinfo=timezone.utc)
    fake_time.set_time(now)

    # 1. Crear Elección TALLIED con sellos
    election = Election(
        organization_id=org.id,
        name="Elección Rectoral 2026",
        timezone="America/La_Paz",
        registration_opens_at=now - timedelta(days=15),
        registration_closes_at=now - timedelta(days=10),
        voting_opens_at=now - timedelta(days=2),
        voting_closes_at=now - timedelta(days=1),
        status=ElectionStatus.TALLIED,
        k_anonymity=5,
        created_by=admin.id,
        config_hash="c0ffee" * 10 + "0000",
        roll_hash="decaf0" * 10 + "1111",
        merkle_root="beef00" * 10 + "2222",
        key_ceremony_hash="keycer" * 10 + "3333",
        tally_ceremony_hash="tallyc" * 10 + "4444",
        paillier_public_n="1234567890987654321",
        paillier_public_key="1234567890987654321",
        shamir_threshold_k=3,
        shamir_total_n=5,
    )
    test_db.add(election)
    await test_db.flush()

    # 2. Historial de cambios de cronograma
    ch = ScheduleChange(
        organization_id=org.id,
        election_id=election.id,
        field_name="voting_closes_at",
        old_value=now - timedelta(days=1, hours=2),
        new_value=now - timedelta(days=1),
        election_status_at_change="VOTING_OPEN",
        reason="Ampliación autorizada por resolución del Tribunal Electoral Universitario por alta participación.",
        changed_by=admin.id,
        changed_at=now - timedelta(days=1, hours=2),
    )
    test_db.add(ch)
    await test_db.flush()

    # 3. Estructura y Celdas de Escrutinio con k-anonimato
    grp = VoterGroup(organization_id=org.id, election_id=election.id, name="General", code="GEN")
    test_db.add(grp)
    await test_db.flush()

    lvl = HierarchyLevel(group_id=grp.id, depth=1, name="Universidad")
    test_db.add(lvl)
    await test_db.flush()

    node_main = UnitNode(group_id=grp.id, level_id=lvl.id, parent_id=None, name="Campus Central", code="CC", path="/CC/", depth=1)
    node_small = UnitNode(group_id=grp.id, level_id=lvl.id, parent_id=None, name="Sede Rural Pequeña", code="SR", path="/SR/", depth=1)
    test_db.add_all([node_main, node_small])
    await test_db.flush()

    cnt = Contest(
        group_id=grp.id,
        scope_level_id=lvl.id,
        name="Rector",
        display_order=1,
    )
    test_db.add(cnt)
    await test_db.flush()

    csty_main = Constituency(contest_id=cnt.id, node_id=node_main.id)
    csty_small = Constituency(contest_id=cnt.id, node_id=node_small.id)
    test_db.add_all([csty_main, csty_small])
    await test_db.flush()

    # Celda 1: Campus Central (> k=5 votos) -> Resultados descifrados visibles
    cell_main = HomomorphicTallyCell(
        organization_id=org.id,
        election_id=election.id,
        contest_id=cnt.id,
        constituency_id=csty_main.id,
        cell_scope_type="CONSTITUENCY_TOTAL",
        cell_key="TOTAL",
        cell_label="Campus Central",
        ballots_aggregated=120,
        option_order_keys=["cand-1", "cand-2", "BLANK", "NULL"],
        aggregated_ciphertexts=["0x1", "0x2"],
        decrypted_counts={"cand-1": 80, "cand-2": 35, "BLANK": 5, "NULL": 0},
        suppressed_by_k_anonymity=False,
        cell_proof_hash="cellproofmain0000000000000000000000000000000000000000000000000000",
    )

    # Celda 2: Sede Rural (3 votos < k=5) -> Suprimido por k-anonimato
    cell_small = HomomorphicTallyCell(
        organization_id=org.id,
        election_id=election.id,
        contest_id=cnt.id,
        constituency_id=csty_small.id,
        cell_scope_type="CONSTITUENCY_TOTAL",
        cell_key="TOTAL",
        cell_label="Sede Rural Pequeña",
        ballots_aggregated=3,
        option_order_keys=["cand-1", "cand-2", "BLANK", "NULL"],
        aggregated_ciphertexts=["0x3", "0x4"],
        decrypted_counts=None,
        suppressed_by_k_anonymity=True,
        cell_proof_hash="cellproofsmall000000000000000000000000000000000000000000000000000",
    )
    test_db.add_all([cell_main, cell_small])
    await test_db.flush()

    # 4. Cadena de votos íntegra (3 votos de prueba)
    prev_h = "0" * 64
    for idx in range(1, 4):
        vh = f"{idx:064x}"
        v = Vote(
            election_id=election.id,
            constituency_id=csty_main.id,
            chain_index=idx,
            prev_hash=prev_h,
            vote_hash=vh,
            receipt_hash=f"RCPT-{idx:032x}",
            encoded_payload=json.dumps({"scheme": "PAILLIER_V1"}),
            choice_type=VoteChoiceType.BLANK,
            candidate_id=None,
            segment_path="/CC/",
            nullifier=f"nullifier-pub-{idx}",
            created_at=now,
        )
        test_db.add(v)
        prev_h = vh

    # 5. Votantes confidenciales en padrón
    voter_secret = Voter(
        organization_id=org.id,
        election_id=election.id,
        group_id=grp.id,
        node_id=node_main.id,
        document_id="CI-TOPSECRET-998877",
        full_name="Juan Perez Confidencial",
        email="juan.confidencial@secreto.com",
        status=VoterStatus.ACTIVE,
    )
    test_db.add(voter_secret)
    await test_db.commit()

    # 6. Invocación pública sin token
    res = await client.get(f"/public/audit/elections/{election.id}")
    assert res.status_code == 200, res.text
    data = res.json()

    # Sellos y estado
    assert data["election_id"] == str(election.id)
    assert data["config_hash"] == election.config_hash
    assert data["roll_hash"] == election.roll_hash
    assert data["merkle_root"] == election.merkle_root
    assert data["key_ceremony_hash"] == election.key_ceremony_hash
    assert data["tally_ceremony_hash"] == election.tally_ceremony_hash
    assert data["shamir_threshold_k"] == 3
    assert data["shamir_total_n"] == 5

    # Verificación en vivo de cadena de votos
    assert data["votes_integrity"]["chain_valid"] is True
    assert data["votes_integrity"]["total_items"] == 3

    # Historial de cronograma con motivo oficial
    assert len(data["schedule_changes"]) == 1
    assert data["schedule_changes"][0]["field_name"] == "voting_closes_at"
    assert "Ampliación autorizada" in data["schedule_changes"][0]["reason"]

    # Resultados post-cierre y k-anonimato
    assert data["results_published"] is True
    results = data["results"]
    assert len(results) == 2

    # Celda mayor a k=5 tiene resultados visibles
    res_main = next(r for r in results if r["constituency_label"] == "Campus Central")
    assert res_main["suppressed_by_k_anonymity"] is False
    assert res_main["results"]["cand-1"] == 80

    # Celda con 3 votos (< k=5) está suprimida por k-anonimato
    res_small = next(r for r in results if r["constituency_label"] == "Sede Rural Pequeña")
    assert res_small["suppressed_by_k_anonymity"] is True
    assert res_small["results"] is None

    # INVARIANTE #14: Comprobar que NINGÚN dato personal se filtra en el JSON devuelto
    raw_response_text = json.dumps(data)
    assert "CI-TOPSECRET" not in raw_response_text
    assert "Juan Perez Confidencial" not in raw_response_text
    assert "secreto.com" not in raw_response_text
    assert "juan.confidencial" not in raw_response_text


@pytest.mark.asyncio
async def test_public_audit_dossier_hermetic_results_when_voting_open(
    test_db: AsyncSession,
    client: AsyncClient,
    org1_setup,
):
    """
    Invariante #11: Mientras la votación está abierta (VOTING_OPEN),
    el portal público muestra sellos y participación pero NUNCA resultados.
    """
    org, admin, _ = org1_setup
    now = datetime(2026, 11, 26, 12, 0, 0, tzinfo=timezone.utc)

    election = Election(
        organization_id=org.id,
        name="Elección Abierta Hermética",
        timezone="America/La_Paz",
        registration_opens_at=now - timedelta(days=2),
        registration_closes_at=now - timedelta(hours=10),
        voting_opens_at=now - timedelta(hours=4),
        voting_closes_at=now + timedelta(hours=4),
        status=ElectionStatus.VOTING_OPEN,
        created_by=admin.id,
        config_hash="confighashopen0000000000000000000000000000000000000000000000000000",
    )
    test_db.add(election)
    await test_db.commit()

    res = await client.get(f"/public/audit/elections/{election.id}")
    assert res.status_code == 200, res.text
    data = res.json()

    assert data["results_published"] is False
    assert data["results"] is None
    assert "herméticos" in data["results_notice"].lower()
