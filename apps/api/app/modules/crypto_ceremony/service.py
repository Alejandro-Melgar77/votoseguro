"""
S3-01 y S3-02: Servicio de Ceremonia Criptográfica de Claves y Escrutinio con Shamir
Gestiona la generación de pares de claves Paillier, la fragmentación de la clave privada
entre autoridades de la Corte Electoral mediante Shamir (k de n), la validación de compromisos
criptográficos y el descifrado oficial del escrutinio homomórfico acumulado.
"""
import hashlib
import json
import uuid
from datetime import datetime, timezone
import phe.paillier as paillier
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import TenantContext
from app.core.exceptions import (
    ConflictException,
    ForbiddenException,
    NotFoundException,
    UnprocessableEntityException,
)
from app.crypto.hashing import canonical_json, sha256_hex
from app.crypto.shamir import (
    DEFAULT_SHAMIR_PRIME,
    CorruptedShareException,
    InsufficientSharesException,
    InvalidShareCommitmentException,
    ShamirSecurityException,
    combine_shares,
    compute_share_commitment,
    format_share,
    pack_paillier_private_key,
    parse_share,
    split_secret,
    unpack_paillier_private_key,
)
from app.db.models.audit import AuditLog
from app.db.models.election import Election, ElectionStatus, ElectoralTrusteeShare
from app.modules.crypto_ceremony.schemas import (
    CeremonyStatusResponse,
    ShamirSetupRequest,
    ShamirSetupResponse,
    ShamirUnlockRequest,
    ShamirUnlockResponse,
    TrusteeConfig,
    TrusteeShareItem,
)
from app.modules.results.homomorphic_tally import HomomorphicTallyEngine


class CryptoCeremonyService:
    """
    Servicio de orquestación de la Ceremonia Criptográfica de VotoSeguro.
    """

    @staticmethod
    async def execute_key_ceremony(
        db: AsyncSession,
        election_id: uuid.UUID,
        tenant: TenantContext,
        req: ShamirSetupRequest,
        client_ip: str | None = None,
    ) -> ShamirSetupResponse:
        """
        Ejecuta la Ceremonia de Generación de Claves (S3-02):
        1. Genera el par asimétrico Paillier (public_key, private_key).
        2. Almacena paillier_public_n en la elección.
        3. Empaqueta la private_key (p, q) y la divide en n fragmentos con umbral k mediante Shamir.
        4. Registra los compromisos criptográficos en electoral_trustee_share.
        5. Destruye la private_key completa de la memoria RAM.
        """
        stmt = select(Election).where(
            Election.id == election_id,
            Election.organization_id == tenant.organization_id,
        )
        election = (await db.execute(stmt)).scalar_one_or_none()
        if not election:
            raise NotFoundException("Elección no encontrada en su institución.")

        if req.threshold_k < 2:
            raise UnprocessableEntityException("El umbral k debe ser mayor o igual a 2.")
        if req.total_n < req.threshold_k:
            raise UnprocessableEntityException(
                f"El número total de custodios n ({req.total_n}) debe ser mayor o igual al umbral k ({req.threshold_k})."
            )

        # Configurar custodios institucionales por defecto si no fueron especificados
        default_trustees_config = [
            TrusteeConfig(trustee_name="Vocal 1 - Presidencia Corte Electoral", trustee_email="vocal1.presidencia@corte.edu.bo"),
            TrusteeConfig(trustee_name="Vocal 2 - Vicepresidencia Corte Electoral", trustee_email="vocal2.vicepresidencia@corte.edu.bo"),
            TrusteeConfig(trustee_name="Vocal 3 - Secretaría de Cámara Electoral", trustee_email="vocal3.secretaria@corte.edu.bo"),
            TrusteeConfig(trustee_name="Vocal 4 - Delegado Docente Oficial", trustee_email="vocal4.docente@corte.edu.bo"),
            TrusteeConfig(trustee_name="Vocal 5 - Delegado Estudiantil Oficial", trustee_email="vocal5.estudiantil@corte.edu.bo"),
        ]

        trustees_to_assign = req.trustees or default_trustees_config[: req.total_n]
        while len(trustees_to_assign) < req.total_n:
            idx = len(trustees_to_assign) + 1
            trustees_to_assign.append(
                TrusteeConfig(
                    trustee_name=f"Vocal {idx} - Custodio Institucional",
                    trustee_email=f"vocal{idx}.custodio@corte.edu.bo",
                )
            )

        # 1. Generar par de claves Paillier
        key_size = req.key_size if req.key_size in (512, 1024, 2048) else 1024
        public_key, private_key = paillier.generate_paillier_keypair(n_length=key_size)

        # 2. Empaquetar clave privada en entero S
        secret_s = pack_paillier_private_key(private_key.p, private_key.q)

        # 3. Fragmentar mediante Shamir sobre cuerpo finito F_P
        shares = split_secret(secret_s, req.threshold_k, req.total_n)

        # Eliminar registros previos de custodios para esta elección si se reconfigura
        await db.execute(
            delete(ElectoralTrusteeShare).where(ElectoralTrusteeShare.election_id == election.id)
        )

        trustee_items: list[TrusteeShareItem] = []
        commitments_for_hash: list[dict[str, Any]] = []

        now_utc = datetime.now(timezone.utc)

        for idx, (x_val, y_val) in enumerate(shares, start=1):
            t_cfg = trustees_to_assign[idx - 1]
            token = format_share(x_val, req.threshold_k, req.total_n, y_val)
            commit = compute_share_commitment(election.id, x_val, y_val)

            trustee_record = ElectoralTrusteeShare(
                organization_id=election.organization_id,
                election_id=election.id,
                share_index=x_val,
                trustee_name=t_cfg.trustee_name,
                trustee_email=t_cfg.trustee_email,
                commitment_hash=commit,
                demo_share_token=token,
                submitted_for_tally=False,
                submitted_at=None,
                created_at=now_utc,
            )
            db.add(trustee_record)

            item = TrusteeShareItem(
                share_index=x_val,
                trustee_name=t_cfg.trustee_name,
                trustee_email=t_cfg.trustee_email,
                commitment_hash=commit,
                demo_share_token=token,
                submitted_for_tally=False,
                submitted_at=None,
            )
            trustee_items.append(item)
            commitments_for_hash.append({
                "share_index": x_val,
                "trustee_name": t_cfg.trustee_name,
                "commitment_hash": commit,
            })

        # Acta canónica y hash de la ceremonia
        act_payload = {
            "election_id": str(election.id),
            "organization_id": str(election.organization_id),
            "paillier_public_n": str(public_key.n),
            "paillier_key_size": key_size,
            "shamir_threshold_k": req.threshold_k,
            "shamir_total_n": req.total_n,
            "commitments": commitments_for_hash,
        }
        key_ceremony_hash = sha256_hex(canonical_json(act_payload))

        # Actualizar datos criptográficos en la elección
        election.encryption_scheme = "PAILLIER_HOMOMORPHIC"
        election.paillier_public_n = str(public_key.n)
        election.paillier_public_key = json.dumps({"n": str(public_key.n), "key_size": key_size})
        election.paillier_key_size = key_size
        election.shamir_threshold_k = req.threshold_k
        election.shamir_total_n = req.total_n
        election.shamir_prime_modulus = str(DEFAULT_SHAMIR_PRIME)
        election.key_ceremony_hash = key_ceremony_hash
        election.updated_at = now_utc

        # Registro en Bitácora Inmutable de Auditoría
        audit_entry = AuditLog(
            organization_id=election.organization_id,
            election_id=election.id,
            actor_id=tenant.user.id,
            actor_role=tenant.user.role.value,
            action="KEY_CEREMONY_COMPLETED",
            entity_type="election",
            entity_id=str(election.id),
            ip_address=client_ip,
            payload={
                "paillier_key_size": key_size,
                "threshold_k": req.threshold_k,
                "total_n": req.total_n,
                "key_ceremony_hash": key_ceremony_hash,
            },
        )
        db.add(audit_entry)

        # Destrucción física de las variables de clave privada en memoria RAM
        del private_key
        del secret_s

        await db.commit()
        await db.refresh(election)

        return ShamirSetupResponse(
            election_id=election.id,
            encryption_scheme=election.encryption_scheme,
            paillier_public_n=election.paillier_public_n,
            paillier_key_size=election.paillier_key_size,
            threshold_k=election.shamir_threshold_k,
            total_n=election.shamir_total_n,
            key_ceremony_hash=key_ceremony_hash,
            trustees=trustee_items,
        )

    @staticmethod
    async def get_ceremony_status(
        db: AsyncSession,
        election_id: uuid.UUID,
        tenant: TenantContext,
    ) -> CeremonyStatusResponse:
        """
        Consulta el estado de la Ceremonia Criptográfica, parámetros públicos
        y estado de recepción de fragmentos de los custodios.
        """
        stmt = select(Election).where(
            Election.id == election_id,
            Election.organization_id == tenant.organization_id,
        )
        election = (await db.execute(stmt)).scalar_one_or_none()
        if not election:
            raise NotFoundException("Elección no encontrada en su institución.")

        stmt_trustees = (
            select(ElectoralTrusteeShare)
            .where(ElectoralTrusteeShare.election_id == election.id)
            .order_by(ElectoralTrusteeShare.share_index.asc())
        )
        trustees = (await db.execute(stmt_trustees)).scalars().all()

        trustee_items = [
            TrusteeShareItem(
                share_index=t.share_index,
                trustee_name=t.trustee_name,
                trustee_email=t.trustee_email,
                commitment_hash=t.commitment_hash,
                demo_share_token=t.demo_share_token,
                submitted_for_tally=t.submitted_for_tally,
                submitted_at=t.submitted_at,
            )
            for t in trustees
        ]

        return CeremonyStatusResponse(
            election_id=election.id,
            encryption_scheme=election.encryption_scheme or "PAILLIER_HOMOMORPHIC",
            paillier_public_n=election.paillier_public_n,
            paillier_key_size=election.paillier_key_size,
            threshold_k=election.shamir_threshold_k,
            total_n=election.shamir_total_n,
            key_ceremony_completed=bool(election.key_ceremony_hash),
            key_ceremony_hash=election.key_ceremony_hash,
            tally_ceremony_completed=bool(election.tally_ceremony_hash),
            tally_ceremony_hash=election.tally_ceremony_hash,
            election_status=election.status.value,
            trustees=trustee_items,
        )

    @staticmethod
    async def execute_tally_unlock(
        db: AsyncSession,
        election_id: uuid.UUID,
        tenant: TenantContext,
        req: ShamirUnlockRequest,
        client_ip: str | None = None,
    ) -> ShamirUnlockResponse:
        """
        Apertura Oficial del Escrutinio Homomórfico (S3-01 + S3-02):
        1. Recibe los k fragmentos institucionales aportados por los vocales.
        2. Verifica que len(shares) >= k. Si no, rechaza con HTTP 422.
        3. Comprueba matemáticamente cada fragmento frente a su commitment_hash. Si falla, rechaza con HTTP 422.
        4. Reconstruye la clave privada Paillier en memoria RAM mediante interpolación de Lagrange.
        5. Descifra ÚNICAMENTE los acumuladores de homomorphic_tally_cell (jamás votos individuales).
        6. Transiciona la elección al estado final TALLIED y genera tally_ceremony_hash.
        7. Destruye la clave privada de la memoria RAM.
        """
        stmt = select(Election).where(
            Election.id == election_id,
            Election.organization_id == tenant.organization_id,
        )
        election = (await db.execute(stmt)).scalar_one_or_none()
        if not election:
            raise NotFoundException("Elección no encontrada en su institución.")

        # Invariante #11: La votación debe estar cerrada antes de desbloquear el escrutinio
        if election.status not in (ElectionStatus.VOTING_CLOSED, ElectionStatus.TALLIED):
            raise ConflictException(
                f"La elección debe encontrarse en estado VOTING_CLOSED para desbloquear el escrutinio oficial "
                f"(estado actual: {election.status.value})."
            )

        if not election.paillier_public_n:
            raise UnprocessableEntityException(
                "La elección no cuenta con una clave pública Paillier registrada."
            )

        required_k = election.shamir_threshold_k or 3

        # 1. Validación de cantidad mínima de fragmentos (Quórum k de n)
        if len(req.shares) < required_k:
            raise UnprocessableEntityException(
                f"Se requieren al menos {required_k} fragmentos válidos de la Corte Electoral "
                f"para reconstruir la clave de descifrado (se recibieron {len(req.shares)})."
            )

        # 2. Cargar custodios registrados
        stmt_trustees = select(ElectoralTrusteeShare).where(
            ElectoralTrusteeShare.election_id == election.id
        )
        trustees = (await db.execute(stmt_trustees)).scalars().all()
        trustees_by_index = {t.share_index: t for t in trustees}

        parsed_shares: list[tuple[int, int]] = []
        participating_indices: list[int] = []

        # 3. Validar formato y compromisos criptográficos de cada fragmento
        for raw_share in req.shares:
            try:
                x_val, y_val = parse_share(raw_share)
            except CorruptedShareException as err:
                raise UnprocessableEntityException(str(err)) from err

            trustee = trustees_by_index.get(x_val)
            if not trustee:
                raise UnprocessableEntityException(
                    f"El fragmento #{x_val} no corresponde a ningún custodio registrado para esta elección."
                )

            # Verificar compromiso SHA-256
            expected_commitment = compute_share_commitment(election.id, x_val, y_val)
            if expected_commitment != trustee.commitment_hash:
                raise UnprocessableEntityException(
                    f"El fragmento #{x_val} de '{trustee.trustee_name}' no coincide con el compromiso "
                    f"criptográfico registrado en la Ceremonia de Claves (posible alteración o corrupción)."
                )

            parsed_shares.append((x_val, y_val))
            participating_indices.append(x_val)

        # 4. Reconstrucción de la clave privada Paillier mediante interpolación de Lagrange
        prime_mod = int(election.shamir_prime_modulus) if election.shamir_prime_modulus else DEFAULT_SHAMIR_PRIME
        try:
            secret_int = combine_shares(parsed_shares, prime=prime_mod, min_k=required_k)
            p_val, q_val = unpack_paillier_private_key(secret_int)
        except (InsufficientSharesException, ShamirSecurityException) as err:
            raise UnprocessableEntityException(str(err)) from err

        # Validar concordancia matemática con el módulo público n = p * q
        pub_n = int(election.paillier_public_n)
        if (p_val * q_val) != pub_n:
            raise UnprocessableEntityException(
                "La clave privada reconstruida no coincide matemáticamente con el módulo público "
                "de la elección (p * q != n)."
            )

        # Construir objetos de clave Paillier para el descifrado oficial
        pk = paillier.PaillierPublicKey(pub_n)
        priv_key = paillier.PaillierPrivateKey(pk, p_val, q_val)

        # 5. Ejecutar la suma homomórfica previa si no se hubiese realizado
        await HomomorphicTallyEngine.aggregate_votes_for_election(db, election)

        # 6. Descifrado exclusivo de los acumuladores por celda
        tally_summary = await HomomorphicTallyEngine.decrypt_election_tally(db, election, priv_key)

        # Actualizar constancia de custodios participantes
        now_utc = datetime.now(timezone.utc)
        for t in trustees:
            if t.share_index in participating_indices:
                t.submitted_for_tally = True
                t.submitted_at = now_utc

        # Registro en Bitácora Inmutable de Auditoría
        audit_entry = AuditLog(
            organization_id=election.organization_id,
            election_id=election.id,
            actor_id=tenant.user.id,
            actor_role=tenant.user.role.value,
            action="TALLY_CEREMONY_UNLOCKED",
            entity_type="election",
            entity_id=str(election.id),
            ip_address=client_ip,
            payload={
                "tally_ceremony_hash": tally_summary["tally_ceremony_hash"],
                "participating_trustees": participating_indices,
                "decrypted_cells_count": tally_summary["decrypted_cells_count"],
                "suppressed_cells_count": tally_summary["suppressed_cells_count"],
            },
        )
        db.add(audit_entry)

        # Destrucción física obligatoria de los secretos en memoria RAM
        del priv_key
        del p_val
        del q_val
        del secret_int

        await db.commit()

        return ShamirUnlockResponse(
            election_id=election.id,
            status=ElectionStatus.TALLIED.value,
            tally_ceremony_hash=tally_summary["tally_ceremony_hash"],
            decrypted_cells_count=tally_summary["decrypted_cells_count"],
            suppressed_cells_count=tally_summary["suppressed_cells_count"],
            total_ballots_tallied=tally_summary["total_ballots_tallied"],
        )
