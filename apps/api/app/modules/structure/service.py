"""
Servicio de Negocio para Estructura Electoral: Grupos, Jerarquías, Nodos, Filtros, Cargos y Circunscripciones (S1-03, S1-04)
"""
import csv
import io
import uuid
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import (
    ConflictException,
    NotFoundException,
    UnprocessableEntityException,
)
from app.db.models.election import Election
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
from app.modules.structure.guards import require_election_draft, require_group_draft
from app.modules.structure.schemas import (
    CandidateBrief,
    ConstituencyBrief,
    ContestBreakdownConfig,
    ContestBreakdownResponse,
    ContestCreate,
    ContestResponse,
    ContestUpdate,
    FilterDefinitionCreate,
    FilterDefinitionResponse,
    HierarchyLevelCreate,
    HierarchyLevelResponse,
    NodeImportResult,
    NodeImportRowError,
    UnitNodeCreate,
    UnitNodeResponse,
    UnitNodeTreeNode,
    UnitNodeUpdate,
    VoterGroupCreate,
    VoterGroupResponse,
    VoterGroupUpdate,
    VoterGroupVotingWindowUpdate,
)


class StructureService:

    # -------------------------------------------------------------------------
    # Grupos de Votantes (VoterGroup)
    # -------------------------------------------------------------------------

    @staticmethod
    async def create_group(
        db: AsyncSession, election_id: uuid.UUID, payload: VoterGroupCreate, organization_id: uuid.UUID
    ) -> VoterGroupResponse:
        election = await require_election_draft(db, election_id)
        if election.organization_id != organization_id:
            raise NotFoundException("Elección no encontrada.")

        code_clean = payload.code.strip().upper()
        # Verificar unicidad de código
        stmt = select(VoterGroup).where(
            VoterGroup.election_id == election_id,
            func.upper(VoterGroup.code) == code_clean,
        )
        if (await db.execute(stmt)).scalar_one_or_none():
            raise UnprocessableEntityException(f"Ya existe un grupo con el código '{code_clean}' en esta elección.")

        # Validar ventana horaria si se define
        if payload.voting_opens_at or payload.voting_closes_at:
            if not (payload.voting_opens_at and payload.voting_closes_at):
                raise UnprocessableEntityException("Debe especificar tanto inicio como fin de la ventana horaria del grupo.")
            if not (
                election.voting_opens_at <= payload.voting_opens_at < payload.voting_closes_at <= election.voting_closes_at
            ):
                raise UnprocessableEntityException(
                    "La ventana de votación del grupo debe estar contenida estrictamente dentro de la ventana general de la elección."
                )

        group = VoterGroup(
            organization_id=organization_id,
            election_id=election_id,
            name=payload.name.strip(),
            code=code_clean,
            description=payload.description.strip() if payload.description else None,
            voting_opens_at=payload.voting_opens_at,
            voting_closes_at=payload.voting_closes_at,
        )
        db.add(group)
        await db.commit()
        await db.refresh(group)

        return VoterGroupResponse(
            id=group.id,
            organization_id=group.organization_id,
            election_id=group.election_id,
            name=group.name,
            code=group.code,
            description=group.description,
            voting_opens_at=group.voting_opens_at,
            voting_closes_at=group.voting_closes_at,
            created_at=group.created_at,
            levels_count=0,
            nodes_count=0,
            contests_count=0,
        )

    @staticmethod
    async def list_groups(db: AsyncSession, election_id: uuid.UUID, organization_id: uuid.UUID) -> list[VoterGroupResponse]:
        stmt_elect = select(Election).where(Election.id == election_id, Election.organization_id == organization_id)
        if not (await db.execute(stmt_elect)).scalar_one_or_none():
            raise NotFoundException("Elección no encontrada.")

        stmt = (
            select(VoterGroup)
            .where(VoterGroup.election_id == election_id)
            .options(
                selectinload(VoterGroup.levels),
                selectinload(VoterGroup.nodes),
                selectinload(VoterGroup.contests),
            )
            .order_by(VoterGroup.code.asc())
        )
        groups = (await db.execute(stmt)).scalars().all()

        return [
            VoterGroupResponse(
                id=g.id,
                organization_id=g.organization_id,
                election_id=g.election_id,
                name=g.name,
                code=g.code,
                description=g.description,
                voting_opens_at=g.voting_opens_at,
                voting_closes_at=g.voting_closes_at,
                created_at=g.created_at,
                levels_count=len(g.levels),
                nodes_count=len(g.nodes),
                contests_count=len(g.contests),
            )
            for g in groups
        ]

    @staticmethod
    async def update_group(db: AsyncSession, group_id: uuid.UUID, payload: VoterGroupUpdate) -> VoterGroupResponse:
        group, _ = await require_group_draft(db, group_id)

        if payload.name:
            group.name = payload.name.strip()
        if payload.code:
            code_clean = payload.code.strip().upper()
            stmt_dup = select(VoterGroup).where(
                VoterGroup.election_id == group.election_id,
                VoterGroup.id != group_id,
                func.upper(VoterGroup.code) == code_clean,
            )
            if (await db.execute(stmt_dup)).scalar_one_or_none():
                raise UnprocessableEntityException(f"Ya existe otro grupo con el código '{code_clean}'.")
            group.code = code_clean
        if payload.description is not None:
            group.description = payload.description.strip() if payload.description else None

        await db.commit()
        await db.refresh(group)
        return await StructureService.get_group_response(db, group.id)

    @staticmethod
    async def update_group_voting_window(
        db: AsyncSession, group_id: uuid.UUID, payload: VoterGroupVotingWindowUpdate
    ) -> VoterGroupResponse:
        stmt = select(VoterGroup).where(VoterGroup.id == group_id)
        group = (await db.execute(stmt)).scalar_one_or_none()
        if not group:
            raise NotFoundException("Grupo no encontrado.")

        stmt_elect = select(Election).where(Election.id == group.election_id)
        election = (await db.execute(stmt_elect)).scalar_one()

        if payload.voting_opens_at or payload.voting_closes_at:
            if not (payload.voting_opens_at and payload.voting_closes_at):
                raise UnprocessableEntityException("Debe especificar tanto inicio como fin de la ventana horaria.")
            if not (
                election.voting_opens_at <= payload.voting_opens_at < payload.voting_closes_at <= election.voting_closes_at
            ):
                raise UnprocessableEntityException(
                    "La ventana del grupo debe estar contenida estrictamente en la ventana de votación de la elección."
                )
            group.voting_opens_at = payload.voting_opens_at
            group.voting_closes_at = payload.voting_closes_at
        else:
            group.voting_opens_at = None
            group.voting_closes_at = None

        await db.commit()
        await db.refresh(group)
        return await StructureService.get_group_response(db, group.id)

    @staticmethod
    async def delete_group(db: AsyncSession, group_id: uuid.UUID) -> None:
        group, _ = await require_group_draft(db, group_id)
        await db.delete(group)
        await db.commit()

    @staticmethod
    async def get_group_response(db: AsyncSession, group_id: uuid.UUID) -> VoterGroupResponse:
        stmt = (
            select(VoterGroup)
            .where(VoterGroup.id == group_id)
            .options(
                selectinload(VoterGroup.levels),
                selectinload(VoterGroup.nodes),
                selectinload(VoterGroup.contests),
            )
        )
        group = (await db.execute(stmt)).scalar_one()
        return VoterGroupResponse(
            id=group.id,
            organization_id=group.organization_id,
            election_id=group.election_id,
            name=group.name,
            code=group.code,
            description=group.description,
            voting_opens_at=group.voting_opens_at,
            voting_closes_at=group.voting_closes_at,
            created_at=group.created_at,
            levels_count=len(group.levels),
            nodes_count=len(group.nodes),
            contests_count=len(group.contests),
        )

    # -------------------------------------------------------------------------
    # Niveles Jerárquicos (HierarchyLevel)
    # -------------------------------------------------------------------------

    @staticmethod
    async def create_level(
        db: AsyncSession, group_id: uuid.UUID, payload: HierarchyLevelCreate
    ) -> HierarchyLevelResponse:
        group, _ = await require_group_draft(db, group_id)

        stmt_max = select(func.max(HierarchyLevel.depth)).where(HierarchyLevel.group_id == group_id)
        max_depth = (await db.execute(stmt_max)).scalar() or 0
        new_depth = max_depth + 1

        name_clean = payload.name.strip()
        stmt_dup = select(HierarchyLevel).where(
            HierarchyLevel.group_id == group_id, func.lower(HierarchyLevel.name) == name_clean.lower()
        )
        if (await db.execute(stmt_dup)).scalar_one_or_none():
            raise UnprocessableEntityException(f"Ya existe un nivel con el nombre '{name_clean}' en este grupo.")

        level = HierarchyLevel(group_id=group_id, depth=new_depth, name=name_clean)
        db.add(level)
        await db.commit()
        await db.refresh(level)
        return HierarchyLevelResponse.model_validate(level)

    @staticmethod
    async def list_levels(db: AsyncSession, group_id: uuid.UUID) -> list[HierarchyLevelResponse]:
        stmt = select(HierarchyLevel).where(HierarchyLevel.group_id == group_id).order_by(HierarchyLevel.depth.asc())
        levels = (await db.execute(stmt)).scalars().all()
        return [HierarchyLevelResponse.model_validate(lvl) for lvl in levels]

    @staticmethod
    async def delete_level(db: AsyncSession, level_id: uuid.UUID) -> None:
        stmt = select(HierarchyLevel).where(HierarchyLevel.id == level_id)
        level = (await db.execute(stmt)).scalar_one_or_none()
        if not level:
            raise NotFoundException("Nivel jerárquico no encontrado.")

        await require_group_draft(db, level.group_id)

        # Solo se permite eliminar el nivel de máxima profundidad
        stmt_max = select(func.max(HierarchyLevel.depth)).where(HierarchyLevel.group_id == level.group_id)
        max_depth = (await db.execute(stmt_max)).scalar()
        if level.depth != max_depth:
            raise UnprocessableEntityException(
                f"Solo puede eliminarse el nivel más profundo (Nivel {max_depth}). Elimine primero los niveles inferiores."
            )

        # Verificar si tiene nodos asociados
        stmt_nodes = select(func.count(UnitNode.id)).where(UnitNode.level_id == level_id)
        node_count = (await db.execute(stmt_nodes)).scalar() or 0
        if node_count > 0:
            raise UnprocessableEntityException(
                f"No puede eliminarse el nivel '{level.name}' porque contiene {node_count} nodo(s). Elimínelos primero."
            )

        # Verificar si tiene cargos asociados
        stmt_contests = select(func.count(Contest.id)).where(Contest.scope_level_id == level_id)
        contest_count = (await db.execute(stmt_contests)).scalar() or 0
        if contest_count > 0:
            raise UnprocessableEntityException(
                f"No puede eliminarse el nivel '{level.name}' porque es el alcance de {contest_count} cargo(s)."
            )

        await db.delete(level)
        await db.commit()

    # -------------------------------------------------------------------------
    # Nodos Jerárquicos y Ruta Materializada (UnitNode)
    # -------------------------------------------------------------------------

    @staticmethod
    async def create_node(db: AsyncSession, group_id: uuid.UUID, payload: UnitNodeCreate) -> UnitNodeResponse:
        group, election = await require_group_draft(db, group_id)

        # Verificar nivel
        stmt_lvl = select(HierarchyLevel).where(HierarchyLevel.id == payload.level_id, HierarchyLevel.group_id == group_id)
        level = (await db.execute(stmt_lvl)).scalar_one_or_none()
        if not level:
            raise NotFoundException("Nivel jerárquico no encontrado en este grupo.")

        code_clean = payload.code.strip().upper()
        # Unicidad de código dentro del grupo
        stmt_dup = select(UnitNode).where(
            UnitNode.group_id == group_id, func.upper(UnitNode.code) == code_clean
        )
        if (await db.execute(stmt_dup)).scalar_one_or_none():
            raise UnprocessableEntityException(f"Ya existe un nodo con el código '{code_clean}' en este grupo.")

        # Regla de Ruta Materializada
        if level.depth == 1:
            if payload.parent_id is not None:
                raise UnprocessableEntityException("Los nodos de nivel raíz (depth 1) no pueden tener un nodo padre.")
            parent_id = None
            path = f"/{code_clean}/"
        else:
            if payload.parent_id is None:
                raise UnprocessableEntityException(f"Los nodos de nivel {level.depth} requieren obligatoriamente un nodo padre.")
            stmt_parent = select(UnitNode).options(selectinload(UnitNode.level)).where(
                UnitNode.id == payload.parent_id, UnitNode.group_id == group_id
            )
            parent = (await db.execute(stmt_parent)).scalar_one_or_none()
            if not parent:
                raise NotFoundException("Nodo padre no encontrado en este grupo.")

            if parent.level.depth != level.depth - 1:
                raise UnprocessableEntityException(
                    f"El nodo padre ('{parent.name}', nivel {parent.level.depth}) debe pertenecer exactamente al nivel inmediatamente superior (nivel {level.depth - 1})."
                )
            parent_id = parent.id
            path = f"{parent.path}{code_clean}/"

        node = UnitNode(
            group_id=group_id,
            level_id=level.id,
            parent_id=parent_id,
            name=payload.name.strip(),
            code=code_clean,
            path=path,
            depth=level.depth,
        )
        db.add(node)
        await db.flush()

        # Sincronización automática de circunscripciones para cargos con este scope_level_id
        await StructureService.sync_constituencies_for_node(db, node)

        await db.commit()
        await db.refresh(node)
        return UnitNodeResponse.model_validate(node)

    @staticmethod
    async def get_nodes_tree(db: AsyncSession, group_id: uuid.UUID) -> list[UnitNodeTreeNode]:
        stmt = (
            select(UnitNode)
            .where(UnitNode.group_id == group_id)
            .order_by(UnitNode.depth.asc(), UnitNode.code.asc())
        )
        nodes = (await db.execute(stmt)).scalars().all()

        nodes_by_id: dict[uuid.UUID, UnitNodeTreeNode] = {}
        roots: list[UnitNodeTreeNode] = []

        for n in nodes:
            tree_node = UnitNodeTreeNode(
                id=n.id,
                group_id=n.group_id,
                level_id=n.level_id,
                parent_id=n.parent_id,
                name=n.name,
                code=n.code,
                path=n.path,
                depth=n.depth,
                children=[],
            )
            nodes_by_id[n.id] = tree_node
            if n.parent_id is None:
                roots.append(tree_node)
            else:
                parent = nodes_by_id.get(n.parent_id)
                if parent:
                    parent.children.append(tree_node)
                else:
                    roots.append(tree_node)

        return roots

    @staticmethod
    async def update_node(db: AsyncSession, node_id: uuid.UUID, payload: UnitNodeUpdate) -> UnitNodeResponse:
        stmt = select(UnitNode).where(UnitNode.id == node_id)
        node = (await db.execute(stmt)).scalar_one_or_none()
        if not node:
            raise NotFoundException("Nodo no encontrado.")

        await require_group_draft(db, node.group_id)

        if payload.name:
            node.name = payload.name.strip()

        if payload.code and payload.code.strip().upper() != node.code:
            new_code = payload.code.strip().upper()
            # Validar unicidad
            stmt_dup = select(UnitNode).where(
                UnitNode.group_id == node.group_id,
                UnitNode.id != node_id,
                func.upper(UnitNode.code) == new_code,
            )
            if (await db.execute(stmt_dup)).scalar_one_or_none():
                raise UnprocessableEntityException(f"Ya existe un nodo con el código '{new_code}' en este grupo.")

            old_path = node.path
            # Recomputar path del nodo
            if node.parent_id is None:
                new_path = f"/{new_code}/"
            else:
                stmt_parent = select(UnitNode).where(UnitNode.id == node.parent_id)
                parent = (await db.execute(stmt_parent)).scalar_one()
                new_path = f"{parent.path}{new_code}/"

            node.code = new_code
            node.path = new_path

            # Actualizar recursivamente todos los nodos descendientes
            stmt_desc = select(UnitNode).where(
                UnitNode.group_id == node.group_id,
                UnitNode.path.like(f"{old_path}%"),
                UnitNode.id != node.id,
            )
            descendants = (await db.execute(stmt_desc)).scalars().all()
            for d in descendants:
                d.path = new_path + d.path[len(old_path):]

        await db.commit()
        await db.refresh(node)
        return UnitNodeResponse.model_validate(node)

    @staticmethod
    async def delete_node(db: AsyncSession, node_id: uuid.UUID) -> None:
        stmt = select(UnitNode).where(UnitNode.id == node_id)
        node = (await db.execute(stmt)).scalar_one_or_none()
        if not node:
            raise NotFoundException("Nodo no encontrado.")

        await require_group_draft(db, node.group_id)

        # Verificar si tiene nodos hijos
        stmt_children = select(func.count(UnitNode.id)).where(UnitNode.parent_id == node_id)
        child_count = (await db.execute(stmt_children)).scalar() or 0
        if child_count > 0:
            raise UnprocessableEntityException(
                f"No puede eliminarse el nodo '{node.name}' porque contiene {child_count} sub-nodo(s) hijo(s). Elimínelos primero."
            )

        # Eliminar circunscripciones asociadas si están vacías o en borrador
        await db.delete(node)
        await db.commit()

    @staticmethod
    async def import_nodes_csv(db: AsyncSession, group_id: uuid.UUID, csv_content: str) -> NodeImportResult:
        """
        Importa nodos desde CSV: code,name,level_depth,parent_code.
        Ordena topológicamente por level_depth ASC y procesa con tolerancia a fallos fila a fila.
        """
        group, _ = await require_group_draft(db, group_id)

        # Cargar niveles del grupo
        stmt_levels = select(HierarchyLevel).where(HierarchyLevel.group_id == group_id)
        levels_by_depth = {lvl.depth: lvl for lvl in (await db.execute(stmt_levels)).scalars().all()}

        # Cargar nodos existentes por código
        stmt_nodes = select(UnitNode).where(UnitNode.group_id == group_id)
        nodes_by_code = {n.code.upper(): n for n in (await db.execute(stmt_nodes)).scalars().all()}

        reader = csv.DictReader(io.StringIO(csv_content))
        raw_rows = []
        for idx, row in enumerate(reader, start=2):
            raw_rows.append((idx, row))

        # Validar y parsear level_depth para orden topológico
        parsed_rows = []
        errors: list[NodeImportRowError] = []

        for row_num, row in raw_rows:
            code = (row.get("code") or "").strip().upper()
            name = (row.get("name") or "").strip()
            depth_str = (row.get("level_depth") or "").strip()
            parent_code = (row.get("parent_code") or "").strip().upper()

            if not code or not name or not depth_str:
                errors.append(NodeImportRowError(row=row_num, code=code or "?", message="Faltan columnas requeridas (code, name, level_depth)."))
                continue

            try:
                depth = int(depth_str)
            except ValueError:
                errors.append(NodeImportRowError(row=row_num, code=code, message=f"level_depth '{depth_str}' no es un entero válido."))
                continue

            parsed_rows.append({
                "row_num": row_num,
                "code": code,
                "name": name,
                "depth": depth,
                "parent_code": parent_code,
            })

        # Ordenar topológicamente: primero profundidad 1, luego 2, etc.
        parsed_rows.sort(key=lambda r: r["depth"])

        created_nodes = 0
        for item in parsed_rows:
            code = item["code"]
            depth = item["depth"]
            parent_code = item["parent_code"]
            name = item["name"]
            row_num = item["row_num"]

            level = levels_by_depth.get(depth)
            if not level:
                errors.append(NodeImportRowError(row=row_num, code=code, message=f"No existe el nivel de profundidad {depth} configurado en el grupo."))
                continue

            if code in nodes_by_code:
                errors.append(NodeImportRowError(row=row_num, code=code, message=f"El código de nodo '{code}' ya existe."))
                continue

            if depth == 1:
                parent_id = None
                path = f"/{code}/"
            else:
                if not parent_code:
                    errors.append(NodeImportRowError(row=row_num, code=code, message=f"El nodo de nivel {depth} requiere parent_code."))
                    continue
                parent = nodes_by_code.get(parent_code)
                if not parent:
                    errors.append(NodeImportRowError(row=row_num, code=code, message=f"El nodo padre '{parent_code}' no existe o no fue procesado aún."))
                    continue
                if parent.depth != depth - 1:
                    errors.append(NodeImportRowError(row=row_num, code=code, message=f"El nodo padre '{parent_code}' tiene nivel {parent.depth}, se esperaba {depth - 1}."))
                    continue
                parent_id = parent.id
                path = f"{parent.path}{code}/"

            node = UnitNode(
                group_id=group_id,
                level_id=level.id,
                parent_id=parent_id,
                name=name,
                code=code,
                path=path,
                depth=depth,
            )
            db.add(node)
            await db.flush()

            nodes_by_code[code] = node
            created_nodes += 1
            await StructureService.sync_constituencies_for_node(db, node)

        await db.commit()
        return NodeImportResult(
            total_rows=len(raw_rows),
            created_nodes=created_nodes,
            errors=errors,
        )

    # -------------------------------------------------------------------------
    # Filtros Dinámicos (FilterDefinition)
    # -------------------------------------------------------------------------

    @staticmethod
    async def create_filter(
        db: AsyncSession, group_id: uuid.UUID, payload: FilterDefinitionCreate
    ) -> FilterDefinitionResponse:
        group, _ = await require_group_draft(db, group_id)

        key_clean = payload.key.strip().lower()
        stmt_dup = select(FilterDefinition).where(
            FilterDefinition.group_id == group_id, func.lower(FilterDefinition.key) == key_clean
        )
        if (await db.execute(stmt_dup)).scalar_one_or_none():
            raise UnprocessableEntityException(f"Ya existe un filtro con la clave '{key_clean}' en este grupo.")

        filter_def = FilterDefinition(
            group_id=group_id,
            key=key_clean,
            label=payload.label.strip(),
            allowed_values=payload.allowed_values,
            is_required=payload.is_required,
        )
        db.add(filter_def)
        await db.commit()
        await db.refresh(filter_def)
        return FilterDefinitionResponse.model_validate(filter_def)

    @staticmethod
    async def list_filters(db: AsyncSession, group_id: uuid.UUID) -> list[FilterDefinitionResponse]:
        stmt = select(FilterDefinition).where(FilterDefinition.group_id == group_id).order_by(FilterDefinition.key.asc())
        filters = (await db.execute(stmt)).scalars().all()
        return [FilterDefinitionResponse.model_validate(f) for f in filters]

    @staticmethod
    async def delete_filter(db: AsyncSession, filter_id: uuid.UUID) -> None:
        stmt = select(FilterDefinition).where(FilterDefinition.id == filter_id)
        filter_def = (await db.execute(stmt)).scalar_one_or_none()
        if not filter_def:
            raise NotFoundException("Filtro no encontrado.")

        await require_group_draft(db, filter_def.group_id)
        await db.delete(filter_def)
        await db.commit()

    # -------------------------------------------------------------------------
    # Cargos, Desgloses y Circunscripciones (Contest, Breakdown, Constituency)
    # -------------------------------------------------------------------------

    @staticmethod
    async def create_contest(
        db: AsyncSession, group_id: uuid.UUID, payload: ContestCreate
    ) -> ContestResponse:
        group, _ = await require_group_draft(db, group_id)

        # Validar scope_level_id
        stmt_lvl = select(HierarchyLevel).where(
            HierarchyLevel.id == payload.scope_level_id, HierarchyLevel.group_id == group_id
        )
        scope_level = (await db.execute(stmt_lvl)).scalar_one_or_none()
        if not scope_level:
            raise NotFoundException("Nivel de alcance no encontrado en este grupo.")

        name_clean = payload.name.strip()
        stmt_dup = select(Contest).where(
            Contest.group_id == group_id, func.lower(Contest.name) == name_clean.lower()
        )
        if (await db.execute(stmt_dup)).scalar_one_or_none():
            raise UnprocessableEntityException(f"Ya existe un cargo con el nombre '{name_clean}' en este grupo.")

        contest = Contest(
            group_id=group_id,
            name=name_clean,
            description=payload.description.strip() if payload.description else None,
            scope_level_id=scope_level.id,
            allow_blank=payload.allow_blank,
            allow_null=payload.allow_null,
            display_order=payload.display_order,
        )
        db.add(contest)
        await db.flush()

        # Algoritmo 3.1: Autogenerar Circunscripciones para todos los nodos en scope_level
        stmt_nodes = select(UnitNode).where(
            UnitNode.group_id == group_id, UnitNode.level_id == scope_level.id
        )
        nodes = (await db.execute(stmt_nodes)).scalars().all()
        for n in nodes:
            db.add(Constituency(contest_id=contest.id, node_id=n.id))

        # Configurar desgloses especificados o por defecto
        if payload.breakdowns:
            for b in payload.breakdowns:
                await StructureService.validate_and_add_breakdown(db, contest, b)
        else:
            # Crear desgloses por niveles con depth >= scope_level.depth
            stmt_all_levels = select(HierarchyLevel).where(
                HierarchyLevel.group_id == group_id, HierarchyLevel.depth >= scope_level.depth
            ).order_by(HierarchyLevel.depth.asc())
            deeper_levels = (await db.execute(stmt_all_levels)).scalars().all()
            for dl in deeper_levels:
                db.add(ContestBreakdown(
                    contest_id=contest.id,
                    kind=BreakdownKind.LEVEL,
                    level_id=dl.id,
                    filter_id=None,
                    label=f"Desglose por {dl.name}",
                ))

        await db.commit()
        await db.refresh(contest)
        return await StructureService.get_contest_response(db, contest.id)

    @staticmethod
    async def list_contests(db: AsyncSession, group_id: uuid.UUID) -> list[ContestResponse]:
        stmt = (
            select(Contest)
            .where(Contest.group_id == group_id)
            .options(
                selectinload(Contest.scope_level),
                selectinload(Contest.breakdowns),
                selectinload(Contest.constituencies),
            )
            .order_by(Contest.display_order.asc(), Contest.name.asc())
        )
        contests = (await db.execute(stmt)).scalars().all()

        return [
            ContestResponse(
                id=c.id,
                group_id=c.group_id,
                name=c.name,
                description=c.description,
                scope_level_id=c.scope_level_id,
                scope_level_name=c.scope_level.name if c.scope_level else None,
                scope_level_depth=c.scope_level.depth if c.scope_level else None,
                allow_blank=c.allow_blank,
                allow_null=c.allow_null,
                display_order=c.display_order,
                constituencies_count=len(c.constituencies),
                breakdowns=[
                    ContestBreakdownResponse(
                        id=b.id,
                        contest_id=b.contest_id,
                        kind=b.kind,
                        level_id=b.level_id,
                        filter_id=b.filter_id,
                        label=b.label,
                    )
                    for b in c.breakdowns
                ],
            )
            for c in contests
        ]

    @staticmethod
    async def update_contest(db: AsyncSession, contest_id: uuid.UUID, payload: ContestUpdate) -> ContestResponse:
        stmt = select(Contest).where(Contest.id == contest_id)
        contest = (await db.execute(stmt)).scalar_one_or_none()
        if not contest:
            raise NotFoundException("Cargo no encontrado.")

        await require_group_draft(db, contest.group_id)

        if payload.name:
            contest.name = payload.name.strip()
        if payload.description is not None:
            contest.description = payload.description.strip() if payload.description else None
        if payload.allow_blank is not None:
            contest.allow_blank = payload.allow_blank
        if payload.allow_null is not None:
            contest.allow_null = payload.allow_null
        if payload.display_order is not None:
            contest.display_order = payload.display_order

        if payload.scope_level_id and payload.scope_level_id != contest.scope_level_id:
            # Validar nuevo nivel
            stmt_lvl = select(HierarchyLevel).where(
                HierarchyLevel.id == payload.scope_level_id, HierarchyLevel.group_id == contest.group_id
            )
            new_level = (await db.execute(stmt_lvl)).scalar_one_or_none()
            if not new_level:
                raise NotFoundException("Nuevo nivel de alcance no encontrado.")

            contest.scope_level_id = new_level.id

            # Re-sincronizar circunscripciones: eliminar existentes y crear para los nodos del nuevo nivel
            await db.execute(delete(Constituency).where(Constituency.contest_id == contest.id))
            stmt_nodes = select(UnitNode).where(
                UnitNode.group_id == contest.group_id, UnitNode.level_id == new_level.id
            )
            nodes = (await db.execute(stmt_nodes)).scalars().all()
            for n in nodes:
                db.add(Constituency(contest_id=contest.id, node_id=n.id))

        await db.commit()
        await db.refresh(contest)
        return await StructureService.get_contest_response(db, contest.id)

    @staticmethod
    async def delete_contest(db: AsyncSession, contest_id: uuid.UUID) -> None:
        stmt = select(Contest).where(Contest.id == contest_id)
        contest = (await db.execute(stmt)).scalar_one_or_none()
        if not contest:
            raise NotFoundException("Cargo no encontrado.")

        await require_group_draft(db, contest.group_id)
        await db.delete(contest)
        await db.commit()

    @staticmethod
    async def update_breakdowns(
        db: AsyncSession, contest_id: uuid.UUID, breakdowns: list[ContestBreakdownConfig]
    ) -> list[ContestBreakdownResponse]:
        stmt = select(Contest).where(Contest.id == contest_id)
        contest = (await db.execute(stmt)).scalar_one_or_none()
        if not contest:
            raise NotFoundException("Cargo no encontrado.")

        await require_group_draft(db, contest.group_id)

        # Eliminar desgloses anteriores
        await db.execute(delete(ContestBreakdown).where(ContestBreakdown.contest_id == contest_id))

        new_breakdowns = []
        for b in breakdowns:
            cb = await StructureService.validate_and_add_breakdown(db, contest, b)
            new_breakdowns.append(cb)

        await db.commit()
        return [
            ContestBreakdownResponse(
                id=b.id,
                contest_id=b.contest_id,
                kind=b.kind,
                level_id=b.level_id,
                filter_id=b.filter_id,
                label=b.label,
            )
            for b in new_breakdowns
        ]

    @staticmethod
    async def validate_and_add_breakdown(
        db: AsyncSession, contest: Contest, b: ContestBreakdownConfig
    ) -> ContestBreakdown:
        if b.kind == BreakdownKind.LEVEL:
            if not b.level_id:
                raise UnprocessableEntityException("Un desglose de tipo LEVEL requiere 'level_id'.")
            stmt_lvl = select(HierarchyLevel).where(
                HierarchyLevel.id == b.level_id, HierarchyLevel.group_id == contest.group_id
            )
            target_level = (await db.execute(stmt_lvl)).scalar_one_or_none()
            if not target_level:
                raise NotFoundException(f"Nivel {b.level_id} no encontrado en este grupo.")

            # Obtener nivel del contest
            stmt_scope = select(HierarchyLevel).where(HierarchyLevel.id == contest.scope_level_id)
            scope_level = (await db.execute(stmt_scope)).scalar_one()

            if target_level.depth < scope_level.depth:
                raise UnprocessableEntityException(
                    f"El nivel de desglose '{target_level.name}' (profundidad {target_level.depth}) no puede ser más general que el nivel de alcance del cargo '{scope_level.name}' (profundidad {scope_level.depth})."
                )

            cb = ContestBreakdown(
                contest_id=contest.id,
                kind=BreakdownKind.LEVEL,
                level_id=target_level.id,
                filter_id=None,
                label=b.label.strip(),
            )
        else:
            if not b.filter_id:
                raise UnprocessableEntityException("Un desglose de tipo FILTER requiere 'filter_id'.")
            stmt_flt = select(FilterDefinition).where(
                FilterDefinition.id == b.filter_id, FilterDefinition.group_id == contest.group_id
            )
            target_filter = (await db.execute(stmt_flt)).scalar_one_or_none()
            if not target_filter:
                raise NotFoundException(f"Filtro {b.filter_id} no encontrado en este grupo.")

            cb = ContestBreakdown(
                contest_id=contest.id,
                kind=BreakdownKind.FILTER,
                level_id=None,
                filter_id=target_filter.id,
                label=b.label.strip(),
            )

        db.add(cb)
        await db.flush()
        return cb

    @staticmethod
    async def list_constituencies(db: AsyncSession, contest_id: uuid.UUID) -> list[ConstituencyBrief]:
        stmt = (
            select(Constituency)
            .where(Constituency.contest_id == contest_id)
            .options(
                selectinload(Constituency.node),
                selectinload(Constituency.candidates),
            )
        )
        constituencies = (await db.execute(stmt)).scalars().all()
        # Ordenar por path del nodo
        constituencies.sort(key=lambda c: c.node.path if c.node else "")

        result = []
        for c in constituencies:
            cands = sorted(c.candidates, key=lambda cd: cd.ballot_order)
            result.append(
                ConstituencyBrief(
                    id=c.id,
                    contest_id=c.contest_id,
                    node_id=c.node_id,
                    node_name=c.node.name if c.node else "Nodo desconocido",
                    node_code=c.node.code if c.node else "N/A",
                    node_path=c.node.path if c.node else "",
                    candidates=[
                        CandidateBrief(
                            id=cd.id,
                            name=cd.name,
                            party_or_front=cd.party_or_front,
                            photo_url=cd.photo_url,
                            ballot_order=cd.ballot_order,
                        )
                        for cd in cands
                    ],
                )
            )
        return result

    @staticmethod
    async def sync_constituencies_for_node(db: AsyncSession, node: UnitNode) -> None:
        """
        Sincroniza de forma idempotente las circunscripciones cuando se añade un nodo
        a un nivel que es el scope_level de algún cargo en el mismo grupo.
        """
        stmt_contests = select(Contest).where(
            Contest.group_id == node.group_id, Contest.scope_level_id == node.level_id
        )
        contests = (await db.execute(stmt_contests)).scalars().all()
        for c in contests:
            stmt_const = select(Constituency).where(
                Constituency.contest_id == c.id, Constituency.node_id == node.id
            )
            existing = (await db.execute(stmt_const)).scalar_one_or_none()
            if not existing:
                db.add(Constituency(contest_id=c.id, node_id=node.id))

    @staticmethod
    async def get_contest_response(db: AsyncSession, contest_id: uuid.UUID) -> ContestResponse:
        stmt = (
            select(Contest)
            .where(Contest.id == contest_id)
            .options(
                selectinload(Contest.scope_level),
                selectinload(Contest.breakdowns),
                selectinload(Contest.constituencies),
            )
        )
        contest = (await db.execute(stmt)).scalar_one()
        return ContestResponse(
            id=contest.id,
            group_id=contest.group_id,
            name=contest.name,
            description=contest.description,
            scope_level_id=contest.scope_level_id,
            scope_level_name=contest.scope_level.name if contest.scope_level else None,
            scope_level_depth=contest.scope_level.depth if contest.scope_level else None,
            allow_blank=contest.allow_blank,
            allow_null=contest.allow_null,
            display_order=contest.display_order,
            constituencies_count=len(contest.constituencies),
            breakdowns=[
                ContestBreakdownResponse(
                    id=b.id,
                    contest_id=b.contest_id,
                    kind=b.kind,
                    level_id=b.level_id,
                    filter_id=b.filter_id,
                    label=b.label,
                )
                for b in contest.breakdowns
            ],
        )
