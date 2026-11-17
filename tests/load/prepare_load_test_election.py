"""
Script de Aprovisionamiento para Pruebas de Carga Masiva (k6) — VotoSeguro v3.0.0
Genera una elección de estrés configurada con cifrado homomórfico Paillier y Shamir,
1,000 votantes en estado ACTIVE y sus 1,000 credenciales de votación válidas.
Exporta el archivo 'voters_credentials.json' listo para ser consumido por k6.
"""
import argparse
import asyncio
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
import secrets
import sys
import uuid

# Asegurar importación de app desde apps/api
CURRENT_DIR = Path(__file__).resolve().parent
REPO_ROOT = CURRENT_DIR.parent.parent
API_DIR = REPO_ROOT / "apps" / "api"
if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))

import phe.paillier as paillier
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.security import get_password_hash
from app.crypto.hashing import sha256_hex
from app.crypto.shamir import (
    DEFAULT_SHAMIR_PRIME,
    compute_share_commitment,
    format_share,
    pack_paillier_private_key,
    split_secret,
)
from app.db.models.election import (
    Election,
    ElectionStatus,
    ElectoralTrusteeShare,
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
from app.db.models.voter import Voter, VoterStatus
from app.db.models.voting import VotingCredential, Vote


async def prepare_load_test_election(
    num_voters: int = 1000,
    output_filename: str = "voters_credentials.json",
    reset_existing: bool = True,
):
    print("=" * 80)
    print("VOTOSEGURO v3.0.0 — APROVISIONADOR DE ELECCIÓN DE CARGA MASIVA (k6)")
    print(f"Meta de electores activos: {num_voters} votantes concurrentes")
    print("=" * 80)

    engine = create_async_engine(settings.DATABASE_URL, echo=False, future=True)
    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as session:
        # 1. Asegurar Organización de Carga
        org_slug = "load-test-university"
        stmt_org = select(Organization).where(Organization.slug == org_slug)
        org = (await session.execute(stmt_org)).scalar_one_or_none()

        if not org:
            org = Organization(
                name="Universidad Nacional de Pruebas de Carga",
                slug=org_slug,
                org_type=OrganizationType.UNIVERSITY,
                status=OrganizationStatus.ACTIVE,
                contact_email="loadtest@votoseguro.org",
            )
            session.add(org)
            await session.flush()
            print(f"[+] Organización creada: {org.name} (ID: {org.id})")
        else:
            print(f"[*] Organización existente: {org.name} (ID: {org.id})")

        # 2. Asegurar Usuario Administrador General
        admin_email = "admin.loadtest@votoseguro.org"
        stmt_user = select(User).where(User.email == admin_email)
        admin_user = (await session.execute(stmt_user)).scalar_one_or_none()
        if not admin_user:
            admin_user = User(
                organization_id=org.id,
                email=admin_email,
                full_name="Administrador de Pruebas de Rendimiento",
                password_hash=get_password_hash("LoadTestAdmin2026!"),
                role=UserRole.ADMIN_GENERAL,
                status=UserStatus.ACTIVE,
            )
            session.add(admin_user)
            await session.flush()
            print(f"[+] Usuario Administrador creado: {admin_user.email}")

        # 3. Limpiar o reutilizar elección de carga
        election_name = "Elección Oficial de Carga y Concurrencia k6 (1000 VUs)"
        stmt_elec = select(Election).where(
            Election.organization_id == org.id,
            Election.name == election_name,
        )
        election = (await session.execute(stmt_elec)).scalar_one_or_none()

        if election and reset_existing:
            print(f"[*] Eliminando datos previos de la elección de carga: {election.id}...")
            # Limpiar credenciales, votos, etc.
            await session.execute(delete(Vote).where(Vote.election_id == election.id))
            await session.execute(delete(VotingCredential).where(VotingCredential.election_id == election.id))
            await session.execute(delete(Voter).where(Voter.election_id == election.id))
            await session.execute(delete(Election).where(Election.id == election.id))
            await session.flush()
            election = None

        now = datetime.now(timezone.utc)

        if not election:
            # 4. Generar par de claves Paillier de 1024 bits para la elección
            print("[*] Generando par de claves Paillier de 1024 bits...")
            pub_key, priv_key = paillier.generate_paillier_keypair(n_length=1024)
            n_str = str(pub_key.n)

            # Dividir secreto Shamir con k=2, n=3
            threshold_k = 2
            total_n = 3
            secret_s = pack_paillier_private_key(priv_key.p, priv_key.q)
            shares = split_secret(secret_s, k=threshold_k, n=total_n, prime=DEFAULT_SHAMIR_PRIME)

            key_ceremony_hash = sha256_hex(f"CEREMONY_LOADTEST:{n_str}:{threshold_k}:{total_n}")

            election = Election(
                organization_id=org.id,
                name=election_name,
                timezone="America/La_Paz",
                registration_opens_at=now - timedelta(days=2),
                registration_closes_at=now - timedelta(days=1),
                voting_opens_at=now - timedelta(hours=2),
                voting_closes_at=now + timedelta(days=7),
                status=ElectionStatus.VOTING_OPEN,
                k_anonymity=5,
                created_by=admin_user.id,
                encryption_scheme="PAILLIER_HOMOMORPHIC",
                paillier_public_n=n_str,
                paillier_public_key=n_str,
                paillier_key_size=1024,
                shamir_threshold_k=threshold_k,
                shamir_total_n=total_n,
                shamir_prime_modulus=str(DEFAULT_SHAMIR_PRIME),
                key_ceremony_hash=key_ceremony_hash,
                config_hash=sha256_hex(f"CONFIG_HASH_LOADTEST:{now.isoformat()}"),
                roll_hash=sha256_hex(f"ROLL_HASH_LOADTEST:{now.isoformat()}"),
                merkle_root=sha256_hex(f"MERKLE_ROOT_LOADTEST:{now.isoformat()}"),
            )
            session.add(election)
            await session.flush()
            print(f"[+] Elección creada en VOTING_OPEN: {election.name} (ID: {election.id})")

            # Registrar custodios
            for share in shares:
                share_fmt = format_share(share[0], threshold_k, total_n, share[1])
                c_hash = compute_share_commitment(election.id, share[0], share[1])
                trustee = ElectoralTrusteeShare(
                    organization_id=org.id,
                    election_id=election.id,
                    share_index=share[0],
                    trustee_name=f"Vocal Electoral Custodio {share[0]} (Load Test)",
                    trustee_email=f"trustee{share[0]}.load@votoseguro.org",
                    commitment_hash=c_hash,
                    demo_share_token=share_fmt,
                )
                session.add(trustee)
            await session.flush()
            print(f"[+] {total_n} custodios electorales Shamir registrados con éxito.")

            # 5. Estructura Jerárquica
            group = VoterGroup(
                organization_id=org.id,
                election_id=election.id,
                name="Estudiantes y Docentes",
                code="EST_DOC",
            )
            session.add(group)
            await session.flush()

            lvl = HierarchyLevel(group_id=group.id, depth=1, name="Facultad")
            session.add(lvl)
            await session.flush()

            node = UnitNode(
                group_id=group.id,
                level_id=lvl.id,
                parent_id=None,
                name="Facultad de Ciencias de la Computación",
                code="FICCT",
                path="/FICCT/",
                depth=1,
            )
            session.add(node)
            await session.flush()

            # Cargo electoral
            contest = Contest(
                group_id=group.id,
                scope_level_id=lvl.id,
                name="Rectorado Universitario",
                allow_blank=True,
                allow_null=True,
                display_order=1,
            )
            session.add(contest)
            await session.flush()

            # Circunscripción
            constituency = Constituency(contest_id=contest.id, node_id=node.id)
            session.add(constituency)
            await session.flush()

            # Candidatos
            cand_1 = Candidate(
                constituency_id=constituency.id,
                name="Dra. Patricia Morales (Frente Innovación)",
                party_or_front="INNOVACION_ACADEMICA",
                ballot_order=1,
            )
            cand_2 = Candidate(
                constituency_id=constituency.id,
                name="Ing. Roberto Quiroga (Frente Excelencia)",
                party_or_front="EXCELENCIA_UNIVERSITARIA",
                ballot_order=2,
            )
            session.add_all([cand_1, cand_2])
            await session.flush()
            print(f"[+] Estructura configurada: Contest {contest.name}, 2 candidatos registrados.")
        else:
            # Recuperar entidades asociadas
            stmt_c = select(Contest).join(VoterGroup).where(VoterGroup.election_id == election.id)
            contest = (await session.execute(stmt_c)).scalars().first()
            stmt_const = select(Constituency).where(Constituency.contest_id == contest.id)
            constituency = (await session.execute(stmt_const)).scalars().first()
            stmt_cands = select(Candidate).where(Candidate.constituency_id == constituency.id).order_by(Candidate.ballot_order)
            cands = list((await session.execute(stmt_cands)).scalars().all())
            cand_1, cand_2 = cands[0], cands[1]
            stmt_node = select(UnitNode).join(HierarchyLevel).join(VoterGroup).where(VoterGroup.election_id == election.id)
            node = (await session.execute(stmt_node)).scalars().first()
            stmt_grp = select(VoterGroup).where(VoterGroup.election_id == election.id)
            group = (await session.execute(stmt_grp)).scalars().first()

        # 6. Aprovisionamiento masivo de votantes y credenciales
        print(f"[*] Aprovisionando {num_voters} votantes ACTIVE y sus credenciales...")
        credentials_export = []

        batch_size = 250
        voters_batch = []
        credentials_batch = []

        for i in range(1, num_voters + 1):
            doc_id = f"CI-LOAD-{i:05d}"
            full_name = f"Votante Carga Masiva {i:05d}"
            voter_id = uuid.uuid4()

            voter = Voter(
                id=voter_id,
                organization_id=org.id,
                election_id=election.id,
                group_id=group.id,
                node_id=node.id,
                document_id=doc_id,
                full_name=full_name,
                email=f"voter{i:05d}.load@uagrm.edu.bo",
                status=VoterStatus.ACTIVE,
            )
            voters_batch.append(voter)

            # Código de credencial de formato VS-XXXX-XXXX-XXXX
            token_suffix = secrets.token_hex(2).upper()
            raw_token = f"VS-LOAD-{i:05d}-{token_suffix}"
            token_hash = sha256_hex(raw_token)

            cred = VotingCredential(
                id=uuid.uuid4(),
                election_id=election.id,
                voter_id=voter_id,
                token_hash=token_hash,
                raw_token=raw_token,
                issued_at=now,
                expires_at=election.voting_closes_at,
                used_at=None,
            )
            credentials_batch.append(cred)

            # Opción de voto distribuida para simular diversidad en la urna
            chosen_candidate = cand_1 if (i % 2 == 1) else cand_2
            choice_type = "CANDIDATE" if (i % 10 != 0) else ("BLANK" if i % 20 != 0 else "NULL")
            candidate_id_val = str(chosen_candidate.id) if choice_type == "CANDIDATE" else None

            credentials_export.append({
                "voter_index": i,
                "document_id": doc_id,
                "credential_code": raw_token,
                "election_id": str(election.id),
                "contest_id": str(contest.id),
                "constituency_id": str(constituency.id),
                "choice_type": choice_type,
                "candidate_id": candidate_id_val,
            })

            if len(voters_batch) >= batch_size:
                session.add_all(voters_batch)
                await session.flush()
                session.add_all(credentials_batch)
                await session.flush()
                voters_batch.clear()
                credentials_batch.clear()
                print(f"    -> {i}/{num_voters} votantes insertados...")

        if voters_batch:
            session.add_all(voters_batch)
            await session.flush()
            session.add_all(credentials_batch)
            await session.flush()

        await session.commit()
        print(f"[+] Total de {num_voters} votantes y credenciales persistidos exitosamente.")

        # 7. Exportar archivo JSON para consumo de k6
        out_paths = [
            CURRENT_DIR / output_filename,
            REPO_ROOT / "tests" / "load" / output_filename,
        ]

        for p in set(out_paths):
            p.parent.mkdir(parents=True, exist_ok=True)
            with open(p, "w", encoding="utf-8") as f:
                json.dump(credentials_export, f, indent=2)
            print(f"[+] Archivo de credenciales exportado: {p} ({len(credentials_export)} registros)")

        print("=" * 80)
        print("APROVISIONAMIENTO COMPLETADO EXITOSAMENTE")
        print(f"Elección ID: {election.id}")
        print(f"Total Votantes Listos: {num_voters}")
        print("Comando de ejecución de prueba de carga:")
        print(f"  k6 run tests/load/votoseguro_load_test.js")
        print("=" * 80)

    await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Aprovisionar elección para pruebas de carga k6.")
    parser.add_argument("--voters", type=int, default=1000, help="Número de votantes a generar (default: 1000)")
    parser.add_argument("--output", type=str, default="voters_credentials.json", help="Nombre de archivo JSON de salida")
    parser.add_argument("--no-reset", action="store_true", help="No reiniciar la elección existente")

    args = parser.parse_args()
    asyncio.run(
        prepare_load_test_election(
            num_voters=args.voters,
            output_filename=args.output,
            reset_existing=not args.no_reset,
        )
    )
