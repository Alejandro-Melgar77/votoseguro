"""
Pruebas de Sembrado de Datos de Demostración Idempotente (seed:demo)
- Universidad EL GRAN ESTUDIO (Estudiantes, Docentes, 35+ votantes, homónimos IA-L2a, enlaces)
- Elecciones Nacionales Ecuador (4 niveles jerárquicos territoriales, binomio presidencial)
- Endpoint protegido POST /api/v1/platform/seed-demo
"""
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.election import Election
from app.db.models.organization import Organization
from app.db.models.structure import Contest, VoterGroup
from app.db.models.user import User
from app.db.models.voter import RegistrationLink, Voter
from app.db.seed_demo import run_seed_demo


@pytest.mark.asyncio
async def test_seed_demo_idempotency_and_completeness(test_db: AsyncSession):
    # 1. Primera ejecución del sembrado
    res1 = await run_seed_demo(test_db)
    assert res1["status"] == "success"
    assert "Universidad EL GRAN ESTUDIO" in res1["org1"]
    assert "Ecuador" in res1["org2"]

    # 2. Verificación de Universidad EL GRAN ESTUDIO
    stmt_org1 = select(Organization).where(Organization.slug == "el-gran-estudio")
    org1 = (await test_db.execute(stmt_org1)).scalar_one_or_none()
    assert org1 is not None

    stmt_admin1 = select(User).where(User.email == "admin@granestudio.edu.bo")
    admin1 = (await test_db.execute(stmt_admin1)).scalar_one_or_none()
    assert admin1 is not None
    assert admin1.organization_id == org1.id

    stmt_elections1 = select(Election).where(Election.organization_id == org1.id)
    elections1 = (await test_db.execute(stmt_elections1)).scalars().all()
    assert len(elections1) >= 1
    el1 = elections1[0]
    assert el1.config_hash is not None

    stmt_groups1 = select(VoterGroup).where(VoterGroup.election_id == el1.id)
    groups1 = (await test_db.execute(stmt_groups1)).scalars().all()
    assert len(groups1) == 2  # ESTUDIANTES y DOCENTES

    stmt_voters1 = select(Voter).where(Voter.election_id == el1.id)
    voters1 = (await test_db.execute(stmt_voters1)).scalars().all()
    assert len(voters1) >= 35

    # Verificar homónimos (José Rodríguez / Jose Rodriguez S.) con distinto CI (IA-L2a)
    homonyms = [v for v in voters1 if "Rodr\u00edguez" in v.full_name or "Rodriguez" in v.full_name]
    assert len(homonyms) >= 2
    assert homonyms[0].document_id != homonyms[1].document_id

    stmt_links1 = select(RegistrationLink).where(RegistrationLink.election_id == el1.id)
    links1 = (await test_db.execute(stmt_links1)).scalars().all()
    assert len(links1) >= 2
    assert all(l.raw_token is not None for l in links1)

    # 3. Verificación de CNE Ecuador
    stmt_org2 = select(Organization).where(Organization.slug == "cne-ecuador")
    org2 = (await test_db.execute(stmt_org2)).scalar_one_or_none()
    assert org2 is not None

    stmt_admin2 = select(User).where(User.email == "admin@cne.gob.ec")
    admin2 = (await test_db.execute(stmt_admin2)).scalar_one_or_none()
    assert admin2 is not None
    assert admin2.organization_id == org2.id

    stmt_elections2 = select(Election).where(Election.organization_id == org2.id)
    elections2 = (await test_db.execute(stmt_elections2)).scalars().all()
    assert len(elections2) >= 1
    el2 = elections2[0]
    assert el2.config_hash is not None

    stmt_contests2 = (
        select(Contest)
        .join(VoterGroup, Contest.group_id == VoterGroup.id)
        .where(VoterGroup.election_id == el2.id)
    )
    contests2 = (await test_db.execute(stmt_contests2)).scalars().all()
    assert any("Presidente" in c.name for c in contests2)

    # 4. Segunda ejecución para validar idempotencia (sin duplicaciones ni excepciones)
    res2 = await run_seed_demo(test_db)
    assert res2["status"] == "success"

    voters_after_second_run = (await test_db.execute(stmt_voters1)).scalars().all()
    assert len(voters_after_second_run) == len(voters1)


@pytest.mark.asyncio
async def test_platform_seed_demo_endpoint(
    test_db: AsyncSession,
    client: AsyncClient,
    platform_admin_token: str,
    org1_setup,
):
    org, admin, admin_token = org1_setup

    # 1. Sin autenticación -> 401
    r_unauth = await client.post("/platform/seed-demo")
    assert r_unauth.status_code == 401

    # 2. Con rol no-PLATFORM_ADMIN -> 403
    r_forbidden = await client.post(
        "/platform/seed-demo",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r_forbidden.status_code == 403

    # 3. Con PLATFORM_ADMIN -> 200 OK y ejecuta el sembrado
    r_ok = await client.post(
        "/platform/seed-demo",
        headers={"Authorization": f"Bearer {platform_admin_token}"},
    )
    assert r_ok.status_code == 200
    data = r_ok.json()
    assert data["status"] == "success"
    assert "Universidad EL GRAN ESTUDIO" in data["results"]["org1"]
    assert "Ecuador" in data["results"]["org2"]
