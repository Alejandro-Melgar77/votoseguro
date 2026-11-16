"""
Rutas API para la Ceremonia Criptográfica de Claves y Escrutinio Homomórfico (S3-01 y S3-02)
Expone los endpoints de setup, unlock y status tanto en /shamir como en /crypto.
"""
import uuid
from typing import Annotated
from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import TenantContext, get_tenant_context, require_admin_general
from app.db.session import get_db_session
from app.modules.crypto_ceremony.schemas import (
    CeremonyStatusResponse,
    ShamirSetupRequest,
    ShamirSetupResponse,
    ShamirUnlockRequest,
    ShamirUnlockResponse,
)
from app.modules.crypto_ceremony.service import CryptoCeremonyService

router = APIRouter(prefix="/elections", tags=["Criptografía y Ceremonia de Claves"])


@router.post(
    "/{election_id}/shamir/setup",
    response_model=ShamirSetupResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Inicializar Ceremonia de Claves y Reparto Shamir (S3-02)",
)
@router.post(
    "/{election_id}/crypto/key-ceremony",
    response_model=ShamirSetupResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Alias: Ceremonia de Generación de Claves Paillier y Fragmentos",
)
async def setup_key_ceremony(
    election_id: uuid.UUID,
    payload: ShamirSetupRequest,
    tenant: Annotated[TenantContext, Depends(require_admin_general)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    request: Request,
):
    """
    Genera el par de claves Paillier de la elección, empaqueta la clave privada
    y la divide en n fragmentos institucionales mediante el esquema de Shamir (k de n).
    Registra los compromisos criptográficos en base de datos y destruye la clave privada en RAM.
    """
    client_ip = request.client.host if request.client else None
    return await CryptoCeremonyService.execute_key_ceremony(
        db=db,
        election_id=election_id,
        tenant=tenant,
        req=payload,
        client_ip=client_ip,
    )


@router.post(
    "/{election_id}/shamir/unlock",
    response_model=ShamirUnlockResponse,
    status_code=status.HTTP_200_OK,
    summary="Apertura Oficial del Escrutinio Homomórfico con Quórum Shamir (S3-01 y S3-02)",
)
@router.post(
    "/{election_id}/crypto/tally-decrypt",
    response_model=ShamirUnlockResponse,
    status_code=status.HTTP_200_OK,
    summary="Alias: Descifrado Homomórfico del Escrutinio por Quórum",
)
async def unlock_tally_ceremony(
    election_id: uuid.UUID,
    payload: ShamirUnlockRequest,
    tenant: Annotated[TenantContext, Depends(require_admin_general)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    request: Request,
):
    """
    Recibe los k fragmentos aportados por las autoridades electorales. Valida sus compromisos,
    reconstruye la clave privada en RAM mediante interpolación de Lagrange, descifra los acumuladores
    homomórficos agrupados por circunscripción y desglose (respetando k-anonimato), pasa la elección
    al estado final TALLIED y destruye la clave privada de la memoria.
    """
    client_ip = request.client.host if request.client else None
    return await CryptoCeremonyService.execute_tally_unlock(
        db=db,
        election_id=election_id,
        tenant=tenant,
        req=payload,
        client_ip=client_ip,
    )


@router.get(
    "/{election_id}/shamir/status",
    response_model=CeremonyStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Consultar Estado de la Ceremonia Criptográfica",
)
@router.get(
    "/{election_id}/crypto/ceremony-status",
    response_model=CeremonyStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Alias: Estado de Ceremonia y Parámetros Públicos",
)
async def get_ceremony_status(
    election_id: uuid.UUID,
    tenant: Annotated[TenantContext, Depends(get_tenant_context)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
):
    """
    Devuelve los parámetros públicos de la elección (módulo n de Paillier, umbral k de n,
    hashes de acta de ceremonia y listado de autoridades con estado de entrega de fragmentos).
    """
    return await CryptoCeremonyService.get_ceremony_status(
        db=db,
        election_id=election_id,
        tenant=tenant,
    )
