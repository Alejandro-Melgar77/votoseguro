"""
Router API para Estructura Electoral: Grupos, Jerarquías, Nodos, Filtros, Cargos y Circunscripciones (S1-03, S1-04)
"""
import uuid
from typing import Annotated
from fastapi import APIRouter, Depends, File, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import (
    TenantContext,
    get_tenant_context,
    require_admin_general,
)
from app.db.session import get_db_session
from app.modules.structure.schemas import (
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
    UnitNodeCreate,
    UnitNodeResponse,
    UnitNodeTreeNode,
    UnitNodeUpdate,
    VoterGroupCreate,
    VoterGroupResponse,
    VoterGroupUpdate,
    VoterGroupVotingWindowUpdate,
)
from app.modules.structure.service import StructureService

router = APIRouter(tags=["Estructura Electoral y Jerarquías"])


# =============================================================================
# Grupos de Votantes (VoterGroup)
# =============================================================================

@router.post("/elections/{election_id}/groups", response_model=VoterGroupResponse, status_code=status.HTTP_201_CREATED)
async def create_voter_group(
    election_id: uuid.UUID,
    payload: VoterGroupCreate,
    tenant: Annotated[TenantContext, Depends(require_admin_general)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
):
    """Crea un grupo de votantes dentro de una elección en borrador (DRAFT)."""
    return await StructureService.create_group(
        db=db,
        election_id=election_id,
        payload=payload,
        organization_id=tenant.organization_id,
    )


@router.get("/elections/{election_id}/groups", response_model=list[VoterGroupResponse])
async def list_voter_groups(
    election_id: uuid.UUID,
    tenant: Annotated[TenantContext, Depends(get_tenant_context)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
):
    """Lista todos los grupos de votantes configurados para una elección."""
    return await StructureService.list_groups(
        db=db, election_id=election_id, organization_id=tenant.organization_id
    )


@router.put("/groups/{group_id}", response_model=VoterGroupResponse)
async def update_voter_group(
    group_id: uuid.UUID,
    payload: VoterGroupUpdate,
    tenant: Annotated[TenantContext, Depends(require_admin_general)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
):
    """Actualiza datos básicos de un grupo de votantes (solo en DRAFT)."""
    return await StructureService.update_group(db=db, group_id=group_id, payload=payload)


@router.delete("/groups/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_voter_group(
    group_id: uuid.UUID,
    tenant: Annotated[TenantContext, Depends(require_admin_general)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
):
    """Elimina un grupo de votantes y todos sus niveles, nodos y cargos (solo en DRAFT)."""
    await StructureService.delete_group(db=db, group_id=group_id)


@router.put("/groups/{group_id}/voting-window", response_model=VoterGroupResponse)
async def update_group_voting_window(
    group_id: uuid.UUID,
    payload: VoterGroupVotingWindowUpdate,
    tenant: Annotated[TenantContext, Depends(require_admin_general)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
):
    """Configura o anula la ventana de votación propia opcional para un grupo (RF-19)."""
    return await StructureService.update_group_voting_window(db=db, group_id=group_id, payload=payload)


# =============================================================================
# Niveles Jerárquicos (HierarchyLevel)
# =============================================================================

@router.post("/groups/{group_id}/levels", response_model=HierarchyLevelResponse, status_code=status.HTTP_201_CREATED)
async def create_hierarchy_level(
    group_id: uuid.UUID,
    payload: HierarchyLevelCreate,
    tenant: Annotated[TenantContext, Depends(require_admin_general)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
):
    """Añade un nuevo nivel jerárquico al grupo con depth = max_depth + 1 (solo en DRAFT)."""
    return await StructureService.create_level(db=db, group_id=group_id, payload=payload)


@router.get("/groups/{group_id}/levels", response_model=list[HierarchyLevelResponse])
async def list_hierarchy_levels(
    group_id: uuid.UUID,
    tenant: Annotated[TenantContext, Depends(get_tenant_context)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
):
    """Lista los niveles jerárquicos de un grupo ordenados por profundidad (depth ASC)."""
    return await StructureService.list_levels(db=db, group_id=group_id)


@router.delete("/levels/{level_id}", status_code=status.HTTP_204_NO_CONTENT)
@router.delete("/groups/{group_id}/levels/{level_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_hierarchy_level(
    level_id: uuid.UUID,
    tenant: Annotated[TenantContext, Depends(require_admin_general)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    group_id: uuid.UUID | None = None,
):
    """Elimina el nivel de mayor profundidad si no contiene nodos ni cargos (solo en DRAFT)."""
    await StructureService.delete_level(db=db, level_id=level_id)


# =============================================================================
# Nodos Jerárquicos y Ruta Materializada (UnitNode)
# =============================================================================

@router.post("/groups/{group_id}/nodes", response_model=UnitNodeResponse, status_code=status.HTTP_201_CREATED)
async def create_unit_node(
    group_id: uuid.UUID,
    payload: UnitNodeCreate,
    tenant: Annotated[TenantContext, Depends(require_admin_general)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
):
    """Crea un nodo en el árbol jerárquico calculando su ruta materializada (path) y sincronizando circunscripciones."""
    return await StructureService.create_node(db=db, group_id=group_id, payload=payload)


@router.get("/groups/{group_id}/nodes/tree", response_model=list[UnitNodeTreeNode])
async def get_nodes_tree(
    group_id: uuid.UUID,
    tenant: Annotated[TenantContext, Depends(get_tenant_context)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
):
    """Retorna el árbol jerárquico completo estructurado con nodos raíz y sus hijos (children)."""
    return await StructureService.get_nodes_tree(db=db, group_id=group_id)


@router.patch("/nodes/{node_id}", response_model=UnitNodeResponse)
async def update_unit_node(
    node_id: uuid.UUID,
    payload: UnitNodeUpdate,
    tenant: Annotated[TenantContext, Depends(require_admin_general)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
):
    """Actualiza nombre o código de un nodo, propagando el cambio de path a sus descendientes."""
    return await StructureService.update_node(db=db, node_id=node_id, payload=payload)


@router.delete("/nodes/{node_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_unit_node(
    node_id: uuid.UUID,
    tenant: Annotated[TenantContext, Depends(require_admin_general)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
):
    """Elimina un nodo unitario si no contiene descendientes ni circunscripciones activas."""
    await StructureService.delete_node(db=db, node_id=node_id)


@router.post("/groups/{group_id}/nodes/import", response_model=NodeImportResult)
async def import_nodes_csv(
    group_id: uuid.UUID,
    file: UploadFile = File(...),
    tenant: Annotated[TenantContext, Depends(require_admin_general)] = None,
    db: Annotated[AsyncSession, Depends(get_db_session)] = None,
):
    """Importa masivamente nodos desde un archivo CSV con orden topológico y sincronización de circunscripciones."""
    content_bytes = await file.read()
    csv_text = content_bytes.decode("utf-8-sig", errors="replace")
    return await StructureService.import_nodes_csv(db=db, group_id=group_id, csv_content=csv_text)


# =============================================================================
# Filtros Dinámicos (FilterDefinition)
# =============================================================================

@router.post("/groups/{group_id}/filters", response_model=FilterDefinitionResponse, status_code=status.HTTP_201_CREATED)
async def create_filter_definition(
    group_id: uuid.UUID,
    payload: FilterDefinitionCreate,
    tenant: Annotated[TenantContext, Depends(require_admin_general)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
):
    """Define un atributo adicional/filtro dinámico para los votantes del grupo."""
    return await StructureService.create_filter(db=db, group_id=group_id, payload=payload)


@router.get("/groups/{group_id}/filters", response_model=list[FilterDefinitionResponse])
async def list_filter_definitions(
    group_id: uuid.UUID,
    tenant: Annotated[TenantContext, Depends(get_tenant_context)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
):
    """Lista los filtros dinámicos configurados para un grupo."""
    return await StructureService.list_filters(db=db, group_id=group_id)


@router.delete("/filters/{filter_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_filter_definition(
    filter_id: uuid.UUID,
    tenant: Annotated[TenantContext, Depends(require_admin_general)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
):
    """Elimina una definición de filtro dinámico del grupo (solo en DRAFT)."""
    await StructureService.delete_filter(db=db, filter_id=filter_id)


# =============================================================================
# Cargos (Contests), Desgloses y Circunscripciones (Constituencies)
# =============================================================================

@router.post("/groups/{group_id}/contests", response_model=ContestResponse, status_code=status.HTTP_201_CREATED)
async def create_contest(
    group_id: uuid.UUID,
    payload: ContestCreate,
    tenant: Annotated[TenantContext, Depends(require_admin_general)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
):
    """Crea un cargo en disputa autogenerando inmediatamente las circunscripciones para su nivel de alcance."""
    return await StructureService.create_contest(db=db, group_id=group_id, payload=payload)


@router.get("/groups/{group_id}/contests", response_model=list[ContestResponse])
async def list_contests(
    group_id: uuid.UUID,
    tenant: Annotated[TenantContext, Depends(get_tenant_context)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
):
    """Lista todos los cargos configurados para el grupo de votantes."""
    return await StructureService.list_contests(db=db, group_id=group_id)


@router.put("/contests/{contest_id}", response_model=ContestResponse)
async def update_contest(
    contest_id: uuid.UUID,
    payload: ContestUpdate,
    tenant: Annotated[TenantContext, Depends(require_admin_general)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
):
    """Actualiza la configuración de un cargo (solo en DRAFT)."""
    return await StructureService.update_contest(db=db, contest_id=contest_id, payload=payload)


@router.delete("/contests/{contest_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_contest(
    contest_id: uuid.UUID,
    tenant: Annotated[TenantContext, Depends(require_admin_general)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
):
    """Elimina un cargo y sus circunscripciones y candidatos asociados (solo en DRAFT)."""
    await StructureService.delete_contest(db=db, contest_id=contest_id)


@router.put("/contests/{contest_id}/breakdowns", response_model=list[ContestBreakdownResponse])
async def update_contest_breakdowns(
    contest_id: uuid.UUID,
    breakdowns: list[ContestBreakdownConfig],
    tenant: Annotated[TenantContext, Depends(require_admin_general)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
):
    """Configura los desgloses de resultados habilitados para un cargo."""
    return await StructureService.update_breakdowns(db=db, contest_id=contest_id, breakdowns=breakdowns)


@router.get("/contests/{contest_id}/constituencies", response_model=list[ConstituencyBrief])
async def list_contest_constituencies(
    contest_id: uuid.UUID,
    tenant: Annotated[TenantContext, Depends(get_tenant_context)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
):
    """Retorna todas las circunscripciones autogeneradas para un cargo con sus candidatos."""
    return await StructureService.list_constituencies(db=db, contest_id=contest_id)
