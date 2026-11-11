"""
Servicio Criptográfico de Auditoría e Integridad Electoral (S2-02, S2-05, S2-07)
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import NotFoundException, UnprocessableEntityException
from app.core.time import ensure_utc
from app.crypto.hashing import canonical_json, sha256_hex
from app.crypto.merkle import MerkleTree, compute_voter_leaf_hash, verify_merkle_inclusion_proof
from app.db.models.audit import AuditLog
from app.db.models.election import Election
from app.db.models.voter import Voter, VoterStatus
from app.db.models.voting import Vote
from app.modules.integrity.schemas import (
    AuditChainIntegrityResponse,
    MerkleInclusionProofResponse,
    MerkleProofStep,
    MerkleVerifyResponse,
    VoteChainIntegrityResponse,
)


class IntegrityService:
    @staticmethod
    async def verify_vote_chain(
        db: AsyncSession,
        election_id: uuid.UUID,
    ) -> VoteChainIntegrityResponse:
        """
        S2-02: Recorre la cadena completa de sufragios en la tabla 'vote' de la elección
        y comprueba cada eslabón secuencialmente recalculando los hashes canónicos SHA-256.
        Detecta cualquier alteración manual en SQL (candidate_id, choice_type, payload, etc.).
        """
        election = await db.get(Election, election_id)
        if not election:
            raise NotFoundException(f"Elección con ID {election_id} no encontrada.")

        now_utc = datetime.now(timezone.utc)
        genesis_vote_hash = sha256_hex(f"VOTOSEGURO:VOTE_GENESIS:{election.id}:{election.config_hash or 'DRAFT'}")

        stmt = (
            select(Vote)
            .where(Vote.election_id == election_id)
            .order_by(Vote.chain_index.asc())
        )
        votes = (await db.execute(stmt)).scalars().all()

        total_blocks = len(votes)
        if total_blocks == 0:
            return VoteChainIntegrityResponse(
                valid=True,
                election_id=election_id,
                genesis_hash=genesis_vote_hash,
                head_hash=None,
                total_blocks=0,
                verified_blocks=0,
                broken_at_index=None,
                broken_vote_id=None,
                error_detail=None,
                checked_at=now_utc,
            )

        expected_prev_hash = genesis_vote_hash
        expected_index = 1
        verified_blocks = 0

        for v in votes:
            if v.chain_index != expected_index:
                return VoteChainIntegrityResponse(
                    valid=False,
                    election_id=election_id,
                    genesis_hash=genesis_vote_hash,
                    head_hash=expected_prev_hash,
                    total_blocks=total_blocks,
                    verified_blocks=verified_blocks,
                    broken_at_index=expected_index,
                    broken_vote_id=str(v.id),
                    error_detail=f"Discontinuidad en la secuencia de la cadena: se esperaba #{expected_index}, se encontró #{v.chain_index}.",
                    checked_at=now_utc,
                )

            if v.prev_hash != expected_prev_hash:
                return VoteChainIntegrityResponse(
                    valid=False,
                    election_id=election_id,
                    genesis_hash=genesis_vote_hash,
                    head_hash=expected_prev_hash,
                    total_blocks=total_blocks,
                    verified_blocks=verified_blocks,
                    broken_at_index=v.chain_index,
                    broken_vote_id=str(v.id),
                    error_detail=f"Eslabón roto en bloque #{v.chain_index}: el prev_hash registrado ({v.prev_hash[:16]}...) no coincide con el hash previo esperado ({expected_prev_hash[:16]}...).",
                    checked_at=now_utc,
                )

            # Recalcular hash canónico del bloque
            choice_val = v.choice_type.value if hasattr(v.choice_type, "value") else str(v.choice_type)
            expected_payload = {
                "chain_index": v.chain_index,
                "prev_hash": v.prev_hash,
                "election_id": str(v.election_id),
                "constituency_id": str(v.constituency_id),
                "choice_type": choice_val,
                "candidate_id": str(v.candidate_id) if v.candidate_id else None,
                "encoded_payload": v.encoded_payload,
                "segment_path": v.segment_path,
                "nullifier": v.nullifier,
                "receipt_hash": v.receipt_hash,
                "created_at_iso": ensure_utc(v.created_at).isoformat(),
            }
            computed_vote_hash = sha256_hex(canonical_json(expected_payload))

            if v.vote_hash != computed_vote_hash:
                return VoteChainIntegrityResponse(
                    valid=False,
                    election_id=election_id,
                    genesis_hash=genesis_vote_hash,
                    head_hash=expected_prev_hash,
                    total_blocks=total_blocks,
                    verified_blocks=verified_blocks,
                    broken_at_index=v.chain_index,
                    broken_vote_id=str(v.id),
                    error_detail=f"Alteración o adulteración de datos detectada en el voto #{v.chain_index}: el hash del bloque no corresponde a su contenido verificado.",
                    checked_at=now_utc,
                )

            expected_prev_hash = v.vote_hash
            expected_index += 1
            verified_blocks += 1

        return VoteChainIntegrityResponse(
            valid=True,
            election_id=election_id,
            genesis_hash=genesis_vote_hash,
            head_hash=expected_prev_hash,
            total_blocks=total_blocks,
            verified_blocks=verified_blocks,
            broken_at_index=None,
            broken_vote_id=None,
            error_detail=None,
            checked_at=now_utc,
        )

    @staticmethod
    async def verify_audit_chain(
        db: AsyncSession,
        election_id: uuid.UUID,
    ) -> AuditChainIntegrityResponse:
        """
        S2-05: Verifica la cadena inmutable de la bitácora de auditoría para la elección/organización.
        """
        election = await db.get(Election, election_id)
        if not election:
            raise NotFoundException(f"Elección con ID {election_id} no encontrada.")

        now_utc = datetime.now(timezone.utc)
        genesis_hash = sha256_hex(f"VOTOSEGURO:AUDIT_GENESIS:{election.organization_id or 'GLOBAL'}")

        stmt = (
            select(AuditLog)
            .where(
                (AuditLog.election_id == election_id)
                | (AuditLog.organization_id == election.organization_id)
            )
            .order_by(AuditLog.chain_index.asc())
        )
        entries = (await db.execute(stmt)).scalars().all()

        total_entries = len(entries)
        if total_entries == 0:
            return AuditChainIntegrityResponse(
                valid=True,
                organization_id=election.organization_id,
                election_id=election_id,
                genesis_hash=genesis_hash,
                head_hash=None,
                total_entries=0,
                verified_entries=0,
                broken_at_index=None,
                broken_entry_id=None,
                error_detail=None,
                checked_at=now_utc,
            )

        expected_prev_hash = entries[0].prev_hash or genesis_hash
        verified_count = 0

        for entry in entries:
            if entry.prev_hash and entry.prev_hash != expected_prev_hash and verified_count > 0:
                return AuditChainIntegrityResponse(
                    valid=False,
                    organization_id=election.organization_id,
                    election_id=election_id,
                    genesis_hash=genesis_hash,
                    head_hash=expected_prev_hash,
                    total_entries=total_entries,
                    verified_entries=verified_count,
                    broken_at_index=entry.chain_index,
                    broken_entry_id=entry.id,
                    error_detail=f"Discontinuidad en la cadena de auditoría en la entrada #{entry.chain_index}.",
                    checked_at=now_utc,
                )

            # Recalcular hash canónico
            entry_payload = {
                "chain_index": entry.chain_index,
                "prev_hash": entry.prev_hash,
                "organization_id": str(entry.organization_id) if entry.organization_id else None,
                "election_id": str(entry.election_id) if entry.election_id else None,
                "actor_id": str(entry.actor_id) if entry.actor_id else None,
                "actor_role": entry.actor_role,
                "action": entry.action,
                "entity_type": entry.entity_type,
                "entity_id": str(entry.entity_id),
                "payload": entry.payload or {},
                "created_at_iso": ensure_utc(entry.created_at).isoformat(),
            }
            computed_entry_hash = sha256_hex(canonical_json(entry_payload))

            if entry.entry_hash and entry.entry_hash != computed_entry_hash:
                return AuditChainIntegrityResponse(
                    valid=False,
                    organization_id=election.organization_id,
                    election_id=election_id,
                    genesis_hash=genesis_hash,
                    head_hash=expected_prev_hash,
                    total_entries=total_entries,
                    verified_entries=verified_count,
                    broken_at_index=entry.chain_index,
                    broken_entry_id=entry.id,
                    error_detail=f"Entrada de auditoría adulterada en #{entry.chain_index}.",
                    checked_at=now_utc,
                )

            expected_prev_hash = entry.entry_hash or computed_entry_hash
            verified_count += 1

        return AuditChainIntegrityResponse(
            valid=True,
            organization_id=election.organization_id,
            election_id=election_id,
            genesis_hash=genesis_hash,
            head_hash=expected_prev_hash,
            total_entries=total_entries,
            verified_entries=verified_count,
            broken_at_index=None,
            broken_entry_id=None,
            error_detail=None,
            checked_at=now_utc,
        )

    @staticmethod
    async def get_voter_merkle_proof(
        db: AsyncSession,
        election_id: uuid.UUID,
        document_id: str,
    ) -> MerkleInclusionProofResponse:
        """
        S2-07: Genera la prueba criptográfica de inclusión en el Árbol de Merkle del padrón
        para un votante en estado ACTIVE, sin revelar jamás los datos de los demás votantes.
        """
        election = await db.get(Election, election_id)
        if not election:
            raise NotFoundException(f"Elección con ID {election_id} no encontrada.")

        doc_clean = str(document_id).strip()

        # Buscar todos los votantes ACTIVE ordenados por document_id ASC
        stmt = (
            select(Voter)
            .options(selectinload(Voter.node), selectinload(Voter.group))
            .where(
                Voter.election_id == election_id,
                Voter.status == VoterStatus.ACTIVE,
            )
            .order_by(Voter.document_id.asc())
        )
        active_voters = (await db.execute(stmt)).scalars().all()

        target_index = -1
        target_voter = None
        leaves: list[str] = []

        for idx, v in enumerate(active_voters):
            leaf_h = compute_voter_leaf_hash(
                election_id=str(election_id),
                document_id=v.document_id,
                group_code=v.group.code if v.group else (v.group.name if v.group else ""),
                node_path=v.node.path if v.node else "",
                status="ACTIVE",
            )
            leaves.append(leaf_h)
            if v.document_id.strip() == doc_clean:
                target_index = idx
                target_voter = v

        if target_index == -1 or not target_voter:
            raise NotFoundException(
                f"El votante con documento '{doc_clean}' no se encuentra habilitado en el padrón activo de esta elección."
            )

        tree = MerkleTree(leaves, str(election_id))
        proof_steps = tree.get_inclusion_proof(target_index)

        steps_models = [
            MerkleProofStep(position=s["position"], sibling_hash=s["sibling_hash"])
            for s in proof_steps
        ]

        return MerkleInclusionProofResponse(
            election_id=election_id,
            document_id=doc_clean,
            leaf_hash=leaves[target_index],
            leaf_index=target_index,
            total_active_voters=len(active_voters),
            merkle_root=election.merkle_root or tree.root,
            proof=steps_models,
        )

    @staticmethod
    def verify_merkle_proof(
        leaf_hash: str,
        merkle_root: str,
        proof: list[MerkleProofStep],
    ) -> MerkleVerifyResponse:
        """
        S2-07: Verifica matemáticamente una prueba de inclusión recalculando la raíz paso a paso.
        """
        steps_dicts = [{"position": p.position, "sibling_hash": p.sibling_hash} for p in proof]
        valid = verify_merkle_inclusion_proof(leaf_hash, merkle_root, steps_dicts)

        # Computar la raíz obtenida
        curr = leaf_hash.strip().lower()
        for p in proof:
            pos = p.position
            sib = p.sibling_hash.strip().lower()
            try:
                curr_b = bytes.fromhex(curr)
                sib_b = bytes.fromhex(sib)
                if pos == "left":
                    curr = sha256_hex(b"\x01" + sib_b + curr_b)
                else:
                    curr = sha256_hex(b"\x01" + curr_b + sib_b)
            except Exception:
                curr = "INVALID_HASH"
                break

        return MerkleVerifyResponse(
            valid=valid,
            computed_root=curr,
            expected_root=merkle_root.strip().lower(),
        )
