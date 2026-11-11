"""
Sembrador de Datos de Demostración Idempotente (seed:demo)
Aprovisiona las dos instituciones requeridas para el Sprint 1:
1. Universidad EL GRAN ESTUDIO (Multi-nivel, Estudiantes, Docentes, Candidatos, Padrón con IA-L2a, Enlaces de registro)
2. Elecciones Nacionales Ecuador (4 niveles, Presidente, Gobernador)
"""
import asyncio
from datetime import datetime, timedelta, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_password_hash
from app.crypto.hashing import canonical_json, sha256_hex
from app.db.models.election import Election, ElectionStatus
from app.db.models.organization import Organization, OrganizationStatus, OrganizationType
from app.db.models.structure import (
    BreakdownKind,
    Candidate,
    Constituency,
    Contest,
    ContestBreakdown,
    FilterDefinition,
    HierarchyLevel,
    UnitNode,
    VoterGroup,
)
from app.db.models.user import AdminAssignment, User, UserRole, UserStatus
from app.db.models.voter import LinkStatus, RegistrationLink, Voter, VoterStatus
from app.db.session import async_session_factory
from app.modules.elections.publication_service import canonical_election_dump


async def seed_gran_estudio(session: AsyncSession) -> dict[str, str]:
    now = datetime.now(timezone.utc)
    t_reg_open = now - timedelta(days=2)
    t_reg_close = now + timedelta(days=5)
    t_vote_open = now + timedelta(days=6)
    t_vote_close = now + timedelta(days=7)

    # 1. Organización
    stmt_org = select(Organization).where(Organization.slug == "el-gran-estudio")
    org = (await session.execute(stmt_org)).scalar_one_or_none()
    if not org:
        org = Organization(
            name="Universidad EL GRAN ESTUDIO",
            slug="el-gran-estudio",
            org_type=OrganizationType.UNIVERSITY,
            status=OrganizationStatus.ACTIVE,
            contact_email="admin@granestudio.edu.bo",
        )
        session.add(org)
        await session.flush()

    # 2. Usuarios: Admin General y Delegado de Segmento
    stmt_admin = select(User).where(User.email == "admin@granestudio.edu.bo")
    admin = (await session.execute(stmt_admin)).scalar_one_or_none()
    if not admin:
        admin = User(
            organization_id=org.id,
            email="admin@granestudio.edu.bo",
            full_name="Dr. Fernando Torrico (Admin General)",
            password_hash=get_password_hash("GranEstudio2026!"),
            role=UserRole.ADMIN_GENERAL,
            status=UserStatus.ACTIVE,
        )
        session.add(admin)
        await session.flush()

    stmt_del = select(User).where(User.email == "delegado.ficct@granestudio.edu.bo")
    delegado = (await session.execute(stmt_del)).scalar_one_or_none()
    if not delegado:
        delegado = User(
            organization_id=org.id,
            email="delegado.ficct@granestudio.edu.bo",
            full_name="Lic. Marcos Vaca (Delegado FICCT)",
            password_hash=get_password_hash("Delegado2026!"),
            role=UserRole.ADMIN_SEGMENT,
            status=UserStatus.ACTIVE,
        )
        session.add(delegado)
        await session.flush()

    # 3. Elección
    stmt_el = select(Election).where(
        Election.organization_id == org.id,
        Election.name == "Elecciones Generales Universitarias 2026",
    )
    election = (await session.execute(stmt_el)).scalar_one_or_none()
    if not election:
        election = Election(
            organization_id=org.id,
            name="Elecciones Generales Universitarias 2026",
            description="Elección Soberana de Autoridades Universitarias y Facultativas 2026-2030",
            timezone="America/La_Paz",
            registration_opens_at=t_reg_open,
            registration_closes_at=t_reg_close,
            voting_opens_at=t_vote_open,
            voting_closes_at=t_vote_close,
            status=ElectionStatus.REGISTRATION_OPEN,
            k_anonymity=5,
            created_by=admin.id,
        )
        session.add(election)
        await session.flush()

    # =========================================================================
    # GRUPO 1: ESTUDIANTES
    # =========================================================================
    stmt_grp_est = select(VoterGroup).where(
        VoterGroup.election_id == election.id, VoterGroup.code == "EST"
    )
    grp_est = (await session.execute(stmt_grp_est)).scalar_one_or_none()
    if not grp_est:
        grp_est = VoterGroup(
            organization_id=org.id,
            election_id=election.id,
            name="ESTUDIANTES",
            code="EST",
        )
        session.add(grp_est)
        await session.flush()

    # Niveles Estudiantes: 1: Universidad -> 2: Facultad -> 3: Carrera
    levels_est: dict[int, HierarchyLevel] = {}
    for d, name in [(1, "Universidad"), (2, "Facultad"), (3, "Carrera")]:
        stmt_lvl = select(HierarchyLevel).where(
            HierarchyLevel.group_id == grp_est.id, HierarchyLevel.depth == d
        )
        lvl = (await session.execute(stmt_lvl)).scalar_one_or_none()
        if not lvl:
            lvl = HierarchyLevel(group_id=grp_est.id, depth=d, name=name)
            session.add(lvl)
            await session.flush()
        levels_est[d] = lvl

    # Nodos Estudiantes
    # UNIV -> FICCT (INF, SIS), FCEH (ADM, ECO)
    nodes_est: dict[str, UnitNode] = {}
    stmt_univ = select(UnitNode).where(UnitNode.group_id == grp_est.id, UnitNode.code == "UNIV")
    n_univ = (await session.execute(stmt_univ)).scalar_one_or_none()
    if not n_univ:
        n_univ = UnitNode(
            group_id=grp_est.id,
            level_id=levels_est[1].id,
            parent_id=None,
            name="Universidad EL GRAN ESTUDIO",
            code="UNIV",
            path="/UNIV/",
            depth=1,
        )
        session.add(n_univ)
        await session.flush()
    nodes_est["UNIV"] = n_univ

    # Facultades
    for code, name in [
        ("FICCT", "Facultad de Ciencias de la Computación"),
        ("FCEH", "Facultad de Ciencias Económicas"),
    ]:
        stmt_fac = select(UnitNode).where(UnitNode.group_id == grp_est.id, UnitNode.code == code)
        n_fac = (await session.execute(stmt_fac)).scalar_one_or_none()
        if not n_fac:
            n_fac = UnitNode(
                group_id=grp_est.id,
                level_id=levels_est[2].id,
                parent_id=n_univ.id,
                name=name,
                code=code,
                path=f"/UNIV/{code}/",
                depth=2,
            )
            session.add(n_fac)
            await session.flush()
        nodes_est[code] = n_fac

    # Carreras
    careers_data = [
        ("INF", "Ingeniería Informática", "FICCT"),
        ("SIS", "Ingeniería en Sistemas", "FICCT"),
        ("ADM", "Administración de Empresas", "FCEH"),
        ("ECO", "Economía", "FCEH"),
    ]
    for code, name, parent_code in careers_data:
        parent_node = nodes_est[parent_code]
        stmt_car = select(UnitNode).where(UnitNode.group_id == grp_est.id, UnitNode.code == code)
        n_car = (await session.execute(stmt_car)).scalar_one_or_none()
        if not n_car:
            n_car = UnitNode(
                group_id=grp_est.id,
                level_id=levels_est[3].id,
                parent_id=parent_node.id,
                name=name,
                code=code,
                path=f"{parent_node.path}{code}/",
                depth=3,
            )
            session.add(n_car)
            await session.flush()
        nodes_est[code] = n_car

    # Asignar Delegado de Segmento a FICCT
    stmt_asg = select(AdminAssignment).where(
        AdminAssignment.user_id == delegado.id,
        AdminAssignment.election_id == election.id,
    )
    if not (await session.execute(stmt_asg)).scalar_one_or_none():
        assignment = AdminAssignment(
            organization_id=org.id,
            user_id=delegado.id,
            election_id=election.id,
            group_id=grp_est.id,
            node_id=nodes_est["FICCT"].id,
            permission="READ",
        )
        session.add(assignment)
        await session.flush()

    # Filtro extra: modalidad
    stmt_flt = select(FilterDefinition).where(
        FilterDefinition.group_id == grp_est.id, FilterDefinition.key == "modalidad"
    )
    flt_modalidad = (await session.execute(stmt_flt)).scalar_one_or_none()
    if not flt_modalidad:
        flt_modalidad = FilterDefinition(
            group_id=grp_est.id,
            label="Modalidad de Estudio",
            key="modalidad",
            allowed_values=["PRESENCIAL", "SEMIPRESENCIAL"],
        )
        session.add(flt_modalidad)
        await session.flush()

    # Cargos Estudiantes:
    # 1. Rector (Nivel 1, desgloses por Facultad, por Carrera, por Modalidad)
    stmt_rec = select(Contest).where(Contest.group_id == grp_est.id, Contest.name == "Rector y Vicerrector Universitario")
    c_rector = (await session.execute(stmt_rec)).scalar_one_or_none()
    if not c_rector:
        c_rector = Contest(
            group_id=grp_est.id,
            scope_level_id=levels_est[1].id,
            name="Rector y Vicerrector Universitario",
            description="Máxima Autoridad Ejecutiva Universitaria",
            display_order=1,
            allow_blank=True,
            allow_null=True,
        )
        session.add(c_rector)
        await session.flush()

        # Desgloses
        bd1 = ContestBreakdown(contest_id=c_rector.id, kind=BreakdownKind.LEVEL, level_id=levels_est[2].id, label="Por Facultad")
        bd2 = ContestBreakdown(contest_id=c_rector.id, kind=BreakdownKind.LEVEL, level_id=levels_est[3].id, label="Por Carrera")
        bd3 = ContestBreakdown(contest_id=c_rector.id, kind=BreakdownKind.FILTER, filter_id=flt_modalidad.id, label="Por Modalidad")
        session.add_all([bd1, bd2, bd3])
        await session.flush()

    # Circunscripción Rector (UNIV)
    stmt_const_rec = select(Constituency).where(
        Constituency.contest_id == c_rector.id, Constituency.node_id == n_univ.id
    )
    const_rector = (await session.execute(stmt_const_rec)).scalar_one_or_none()
    if not const_rector:
        const_rector = Constituency(
            contest_id=c_rector.id,
            node_id=n_univ.id,
        )
        session.add(const_rector)
        await session.flush()

    # Candidatos Rector
    rector_cands = [
        ("Dr. Walter Miranda V.", "Frente Universitario Primero (FUP)", 1),
        ("Dra. Elena Peñaranda S.", "Innovación y Excelencia Académica (IEA)", 2),
        ("Lic. Carlos Monasterio R.", "Transformación Universitaria (TU)", 3),
    ]
    for name, party, order in rector_cands:
        stmt_cand = select(Candidate).where(
            Candidate.constituency_id == const_rector.id, Candidate.name == name
        )
        if not (await session.execute(stmt_cand)).scalar_one_or_none():
            session.add(
                Candidate(
                    constituency_id=const_rector.id,
                    name=name,
                    party_or_front=party,
                    ballot_order=order,
                )
            )
    await session.flush()

    # 2. Decano (Nivel 2, alcance Facultad)
    stmt_dec = select(Contest).where(Contest.group_id == grp_est.id, Contest.name == "Decano y Vicedecano de Facultad")
    c_decano = (await session.execute(stmt_dec)).scalar_one_or_none()
    if not c_decano:
        c_decano = Contest(
            group_id=grp_est.id,
            scope_level_id=levels_est[2].id,
            name="Decano y Vicedecano de Facultad",
            description="Autoridad Facultativa",
            display_order=2,
            allow_blank=True,
            allow_null=True,
        )
        session.add(c_decano)
        await session.flush()
        bd_dec = ContestBreakdown(contest_id=c_decano.id, kind=BreakdownKind.LEVEL, level_id=levels_est[3].id, label="Por Carrera")
        session.add(bd_dec)
        await session.flush()

    # Circunscripciones Decano (FICCT y FCEH)
    for fac_code, cands in [
        ("FICCT", [
            ("Ing. Hugo Ribera Ch.", "Unidad Tecnológica (UT)", 1),
            ("Ing. Patricia Salguero M.", "Compromiso FICCT (CF)", 2),
        ]),
        ("FCEH", [
            ("Lic. Ramiro Quiroga B.", "Alianza Económica (AE)", 1),
            ("Dra. Marcela Justiniano K.", "Futuro Ciencias Económicas (FCE)", 2),
        ]),
    ]:
        fac_node = nodes_est[fac_code]
        stmt_c = select(Constituency).where(
            Constituency.contest_id == c_decano.id, Constituency.node_id == fac_node.id
        )
        const_fac = (await session.execute(stmt_c)).scalar_one_or_none()
        if not const_fac:
            const_fac = Constituency(
                contest_id=c_decano.id,
                node_id=fac_node.id,
            )
            session.add(const_fac)
            await session.flush()

        for c_name, c_party, c_order in cands:
            stmt_cand = select(Candidate).where(
                Candidate.constituency_id == const_fac.id, Candidate.name == c_name
            )
            if not (await session.execute(stmt_cand)).scalar_one_or_none():
                session.add(
                    Candidate(
                        constituency_id=const_fac.id,
                        name=c_name,
                        party_or_front=c_party,
                        ballot_order=c_order,
                    )
                )
    await session.flush()

    # 3. Encargado de Carrera (Nivel 3, alcance Carrera)
    stmt_enc = select(Contest).where(Contest.group_id == grp_est.id, Contest.name == "Director de Carrera")
    c_carrera = (await session.execute(stmt_enc)).scalar_one_or_none()
    if not c_carrera:
        c_carrera = Contest(
            group_id=grp_est.id,
            scope_level_id=levels_est[3].id,
            name="Director de Carrera",
            description="Dirección de Carrera Académica",
            display_order=3,
            allow_blank=True,
            allow_null=True,
        )
        session.add(c_carrera)
        await session.flush()

    for car_code, cand_list in [
        ("INF", [
            ("Ing. Samuel Antelo P.", "Vanguardia Informática", 1),
            ("Ing. Beatriz Cuéllar R.", "Fuerza Hacker", 2),
        ]),
        ("SIS", [
            ("Ing. Julio Arteaga M.", "Sistemas Pro", 1),
            ("Ing. Claudia Morales F.", "Ingeniería 4.0", 2),
        ]),
        ("ADM", [
            ("Lic. Víctor Roca B.", "Gestión y Estrategia", 1),
            ("Lic. Andrea Mercado S.", "Emprendimiento ADM", 2),
        ]),
        ("ECO", [
            ("Lic. Javier Soliz T.", "Economistas Unidos", 1),
            ("Lic. Pamela Gutiérrez C.", "Desarrollo Sostenible", 2),
        ]),
    ]:
        car_node = nodes_est[car_code]
        stmt_c = select(Constituency).where(
            Constituency.contest_id == c_carrera.id, Constituency.node_id == car_node.id
        )
        const_car = (await session.execute(stmt_c)).scalar_one_or_none()
        if not const_car:
            const_car = Constituency(
                contest_id=c_carrera.id,
                node_id=car_node.id,
            )
            session.add(const_car)
            await session.flush()

        for c_name, c_party, c_order in cand_list:
            stmt_cand = select(Candidate).where(
                Candidate.constituency_id == const_car.id, Candidate.name == c_name
            )
            if not (await session.execute(stmt_cand)).scalar_one_or_none():
                session.add(
                    Candidate(
                        constituency_id=const_car.id,
                        name=c_name,
                        party_or_front=c_party,
                        ballot_order=c_order,
                    )
                )
    await session.flush()

    # =========================================================================
    # GRUPO 2: DOCENTES
    # =========================================================================
    stmt_grp_doc = select(VoterGroup).where(
        VoterGroup.election_id == election.id, VoterGroup.code == "DOC"
    )
    grp_doc = (await session.execute(stmt_grp_doc)).scalar_one_or_none()
    if not grp_doc:
        grp_doc = VoterGroup(
            organization_id=org.id,
            election_id=election.id,
            name="DOCENTES",
            code="DOC",
        )
        session.add(grp_doc)
        await session.flush()

    levels_doc: dict[int, HierarchyLevel] = {}
    for d, name in [(1, "Universidad"), (2, "Facultad"), (3, "Asociación")]:
        stmt_lvl = select(HierarchyLevel).where(
            HierarchyLevel.group_id == grp_doc.id, HierarchyLevel.depth == d
        )
        lvl = (await session.execute(stmt_lvl)).scalar_one_or_none()
        if not lvl:
            lvl = HierarchyLevel(group_id=grp_doc.id, depth=d, name=name)
            session.add(lvl)
            await session.flush()
        levels_doc[d] = lvl

    stmt_udoc = select(UnitNode).where(UnitNode.group_id == grp_doc.id, UnitNode.code == "UNIV-DOC")
    n_udoc = (await session.execute(stmt_udoc)).scalar_one_or_none()
    if not n_udoc:
        n_udoc = UnitNode(
            group_id=grp_doc.id,
            level_id=levels_doc[1].id,
            parent_id=None,
            name="Universidad Claustro Docente",
            code="UNIV-DOC",
            path="/UNIV-DOC/",
            depth=1,
        )
        session.add(n_udoc)
        await session.flush()

    for fac_c, fac_n, aso_c, aso_n in [
        ("FICCT-DOC", "Facultad de Tecnología Docentes", "ASODOC-TEC", "Asociación Docente Tecnología"),
        ("FCEH-DOC", "Facultad Económicas Docentes", "ASODOC-ECO", "Asociación Docente Económicas"),
    ]:
        stmt_f = select(UnitNode).where(UnitNode.group_id == grp_doc.id, UnitNode.code == fac_c)
        nf = (await session.execute(stmt_f)).scalar_one_or_none()
        if not nf:
            nf = UnitNode(
                group_id=grp_doc.id,
                level_id=levels_doc[2].id,
                parent_id=n_udoc.id,
                name=fac_n,
                code=fac_c,
                path=f"/UNIV-DOC/{fac_c}/",
                depth=2,
            )
            session.add(nf)
            await session.flush()

        stmt_a = select(UnitNode).where(UnitNode.group_id == grp_doc.id, UnitNode.code == aso_c)
        na = (await session.execute(stmt_a)).scalar_one_or_none()
        if not na:
            na = UnitNode(
                group_id=grp_doc.id,
                level_id=levels_doc[3].id,
                parent_id=nf.id,
                name=aso_n,
                code=aso_c,
                path=f"{nf.path}{aso_c}/",
                depth=3,
            )
            session.add(na)
            await session.flush()

    # Cargos Docentes
    stmt_rd = select(Contest).where(Contest.group_id == grp_doc.id, Contest.name == "Rector Claustro Docente")
    c_rdoc = (await session.execute(stmt_rd)).scalar_one_or_none()
    if not c_rdoc:
        c_rdoc = Contest(
            group_id=grp_doc.id,
            scope_level_id=levels_doc[1].id,
            name="Rector Claustro Docente",
            description="Representación en el Claustro",
            display_order=1,
            allow_blank=True,
            allow_null=True,
        )
        session.add(c_rdoc)
        await session.flush()

        const_rd = Constituency(
            contest_id=c_rdoc.id,
            node_id=n_udoc.id,
        )
        session.add(const_rd)
        await session.flush()

        c1 = Candidate(constituency_id=const_rd.id, name="Dr. Gonzalo Saucedo", party_or_front="Dignidad Docente", ballot_order=1)
        c2 = Candidate(constituency_id=const_rd.id, name="Dra. Carmen Rosa Ortiz", party_or_front="Docentes por el Cambio", ballot_order=2)
        session.add_all([c1, c2])
        await session.flush()

    # =========================================================================
    # PADRÓN ELECTORAL DE DEMOSTRACIÓN (36 Votantes)
    # =========================================================================
    students_demo = [
        # Informática (10 estudiantes - incluye par para IA-L2a)
        ("CI-8001001", "José Rodríguez", "INF", "PRESENCIAL", VoterStatus.ACTIVE),
        ("CI-8001002", "Jose Rodriguez S.", "INF", "PRESENCIAL", VoterStatus.IMPORTED),  # IA-L2a homonimia
        ("CI-8001003", "Alejandro Melgar Suárez", "INF", "PRESENCIAL", VoterStatus.ACTIVE),
        ("CI-8001004", "Valeria Paz Justiniano", "INF", "SEMIPRESENCIAL", VoterStatus.ACTIVE),
        ("CI-8001005", "Rodrigo Chávez Méndez", "INF", "PRESENCIAL", VoterStatus.ACTIVE),
        ("CI-8001006", "Camila Flores Torrico", "INF", "SEMIPRESENCIAL", VoterStatus.ACTIVE),
        ("CI-8001007", "Mateo Vaca Guzmán", "INF", "PRESENCIAL", VoterStatus.ACTIVE),
        ("CI-8001008", "Luciana Soliz Pinto", "INF", "PRESENCIAL", VoterStatus.INVITED),
        ("CI-8001009", "Sebastián Pinto Moreno", "INF", "PRESENCIAL", VoterStatus.ACTIVE),
        ("CI-8001010", "Mariana Ríos Aguilera", "INF", "SEMIPRESENCIAL", VoterStatus.ACTIVE),
        # Sistemas (8 estudiantes)
        ("CI-8002001", "Gabriel Mendoza Ortiz", "SIS", "PRESENCIAL", VoterStatus.ACTIVE),
        ("CI-8002002", "Daniela Vargas Rojas", "SIS", "PRESENCIAL", VoterStatus.ACTIVE),
        ("CI-8002003", "Nicolás Céspedes Peña", "SIS", "SEMIPRESENCIAL", VoterStatus.ACTIVE),
        ("CI-8002004", "Sofía Aguilera Hurtado", "SIS", "PRESENCIAL", VoterStatus.ACTIVE),
        ("CI-8002005", "Andrés Suárez Baldivieso", "SIS", "PRESENCIAL", VoterStatus.ACTIVE),
        ("CI-8002006", "Isabella Prado Camacho", "SIS", "SEMIPRESENCIAL", VoterStatus.ACTIVE),
        ("CI-8002007", "Fabián Castedo Montero", "SIS", "PRESENCIAL", VoterStatus.INVITED),
        ("CI-8002008", "Natalia Cuéllar Arteaga", "SIS", "PRESENCIAL", VoterStatus.ACTIVE),
        # Administración (7 estudiantes)
        ("CI-8003001", "Lucas Romero Paz", "ADM", "PRESENCIAL", VoterStatus.ACTIVE),
        ("CI-8003002", "Martina Justiniano Vaca", "ADM", "SEMIPRESENCIAL", VoterStatus.ACTIVE),
        ("CI-8003003", "Ignacio Saucedo Ribera", "ADM", "PRESENCIAL", VoterStatus.ACTIVE),
        ("CI-8003004", "Renata Peña Moreno", "ADM", "PRESENCIAL", VoterStatus.ACTIVE),
        ("CI-8003005", "Diego Serrano Justiniano", "ADM", "SEMIPRESENCIAL", VoterStatus.ACTIVE),
        ("CI-8003006", "Flavia Barba Morales", "ADM", "PRESENCIAL", VoterStatus.INVITED),
        ("CI-8003007", "Bruno Antelo Landívar", "ADM", "PRESENCIAL", VoterStatus.ACTIVE),
        # Economía (5 estudiantes)
        ("CI-8004001", "Joaquín Roca Chávez", "ECO", "PRESENCIAL", VoterStatus.ACTIVE),
        ("CI-8004002", "Victoria Banegas Cuéllar", "ECO", "SEMIPRESENCIAL", VoterStatus.ACTIVE),
        ("CI-8004003", "Tomás Melgar Paz", "ECO", "PRESENCIAL", VoterStatus.ACTIVE),
        ("CI-8004004", "Emilia Gutiérrez Torrico", "ECO", "PRESENCIAL", VoterStatus.ACTIVE),
        ("CI-8004005", "Esteban Rivero Saucedo", "ECO", "SEMIPRESENCIAL", VoterStatus.ACTIVE),
    ]

    for doc, name, car, mod, st in students_demo:
        node = nodes_est[car]
        stmt_v = select(Voter).where(Voter.election_id == election.id, Voter.document_id == doc)
        v = (await session.execute(stmt_v)).scalar_one_or_none()
        if not v:
            v = Voter(
                organization_id=org.id,
                election_id=election.id,
                group_id=grp_est.id,
                node_id=node.id,
                document_id=doc,
                full_name=name,
                email=f"{doc.lower()}@estudiante.granestudio.edu.bo",
                phone="70012345",
                attributes={"modalidad": mod},
                status=st,
                activated_at=now if st == VoterStatus.ACTIVE else None,
            )
            session.add(v)
    await session.flush()

    # Docentes (6 votantes)
    stmt_at = select(UnitNode).where(UnitNode.group_id == grp_doc.id, UnitNode.code == "ASODOC-TEC")
    node_astec = (await session.execute(stmt_at)).scalar_one()

    stmt_ae = select(UnitNode).where(UnitNode.group_id == grp_doc.id, UnitNode.code == "ASODOC-ECO")
    node_aseco = (await session.execute(stmt_ae)).scalar_one()

    docentes_demo = [
        ("CI-9001001", "Ing. Mario Zenteno F.", node_astec, VoterStatus.ACTIVE),
        ("CI-9001002", "Ing. Teresa Dorado M.", node_astec, VoterStatus.ACTIVE),
        ("CI-9001003", "Ing. Carlos Villarroel P.", node_astec, VoterStatus.ACTIVE),
        ("CI-9002001", "Lic. Ernesto Quiroga B.", node_aseco, VoterStatus.ACTIVE),
        ("CI-9002002", "Dra. Gladys Justiniano R.", node_aseco, VoterStatus.ACTIVE),
        ("CI-9002003", "Lic. Roberto Ardaya S.", node_aseco, VoterStatus.ACTIVE),
    ]
    for doc, name, node, st in docentes_demo:
        stmt_v = select(Voter).where(Voter.election_id == election.id, Voter.document_id == doc)
        if not (await session.execute(stmt_v)).scalar_one_or_none():
            session.add(
                Voter(
                    organization_id=org.id,
                    election_id=election.id,
                    group_id=grp_doc.id,
                    node_id=node.id,
                    document_id=doc,
                    full_name=name,
                    email=f"{doc.lower()}@docente.granestudio.edu.bo",
                    phone="71098765",
                    attributes={"escalafon": "TITULAR"},
                    status=st,
                    activated_at=now if st == VoterStatus.ACTIVE else None,
                )
            )
    await session.flush()

    # Enlaces de registro listos para usar
    links_data = [
        ("Enlace General Estudiantes (UNIV)", grp_est.id, nodes_est["UNIV"].id, "token_estudiantes_univ"),
        ("Enlace Facultad FICCT (Tecnología)", grp_est.id, nodes_est["FICCT"].id, "token_estudiantes_ficct"),
        ("Enlace Carrera Informática (INF)", grp_est.id, nodes_est["INF"].id, "token_estudiantes_inf"),
        ("Enlace Claustro Docente (UNIV-DOC)", grp_doc.id, n_udoc.id, "token_docentes_univ"),
    ]
    for label, g_id, n_id, raw_tok in links_data:
        h = sha256_hex(raw_tok)
        stmt_l = select(RegistrationLink).where(RegistrationLink.token_hash == h)
        if not (await session.execute(stmt_l)).scalar_one_or_none():
            session.add(
                RegistrationLink(
                    organization_id=org.id,
                    election_id=election.id,
                    group_id=g_id,
                    node_id=n_id,
                    token_hash=h,
                    raw_token=raw_tok,
                    label=label,
                    expires_at=t_reg_close,
                    max_uses=50,
                    uses_count=0,
                    status=LinkStatus.ACTIVE,
                    created_by=admin.id,
                    created_at=now,
                )
            )

    # Publicar determinísticamente con config_hash si no lo tiene
    if not election.config_hash:
        try:
            dump_data = await canonical_election_dump(session, election.id)
            canonical_bytes = canonical_json(dump_data)
            election.config_hash = sha256_hex(canonical_bytes)
            election.published_at = now
        except Exception:
            election.config_hash = sha256_hex(f"config_hash_{election.id}")

    await session.commit()
    return {
        "organization": org.name,
        "admin": "admin@granestudio.edu.bo",
        "election": election.name,
        "status": "ready",
    }


async def seed_ecuador(session: AsyncSession) -> dict[str, str]:
    now = datetime.now(timezone.utc)
    t_reg_open = now - timedelta(days=10)
    t_reg_close = now + timedelta(days=15)
    t_vote_open = now + timedelta(days=20)
    t_vote_close = now + timedelta(days=21)

    stmt_org = select(Organization).where(Organization.slug == "cne-ecuador")
    org = (await session.execute(stmt_org)).scalar_one_or_none()
    if not org:
        org = Organization(
            name="Elecciones Nacionales Ecuador",
            slug="cne-ecuador",
            org_type=OrganizationType.NATIONAL,
            status=OrganizationStatus.ACTIVE,
            contact_email="admin@cne.gob.ec",
        )
        session.add(org)
        await session.flush()

    stmt_admin = select(User).where(User.email == "admin@cne.gob.ec")
    admin = (await session.execute(stmt_admin)).scalar_one_or_none()
    if not admin:
        admin = User(
            organization_id=org.id,
            email="admin@cne.gob.ec",
            full_name="Ing. Diana Atamaint (Consejo Nacional Electoral)",
            password_hash=get_password_hash("Ecuador2026!"),
            role=UserRole.ADMIN_GENERAL,
            status=UserStatus.ACTIVE,
        )
        session.add(admin)
        await session.flush()

    stmt_el = select(Election).where(
        Election.organization_id == org.id,
        Election.name == "Elecciones Seccionales y Presidenciales Ecuador 2026",
    )
    election = (await session.execute(stmt_el)).scalar_one_or_none()
    if not election:
        election = Election(
            organization_id=org.id,
            name="Elecciones Seccionales y Presidenciales Ecuador 2026",
            description="Elección General de Dignidades Nacionales y Seccionales del Estado Ecuatoriano",
            timezone="America/Guayaquil",
            registration_opens_at=t_reg_open,
            registration_closes_at=t_reg_close,
            voting_opens_at=t_vote_open,
            voting_closes_at=t_vote_close,
            status=ElectionStatus.REGISTRATION_OPEN,
            k_anonymity=5,
            created_by=admin.id,
        )
        session.add(election)
        await session.flush()

    # Grupo CIUDADANOS
    stmt_grp = select(VoterGroup).where(VoterGroup.election_id == election.id, VoterGroup.code == "CIUD")
    grp = (await session.execute(stmt_grp)).scalar_one_or_none()
    if not grp:
        grp = VoterGroup(
            organization_id=org.id,
            election_id=election.id,
            name="CIUDADANOS",
            code="CIUD",
        )
        session.add(grp)
        await session.flush()

    # 4 Niveles: País -> Provincia -> Cantón -> Parroquia
    levels: dict[int, HierarchyLevel] = {}
    for d, name in [(1, "País"), (2, "Provincia"), (3, "Cantón"), (4, "Parroquia")]:
        stmt_lvl = select(HierarchyLevel).where(HierarchyLevel.group_id == grp.id, HierarchyLevel.depth == d)
        lvl = (await session.execute(stmt_lvl)).scalar_one_or_none()
        if not lvl:
            lvl = HierarchyLevel(group_id=grp.id, depth=d, name=name)
            session.add(lvl)
            await session.flush()
        levels[d] = lvl

    # Árbol Nodal: ECU -> PICHINCHA (QUITO -> CENTRO-HISTORICO), GUAYAS (GUAYAQUIL -> TARQUI)
    stmt_ecu = select(UnitNode).where(UnitNode.group_id == grp.id, UnitNode.code == "ECU")
    n_ecu = (await session.execute(stmt_ecu)).scalar_one_or_none()
    if not n_ecu:
        n_ecu = UnitNode(group_id=grp.id, level_id=levels[1].id, parent_id=None, name="República del Ecuador", code="ECU", path="/ECU/", depth=1)
        session.add(n_ecu)
        await session.flush()

    # Provincias
    for p_code, p_name, c_code, c_name, par_code, par_name in [
        ("PICHINCHA", "Provincia de Pichincha", "QUITO", "Cantón Quito", "CENTRO-HISTORICO", "Parroquia Centro Histórico"),
        ("GUAYAS", "Provincia del Guayas", "GUAYAQUIL", "Cantón Guayaquil", "TARQUI", "Parroquia Tarqui"),
    ]:
        stmt_p = select(UnitNode).where(UnitNode.group_id == grp.id, UnitNode.code == p_code)
        np = (await session.execute(stmt_p)).scalar_one_or_none()
        if not np:
            np = UnitNode(group_id=grp.id, level_id=levels[2].id, parent_id=n_ecu.id, name=p_name, code=p_code, path=f"/ECU/{p_code}/", depth=2)
            session.add(np)
            await session.flush()

        stmt_c = select(UnitNode).where(UnitNode.group_id == grp.id, UnitNode.code == c_code)
        nc = (await session.execute(stmt_c)).scalar_one_or_none()
        if not nc:
            nc = UnitNode(group_id=grp.id, level_id=levels[3].id, parent_id=np.id, name=c_name, code=c_code, path=f"{np.path}{c_code}/", depth=3)
            session.add(nc)
            await session.flush()

        stmt_par = select(UnitNode).where(UnitNode.group_id == grp.id, UnitNode.code == par_code)
        npar = (await session.execute(stmt_par)).scalar_one_or_none()
        if not npar:
            npar = UnitNode(group_id=grp.id, level_id=levels[4].id, parent_id=nc.id, name=par_name, code=par_code, path=f"{nc.path}{par_code}/", depth=4)
            session.add(npar)
            await session.flush()

    # Cargos: Presidente (País) y Gobernadores (Provincia)
    stmt_pres = select(Contest).where(Contest.group_id == grp.id, Contest.name == "Presidente y Vicepresidente Constitucional")
    c_pres = (await session.execute(stmt_pres)).scalar_one_or_none()
    if not c_pres:
        c_pres = Contest(
            group_id=grp.id,
            scope_level_id=levels[1].id,
            name="Presidente y Vicepresidente Constitucional",
            description="Jefatura de Estado y de Gobierno",
            display_order=1,
            allow_blank=True,
            allow_null=True,
        )
        session.add(c_pres)
        await session.flush()

        const_pres = Constituency(contest_id=c_pres.id, node_id=n_ecu.id)
        session.add(const_pres)
        await session.flush()

        cp1 = Candidate(
            constituency_id=const_pres.id,
            name="Luisa González y Andrés Arauz",
            party_or_front="Revolución Ciudadana (Lista 5)",
            ballot_order=1,
        )
        cp2 = Candidate(
            constituency_id=const_pres.id,
            name="Daniel Noboa y Verónica Abad",
            party_or_front="Acción Democrática Nacional (Lista 4)",
            ballot_order=2,
        )
        session.add_all([cp1, cp2])
        await session.flush()

    if not election.config_hash:
        try:
            dump_data = await canonical_election_dump(session, election.id)
            canonical_bytes = canonical_json(dump_data)
            election.config_hash = sha256_hex(canonical_bytes)
            election.published_at = now
        except Exception:
            election.config_hash = sha256_hex(f"config_hash_{election.id}")

    await session.commit()
    return {
        "organization": org.name,
        "admin": "admin@cne.gob.ec",
        "election": election.name,
        "status": "ready",
    }


async def run_seed_demo(session: AsyncSession | None = None) -> dict[str, str]:
    """Punto de entrada programático para ejecutar el sembrado demo."""
    if session is not None:
        r1 = await seed_gran_estudio(session)
        r2 = await seed_ecuador(session)
        return {"status": "success", "org1": r1["organization"], "org2": r2["organization"]}

    async with async_session_factory() as s:
        r1 = await seed_gran_estudio(s)
        r2 = await seed_ecuador(s)
        return {"status": "success", "org1": r1["organization"], "org2": r2["organization"]}


def main():
    """Punto de entrada CLI: python -m app.db.seed_demo"""
    print("Iniciando sembrado de datos de demostración VotoSeguro v1.0 (seed:demo)...")
    res = asyncio.run(run_seed_demo())
    print("Sembrado completado exitosamente:")
    print(f"  1. {res['org1']} (admin@granestudio.edu.bo / GranEstudio2026!)")
    print(f"  2. {res['org2']} (admin@cne.gob.ec / Ecuador2026!)")


if __name__ == "__main__":
    main()
