"""
Rutas API para el Portal Público de Auditoría (S3-03 - RF-57).
Endpoints públicos sin login para observadores electorales y ciudadanía.
"""
import uuid
from typing import List
from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rate_limit import limiter
from app.db.session import get_db_session
from app.modules.public_audit.schemas import (
    PublicAuditDossierResponse,
    PublicElectionSummary,
)
from app.modules.public_audit.service import PublicAuditService

router = APIRouter(prefix="/public/audit", tags=["Portal Público de Auditoría (S3-03)"])


@router.get(
    "/elections",
    response_model=List[PublicElectionSummary],
    status_code=status.HTTP_200_OK,
    summary="Listar Elecciones Públicas Publicadas (S3-03)",
)
@limiter.limit("60/minute")
async def list_public_elections(
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    """
    Lista las elecciones oficiales en curso o concluidas (excluyendo borradores).
    No requiere autenticación y expone sellos criptográficos esenciales.
    """
    return await PublicAuditService.list_public_elections(db=db)


@router.get(
    "/elections/{election_id}",
    response_model=PublicAuditDossierResponse,
    status_code=status.HTTP_200_OK,
    summary="Consultar Expediente Integral de Auditoría Pública (S3-03)",
)
@limiter.limit("45/minute")
async def get_public_audit_dossier(
    election_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    """
    Devuelve el expediente completo de auditoría:
    - Sellos criptográficos inmutables (config_hash, roll_hash, merkle_root, paillier_public_key).
    - Estado de verificación en vivo de la cadena de hashes de urna y de la bitácora de auditoría.
    - Historial completo e inmutable de cambios del cronograma electoral (schedule_change) con motivo oficial.
    - Resultados públicos únicamente tras el cierre, aplicando estrictamente k-anonimato.
    - Estricta omisión de datos personales (document_id, email, nombres) o votos individuales.
    """
    return await PublicAuditService.get_public_audit_dossier(
        db=db,
        election_id=election_id,
    )
