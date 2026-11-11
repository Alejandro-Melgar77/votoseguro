"""
Servicio de Negocio para Cabina de Votación, Papeleta Automática y Emisión Atómica (S1-09)
"""
import secrets
import uuid
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.dependencies import TenantContext, VoterSessionContext
from app.core.exceptions import (
    ConflictException,
    ForbiddenException,
    NotFoundException,
    UnauthorizedException,
    UnprocessableEntityException,
)
from app.core.security import create_voter_token
from app.core.time import TimeProvider, ensure_utc
from app.crypto.hashing import canonical_json, compute_receipt_hash, sha256_hex
from app.crypto.nullifier import compute_nullifier
from app.crypto.vote_codec import default_vote_codec
from app.db.models.election import Election, ElectionStatus
from app.db.models.structure import Candidate, Constituency, Contest, UnitNode, VoterGroup
from app.db.models.voter import Voter, VoterStatus
from app.db.models.voting import Vote, VoteChoiceType, VoterParticipation, VotingCredential
from app.modules.audit.service import AuditService
from app.modules.ballots.schemas import (
    AutomaticBallotResponse,
    BallotCandidateDTO,
    BallotContestSectionDTO,
    CastBallotReceiptResponse,
    CastBallotRequest,
    CredentialDispatchItem,
    ReceiptVerificationResponse,
    VoterElectionInfo,
    VoterLoginRequest,
    VoterLoginResponse,
    VoterSessionProfile,
)


def generate_credential_code() -> str:
    """Genera un código de credencial legible de un solo uso con formato VS-XXXX-XXXX-XXXX."""
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    p1 = "".join(secrets.choice(alphabet) for _ in range(4))
    p2 = "".join(secrets.choice(alphabet) for _ in range(4))
    p3 = "".join(secrets.choice(alphabet) for _ in range(4))
    return f"VS-{p1}-{p2}-{p3}"


class BallotService:
    @staticmethod
    async def issue_credentials_for_election(
        db: AsyncSession,
        election: Election,
        db_now,
    ) -> int:
        """
        Invariante #7: Emite credenciales de votación de un solo uso ÚNICAMENTE
        para votantes en estado ACTIVE. Quienes estén en IMPORTED, INVITED o BLOCKED JAMÁS reciben credencial.
        """
        stmt_active = select(Voter).where(
            Voter.election_id == election.id,
            Voter.status == VoterStatus.ACTIVE,
        )
        active_voters = (await db.execute(stmt_active)).scalars().all()

        issued_count = 0
        for v in active_voters:
            stmt_cred = select(VotingCredential).where(
                VotingCredential.voter_id == v.id,
                VotingCredential.election_id == election.id,
            )
            existing = (await db.execute(stmt_cred)).scalar_one_or_none()
            if not existing:
                raw_token = generate_credential_code()
                token_hash = sha256_hex(raw_token)
                cred = VotingCredential(
                    election_id=election.id,
                    voter_id=v.id,
                    token_hash=token_hash,
                    raw_token=raw_token,
                    issued_at=db_now,
                    expires_at=election.voting_closes_at,
                    used_at=None,
                )
                db.add(cred)
                issued_count += 1

        await db.flush()
        return issued_count

    @staticmethod
    async def open_voting_now(
        db: AsyncSession,
        election_id: uuid.UUID,
        tenant: TenantContext,
        time_provider: TimeProvider,
    ) -> dict[str, str | int]:
        """Abre formalmente la votación (VOTING_OPEN) y emite credenciales a los votantes ACTIVE."""
        db_now = await time_provider.now(db)

        stmt = select(Election).where(
            Election.id == election_id,
            Election.organization_id == tenant.organization_id,
        )
        election = (await db.execute(stmt)).scalar_one_or_none()
        if not election:
            raise NotFoundException("Elección no encontrada en su institución.")

        # Si aún estaba en REGISTRATION_OPEN, congelar primero
        if election.status == ElectionStatus.REGISTRATION_OPEN:
            from app.modules.registration.service import RegistrationService
            await RegistrationService.compute_and_freeze_roll_hash(db, election, db_now, tenant)

        election.status = ElectionStatus.VOTING_OPEN
        election.updated_at = db_now

        issued_count = await BallotService.issue_credentials_for_election(db, election, db_now)

        await AuditService.log_event(
            db=db,
            action="ELECTION_VOTING_OPENED",
            entity_type="election",
            entity_id=str(election.id),
            actor_role=tenant.user.role.value,
            actor_id=tenant.user.id,
            organization_id=tenant.organization_id,
            election_id=election.id,
            payload={"credentials_issued": issued_count, "timestamp": db_now.isoformat()},
        )
        await db.commit()

        # S2-04: Transmitir actualización en tiempo real por WebSockets
        try:
            import asyncio
            from app.db.session import async_session_factory
            from app.modules.realtime.manager import ws_manager
            asyncio.create_task(ws_manager.broadcast_election(election.id, async_session_factory, time_provider))
        except Exception:
            pass

        return {
            "message": "Votación abierta formalmente. Credenciales emitidas con éxito.",
            "credentials_issued": issued_count,
            "status": election.status.value,
        }

    @staticmethod
    async def get_credentials_dispatch(
        db: AsyncSession,
        election_id: uuid.UUID,
        tenant: TenantContext,
    ) -> list[CredentialDispatchItem]:
        """
        Retorna la tabla de credenciales generadas para inspección y demo académica.
        Respeta el alcance territorial/segmento de ADMIN_SEGMENT.
        """
        stmt = (
            select(VotingCredential)
            .options(
                selectinload(VotingCredential.voter).selectinload(Voter.group),
                selectinload(VotingCredential.voter).selectinload(Voter.node),
            )
            .where(VotingCredential.election_id == election_id)
            .order_by(VotingCredential.issued_at.desc())
        )
        creds = (await db.execute(stmt)).scalars().all()

        items: list[CredentialDispatchItem] = []
        for c in creds:
            v = c.voter
            if not v:
                continue

            # Filtrar si es ADMIN_SEGMENT
            if tenant.is_segment_admin():
                allowed = False
                for a in tenant.assignments:
                    if a.group_id == v.group_id:
                        if not a.node_id:
                            allowed = True
                            break
                        elif v.node and v.node.path.startswith(a.node.path if hasattr(a, "node") and a.node else ""):
                            allowed = True
                            break
                if not allowed and tenant.assignments:
                    continue

            items.append(
                CredentialDispatchItem(
                    voter_id=v.id,
                    document_id=v.document_id,
                    full_name=v.full_name,
                    group_name=v.group.name if v.group else "",
                    node_name=v.node.name if v.node else "",
                    node_path=v.node.path if v.node else "",
                    credential_code=c.raw_token,
                    issued_at=c.issued_at,
                    used=c.used_at is not None,
                    used_at=c.used_at,
                )
            )

        return items

    @staticmethod
    async def voter_login(
        db: AsyncSession,
        payload: VoterLoginRequest,
        time_provider: TimeProvider,
    ) -> VoterLoginResponse:
        """Autentica a un votante en la cabina oficial de votación con su CI y Credencial de un solo uso."""
        db_now = await time_provider.now(db)
        raw_code = payload.credential_code.strip()
        token_hash = sha256_hex(raw_code)

        # Buscar credencial por hash (o código directo si aplica)
        stmt_cred = (
            select(VotingCredential)
            .options(
                selectinload(VotingCredential.voter).selectinload(Voter.group),
                selectinload(VotingCredential.voter).selectinload(Voter.node),
                selectinload(VotingCredential.election),
            )
            .where(
                (VotingCredential.token_hash == token_hash) | (VotingCredential.raw_token == raw_code)
            )
        )
        cred = (await db.execute(stmt_cred)).scalars().first()
        if not cred:
            raise UnauthorizedException("Credencial de votación no válida o no encontrada.")

        voter = cred.voter
        election = cred.election

        if not voter or not election:
            raise UnauthorizedException("Registro de votante o proceso electoral no válido.")

        # Verificar concordancia con election_id si fue enviado
        if payload.election_id and election.id != payload.election_id:
            raise UnauthorizedException("La credencial no corresponde a la elección seleccionada.")

        # Verificar concordancia con el document_id
        if voter.document_id.strip() != payload.document_id.strip():
            raise UnauthorizedException("El documento de identidad no coincide con la credencial proporcionada.")

        # Invariante #7: El votante debe estar ACTIVE
        if voter.status != VoterStatus.ACTIVE:
            raise ForbiddenException("El votante no se encuentra en estado ACTIVO en el padrón electoral.")

        # Verificar si la credencial ya fue usada
        if cred.used_at is not None:
            raise ConflictException(
                "Esta credencial de votación de un solo uso ya fue utilizada para emitir sufragio."
            )

        # Invariante #6: Verificar ventana oficial de votación
        if election.status != ElectionStatus.VOTING_OPEN or not (
            ensure_utc(election.voting_opens_at) <= db_now < ensure_utc(election.voting_closes_at)
        ):
            raise ForbiddenException(
                "La elección no se encuentra dentro del horario oficial de votación (VOTING_OPEN)."
            )

        # RF-19: Verificar ventana específica por grupo si fue configurada
        group = voter.group
        if group and group.voting_opens_at and group.voting_closes_at:
            if not (ensure_utc(group.voting_opens_at) <= db_now < ensure_utc(group.voting_closes_at)):
                raise ForbiddenException("La votación para su grupo se encuentra fuera del horario establecido.")

        # Generar JWT efímero para sesión de votante
        access_token = create_voter_token(
            voter_id=str(voter.id),
            election_id=str(election.id),
            credential_id=str(cred.id),
        )

        return VoterLoginResponse(
            access_token=access_token,
            token_type="bearer",
            voter=VoterSessionProfile(
                id=voter.id,
                document_id=voter.document_id,
                full_name=voter.full_name,
                group_id=voter.group_id,
                group_name=group.name if group else "",
                node_id=voter.node_id,
                node_name=voter.node.name if voter.node else "",
                node_path=voter.node.path if voter.node else "",
            ),
            election=VoterElectionInfo(
                id=election.id,
                name=election.name,
                voting_closes_at=election.voting_closes_at,
            ),
        )

    @staticmethod
    async def get_automatic_ballot(
        db: AsyncSession,
        session_ctx: VoterSessionContext,
        time_provider: TimeProvider,
    ) -> AutomaticBallotResponse:
        """
        Algoritmo 3.2: Resolución de Papeleta Automática.
        Determina con exactitud qué cargos y candidatos corresponden al votante
        según su group_id y el materialized path de su node_id.
        """
        db_now = await time_provider.now(db)
        election = session_ctx.election
        voter = session_ctx.voter

        # Invariante #6: Rechaza con 403 si la ventana ya cerró
        if election.status != ElectionStatus.VOTING_OPEN or not (
            ensure_utc(election.voting_opens_at) <= db_now < ensure_utc(election.voting_closes_at)
        ):
            raise ForbiddenException("El periodo oficial de votación ha concluido.")

        # Verificar ventana del grupo si aplica
        if voter.group and voter.group.voting_opens_at and voter.group.voting_closes_at:
            if not (ensure_utc(voter.group.voting_opens_at) <= db_now < ensure_utc(voter.group.voting_closes_at)):
                raise ForbiddenException("El periodo de votación para su grupo ha concluido.")

        # Verificar si la credencial ya fue consumida
        if session_ctx.credential.used_at is not None:
            raise ConflictException("Su credencial de votación ya fue utilizada.")

        # Verificar si ya participó en voter_participation
        stmt_part = select(VoterParticipation).where(
            VoterParticipation.election_id == election.id,
            VoterParticipation.voter_id == voter.id,
        )
        if (await db.execute(stmt_part)).scalar_one_or_none():
            raise ConflictException("Ya existe constancia de sufragio emitida para este elector.")

        # Cargar todos los nodos ancestros del votante (donde voter_node.path empieza con node.path)
        voter_path = voter.node.path if voter.node else ""
        stmt_nodes = select(UnitNode).where(UnitNode.group_id == voter.group_id)
        group_nodes = (await db.execute(stmt_nodes)).scalars().all()

        ancestor_nodes_by_level = {
            n.level_id: n for n in group_nodes if voter_path.startswith(n.path)
        }

        # Cargar cargos del grupo ordenados por display_order
        stmt_contests = (
            select(Contest)
            .where(Contest.group_id == voter.group_id)
            .order_by(Contest.display_order.asc(), Contest.name.asc())
        )
        contests = (await db.execute(stmt_contests)).scalars().all()

        contest_sections: list[BallotContestSectionDTO] = []
        for contest in contests:
            # Encontrar el nodo ancestro que corresponde al scope_level_id del cargo
            matched_node = ancestor_nodes_by_level.get(contest.scope_level_id)
            if not matched_node:
                # El votante no tiene circunscripción en este nivel (por diseño, depth >= max(scope_depth))
                continue

            # Buscar la circunscripción
            stmt_const = select(Constituency).where(
                Constituency.contest_id == contest.id,
                Constituency.node_id == matched_node.id,
            )
            constituency = (await db.execute(stmt_const)).scalar_one_or_none()
            if not constituency:
                continue

            # Cargar candidatos ordenados por ballot_order
            stmt_cands = (
                select(Candidate)
                .where(Candidate.constituency_id == constituency.id)
                .order_by(Candidate.ballot_order.asc())
            )
            candidates = (await db.execute(stmt_cands)).scalars().all()

            cand_dtos = [
                BallotCandidateDTO(
                    id=c.id,
                    full_name=getattr(c, "name", "") or getattr(c, "full_name", ""),
                    ballot_number=getattr(c, "ballot_order", 1),
                    ballot_order=c.ballot_order,
                    party_affiliation=getattr(c, "party_or_front", None),
                    party_color=getattr(c, "party_color", None),
                    photo_url=c.photo_url,
                )
                for c in candidates
            ]

            contest_sections.append(
                BallotContestSectionDTO(
                    contest_id=contest.id,
                    contest_name=contest.name,
                    contest_code=getattr(contest, "code", None) or contest.name[:4].upper(),
                    description=contest.description,
                    display_order=contest.display_order,
                    scope_level_id=contest.scope_level_id,
                    allow_blank=contest.allow_blank,
                    allow_null=contest.allow_null,
                    constituency_id=constituency.id,
                    node_id=matched_node.id,
                    node_name=matched_node.name,
                    node_path=matched_node.path,
                    candidates=cand_dtos,
                )
            )

        return AutomaticBallotResponse(
            election_id=election.id,
            election_name=election.name,
            voter_profile=VoterSessionProfile(
                id=voter.id,
                document_id=voter.document_id,
                full_name=voter.full_name,
                group_id=voter.group_id,
                group_name=voter.group.name if voter.group else "",
                node_id=voter.node_id,
                node_name=voter.node.name if voter.node else "",
                node_path=voter.node.path if voter.node else "",
            ),
            contests=contest_sections,
            voting_closes_at=election.voting_closes_at,
        )

    @staticmethod
    async def cast_ballot_atomic(
        db: AsyncSession,
        session_ctx: VoterSessionContext,
        payload: CastBallotRequest,
        time_provider: TimeProvider,
    ) -> CastBallotReceiptResponse:
        """
        Invariante #6, #7, #8, #9, #13, #17: Emisión Atómica Ciega del Sufragio.
        Dentro de UNA ÚNICA TRANSACCIÓN:
        - Verifica horario estricto con reloj de servidor.
        - Bloquea credencial y valida uso único.
        - Valida que las selecciones cubran exactamente la papeleta automática.
        - Calcula nullifier HMAC-SHA256 por cada cargo.
        - Codifica con PlaintextVoteCodec.
        - Trunca tiempo al minuto.
        - Inserta en 'vote' SIN voter_id.
        - Emite receipt_hash determinista y registra voter_participation.
        """
        db_now = await time_provider.now(db)
        election = session_ctx.election
        voter = session_ctx.voter

        # 1. Invariante #6: Verificación temporal estricta
        if election.status != ElectionStatus.VOTING_OPEN or not (
            ensure_utc(election.voting_opens_at) <= db_now < ensure_utc(election.voting_closes_at)
        ):
            raise ForbiddenException("El periodo oficial de votación ha concluido. No se aceptan más sufragios.")

        if voter.group and voter.group.voting_opens_at and voter.group.voting_closes_at:
            if not (ensure_utc(voter.group.voting_opens_at) <= db_now < ensure_utc(voter.group.voting_closes_at)):
                raise ForbiddenException("El periodo de votación para su grupo ha concluido.")

        # 2. Bloquear credencial y verificar uso
        stmt_cred = (
            select(VotingCredential)
            .where(VotingCredential.id == session_ctx.credential_id)
            .with_for_update()
        )
        cred = (await db.execute(stmt_cred)).scalar_one_or_none()
        if not cred or cred.used_at is not None:
            raise ConflictException("Esta credencial de votación ya ha sido utilizada para emitir sufragio.")

        # 3. Resolver la papeleta requerida del votante
        ballot_resp = await BallotService.get_automatic_ballot(db, session_ctx, time_provider)
        expected_constituencies = {c.constituency_id: c for c in ballot_resp.contests}

        submitted_constituencies = [s.constituency_id for s in payload.selections]

        # Validar cobertura exacta (exactamente 1 selección por cada circunscripción)
        if len(payload.selections) != len(expected_constituencies) or set(submitted_constituencies) != set(
            expected_constituencies.keys()
        ):
            raise UnprocessableEntityException(
                f"La papeleta enviada no coincide con su asignación automática. Se requieren exactamente "
                f"{len(expected_constituencies)} selecciones para sus cargos habilitados."
            )

        # 4. Validar cada selección y armar votos
        truncated_time = db_now.replace(second=0, microsecond=0)
        nullifiers: list[str] = []
        votes_to_insert: list[Vote] = []

        for selection in payload.selections:
            contest_section = expected_constituencies[selection.constituency_id]

            if selection.choice_type == VoteChoiceType.CANDIDATE:
                if not selection.candidate_id:
                    raise UnprocessableEntityException("Debe seleccionar un candidato válido.")
                valid_cand_ids = {c.id for c in contest_section.candidates}
                if selection.candidate_id not in valid_cand_ids:
                    raise UnprocessableEntityException(
                        f"El candidato seleccionado no pertenece a la circunscripción de '{contest_section.contest_name}'."
                    )
            elif selection.choice_type == VoteChoiceType.BLANK:
                if not contest_section.allow_blank:
                    raise UnprocessableEntityException(f"El voto en blanco no está habilitado para '{contest_section.contest_name}'.")
                if selection.candidate_id is not None:
                    raise UnprocessableEntityException("El voto en blanco no debe asociar ningún candidato.")
            elif selection.choice_type == VoteChoiceType.NULL:
                if not contest_section.allow_null:
                    raise UnprocessableEntityException(f"El voto nulo no está habilitado para '{contest_section.contest_name}'.")
                if selection.candidate_id is not None:
                    raise UnprocessableEntityException("El voto nulo no debe asociar ningún candidato.")

            # Invariante #8: Nullifier HMAC-SHA256
            nullifier = compute_nullifier(voter.id, selection.constituency_id, settings.NULLIFIER_SECRET)

            # Comprobar si el nullifier ya existe (doble votación para este cargo)
            stmt_null = select(Vote).where(Vote.nullifier == nullifier)
            if (await db.execute(stmt_null)).scalar_one_or_none():
                raise ConflictException("Ya se ha registrado previamente un sufragio para esta circunscripción.")

            nullifiers.append(nullifier)

            # Invariante #13: Codificación de voto
            encoded_payload = default_vote_codec.encode(
                selection.choice_type.value,
                selection.candidate_id,
            )

            # Invariante #9: Creación de fila en 'vote' SIN voter_id
            v = Vote(
                election_id=election.id,
                constituency_id=selection.constituency_id,
                choice_type=selection.choice_type,
                candidate_id=selection.candidate_id,
                encoded_payload=encoded_payload,
                segment_path=voter.node.path if voter.node else "",
                filters_snapshot=voter.attributes or {},
                nullifier=nullifier,
                receipt_hash="",  # Asignado a continuación
                created_at=truncated_time,
            )
            votes_to_insert.append(v)

        # 5. Generar comprobante de urna y receipt_hash global
        nonce = secrets.token_hex(16)
        receipt_hash = compute_receipt_hash(nullifiers, str(election.id), nonce)

        # S2-02: Encadenamiento criptográfico secuencial de votos
        # Bloque Génesis: SHA-256("VOTOSEGURO:VOTE_GENESIS:" + str(election.id) + ":" + (config_hash or "DRAFT"))
        genesis_vote_hash = sha256_hex(f"VOTOSEGURO:VOTE_GENESIS:{election.id}:{election.config_hash or 'DRAFT'}")

        # Bloqueo sobre la elección si el motor lo soporta
        if db.bind and db.bind.dialect.name == "postgresql":
            await db.execute(select(Election).where(Election.id == election.id).with_for_update())

        stmt_last_vote = (
            select(Vote)
            .where(Vote.election_id == election.id)
            .order_by(Vote.chain_index.desc())
            .limit(1)
        )
        last_vote = (await db.execute(stmt_last_vote)).scalar_one_or_none()

        if last_vote and last_vote.vote_hash:
            current_prev_hash = last_vote.vote_hash
            next_index = last_vote.chain_index + 1
        else:
            current_prev_hash = genesis_vote_hash
            next_index = 1

        for v in votes_to_insert:
            v.receipt_hash = receipt_hash
            v.chain_index = next_index
            v.prev_hash = current_prev_hash

            vote_block_payload = {
                "chain_index": next_index,
                "prev_hash": current_prev_hash,
                "election_id": str(election.id),
                "constituency_id": str(v.constituency_id),
                "choice_type": v.choice_type.value if hasattr(v.choice_type, "value") else str(v.choice_type),
                "candidate_id": str(v.candidate_id) if v.candidate_id else None,
                "encoded_payload": v.encoded_payload,
                "segment_path": v.segment_path,
                "nullifier": v.nullifier,
                "receipt_hash": receipt_hash,
                "created_at_iso": ensure_utc(truncated_time).isoformat(),
            }
            v.vote_hash = sha256_hex(canonical_json(vote_block_payload))
            current_prev_hash = v.vote_hash
            next_index += 1
            db.add(v)

        election.votes_chain_head = current_prev_hash

        # 6. Marcar credencial como consumida
        cred.used_at = db_now

        # 7. Registrar constancia de participación del elector
        participation = VoterParticipation(
            election_id=election.id,
            voter_id=voter.id,
            group_id=voter.group_id,
            node_id=voter.node_id,
            completed_at=db_now,
        )
        db.add(participation)

        # 8. Auditoría inmutable sin vincular jamás voter_id a receipt_hash o nullifier
        await AuditService.log_event(
            db=db,
            action="BALLOT_CAST_COMPLETED",
            entity_type="election",
            entity_id=str(election.id),
            actor_role="VOTER",
            organization_id=election.organization_id,
            election_id=election.id,
            payload={
                "contests_count": len(payload.selections),
                "cast_at_minute": truncated_time.isoformat(),
            },
        )

        await db.commit()

        # S2-04: Transmitir actualización en tiempo real por WebSockets
        try:
            import asyncio
            from app.db.session import async_session_factory
            from app.modules.realtime.manager import ws_manager
            asyncio.create_task(ws_manager.broadcast_election(election.id, async_session_factory, time_provider))
        except Exception:
            pass

        return CastBallotReceiptResponse(
            receipt_hash=receipt_hash,
            election_id=election.id,
            election_name=election.name,
            cast_at_minute=truncated_time,
            contests_count=len(payload.selections),
            nonce=nonce,
            status="RECORDED_IN_BALLOT_BOX",
        )

    @staticmethod
    async def verify_receipt(
        db: AsyncSession,
        receipt_hash: str,
    ) -> ReceiptVerificationResponse:
        """
        Verifica públicamente si un comprobante de sufragio existe en la urna digital
        SIN REVELAR JAMÁS la elección o los candidatos votados (Invariante #9).
        S2-03: Incluye chain_proof (eslabones chain_index, vote_hash, prev_hash) y estado de integridad.
        """
        stmt = (
            select(Vote)
            .where(Vote.receipt_hash == receipt_hash.strip())
            .order_by(Vote.chain_index.asc())
        )
        votes = (await db.execute(stmt)).scalars().all()

        if not votes:
            return ReceiptVerificationResponse(
                found=False,
                receipt_hash=receipt_hash,
                election_id=None,
                election_name=None,
                organization_name=None,
                cast_at_minute=None,
                contests_recorded=0,
                status="NOT_FOUND",
                chain_proof=[],
                chain_intact=False,
            )

        first_vote = votes[0]
        election = await db.get(Election, first_vote.election_id)
        org_name = None
        if election:
            from app.db.models.organization import Organization
            org = await db.get(Organization, election.organization_id)
            org_name = org.name if org else None

        from app.modules.ballots.schemas import ReceiptChainProofItem
        chain_proof = [
            ReceiptChainProofItem(
                chain_index=v.chain_index,
                vote_hash=v.vote_hash or "",
                prev_hash=v.prev_hash or "",
            )
            for v in votes
        ]

        # Verificar integridad local de los eslabones del comprobante
        chain_intact = True
        for v in votes:
            expected_payload = {
                "chain_index": v.chain_index,
                "prev_hash": v.prev_hash,
                "election_id": str(v.election_id),
                "constituency_id": str(v.constituency_id),
                "choice_type": v.choice_type.value if hasattr(v.choice_type, "value") else str(v.choice_type),
                "candidate_id": str(v.candidate_id) if v.candidate_id else None,
                "encoded_payload": v.encoded_payload,
                "segment_path": v.segment_path,
                "nullifier": v.nullifier,
                "receipt_hash": v.receipt_hash,
                "created_at_iso": ensure_utc(v.created_at).isoformat(),
            }
            if v.vote_hash != sha256_hex(canonical_json(expected_payload)):
                chain_intact = False
                break

        return ReceiptVerificationResponse(
            found=True,
            receipt_hash=receipt_hash,
            election_id=first_vote.election_id,
            election_name=election.name if election else None,
            organization_name=org_name,
            cast_at_minute=first_vote.created_at,
            contests_recorded=len(votes),
            status="RECORDED_IN_BALLOT_BOX",
            chain_proof=chain_proof,
            chain_intact=chain_intact,
        )
