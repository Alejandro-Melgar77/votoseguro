"""
Pruebas de Invariantes para IA Externa Gemini:
- IA-E1: Informe Ejecutivo en Lenguaje Natural con Privacidad Estricta (Invariante #14).
- IA-E2: Paridad Estructural de Lenguas Originarias (Español, Quechua, Aymara, Guaraní).
"""
import json
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.time import FakeTimeProvider
from app.db.models.audit import AiCallLog, AuditLog
from app.db.models.election import (
    Election,
    ElectionStatus,
    ExecutiveReport,
    ScheduleChange,
)
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
async def test_gemini_executive_report_generation_and_strict_privacy_invariants(
    test_db: AsyncSession,
    client: AsyncClient,
    org1_setup,
    fake_time: FakeTimeProvider,
):
    """
    IA-E1 & Invariante #14: Verifica que el informe ejecutivo oficial se genere
    únicamente sobre métricas consolidadas, registrando la llamada en ai_call_log y audit_log
    sin filtrar jamás CIs, nombres de votantes ni votos individuales.
    """
    org, admin, admin_token = org1_setup
    now = datetime(2026, 11, 26, 18, 0, 0, tzinfo=timezone.utc)
    fake_time.set_time(now)

    # 1. Crear Elección cerrada con sellos de integridad
    election = Election(
        organization_id=org.id,
        name="Elección General Claustro Universitario 2026",
        timezone="America/La_Paz",
        registration_opens_at=now - timedelta(days=10),
        registration_closes_at=now - timedelta(days=5),
        voting_opens_at=now - timedelta(hours=10),
        voting_closes_at=now - timedelta(hours=1),
        status=ElectionStatus.VOTING_CLOSED,
        k_anonymity=5,
        created_by=admin.id,
        config_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        roll_hash="a591a6d40bf420404a011733cfb7b190d62c65bf0bcda32b57b277d9ad9f146e",
        merkle_root="5feceb66ffc86f38d952786c6d696c79c2dbc239dd4e91b46729d73a27fb57e9",
        key_ceremony_hash="d4735e3a265e16eee03f59718b9b5d03019c07d8b6c51f90da3a666eec13ab35",
        encryption_scheme="PAILLIER_HOMOMORPHIC",
        shamir_threshold_k=3,
        shamir_total_n=5,
    )
    test_db.add(election)
    await test_db.flush()

    # 2. Registrar cambios de cronograma formal
    ch1 = ScheduleChange(
        organization_id=org.id,
        election_id=election.id,
        field_name="voting_closes_at",
        old_value=now - timedelta(hours=2),
        new_value=now - timedelta(hours=1),
        election_status_at_change="VOTING_OPEN",
        reason="Prórroga oficial de 1 hora por afluencia ciudadana conforme a resolución de sala plena.",
        changed_by=admin.id,
        changed_at=now - timedelta(hours=2),
    )
    test_db.add(ch1)
    await test_db.flush()

    # 3. Registrar votantes y votos en urna
    grp = VoterGroup(organization_id=org.id, election_id=election.id, name="Docentes", code="DOC")
    test_db.add(grp)
    await test_db.flush()

    lvl = HierarchyLevel(group_id=grp.id, depth=1, name="Universidad")
    test_db.add(lvl)
    await test_db.flush()

    node = UnitNode(group_id=grp.id, level_id=lvl.id, parent_id=None, name="Campus Central", code="CC", path="/CC/", depth=1)
    test_db.add(node)
    await test_db.flush()

    cnt = Contest(
        group_id=grp.id,
        scope_level_id=lvl.id,
        name="Rectorado",
        display_order=1,
    )
    test_db.add(cnt)
    await test_db.flush()

    csty = Constituency(
        contest_id=cnt.id,
        node_id=node.id,
    )
    test_db.add(csty)
    await test_db.flush()

    # 4 votantes habilitados
    for i in range(4):
        v = Voter(
            organization_id=org.id,
            election_id=election.id,
            group_id=grp.id,
            node_id=node.id,
            document_id=f"CI-TEST-{i + 100}",
            full_name=f"Votante Confidencial {i + 1}",
            email=f"voter{i + 1}@privado.edu.bo",
            status=VoterStatus.ACTIVE,
        )
        test_db.add(v)
    await test_db.flush()

    # 3 votos emitidos en urna
    prev_h = "0" * 64
    for idx in range(1, 4):
        vh = f"{idx:064x}"
        vote = Vote(
            election_id=election.id,
            constituency_id=csty.id,
            chain_index=idx,
            prev_hash=prev_h,
            vote_hash=vh,
            receipt_hash=f"RCPT-{idx:032x}",
            encoded_payload=json.dumps({"scheme": "PAILLIER_V1", "ciphertexts": ["0x123", "0x456"]}),
            choice_type=VoteChoiceType.BLANK,
            candidate_id=None,
            segment_path="/CC/",
            nullifier=f"nullifier-exec-{idx}",
            created_at=now,
        )
        test_db.add(vote)
        prev_h = vh
    await test_db.commit()

    # 4. Invocación del endpoint POST /api/v1/ai/reports/executive
    headers = {"Authorization": f"Bearer {admin_token}"}
    req_payload = {
        "election_id": str(election.id),
        "tone": "FORMAL_COURT",
    }

    res = await client.post("/ai/reports/executive", json=req_payload, headers=headers)
    assert res.status_code == 201, res.text
    data = res.json()

    # Verificación de estructura del reporte generado
    assert "title" in data
    assert "summary_markdown" in data
    assert "integrity_certification" in data
    assert "report_hash" in data
    assert len(data["report_hash"]) == 64
    assert data["ai_source"] in ("GEMINI_EXTERNAL_API", "DETERMINISTIC_FALLBACK")
    assert data["language"] == "es"

    # INVARIANTE #14: Verificación estricta de que el payload enviado NO contiene datos personales
    aggregated_payload = data["aggregated_input_payload"]
    raw_payload_text = json.dumps(aggregated_payload)
    assert "CI-TEST" not in raw_payload_text
    assert "Votante Confidencial" not in raw_payload_text
    assert "voter1@privado.edu.bo" not in raw_payload_text
    assert "privado.edu.bo" not in raw_payload_text
    assert aggregated_payload["total_registered_voters"] == 4
    assert aggregated_payload["total_votes_cast"] == 3
    assert aggregated_payload["turnout_percentage"] == 75.0
    assert aggregated_payload["schedule_changes_count"] == 1

    # Verificación de persistencia en tabla executive_report
    stmt_rep = select(ExecutiveReport).where(ExecutiveReport.election_id == election.id)
    saved_reports = list((await test_db.execute(stmt_rep)).scalars().all())
    assert len(saved_reports) >= 1
    assert saved_reports[0].report_hash == data["report_hash"]

    # Verificación de trazabilidad en ai_call_log y audit_log
    stmt_ai = select(AiCallLog).where(
        AiCallLog.election_id == election.id,
        AiCallLog.function_name == "IA-E1_EXECUTIVE_REPORT",
    )
    ai_logs = list((await test_db.execute(stmt_ai)).scalars().all())
    assert len(ai_logs) >= 1
    assert ai_logs[0].status in ("SUCCESS", "FALLBACK_DETERMINISTIC")

    # Invocación del endpoint GET /api/v1/ai/reports/executive/{election_id}
    res_list = await client.get(f"/ai/reports/executive/{election.id}", headers=headers)
    assert res_list.status_code == 200
    reports_list = res_list.json()
    assert len(reports_list) >= 1
    assert reports_list[0]["id"] == data["id"]


def test_i18n_locales_completeness_and_structural_parity():
    """
    IA-E2: Comprueba que los 4 diccionarios de internacionalización
    (Español es.json, Quechua qu.json, Aymara ay.json, Guaraní gn.json)
    existan, sean JSON válidos y posean idéntica estructura de claves.
    """
    locales_dir = Path(__file__).resolve().parent.parent.parent.parent / "apps" / "web" / "src" / "i18n" / "locales"
    langs = ("es", "qu", "ay", "gn")

    loaded_dicts = {}
    for lang in langs:
        file_path = locales_dir / f"{lang}.json"
        assert file_path.exists(), f"Archivo de localización ausente: {file_path}"
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            assert isinstance(data, dict)
            assert "_meta" in data
            assert data["_meta"]["language"] == lang
            loaded_dicts[lang] = data

    def get_all_key_paths(d: dict, prefix: str = "") -> set[str]:
        paths = set()
        for k, v in d.items():
            current = f"{prefix}.{k}" if prefix else k
            if isinstance(v, dict):
                paths.update(get_all_key_paths(v, current))
            else:
                paths.add(current)
        return paths

    es_keys = get_all_key_paths(loaded_dicts["es"])
    assert len(es_keys) >= 40, f"El diccionario en español debe tener al menos 40 claves, encontradas: {len(es_keys)}"

    # Verificar que qu, ay y gn tengan las mismas claves que es (excepto valores de _meta)
    for lang in ("qu", "ay", "gn"):
        target_keys = get_all_key_paths(loaded_dicts[lang])
        missing_in_target = es_keys - target_keys
        extra_in_target = target_keys - es_keys

        assert not missing_in_target, f"[{lang}] Claves faltantes respecto a es.json: {missing_in_target}"
        assert not extra_in_target, f"[{lang}] Claves sobrantes no existentes en es.json: {extra_in_target}"
