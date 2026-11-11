"""
Pruebas Automatizadas de Integridad Criptográfica: Árbol de Merkle del Padrón Electoral (S2-07)
Verifica:
1. Cálculo determinista de 'merkle_root' al congelar el padrón (REGISTRATION_CLOSED).
2. Generación de prueba criptográfica de inclusión (Merkle proof) para un votante.
3. Verificación matemática de la prueba a través del endpoint público sin exponer el padrón.
4. Detección y rechazo de pruebas manipuladas o falsificadas (valid == False).
"""
import uuid
from datetime import datetime, timedelta, timezone
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.time import FakeTimeProvider
from app.crypto.merkle import MerkleTree, compute_voter_leaf_hash
from app.db.models.election import Election, ElectionStatus
from app.db.models.structure import HierarchyLevel, UnitNode, VoterGroup
from app.db.models.voter import Voter, VoterStatus


@pytest.mark.asyncio
async def test_merkle_tree_root_and_inclusion_proof(
    test_db: AsyncSession,
    client: AsyncClient,
    org1_setup,
    fake_time: FakeTimeProvider,
):
    org, admin, admin_token = org1_setup
    now = datetime(2026, 11, 20, 10, 0, 0, tzinfo=timezone.utc)
    fake_time.set_time(now)
    auth_headers = {"Authorization": f"Bearer {admin_token}"}

    # 1. Crear Elección en REGISTRATION_OPEN
    election = Election(
        organization_id=org.id,
        name="Elección Merkle S2-07",
        timezone="America/La_Paz",
        registration_opens_at=now - timedelta(days=2),
        registration_closes_at=now + timedelta(hours=1),
        voting_opens_at=now + timedelta(hours=2),
        voting_closes_at=now + timedelta(hours=10),
        status=ElectionStatus.REGISTRATION_OPEN,
        config_hash="CONFIG_HASH_MERKLE_TEST",
        created_by=admin.id,
    )
    test_db.add(election)
    await test_db.flush()

    grp = VoterGroup(organization_id=org.id, election_id=election.id, name="Facultad", code="FAC")
    test_db.add(grp)
    await test_db.flush()

    lvl = HierarchyLevel(group_id=grp.id, depth=1, name="Carrera")
    test_db.add(lvl)
    await test_db.flush()

    node = UnitNode(group_id=grp.id, level_id=lvl.id, parent_id=None, name="Informática", code="INF", path="/INF/", depth=1)
    test_db.add(node)
    await test_db.flush()

    # Inscribir 5 votantes
    voter_cis = [f"CI-MERKLE-{i}" for i in range(1, 6)]
    voters = []
    for i, ci in enumerate(voter_cis):
        v = Voter(
            organization_id=org.id,
            election_id=election.id,
            group_id=grp.id,
            node_id=node.id,
            document_id=ci,
            full_name=f"Elector Merkle {i+1}",
            status=VoterStatus.ACTIVE,
            attributes={"carrera": "INF"},
        )
        test_db.add(v)
        voters.append(v)
    await test_db.commit()

    # 2. Congelar el padrón electoral -> transición a REGISTRATION_CLOSED
    # Avanzamos el reloj simulado para pasar registration_closes_at
    fake_time.set_time(now + timedelta(hours=1, minutes=5))
    res_freeze = await client.post(f"/elections/{election.id}/registration/close-now", headers=auth_headers)
    assert res_freeze.status_code == 200
    freeze_data = res_freeze.json()
    assert freeze_data["merkle_root"] is not None
    assert len(freeze_data["merkle_root"]) == 64
    assert freeze_data["roll_hash"] is not None

    merkle_root_db = freeze_data["merkle_root"]

    # 3. Obtener prueba de inclusión para el votante 3 (CI-MERKLE-3)
    target_ci = voter_cis[2]
    res_proof = await client.get(f"/elections/{election.id}/merkle/proof/{target_ci}", headers=auth_headers)
    assert res_proof.status_code == 200
    proof_data = res_proof.json()

    assert proof_data["document_id"] == target_ci
    assert proof_data["election_id"] == str(election.id)
    assert proof_data["merkle_root"] == merkle_root_db
    assert proof_data["leaf_hash"] is not None
    assert proof_data["leaf_index"] >= 0
    assert len(proof_data["proof"]) > 0

    # 4. Verificar la prueba de inclusión mediante el endpoint de verificación pública
    verify_payload = {
        "merkle_root": proof_data["merkle_root"],
        "leaf_hash": proof_data["leaf_hash"],
        "proof": proof_data["proof"],
    }
    res_verify = await client.post(f"/elections/{election.id}/merkle/verify", json=verify_payload)
    assert res_verify.status_code == 200
    verify_data = res_verify.json()
    assert verify_data["valid"] is True
    assert verify_data["computed_root"] == merkle_root_db

    # 5. Intentar verificar una prueba adulterada (sibling alterado)
    tampered_proof = [dict(step) for step in proof_data["proof"]]
    # Corromper el hash del primer sibling
    tampered_proof[0]["sibling_hash"] = "0" * 64
    res_tampered = await client.post(
        f"/elections/{election.id}/merkle/verify",
        json={
            "merkle_root": proof_data["merkle_root"],
            "leaf_hash": proof_data["leaf_hash"],
            "proof": tampered_proof,
        },
    )
    assert res_tampered.status_code == 200
    assert res_tampered.json()["valid"] is False

    # 6. Intentar verificar con un leaf_hash no correspondiente
    res_tampered_leaf = await client.post(
        f"/elections/{election.id}/merkle/verify",
        json={
            "merkle_root": proof_data["merkle_root"],
            "leaf_hash": "f" * 64,
            "proof": proof_data["proof"],
        },
    )
    assert res_tampered_leaf.status_code == 200
    assert res_tampered_leaf.json()["valid"] is False
