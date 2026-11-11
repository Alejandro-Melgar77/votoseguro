"""
Rutas API de Integridad Criptográfica, Cadenas de Hashes y Árbol de Merkle (S2-02, S2-05, S2-07)
"""
import uuid
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_roles
from app.db.models.user import UserRole
from app.db.session import get_db_session
from app.modules.integrity.schemas import (
    AuditChainIntegrityResponse,
    MerkleInclusionProofResponse,
    MerkleVerifyRequest,
    MerkleVerifyResponse,
    VoteChainIntegrityResponse,
)
from app.modules.integrity.service import IntegrityService
from app.crypto.paillier_spike import PaillierTallySpikeEngine

router = APIRouter(prefix="", tags=["Integridad Criptográfica"])


@router.get(
    "/elections/{election_id}/integrity/votes",
    response_model=VoteChainIntegrityResponse,
    summary="Auditoría y Verificación de la Cadena de Hashes de Votos (S2-02)",
)
async def verify_votes_chain(
    election_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    tenant=Depends(require_roles(UserRole.PLATFORM_ADMIN, UserRole.ADMIN_GENERAL, UserRole.ADMIN_SEGMENT, UserRole.OBSERVER)),
):
    """
    S2-02: Verifica secuencialmente todos los bloques de voto en la urna de la elección.
    Detecta de inmediato cualquier alteración o manipulación manual en SQL.
    """
    return await IntegrityService.verify_vote_chain(db, election_id)


@router.get(
    "/elections/{election_id}/integrity/audit",
    response_model=AuditChainIntegrityResponse,
    summary="Auditoría y Verificación de la Cadena de Bitácora Inmutable (S2-05)",
)
async def verify_audit_chain(
    election_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    tenant=Depends(require_roles(UserRole.PLATFORM_ADMIN, UserRole.ADMIN_GENERAL, UserRole.ADMIN_SEGMENT, UserRole.OBSERVER)),
):
    """
    S2-05: Verifica la cadena inmutable de la bitácora de auditoría asociada a la elección.
    """
    return await IntegrityService.verify_audit_chain(db, election_id)


@router.get(
    "/elections/{election_id}/merkle/proof/{document_id}",
    response_model=MerkleInclusionProofResponse,
    summary="Obtener Prueba Criptográfica de Inclusión en Árbol de Merkle (S2-07)",
)
async def get_merkle_inclusion_proof(
    election_id: uuid.UUID,
    document_id: str,
    db: AsyncSession = Depends(get_db_session),
):
    """
    S2-07: Endpoint público que permite a cualquier votante obtener su prueba criptográfica
    de inclusión en el padrón electoral congelado sin revelar la identidad de los demás electores.
    """
    return await IntegrityService.get_voter_merkle_proof(db, election_id, document_id)


@router.post(
    "/elections/{election_id}/merkle/verify",
    response_model=MerkleVerifyResponse,
    summary="Verificar Matemáticamente Prueba de Inclusión en Árbol de Merkle (S2-07)",
)
async def verify_merkle_proof_endpoint(
    election_id: uuid.UUID,
    payload: MerkleVerifyRequest,
):
    """
    S2-07: Endpoint público para verificar matemáticamente que una prueba de inclusión
    reconstruye fielmente la raíz del padrón electoral congelado (merkle_root).
    """
    return IntegrityService.verify_merkle_proof(
        leaf_hash=payload.leaf_hash,
        merkle_root=payload.merkle_root,
        proof=payload.proof,
    )


@router.post(
    "/crypto/paillier-spike-benchmark",
    summary="Laboratorio de Cifrado Homomórfico Paillier (Spike Obligatorio Sprint 2)",
)
@router.post(
    "/elections/{election_id}/crypto/paillier-spike-benchmark",
    summary="Laboratorio de Cifrado Homomórfico Paillier por Elección (Spike Obligatorio Sprint 2)",
)
async def run_paillier_spike_benchmark(
    election_id: uuid.UUID | None = None,
    key_size: int = 1024,
    num_votes: int = 12,
    db: AsyncSession = Depends(get_db_session),
    tenant=Depends(require_roles(UserRole.PLATFORM_ADMIN, UserRole.ADMIN_GENERAL)),
):
    """
    Ejecuta en vivo la prueba de concepto matemática de cifrado homomórfico Paillier (phe)
    con suma agrupada por circunscripción y rutas jerárquicas (segment_path).
    """
    engine = PaillierTallySpikeEngine(key_size=key_size)

    # Configuración de circunscripciones de prueba simuladas
    demo_constituencies = [
        {
            "id": "const-rectorado",
            "name": "Rectorado Universitario",
            "options_count": 4,  # Cand A, Cand B, Blanco, Nulo
            "sample_paths": ["/UAGRM/FICCT/INF/", "/UAGRM/FICCT/CIV/", "/UAGRM/FCA/AGR/"],
        },
        {
            "id": "const-decanato-ficct",
            "name": "Decanato FICCT",
            "options_count": 3,  # Cand 1, Blanco, Nulo
            "sample_paths": ["/UAGRM/FICCT/INF/", "/UAGRM/FICCT/CIV/"],
        },
    ]

    benchmark_result = engine.run_benchmark_simulation(
        constituencies_info=demo_constituencies,
        num_simulated_votes=num_votes,
    )
    if election_id:
        benchmark_result["election_id"] = str(election_id)
    return benchmark_result
