"""
Router API para Candidatos y Papeleta (S1-05)
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
from app.modules.candidates.schemas import (
    CandidateCreate,
    CandidateReorderRequest,
    CandidateResponse,
    CandidateUpdate,
    PhotoUploadResponse,
)
from app.modules.candidates.service import CandidateService

router = APIRouter(tags=["Candidatos y Papeleta"])


@router.post("/constituencies/{constituency_id}/candidates", response_model=CandidateResponse, status_code=status.HTTP_201_CREATED)
async def create_candidate(
    constituency_id: uuid.UUID,
    payload: CandidateCreate,
    tenant: Annotated[TenantContext, Depends(require_admin_general)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
):
    """Registra un candidato en una circunscripción electoral (solo en DRAFT)."""
    return await CandidateService.create_candidate(db=db, constituency_id=constituency_id, payload=payload)


@router.get("/constituencies/{constituency_id}/candidates", response_model=list[CandidateResponse])
async def list_candidates(
    constituency_id: uuid.UUID,
    tenant: Annotated[TenantContext, Depends(get_tenant_context)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
):
    """Lista todos los candidatos de una circunscripción ordenados por su posición en la papeleta."""
    return await CandidateService.list_candidates(db=db, constituency_id=constituency_id)


@router.put("/candidates/{candidate_id}", response_model=CandidateResponse)
async def update_candidate(
    candidate_id: uuid.UUID,
    payload: CandidateUpdate,
    tenant: Annotated[TenantContext, Depends(require_admin_general)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
):
    """Actualiza datos de un candidato (nombre, sigla, foto o posición en papeleta)."""
    return await CandidateService.update_candidate(db=db, candidate_id=candidate_id, payload=payload)


@router.delete("/candidates/{candidate_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_candidate(
    candidate_id: uuid.UUID,
    tenant: Annotated[TenantContext, Depends(require_admin_general)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
):
    """Elimina un candidato de su circunscripción (solo en DRAFT)."""
    await CandidateService.delete_candidate(db=db, candidate_id=candidate_id)


@router.put("/constituencies/{constituency_id}/candidates/reorder", response_model=list[CandidateResponse])
async def reorder_candidates(
    constituency_id: uuid.UUID,
    payload: CandidateReorderRequest,
    tenant: Annotated[TenantContext, Depends(require_admin_general)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
):
    """Reordena atómicamente la posición de los candidatos en la papeleta de la circunscripción."""
    return await CandidateService.reorder_candidates(db=db, constituency_id=constituency_id, payload=payload)


@router.post("/candidates/upload-photo", response_model=PhotoUploadResponse)
async def upload_candidate_photo(
    file: UploadFile = File(...),
    tenant: Annotated[TenantContext, Depends(require_admin_general)] = None,
):
    """Valida la fotografía del candidato (JPEG/PNG/WEBP <= 2MB) y retorna su Data URI seguro."""
    content = await file.read()
    photo_url = CandidateService.validate_and_process_photo(content, file.filename or "photo.jpg")
    return PhotoUploadResponse(photo_url=photo_url)
