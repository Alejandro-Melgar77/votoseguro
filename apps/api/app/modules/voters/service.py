"""
Servicio de Negocio para Padrón Electoral, Carga Masiva CSV y Detección de Duplicados (S1-07, IA-L2a)
"""
import csv
import io
import json
import uuid
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.dependencies import TenantContext
from app.core.exceptions import (
    ConflictException,
    ForbiddenException,
    NotFoundException,
    UnprocessableEntityException,
)
from app.core.time import TimeProvider
from app.db.models.audit import AuditLog
from app.db.models.election import Election, ElectionStatus
from app.db.models.structure import (
    Contest,
    FilterDefinition,
    HierarchyLevel,
    UnitNode,
    VoterGroup,
)
from app.db.models.user import AdminAssignment, User
from app.db.models.voter import ImportBatch, ImportIssue, Voter, VoterStatus
from app.modules.voters.duplicate_detector import find_potential_duplicates
from app.modules.voters.schemas import (
    DuplicateResolveRequest,
    GroupSummaryItem,
    ImportBatchResponse,
    ImportIssueResponse,
    NodeSummaryItem,
    RegistrationSummaryResponse,
    VoterCreate,
    VoterResponse,
    VoterUpdate,
)


class VoterService:

    @staticmethod
    async def require_registration_open(db: AsyncSession, election_id: uuid.UUID) -> Election:
        """
        Regla Invariante #5: Toda mutación sobre el padrón exige que la elección
        esté estrictamente en estado REGISTRATION_OPEN.
        """
        stmt = select(Election).where(Election.id == election_id)
        election = (await db.execute(stmt)).scalar_one_or_none()
        if not election:
            raise NotFoundException("Elección no encontrada.")

        if election.status != ElectionStatus.REGISTRATION_OPEN:
            raise ConflictException(
                "El padrón electoral solo puede modificarse mientras la fase de registro está abierta (REGISTRATION_OPEN)."
            )
        return election

    @staticmethod
    async def _validate_voter_node_and_attributes(
        db: AsyncSession, group_id: uuid.UUID, node_id: uuid.UUID, attributes: dict
    ) -> tuple[VoterGroup, UnitNode]:
        """
        Valida que el nodo pertenezca al grupo, que su profundidad sea >= max(depth) de los cargos
        del grupo y que los filtros obligatorios estén presentes con valores válidos.
        """
        stmt_group = (
            select(VoterGroup)
            .where(VoterGroup.id == group_id)
            .options(
                selectinload(VoterGroup.contests).selectinload(Contest.scope_level),
                selectinload(VoterGroup.filters),
            )
        )
        group = (await db.execute(stmt_group)).scalar_one_or_none()
        if not group:
            raise NotFoundException("Grupo de votantes no encontrado.")

        stmt_node = select(UnitNode).where(UnitNode.id == node_id, UnitNode.group_id == group_id)
        node = (await db.execute(stmt_node)).scalar_one_or_none()
        if not node:
            raise NotFoundException("Nodo no encontrado en el grupo especificado.")

        # Validación de profundidad de nodo vs cargos del grupo
        if group.contests:
            contests_with_level = [c for c in group.contests if c.scope_level]
            if contests_with_level:
                deepest_contest = max(contests_with_level, key=lambda c: c.scope_level.depth)
                max_contest_depth = deepest_contest.scope_level.depth
                if node.depth < max_contest_depth:
                    raise UnprocessableEntityException(
                        f"El nodo asignado ('{node.name}', nivel {node.depth}) no tiene la profundidad suficiente para el cargo '{deepest_contest.name}' (requiere nivel {max_contest_depth}: {deepest_contest.scope_level.name})."
                    )

        # Validación de filtros obligatorios
        for flt in group.filters:
            if flt.is_required:
                val = attributes.get(flt.key)
                if val is None or val == "":
                    raise UnprocessableEntityException(
                        f"El atributo '{flt.label}' ({flt.key}) es obligatorio para el grupo '{group.name}'."
                    )
                if flt.allowed_values and val not in flt.allowed_values:
                    raise UnprocessableEntityException(
                        f"El valor '{val}' para el atributo '{flt.label}' no es válido. Opciones permitidas: {flt.allowed_values}."
                    )

        return group, node

    @staticmethod
    async def create_voter(
        db: AsyncSession,
        election_id: uuid.UUID,
        payload: VoterCreate,
        actor: User,
        time_provider: TimeProvider,
        client_ip: str | None = None,
    ) -> VoterResponse:
        election = await VoterService.require_registration_open(db, election_id)

        clean_doc = payload.document_id.strip().upper()
        # Verificar unicidad en la elección
        stmt_dup = select(Voter).where(
            Voter.election_id == election_id, Voter.document_id == clean_doc
        )
        if (await db.execute(stmt_dup)).scalar_one_or_none():
            raise ConflictException(f"Ya existe un votante registrado con el documento '{clean_doc}' en esta elección.")

        group, node = await VoterService._validate_voter_node_and_attributes(
            db, payload.group_id, payload.node_id, payload.attributes
        )

        voter = Voter(
            organization_id=election.organization_id,
            election_id=election_id,
            group_id=payload.group_id,
            node_id=payload.node_id,
            document_id=clean_doc,
            full_name=payload.full_name.strip(),
            email=payload.email.strip().lower() if payload.email else None,
            phone=payload.phone.strip() if payload.phone else None,
            attributes=payload.attributes,
            status=VoterStatus.IMPORTED,
        )
        db.add(voter)
        await db.flush()

        # Detección de posibles duplicados (IA-L2a)
        matches = await find_potential_duplicates(
            db, election_id, clean_doc, voter.full_name, candidate_voter_id=voter.id
        )
        if matches:
            # Crear batch virtual si no hay uno
            batch = ImportBatch(
                organization_id=election.organization_id,
                election_id=election_id,
                uploaded_by=actor.id,
                filename="Registro individual manual",
                total_rows=1,
                valid_rows=1,
                error_rows=0,
                duplicate_warnings=len(matches),
            )
            db.add(batch)
            await db.flush()

            for matched_id, m_doc, m_name, sim, dist in matches:
                issue = ImportIssue(
                    batch_id=batch.id,
                    row_number=1,
                    issue_type="POSSIBLE_DUPLICATE",
                    document_id=clean_doc,
                    raw_full_name=voter.full_name,
                    candidate_voter_id=voter.id,
                    matched_voter_id=matched_id,
                    similarity_score=sim,
                    edit_distance=dist,
                    resolution="PENDING",
                    details={
                        "candidate_document": clean_doc,
                        "candidate_name": voter.full_name,
                        "matched_document": m_doc,
                        "matched_name": m_name,
                    },
                )
                db.add(issue)

        # Auditoría
        db.add(
            AuditLog(
                organization_id=election.organization_id,
                election_id=election.id,
                actor_id=actor.id,
                actor_role=actor.role.value,
                action="VOTER_REGISTERED",
                entity_type="voter",
                entity_id=str(voter.id),
                payload={"document_id": clean_doc, "full_name": voter.full_name, "group_id": str(group.id)},
                ip_address=client_ip,
            )
        )

        await db.commit()
        await db.refresh(voter)

        return VoterResponse(
            id=voter.id,
            organization_id=voter.organization_id,
            election_id=voter.election_id,
            group_id=voter.group_id,
            group_name=group.name,
            node_id=voter.node_id,
            node_name=node.name,
            node_path=node.path,
            document_id=voter.document_id,
            full_name=voter.full_name,
            email=voter.email,
            phone=voter.phone,
            attributes=voter.attributes,
            status=voter.status,
            blocked_reason=voter.blocked_reason,
            invited_at=voter.invited_at,
            activated_at=voter.activated_at,
            created_at=voter.created_at,
        )

    @staticmethod
    async def import_voters_csv(
        db: AsyncSession,
        election_id: uuid.UUID,
        csv_content: str,
        filename: str,
        actor: User,
        time_provider: TimeProvider,
        client_ip: str | None = None,
    ) -> ImportBatchResponse:
        """
        Importa votantes fila por fila de forma resiliente:
        document_id,full_name,email,phone,group_code,node_code,attributes_json
        Registra cada error en ImportIssue(VALIDATION_ERROR) sin abortar las válidas.
        Aplica detector IA-L2a en los registros válidos.
        """
        election = await VoterService.require_registration_open(db, election_id)

        # Pre-cargar grupos y nodos para agilizar la validación
        stmt_groups = (
            select(VoterGroup)
            .where(VoterGroup.election_id == election_id)
            .options(
                selectinload(VoterGroup.contests).selectinload(Contest.scope_level),
                selectinload(VoterGroup.filters),
            )
        )
        groups_by_code = {g.code.upper(): g for g in (await db.execute(stmt_groups)).scalars().all()}

        stmt_nodes = (
            select(UnitNode)
            .join(VoterGroup, UnitNode.group_id == VoterGroup.id)
            .where(VoterGroup.election_id == election_id)
        )
        # Diccionario compuesto por (group_id, node_code)
        nodes_by_group_and_code = {(n.group_id, n.code.upper()): n for n in (await db.execute(stmt_nodes)).scalars().all()}

        # Documentos existentes en la base de datos
        stmt_docs = select(Voter.document_id).where(Voter.election_id == election_id)
        existing_docs = {doc.upper() for doc in (await db.execute(stmt_docs)).scalars().all()}

        reader = csv.DictReader(io.StringIO(csv_content))
        rows = list(reader)

        batch = ImportBatch(
            organization_id=election.organization_id,
            election_id=election_id,
            uploaded_by=actor.id,
            filename=filename,
            total_rows=len(rows),
            valid_rows=0,
            error_rows=0,
            duplicate_warnings=0,
        )
        db.add(batch)
        await db.flush()

        seen_in_batch_docs = set()

        for idx, row in enumerate(rows, start=2):
            doc = (row.get("document_id") or "").strip().upper()
            name = (row.get("full_name") or "").strip()
            email = (row.get("email") or "").strip().lower() or None
            phone = (row.get("phone") or "").strip() or None
            group_code = (row.get("group_code") or "").strip().upper()
            node_code = (row.get("node_code") or "").strip().upper()
            raw_attrs = row.get("attributes_json") or "{}"

            # Validar campos básicos requeridos
            if not doc or not name or not group_code or not node_code:
                batch.error_rows += 1
                db.add(
                    ImportIssue(
                        batch_id=batch.id,
                        row_number=idx,
                        issue_type="VALIDATION_ERROR",
                        document_id=doc or None,
                        raw_full_name=name or None,
                        resolution="PENDING",
                        details={"message": "Faltan campos obligatorios (document_id, full_name, group_code, node_code)."},
                    )
                )
                continue

            # Validar unicidad del documento
            if doc in existing_docs or doc in seen_in_batch_docs:
                batch.error_rows += 1
                db.add(
                    ImportIssue(
                        batch_id=batch.id,
                        row_number=idx,
                        issue_type="VALIDATION_ERROR",
                        document_id=doc,
                        raw_full_name=name,
                        resolution="PENDING",
                        details={"message": f"El documento de identidad '{doc}' ya se encuentra registrado."},
                    )
                )
                continue

            # Validar grupo
            group = groups_by_code.get(group_code)
            if not group:
                batch.error_rows += 1
                db.add(
                    ImportIssue(
                        batch_id=batch.id,
                        row_number=idx,
                        issue_type="VALIDATION_ERROR",
                        document_id=doc,
                        raw_full_name=name,
                        resolution="PENDING",
                        details={"message": f"El grupo con código '{group_code}' no existe en esta elección."},
                    )
                )
                continue

            # Validar nodo
            node = nodes_by_group_and_code.get((group.id, node_code))
            if not node:
                batch.error_rows += 1
                db.add(
                    ImportIssue(
                        batch_id=batch.id,
                        row_number=idx,
                        issue_type="VALIDATION_ERROR",
                        document_id=doc,
                        raw_full_name=name,
                        resolution="PENDING",
                        details={"message": f"El nodo con código '{node_code}' no existe en el grupo '{group_code}'."},
                    )
                )
                continue

            # Validar profundidad del nodo vs cargos del grupo
            if group.contests:
                contests_with_level = [c for c in group.contests if c.scope_level]
                if contests_with_level:
                    deepest_contest = max(contests_with_level, key=lambda c: c.scope_level.depth)
                    max_depth_required = deepest_contest.scope_level.depth
                    if node.depth < max_depth_required:
                        batch.error_rows += 1
                        db.add(
                            ImportIssue(
                                batch_id=batch.id,
                                row_number=idx,
                                issue_type="VALIDATION_ERROR",
                                document_id=doc,
                                raw_full_name=name,
                                resolution="PENDING",
                                details={
                                    "message": f"El nodo asignado ('{node.name}', nivel {node.depth}) no tiene la profundidad suficiente para el cargo '{deepest_contest.name}' (requiere nivel {max_depth_required}: {deepest_contest.scope_level.name})."
                                },
                            )
                        )
                        continue

            # Parsear y validar atributos
            try:
                attrs = json.loads(raw_attrs) if isinstance(raw_attrs, str) else dict(raw_attrs)
            except Exception:
                attrs = {}

            # Validar filtros obligatorios del grupo
            filter_error = None
            for flt in group.filters:
                if flt.is_required:
                    val = attrs.get(flt.key)
                    if val is None or val == "":
                        filter_error = f"El atributo '{flt.label}' ({flt.key}) es obligatorio para el grupo '{group.name}'."
                        break
                    if flt.allowed_values and val not in flt.allowed_values:
                        filter_error = f"El valor '{val}' para '{flt.label}' es inválido. Permitidos: {flt.allowed_values}."
                        break

            if filter_error:
                batch.error_rows += 1
                db.add(
                    ImportIssue(
                        batch_id=batch.id,
                        row_number=idx,
                        issue_type="VALIDATION_ERROR",
                        document_id=doc,
                        raw_full_name=name,
                        resolution="PENDING",
                        details={"message": filter_error},
                    )
                )
                continue

            # Si pasó todas las validaciones: insertar votante
            voter = Voter(
                organization_id=election.organization_id,
                election_id=election_id,
                group_id=group.id,
                node_id=node.id,
                document_id=doc,
                full_name=name,
                email=email,
                phone=phone,
                attributes=attrs,
                status=VoterStatus.IMPORTED,
            )
            db.add(voter)
            await db.flush()

            seen_in_batch_docs.add(doc)
            existing_docs.add(doc)
            batch.valid_rows += 1

            # Detección de posibles duplicados (IA-L2a)
            matches = await find_potential_duplicates(
                db, election_id, doc, name, candidate_voter_id=voter.id
            )
            for matched_id, m_doc, m_name, sim, dist in matches:
                batch.duplicate_warnings += 1
                db.add(
                    ImportIssue(
                        batch_id=batch.id,
                        row_number=idx,
                        issue_type="POSSIBLE_DUPLICATE",
                        document_id=doc,
                        raw_full_name=name,
                        candidate_voter_id=voter.id,
                        matched_voter_id=matched_id,
                        similarity_score=sim,
                        edit_distance=dist,
                        resolution="PENDING",
                        details={
                            "candidate_document": doc,
                            "candidate_name": name,
                            "matched_document": m_doc,
                            "matched_name": m_name,
                        },
                    )
                )

        # Bitácora de auditoría
        db.add(
            AuditLog(
                organization_id=election.organization_id,
                election_id=election.id,
                actor_id=actor.id,
                actor_role=actor.role.value,
                action="VOTER_BATCH_IMPORTED",
                entity_type="import_batch",
                entity_id=str(batch.id),
                payload={
                    "filename": filename,
                    "total_rows": batch.total_rows,
                    "valid_rows": batch.valid_rows,
                    "error_rows": batch.error_rows,
                    "duplicate_warnings": batch.duplicate_warnings,
                },
                ip_address=client_ip,
            )
        )

        await db.commit()
        await db.refresh(batch)
        return ImportBatchResponse.model_validate(batch)

    @staticmethod
    async def get_summary(
        db: AsyncSession, election_id: uuid.UUID, tenant: TenantContext
    ) -> RegistrationSummaryResponse:
        """
        Retorna estadísticas completas de empadronamiento:
        Total, estados, desglose por grupo, desglose por nodo y conteo de alertas de duplicados pendientes.
        Para ADMIN_SEGMENT, restringe los conteos estrictamente a su grupo o subárbol asignado.
        """
        # Filtrado de alcance para ADMIN_SEGMENT
        scoped_group_id = None
        scoped_node_path = None

        if tenant.is_segment_admin():
            stmt_assign = select(AdminAssignment).where(
                AdminAssignment.user_id == tenant.user.id, AdminAssignment.election_id == election_id
            )
            assignment = (await db.execute(stmt_assign)).scalar_one_or_none()
            if not assignment:
                raise ForbiddenException("No tiene asignación delegada para esta elección.")
            scoped_group_id = assignment.group_id
            if assignment.node_id:
                stmt_n = select(UnitNode).where(UnitNode.id == assignment.node_id)
                assigned_node = (await db.execute(stmt_n)).scalar_one_or_none()
                if assigned_node:
                    scoped_node_path = assigned_node.path

        # Consulta base de votantes
        base_query = select(Voter).join(UnitNode, Voter.node_id == UnitNode.id).where(Voter.election_id == election_id)
        if scoped_group_id:
            base_query = base_query.where(Voter.group_id == scoped_group_id)
        if scoped_node_path:
            base_query = base_query.where(UnitNode.path.like(f"{scoped_node_path}%"))

        voters = (await db.execute(base_query.options(selectinload(Voter.group), selectinload(Voter.node)))).scalars().all()

        total = len(voters)
        imported_count = sum(1 for v in voters if v.status == VoterStatus.IMPORTED)
        invited_count = sum(1 for v in voters if v.status == VoterStatus.INVITED)
        active_count = sum(1 for v in voters if v.status == VoterStatus.ACTIVE)
        blocked_count = sum(1 for v in voters if v.status == VoterStatus.BLOCKED)

        activation_pct = round((active_count / total * 100), 1) if total > 0 else 0.0

        # Alertas de duplicados pendientes
        stmt_dup = (
            select(func.count(ImportIssue.id))
            .join(ImportBatch, ImportIssue.batch_id == ImportBatch.id)
            .where(
                ImportBatch.election_id == election_id,
                ImportIssue.issue_type == "POSSIBLE_DUPLICATE",
                ImportIssue.resolution == "PENDING",
            )
        )
        pending_dups = (await db.execute(stmt_dup)).scalar() or 0

        # Desglose por grupo
        groups_map: dict[uuid.UUID, dict] = {}
        for v in voters:
            g = v.group
            if g.id not in groups_map:
                groups_map[g.id] = {
                    "id": g.id,
                    "name": g.name,
                    "code": g.code,
                    "total": 0,
                    "imported": 0,
                    "invited": 0,
                    "active": 0,
                    "blocked": 0,
                }
            groups_map[g.id]["total"] += 1
            if v.status == VoterStatus.IMPORTED:
                groups_map[g.id]["imported"] += 1
            elif v.status == VoterStatus.INVITED:
                groups_map[g.id]["invited"] += 1
            elif v.status == VoterStatus.ACTIVE:
                groups_map[g.id]["active"] += 1
            elif v.status == VoterStatus.BLOCKED:
                groups_map[g.id]["blocked"] += 1

        by_group = [
            GroupSummaryItem(
                group_id=d["id"],
                group_name=d["name"],
                group_code=d["code"],
                total_voters=d["total"],
                imported_count=d["imported"],
                invited_count=d["invited"],
                active_count=d["active"],
                blocked_count=d["blocked"],
            )
            for d in groups_map.values()
        ]

        # Desglose por nodo
        nodes_map: dict[uuid.UUID, dict] = {}
        for v in voters:
            n = v.node
            if n.id not in nodes_map:
                nodes_map[n.id] = {
                    "id": n.id,
                    "name": n.name,
                    "code": n.code,
                    "path": n.path,
                    "depth": n.depth,
                    "total": 0,
                    "active": 0,
                }
            nodes_map[n.id]["total"] += 1
            if v.status == VoterStatus.ACTIVE:
                nodes_map[n.id]["active"] += 1

        by_node = [
            NodeSummaryItem(
                node_id=d["id"],
                node_name=d["name"],
                node_code=d["code"],
                node_path=d["path"],
                depth=d["depth"],
                total_voters=d["total"],
                active_voters=d["active"],
            )
            for d in sorted(nodes_map.values(), key=lambda x: x["path"])
        ]

        return RegistrationSummaryResponse(
            total_voters=total,
            imported_count=imported_count,
            invited_count=invited_count,
            active_count=active_count,
            blocked_count=blocked_count,
            activation_percentage=activation_pct,
            pending_duplicates_count=pending_dups,
            by_group=by_group,
            by_node=by_node,
        )

    @staticmethod
    async def list_voters(
        db: AsyncSession,
        election_id: uuid.UUID,
        tenant: TenantContext,
        group_id: uuid.UUID | None = None,
        node_id: uuid.UUID | None = None,
        status: VoterStatus | None = None,
        search: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[VoterResponse]:
        """
        Lista paginada y filtrable de votantes.
        Aplica automáticamente restricciones de visibilidad si el actor es ADMIN_SEGMENT.
        """
        query = (
            select(Voter)
            .join(UnitNode, Voter.node_id == UnitNode.id)
            .join(VoterGroup, Voter.group_id == VoterGroup.id)
            .where(Voter.election_id == election_id)
            .options(selectinload(Voter.group), selectinload(Voter.node))
        )

        # Restricciones para ADMIN_SEGMENT
        if tenant.is_segment_admin():
            stmt_assign = select(AdminAssignment).where(
                AdminAssignment.user_id == tenant.user.id, AdminAssignment.election_id == election_id
            )
            assignment = (await db.execute(stmt_assign)).scalar_one_or_none()
            if not assignment:
                raise ForbiddenException("No tiene permisos para consultar el padrón de esta elección.")
            if assignment.group_id:
                query = query.where(Voter.group_id == assignment.group_id)
            if assignment.node_id:
                stmt_n = select(UnitNode).where(UnitNode.id == assignment.node_id)
                assigned_node = (await db.execute(stmt_n)).scalar_one()
                query = query.where(UnitNode.path.like(f"{assigned_node.path}%"))

        if group_id:
            query = query.where(Voter.group_id == group_id)
        if node_id:
            stmt_tgt = select(UnitNode).where(UnitNode.id == node_id)
            target_node = (await db.execute(stmt_tgt)).scalar_one_or_none()
            if target_node:
                query = query.where(UnitNode.path.like(f"{target_node.path}%"))
        if status:
            query = query.where(Voter.status == status)
        if search:
            search_clean = f"%{search.strip()}%"
            query = query.where(
                (Voter.document_id.ilike(search_clean)) | (Voter.full_name.ilike(search_clean))
            )

        query = query.order_by(Voter.created_at.desc()).limit(limit).offset(offset)
        voters = (await db.execute(query)).scalars().all()

        return [
            VoterResponse(
                id=v.id,
                organization_id=v.organization_id,
                election_id=v.election_id,
                group_id=v.group_id,
                group_name=v.group.name if v.group else None,
                node_id=v.node_id,
                node_name=v.node.name if v.node else None,
                node_path=v.node.path if v.node else None,
                document_id=v.document_id,
                full_name=v.full_name,
                email=v.email,
                phone=v.phone,
                attributes=v.attributes,
                status=v.status,
                blocked_reason=v.blocked_reason,
                invited_at=v.invited_at,
                activated_at=v.activated_at,
                created_at=v.created_at,
            )
            for v in voters
        ]

    @staticmethod
    async def update_voter(
        db: AsyncSession,
        election_id: uuid.UUID,
        voter_id: uuid.UUID,
        payload: VoterUpdate,
        actor: User,
        client_ip: str | None = None,
    ) -> VoterResponse:
        """Actualiza o bloquea a un votante (únicamente en REGISTRATION_OPEN)."""
        await VoterService.require_registration_open(db, election_id)

        stmt = select(Voter).where(Voter.id == voter_id, Voter.election_id == election_id).options(
            selectinload(Voter.group), selectinload(Voter.node)
        )
        voter = (await db.execute(stmt)).scalar_one_or_none()
        if not voter:
            raise NotFoundException("Votante no encontrado.")

        if payload.email is not None:
            voter.email = payload.email.strip().lower() if payload.email else None
        if payload.phone is not None:
            voter.phone = payload.phone.strip() if payload.phone else None
        if payload.attributes is not None:
            voter.attributes = payload.attributes

        action_name = "VOTER_UPDATED"
        if payload.status:
            if payload.status == VoterStatus.BLOCKED:
                if not payload.blocked_reason or len(payload.blocked_reason.strip()) < 3:
                    raise UnprocessableEntityException("Debe indicar un motivo explícito para bloquear al votante.")
                voter.status = VoterStatus.BLOCKED
                voter.blocked_reason = payload.blocked_reason.strip()
                action_name = "VOTER_BLOCKED"
            else:
                voter.status = payload.status
                if payload.status != VoterStatus.BLOCKED:
                    voter.blocked_reason = None

        db.add(
            AuditLog(
                organization_id=voter.organization_id,
                election_id=election_id,
                actor_id=actor.id,
                actor_role=actor.role.value,
                action=action_name,
                entity_type="voter",
                entity_id=str(voter.id),
                payload={"status": voter.status.value, "blocked_reason": voter.blocked_reason},
                ip_address=client_ip,
            )
        )

        await db.commit()
        await db.refresh(voter)

        return VoterResponse(
            id=voter.id,
            organization_id=voter.organization_id,
            election_id=voter.election_id,
            group_id=voter.group_id,
            group_name=voter.group.name if voter.group else None,
            node_id=voter.node_id,
            node_name=voter.node.name if voter.node else None,
            node_path=voter.node.path if voter.node else None,
            document_id=voter.document_id,
            full_name=voter.full_name,
            email=voter.email,
            phone=voter.phone,
            attributes=voter.attributes,
            status=voter.status,
            blocked_reason=voter.blocked_reason,
            invited_at=voter.invited_at,
            activated_at=voter.activated_at,
            created_at=voter.created_at,
        )

    @staticmethod
    async def delete_voter(
        db: AsyncSession, election_id: uuid.UUID, voter_id: uuid.UUID, actor: User, client_ip: str | None = None
    ) -> None:
        """Elimina/retira a un votante del padrón (únicamente en REGISTRATION_OPEN)."""
        await VoterService.require_registration_open(db, election_id)

        stmt = select(Voter).where(Voter.id == voter_id, Voter.election_id == election_id)
        voter = (await db.execute(stmt)).scalar_one_or_none()
        if not voter:
            raise NotFoundException("Votante no encontrado.")

        db.add(
            AuditLog(
                organization_id=voter.organization_id,
                election_id=election_id,
                actor_id=actor.id,
                actor_role=actor.role.value,
                action="VOTER_REMOVED",
                entity_type="voter",
                entity_id=str(voter.id),
                payload={"document_id": voter.document_id, "full_name": voter.full_name},
                ip_address=client_ip,
            )
        )

        await db.delete(voter)
        await db.commit()

    @staticmethod
    async def list_import_batches(db: AsyncSession, election_id: uuid.UUID) -> list[ImportBatchResponse]:
        stmt = (
            select(ImportBatch)
            .where(ImportBatch.election_id == election_id)
            .order_by(ImportBatch.created_at.desc())
        )
        batches = (await db.execute(stmt)).scalars().all()
        return [ImportBatchResponse.model_validate(b) for b in batches]

    @staticmethod
    async def list_batch_issues(db: AsyncSession, batch_id: uuid.UUID) -> list[ImportIssueResponse]:
        stmt = (
            select(ImportIssue)
            .where(ImportIssue.batch_id == batch_id)
            .order_by(ImportIssue.row_number.asc())
        )
        issues = (await db.execute(stmt)).scalars().all()
        return [ImportIssueResponse.model_validate(i) for i in issues]

    @staticmethod
    async def list_duplicates(db: AsyncSession, election_id: uuid.UUID) -> list[ImportIssueResponse]:
        """Lista las alertas de posibles duplicados en estado PENDING con datos de ambos votantes."""
        stmt = (
            select(ImportIssue)
            .join(ImportBatch, ImportIssue.batch_id == ImportBatch.id)
            .where(
                ImportBatch.election_id == election_id,
                ImportIssue.issue_type == "POSSIBLE_DUPLICATE",
                ImportIssue.resolution == "PENDING",
            )
            .options(
                selectinload(ImportIssue.candidate_voter),
                selectinload(ImportIssue.matched_voter),
            )
            .order_by(ImportIssue.similarity_score.desc())
        )
        issues = (await db.execute(stmt)).scalars().all()

        result = []
        for i in issues:
            res = ImportIssueResponse(
                id=i.id,
                batch_id=i.batch_id,
                row_number=i.row_number,
                issue_type=i.issue_type,
                document_id=i.document_id,
                raw_full_name=i.raw_full_name,
                candidate_voter_id=i.candidate_voter_id,
                candidate_voter_name=i.candidate_voter.full_name if i.candidate_voter else i.raw_full_name,
                matched_voter_id=i.matched_voter_id,
                matched_voter_name=i.matched_voter.full_name if i.matched_voter else None,
                matched_voter_document=i.matched_voter.document_id if i.matched_voter else None,
                similarity_score=i.similarity_score,
                edit_distance=i.edit_distance,
                resolution=i.resolution,
                resolved_by=i.resolved_by,
                resolved_at=i.resolved_at,
                details=i.details,
            )
            result.append(res)
        return result

    @staticmethod
    async def resolve_duplicate(
        db: AsyncSession,
        election_id: uuid.UUID,
        issue_id: uuid.UUID,
        payload: DuplicateResolveRequest,
        actor: User,
        time_provider: TimeProvider,
        client_ip: str | None = None,
    ) -> ImportIssueResponse:
        """
        Bandeja de dictamen humano para duplicados (IA-L2a):
        CONFIRM_DISTINCT: Marca la alerta como personas distintas.
        BLOCK_NEW: Bloquea al votante candidato.
        REMOVE_NEW: Elimina al votante candidato del padrón.
        """
        await VoterService.require_registration_open(db, election_id)

        stmt = (
            select(ImportIssue)
            .join(ImportBatch, ImportIssue.batch_id == ImportBatch.id)
            .where(ImportIssue.id == issue_id, ImportBatch.election_id == election_id)
            .options(
                selectinload(ImportIssue.candidate_voter),
                selectinload(ImportIssue.matched_voter),
            )
        )
        issue = (await db.execute(stmt)).scalar_one_or_none()
        if not issue:
            raise NotFoundException("Alerta de duplicado no encontrada.")

        db_now = await time_provider.now(db)

        if payload.action == "CONFIRM_DISTINCT":
            issue.resolution = "CONFIRMED_DISTINCT"
        elif payload.action == "BLOCK_NEW":
            issue.resolution = "MERGED_OR_REJECTED"
            if issue.candidate_voter:
                issue.candidate_voter.status = VoterStatus.BLOCKED
                issue.candidate_voter.blocked_reason = f"Bloqueado por posible duplicidad: {payload.reason}"
        elif payload.action == "REMOVE_NEW":
            issue.resolution = "MERGED_OR_REJECTED"
            if issue.candidate_voter:
                await db.delete(issue.candidate_voter)

        issue.resolved_by = actor.id
        issue.resolved_at = db_now

        # Bitácora
        stmt_elect = select(Election).where(Election.id == election_id)
        election = (await db.execute(stmt_elect)).scalar_one()

        db.add(
            AuditLog(
                organization_id=election.organization_id,
                election_id=election_id,
                actor_id=actor.id,
                actor_role=actor.role.value,
                action="DUPLICATE_ADJUDICATED",
                entity_type="import_issue",
                entity_id=str(issue.id),
                payload={
                    "action": payload.action,
                    "reason": payload.reason,
                    "candidate_voter_id": str(issue.candidate_voter_id) if issue.candidate_voter_id else None,
                    "matched_voter_id": str(issue.matched_voter_id) if issue.matched_voter_id else None,
                },
                ip_address=client_ip,
            )
        )

        await db.commit()
        await db.refresh(issue)

        return ImportIssueResponse(
            id=issue.id,
            batch_id=issue.batch_id,
            row_number=issue.row_number,
            issue_type=issue.issue_type,
            document_id=issue.document_id,
            raw_full_name=issue.raw_full_name,
            candidate_voter_id=issue.candidate_voter_id,
            candidate_voter_name=issue.candidate_voter.full_name if issue.candidate_voter else issue.raw_full_name,
            matched_voter_id=issue.matched_voter_id,
            matched_voter_name=issue.matched_voter.full_name if issue.matched_voter else None,
            matched_voter_document=issue.matched_voter.document_id if issue.matched_voter else None,
            similarity_score=issue.similarity_score,
            edit_distance=issue.edit_distance,
            resolution=issue.resolution,
            resolved_by=issue.resolved_by,
            resolved_at=issue.resolved_at,
            details=issue.details,
        )
