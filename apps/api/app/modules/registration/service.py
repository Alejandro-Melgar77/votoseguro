"""
Servicio de Negocio para Enlaces de Registro, Activación de Votantes y Congelamiento del Padrón
"""
import secrets
import uuid
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.dependencies import TenantContext
from app.core.exceptions import (
    ConflictException,
    ForbiddenException,
    NotFoundException,
    UnprocessableEntityException,
)
from app.core.time import TimeProvider, ensure_utc
from app.crypto.hashing import canonical_json, sha256_hex
from app.crypto.merkle import MerkleTree, compute_voter_leaf_hash
from app.db.models.election import Election, ElectionStatus
from app.db.models.organization import Organization
from app.db.models.structure import UnitNode, VoterGroup
from app.db.models.user import User
from app.db.models.voter import LinkStatus, RegistrationLink, Voter, VoterStatus
from app.modules.audit.service import AuditService
from app.modules.registration.schemas import (
    PublicRegistrationInfoResponse,
    PublicVoterActivationRequest,
    PublicVoterActivationResponse,
    RegistrationLinkCreate,
    RegistrationLinkResponse,
    RollHashFreezeResponse,
    SelfRegistrationGroupDTO,
    SelfRegistrationInfoResponse,
    SelfRegistrationNodeDTO,
    SelfRegistrationRequest,
    SelfRegistrationResponse,
    SendInvitationsRequest,
    SendInvitationsResponse,
)


class RegistrationService:
    @staticmethod
    async def create_registration_link(
        db: AsyncSession,
        election_id: uuid.UUID,
        payload: RegistrationLinkCreate,
        tenant: TenantContext,
        time_provider: TimeProvider,
    ) -> RegistrationLinkResponse:
        """Crea un nuevo enlace público de registro para un grupo o nodo específico."""
        db_now = await time_provider.now(db)

        # 1. Cargar elección
        stmt_el = select(Election).where(
            Election.id == election_id,
            Election.organization_id == tenant.organization_id,
        )
        election = (await db.execute(stmt_el)).scalar_one_or_none()
        if not election:
            raise NotFoundException("Elección no encontrada en su institución.")

        if election.status not in (ElectionStatus.SCHEDULED, ElectionStatus.REGISTRATION_OPEN):
            raise ConflictException(
                "Los enlaces de registro únicamente pueden crearse cuando la elección se encuentra en estado "
                "SCHEDULED o REGISTRATION_OPEN."
            )

        if ensure_utc(payload.expires_at) > ensure_utc(election.registration_closes_at):
            raise UnprocessableEntityException(
                "La fecha de expiración del enlace no puede superar el cierre de registro oficial de la elección "
                f"({election.registration_closes_at.isoformat()})."
            )

        # 2. Validar grupo
        stmt_grp = select(VoterGroup).where(
            VoterGroup.id == payload.group_id,
            VoterGroup.election_id == election_id,
        )
        group = (await db.execute(stmt_grp)).scalar_one_or_none()
        if not group:
            raise NotFoundException("El grupo de votantes especificado no existe en esta elección.")

        # 3. Validar nodo si se especifica
        node: UnitNode | None = None
        if payload.node_id:
            stmt_node = select(UnitNode).where(
                UnitNode.id == payload.node_id,
                UnitNode.group_id == payload.group_id,
            )
            node = (await db.execute(stmt_node)).scalar_one_or_none()
            if not node:
                raise NotFoundException("El nodo jerárquico especificado no pertenece al grupo de votantes.")

        # 4. Generar token de alta entropía
        raw_token = secrets.token_urlsafe(24)
        token_hash = sha256_hex(raw_token)

        link = RegistrationLink(
            organization_id=tenant.organization_id,
            election_id=election_id,
            group_id=payload.group_id,
            node_id=payload.node_id,
            token_hash=token_hash,
            raw_token=raw_token,
            label=payload.label or f"Enlace {group.name}" + (f" - {node.name}" if node else ""),
            expires_at=payload.expires_at,
            max_uses=payload.max_uses,
            uses_count=0,
            status=LinkStatus.ACTIVE,
            created_by=tenant.user.id,
            created_at=db_now,
        )
        db.add(link)
        await db.flush()

        await AuditService.log_event(
            db=db,
            action="REGISTRATION_LINK_CREATED",
            entity_type="registration_link",
            entity_id=str(link.id),
            actor_role=tenant.user.role.value,
            actor_id=tenant.user.id,
            organization_id=tenant.organization_id,
            election_id=election_id,
            payload={
                "group_id": str(payload.group_id),
                "node_id": str(payload.node_id) if payload.node_id else None,
                "label": link.label,
                "max_uses": payload.max_uses,
                "expires_at": payload.expires_at.isoformat(),
            },
        )
        await db.commit()

        # S2-04: Transmitir actualización de padrón por WebSockets
        try:
            import asyncio
            from app.db.session import async_session_factory
            from app.modules.realtime.manager import ws_manager
            asyncio.create_task(ws_manager.broadcast_election(election.id, async_session_factory, time_provider))
        except Exception:
            pass
        await db.refresh(link)

        return RegistrationLinkResponse(
            id=link.id,
            election_id=link.election_id,
            group_id=link.group_id,
            node_id=link.node_id,
            group_name=group.name,
            node_name=node.name if node else None,
            node_path=node.path if node else None,
            label=link.label,
            token_hash=link.token_hash,
            raw_token=raw_token,
            registration_url=f"/register/{raw_token}",
            expires_at=link.expires_at,
            max_uses=link.max_uses,
            uses_count=link.uses_count,
            status=link.status.value,
            created_at=link.created_at,
        )

    @staticmethod
    async def list_registration_links(
        db: AsyncSession,
        election_id: uuid.UUID,
        tenant: TenantContext,
    ) -> list[RegistrationLinkResponse]:
        """Lista todos los enlaces de registro de la elección, filtrando según alcance de ADMIN_SEGMENT."""
        stmt = (
            select(RegistrationLink)
            .options(selectinload(RegistrationLink.node))
            .where(
                RegistrationLink.election_id == election_id,
                RegistrationLink.organization_id == tenant.organization_id,
            )
            .order_by(RegistrationLink.created_at.desc())
        )

        links = (await db.execute(stmt)).scalars().all()

        # Cargar grupos para nombres
        stmt_groups = select(VoterGroup).where(VoterGroup.election_id == election_id)
        groups = {g.id: g for g in (await db.execute(stmt_groups)).scalars().all()}

        results: list[RegistrationLinkResponse] = []
        for l in links:
            grp = groups.get(l.group_id)
            node = l.node

            # Si es ADMIN_SEGMENT, filtrar por alcance asignado
            if tenant.is_segment_admin():
                allowed = False
                for a in tenant.assignments:
                    if a.group_id == l.group_id:
                        if not a.node_id:
                            allowed = True
                            break
                        elif node and node.path.startswith(a.node.path if hasattr(a, "node") and a.node else ""):
                            allowed = True
                            break
                if not allowed and tenant.assignments:
                    continue

            results.append(
                RegistrationLinkResponse(
                    id=l.id,
                    election_id=l.election_id,
                    group_id=l.group_id,
                    node_id=l.node_id,
                    group_name=grp.name if grp else None,
                    node_name=node.name if node else None,
                    node_path=node.path if node else None,
                    label=l.label,
                    token_hash=l.token_hash,
                    raw_token=l.raw_token,
                    registration_url=f"/register/{l.raw_token or l.token_hash[:16]}",
                    expires_at=l.expires_at,
                    max_uses=l.max_uses,
                    uses_count=l.uses_count,
                    status=l.status.value,
                    created_at=l.created_at,
                )
            )

        return results

    @staticmethod
    async def revoke_registration_link(
        db: AsyncSession,
        election_id: uuid.UUID,
        link_id: uuid.UUID,
        tenant: TenantContext,
    ) -> dict[str, str]:
        """Revoca un enlace de registro."""
        stmt = select(RegistrationLink).where(
            RegistrationLink.id == link_id,
            RegistrationLink.election_id == election_id,
            RegistrationLink.organization_id == tenant.organization_id,
        )
        link = (await db.execute(stmt)).scalar_one_or_none()
        if not link:
            raise NotFoundException("Enlace de registro no encontrado.")

        link.status = LinkStatus.REVOKED
        await AuditService.log_event(
            db=db,
            action="REGISTRATION_LINK_REVOKED",
            entity_type="registration_link",
            entity_id=str(link.id),
            actor_role=tenant.user.role.value,
            actor_id=tenant.user.id,
            organization_id=tenant.organization_id,
            election_id=election_id,
            payload={"link_id": str(link.id)},
        )
        await db.commit()

        # S2-04: Transmitir actualización de padrón por WebSockets
        try:
            import asyncio
            from app.db.session import async_session_factory
            from app.modules.realtime.manager import ws_manager
            asyncio.create_task(ws_manager.broadcast_election(election.id, async_session_factory, time_provider))
        except Exception:
            pass
        return {"message": "Enlace de registro revocado correctamente."}

    @staticmethod
    async def send_invitations(
        db: AsyncSession,
        election_id: uuid.UUID,
        payload: SendInvitationsRequest,
        tenant: TenantContext,
        time_provider: TimeProvider,
    ) -> SendInvitationsResponse:
        """Marca a los votantes IMPORTED del segmento como INVITED."""
        db_now = await time_provider.now(db)

        # Buscar enlace o crear uno rápido si no existe
        stmt_link = (
            select(RegistrationLink)
            .where(
                RegistrationLink.election_id == election_id,
                RegistrationLink.group_id == payload.group_id,
                RegistrationLink.status == LinkStatus.ACTIVE,
            )
            .order_by(RegistrationLink.created_at.desc())
        )
        if payload.node_id:
            stmt_link = stmt_link.where(RegistrationLink.node_id == payload.node_id)
        link = (await db.execute(stmt_link)).scalars().first()

        raw_url = f"/register/{link.raw_token}" if link and link.raw_token else "/register/demo"

        # Buscar votantes a invitar
        stmt_voters = select(Voter).options(selectinload(Voter.node)).where(
            Voter.election_id == election_id,
            Voter.group_id == payload.group_id,
            Voter.status == VoterStatus.IMPORTED,
        )
        voters = (await db.execute(stmt_voters)).scalars().all()

        target_node_path = None
        if payload.node_id:
            node_stmt = select(UnitNode).where(UnitNode.id == payload.node_id)
            target_node = (await db.execute(node_stmt)).scalar_one_or_none()
            if target_node:
                target_node_path = target_node.path

        invited_count = 0
        for v in voters:
            if target_node_path and not (v.node and v.node.path.startswith(target_node_path)):
                continue
            v.status = VoterStatus.INVITED
            v.invited_at = db_now
            invited_count += 1

        await AuditService.log_event(
            db=db,
            action="REGISTRATION_INVITATIONS_SENT",
            entity_type="voter_group",
            entity_id=str(payload.group_id),
            actor_role=tenant.user.role.value,
            actor_id=tenant.user.id,
            organization_id=tenant.organization_id,
            election_id=election_id,
            payload={"invited_count": invited_count, "node_id": str(payload.node_id) if payload.node_id else None},
        )
        await db.commit()

        # S2-04: Transmitir actualización de padrón por WebSockets
        try:
            import asyncio
            from app.db.session import async_session_factory
            from app.modules.realtime.manager import ws_manager
            asyncio.create_task(ws_manager.broadcast_election(election.id, async_session_factory, time_provider))
        except Exception:
            pass

        return SendInvitationsResponse(
            invited_count=invited_count,
            registration_url=raw_url,
            message=f"Se generaron y prepararon {invited_count} invitaciones de registro para el segmento.",
        )

    @staticmethod
    async def get_public_link_info(
        db: AsyncSession,
        token: str,
        time_provider: TimeProvider,
    ) -> PublicRegistrationInfoResponse:
        """Endpoint público que retorna los metadatos de la elección y del segmento según el enlace."""
        db_now = await time_provider.now(db)
        token_hash = sha256_hex(token)

        stmt = (
            select(RegistrationLink)
            .options(
                selectinload(RegistrationLink.node),
            )
            .where(RegistrationLink.token_hash == token_hash)
        )
        link = (await db.execute(stmt)).scalar_one_or_none()
        if not link or link.status == LinkStatus.REVOKED:
            raise NotFoundException("El enlace de registro no es válido, no existe o ha sido revocado.")

        if link.max_uses is not None and link.uses_count >= link.max_uses:
            raise ForbiddenException("El enlace de registro ha alcanzado su límite máximo de usos permitidos.")

        if link.status == LinkStatus.EXPIRED or db_now >= ensure_utc(link.expires_at):
            raise ForbiddenException("El enlace de registro ha expirado.")

        # Cargar elección
        stmt_el = select(Election).where(Election.id == link.election_id)
        election = (await db.execute(stmt_el)).scalar_one_or_none()
        if not election:
            raise NotFoundException("Elección no encontrada.")

        # Invariante #5: Ventana oficial de registro
        if election.status != ElectionStatus.REGISTRATION_OPEN or not (
            ensure_utc(election.registration_opens_at) <= db_now < ensure_utc(election.registration_closes_at)
        ):
            raise ForbiddenException(
                "La fase oficial de registro de votantes no se encuentra abierta en este momento."
            )

        # Cargar organización y grupo
        stmt_org = select(Organization).where(Organization.id == election.organization_id)
        org = (await db.execute(stmt_org)).scalar_one_or_none()

        stmt_grp = select(VoterGroup).where(VoterGroup.id == link.group_id)
        group = (await db.execute(stmt_grp)).scalar_one_or_none()

        node = link.node

        return PublicRegistrationInfoResponse(
            organization_name=org.name if org else "Institución Electoral",
            election_id=election.id,
            election_name=election.name,
            group_id=link.group_id,
            group_name=group.name if group else "",
            node_id=link.node_id,
            node_name=node.name if node else None,
            node_path=node.path if node else None,
            registration_closes_at=election.registration_closes_at,
            link_expires_at=link.expires_at,
            is_valid=True,
        )

    @staticmethod
    async def activate_voter_publicly(
        db: AsyncSession,
        token: str,
        payload: PublicVoterActivationRequest,
        time_provider: TimeProvider,
    ) -> PublicVoterActivationResponse:
        """Activa un votante empadronado a través del enlace público, validando identidad y pertenencia."""
        db_now = await time_provider.now(db)
        token_hash = sha256_hex(token)

        # 1. Validar enlace
        stmt = (
            select(RegistrationLink)
            .options(selectinload(RegistrationLink.node))
            .where(RegistrationLink.token_hash == token_hash)
        )
        link = (await db.execute(stmt)).scalar_one_or_none()
        if not link or link.status == LinkStatus.REVOKED:
            raise NotFoundException("El enlace de registro no es válido, no existe o ha sido revocado.")

        if link.max_uses is not None and link.uses_count >= link.max_uses:
            raise ForbiddenException("El enlace de registro ha alcanzado su límite máximo de usos.")

        if link.status == LinkStatus.EXPIRED or db_now >= ensure_utc(link.expires_at):
            raise ForbiddenException("El enlace de registro ha expirado.")

        # 2. Validar fase de la elección
        stmt_el = select(Election).where(Election.id == link.election_id)
        election = (await db.execute(stmt_el)).scalar_one_or_none()
        if not election:
            raise NotFoundException("Elección no encontrada.")

        if election.status != ElectionStatus.REGISTRATION_OPEN or not (
            ensure_utc(election.registration_opens_at) <= db_now < ensure_utc(election.registration_closes_at)
        ):
            raise ForbiddenException(
                "La fase de registro oficial de la elección no se encuentra abierta para activación."
            )

        # 3. Buscar al votante por document_id
        doc_id = payload.document_id.strip()
        stmt_voter = (
            select(Voter)
            .options(selectinload(Voter.node), selectinload(Voter.group))
            .where(
                Voter.election_id == link.election_id,
                Voter.document_id == doc_id,
            )
        )
        voter = (await db.execute(stmt_voter)).scalar_one_or_none()
        if not voter:
            raise NotFoundException(
                f"No se encontró ningún registro para el documento de identidad '{doc_id}' en el padrón de esta elección."
            )

        # 4. Validar pertenencia al grupo
        if voter.group_id != link.group_id:
            raise ForbiddenException("El votante no pertenece al grupo institucional habilitado por este enlace.")

        # 5. Validar pertenencia al subárbol del nodo si el enlace está segmentado
        if link.node_id is not None and link.node is not None:
            if not voter.node or not voter.node.path.startswith(link.node.path):
                raise ForbiddenException(
                    "El votante no pertenece a la unidad territorial o académica asignada a este enlace de registro."
                )

        # 6. Validar estado del votante
        if voter.status == VoterStatus.BLOCKED:
            raise ForbiddenException("Su registro se encuentra bloqueado en el padrón electoral.")

        # Si ya está activo, devolver respuesta idempotente exitosa
        if voter.status == VoterStatus.ACTIVE:
            return PublicVoterActivationResponse(
                success=True,
                message="Su registro ya se encontraba previamente activado y verificado en el padrón electoral.",
                voter_id=voter.id,
                document_id=voter.document_id,
                full_name=voter.full_name,
                group_name=voter.group.name if voter.group else "",
                node_name=voter.node.name if voter.node else "",
                node_path=voter.node.path if voter.node else "",
                status=voter.status.value,
                activated_at=voter.activated_at or db_now,
            )

        # 7. Activar votante
        voter.status = VoterStatus.ACTIVE
        voter.activated_at = db_now
        if payload.email:
            voter.email = payload.email.strip()
        if payload.phone:
            voter.phone = payload.phone.strip()

        link.uses_count += 1
        if link.max_uses is not None and link.uses_count >= link.max_uses:
            link.status = LinkStatus.EXPIRED

        await AuditService.log_event(
            db=db,
            action="VOTER_ACTIVATED_VIA_LINK",
            entity_type="voter",
            entity_id=str(voter.id),
            actor_role="VOTER",
            organization_id=election.organization_id,
            election_id=election.id,
            payload={
                "document_id": voter.document_id,
                "link_id": str(link.id),
                "timestamp": db_now.isoformat(),
            },
        )
        await db.commit()

        # S2-04: Transmitir actualización de padrón por WebSockets
        try:
            import asyncio
            from app.db.session import async_session_factory
            from app.modules.realtime.manager import ws_manager
            asyncio.create_task(ws_manager.broadcast_election(election.id, async_session_factory, time_provider))
        except Exception:
            pass

        return PublicVoterActivationResponse(
            success=True,
            message="Registro activado exitosamente. Se encuentra formalmente habilitado para sufragar.",
            voter_id=voter.id,
            document_id=voter.document_id,
            full_name=voter.full_name,
            group_name=voter.group.name if voter.group else "",
            node_name=voter.node.name if voter.node else "",
            node_path=voter.node.path if voter.node else "",
            status=voter.status.value,
            activated_at=db_now,
        )

    @staticmethod
    async def compute_and_freeze_roll_hash(
        db: AsyncSession,
        election: Election,
        db_now,
        tenant: TenantContext | None = None,
    ) -> RollHashFreezeResponse:
        """
        Invariante #5: Congelamiento determinista del padrón electoral.
        Calcula el roll_hash canónico (RFC 8785) sobre todos los votantes ACTIVE,
        expira todos los enlaces de registro y transiciona a REGISTRATION_CLOSED.
        """
        # Cargar todos los votantes ACTIVE ordenados por document_id
        stmt_voters = (
            select(Voter)
            .options(selectinload(Voter.node), selectinload(Voter.group))
            .where(
                Voter.election_id == election.id,
                Voter.status == VoterStatus.ACTIVE,
            )
            .order_by(Voter.document_id.asc())
        )
        active_voters = (await db.execute(stmt_voters)).scalars().all()

        canonical_roll_data = [
            {
                "attributes": v.attributes or {},
                "document_id": v.document_id,
                "full_name": v.full_name,
                "group_code": v.group.code if v.group else str(v.group_id),
                "group_id": str(v.group_id),
                "node_id": str(v.node_id),
                "node_path": v.node.path if v.node else "",
                "status": v.status.value,
            }
            for v in active_voters
        ]

        roll_hash = sha256_hex(canonical_json(canonical_roll_data))

        # S2-07: Cálculo del Árbol de Merkle del padrón congelado
        leaves = [
            compute_voter_leaf_hash(
                election_id=str(election.id),
                document_id=v.document_id,
                group_code=v.group.code if v.group else (v.group.name if v.group else ""),
                node_path=v.node.path if v.node else "",
                status="ACTIVE",
            )
            for v in active_voters
        ]
        merkle_tree = MerkleTree(leaves, str(election.id))
        merkle_root = merkle_tree.root

        election.roll_hash = roll_hash
        election.merkle_root = merkle_root
        election.registration_frozen_at = db_now
        election.status = ElectionStatus.REGISTRATION_CLOSED
        election.updated_at = db_now

        # Expirar enlaces de registro activos
        await db.execute(
            update(RegistrationLink)
            .where(
                RegistrationLink.election_id == election.id,
                RegistrationLink.status == LinkStatus.ACTIVE,
            )
            .values(status=LinkStatus.EXPIRED)
        )

        actor_role = tenant.user.role.value if tenant else "SCHEDULER"
        actor_id = tenant.user.id if tenant else None

        await AuditService.log_event(
            db=db,
            action="ROLL_FROZEN",
            entity_type="election",
            entity_id=str(election.id),
            actor_role=actor_role,
            actor_id=actor_id,
            organization_id=election.organization_id,
            election_id=election.id,
            payload={
                "roll_hash": roll_hash,
                "merkle_root": merkle_root,
                "active_voters_count": len(active_voters),
                "timestamp": db_now.isoformat(),
            },
        )
        await db.commit()

        # S2-04: Transmitir actualización de padrón por WebSockets
        try:
            import asyncio
            from app.db.session import async_session_factory
            from app.modules.realtime.manager import ws_manager
            asyncio.create_task(ws_manager.broadcast_election(election.id, async_session_factory, time_provider))
        except Exception:
            pass

        return RollHashFreezeResponse(
            election_id=election.id,
            roll_hash=roll_hash,
            merkle_root=merkle_root,
            active_voters_count=len(active_voters),
            registration_frozen_at=db_now,
            status=election.status.value,
        )

    # =========================================================================
    # S2-10: Autoinscripción en Registro Abierto con Aprobación
    # =========================================================================

    @staticmethod
    async def get_self_registration_info(
        db: AsyncSession,
        election_id: uuid.UUID,
    ) -> SelfRegistrationInfoResponse:
        """
        Retorna la estructura de grupos y nodos válidos para el formulario público de autoinscripción.
        """
        election = await db.get(Election, election_id)
        if not election:
            raise NotFoundException(f"Elección con ID {election_id} no encontrada.")

        from app.db.models.structure import Contest, UnitNode, VoterGroup, FilterDefinition
        stmt_groups = select(VoterGroup).where(VoterGroup.election_id == election_id)
        groups = (await db.execute(stmt_groups)).scalars().all()

        group_ids = [g.id for g in groups]
        filters = []
        if group_ids:
            stmt_filters = select(FilterDefinition).where(FilterDefinition.group_id.in_(group_ids))
            filters = (await db.execute(stmt_filters)).scalars().all()
        filter_defs = [
            {"code": f.key, "label": f.label, "allowed_values": f.allowed_values or [], "is_required": f.is_required}
            for f in filters
        ]

        groups_dto = []
        for g in groups:
            # Calcular profundidad máxima de cargos del grupo
            stmt_contests = select(Contest).options(selectinload(Contest.scope_level)).where(Contest.group_id == g.id)
            contests = (await db.execute(stmt_contests)).scalars().all()
            max_depth = 1
            for c in contests:
                if c.scope_level and c.scope_level.depth > max_depth:
                    max_depth = c.scope_level.depth

            # Cargar nodos del grupo con depth >= max_depth
            stmt_nodes = select(UnitNode).where(
                UnitNode.group_id == g.id,
                UnitNode.depth >= max_depth,
            ).order_by(UnitNode.path.asc())
            nodes = (await db.execute(stmt_nodes)).scalars().all()

            nodes_dto = [
                SelfRegistrationNodeDTO(
                    id=n.id,
                    name=n.name,
                    code=n.code,
                    path=n.path,
                    depth=n.depth,
                )
                for n in nodes
            ]
            groups_dto.append(
                SelfRegistrationGroupDTO(
                    id=g.id,
                    name=g.name,
                    code=g.code,
                    nodes=nodes_dto,
                )
            )

        is_open = (
            election.status == ElectionStatus.REGISTRATION_OPEN
            and election.registration_mode == "OPEN_WITH_APPROVAL"
        )

        return SelfRegistrationInfoResponse(
            election_id=election.id,
            election_name=election.name,
            registration_mode=election.registration_mode,
            status=election.status.value,
            is_open=is_open,
            groups=groups_dto,
            filter_definitions=filter_defs,
        )

    @staticmethod
    async def self_register_voter(
        db: AsyncSession,
        election_id: uuid.UUID,
        payload: SelfRegistrationRequest,
        time_provider: TimeProvider,
    ) -> SelfRegistrationResponse:
        """
        S2-10: Registra a un ciudadano en estado PENDING_APPROVAL cuando el modo es OPEN_WITH_APPROVAL.
        """
        election = await db.get(Election, election_id)
        if not election:
            raise NotFoundException(f"Elección con ID {election_id} no encontrada.")

        if election.registration_mode != "OPEN_WITH_APPROVAL":
            raise ForbiddenException(
                "La autoinscripción pública no está habilitada para esta elección (modo restringido por enlace)."
            )

        if election.status != ElectionStatus.REGISTRATION_OPEN:
            raise ForbiddenException(
                f"La fase de registro no se encuentra abierta actualmente (estado: {election.status.value})."
            )

        doc_clean = payload.document_id.strip()
        stmt_exist = select(Voter).where(
            Voter.election_id == election_id,
            Voter.document_id == doc_clean,
        )
        existing = (await db.execute(stmt_exist)).scalar_one_or_none()
        if existing:
            raise ConflictException(f"Ya existe una solicitud o registro con el documento '{doc_clean}'.")

        from app.db.models.structure import Contest, UnitNode
        node = await db.get(UnitNode, payload.node_id)
        if not node or node.group_id != payload.group_id:
            raise UnprocessableEntityException("La unidad o carrera seleccionada no pertenece al estamento indicado.")

        db_now = await time_provider.now(db)

        voter = Voter(
            organization_id=election.organization_id,
            election_id=election.id,
            group_id=payload.group_id,
            node_id=payload.node_id,
            document_id=doc_clean,
            full_name=payload.full_name.strip(),
            email=payload.email.strip() if payload.email else None,
            phone=payload.phone.strip() if payload.phone else None,
            attributes=payload.attributes or {},
            status=VoterStatus.PENDING_APPROVAL,
            created_at=db_now,
        )
        db.add(voter)
        await db.flush()

        await AuditService.log_event(
            db=db,
            action="VOTER_SELF_REGISTERED_PENDING",
            entity_type="voter",
            entity_id=str(voter.id),
            actor_role="CITIZEN",
            organization_id=election.organization_id,
            election_id=election.id,
            payload={
                "document_id": doc_clean,
                "full_name": voter.full_name,
                "group_id": str(payload.group_id),
                "node_id": str(payload.node_id),
            },
        )
        await db.commit()

        return SelfRegistrationResponse(
            success=True,
            message="Solicitud de inscripción recibida exitosamente. Pendiente de verificación por la comisión electoral.",
            voter_id=voter.id,
            document_id=doc_clean,
            full_name=voter.full_name,
            status=voter.status.value,
        )

    @staticmethod
    async def approve_voter(
        db: AsyncSession,
        election_id: uuid.UUID,
        voter_id: uuid.UUID,
        admin_user: User,
        time_provider: TimeProvider,
    ) -> Voter:
        """
        S2-10: Aprueba la autoinscripción (PENDING_APPROVAL -> ACTIVE).
        """
        voter = await db.get(Voter, voter_id)
        if not voter or voter.election_id != election_id:
            raise NotFoundException(f"Votante con ID {voter_id} no encontrado.")

        status_val = voter.status.value if hasattr(voter.status, "value") else str(voter.status)
        if status_val != "PENDING_APPROVAL":
            raise ConflictException(f"El votante se encuentra en estado '{status_val}', no en PENDING_APPROVAL.")

        db_now = await time_provider.now(db)
        voter.status = VoterStatus.ACTIVE
        voter.activated_at = db_now
        voter.reviewed_by = admin_user.id

        await AuditService.log_event(
            db=db,
            action="VOTER_SELF_REGISTRATION_APPROVED",
            entity_type="voter",
            entity_id=str(voter.id),
            actor_role=admin_user.role.value,
            actor_id=admin_user.id,
            organization_id=voter.organization_id,
            election_id=election_id,
            payload={
                "document_id": voter.document_id,
                "full_name": voter.full_name,
            },
        )
        await db.commit()
        await db.refresh(voter)
        return voter

    @staticmethod
    async def reject_voter(
        db: AsyncSession,
        election_id: uuid.UUID,
        voter_id: uuid.UUID,
        reason: str,
        admin_user: User,
        time_provider: TimeProvider,
    ) -> Voter:
        """
        S2-10: Rechaza la autoinscripción (PENDING_APPROVAL -> BLOCKED con motivo).
        """
        voter = await db.get(Voter, voter_id)
        if not voter or voter.election_id != election_id:
            raise NotFoundException(f"Votante con ID {voter_id} no encontrado.")

        status_val = voter.status.value if hasattr(voter.status, "value") else str(voter.status)
        if status_val != "PENDING_APPROVAL":
            raise ConflictException(f"El votante se encuentra en estado '{status_val}', no en PENDING_APPROVAL.")

        db_now = await time_provider.now(db)
        voter.status = VoterStatus.BLOCKED
        voter.rejection_reason = reason.strip()
        voter.blocked_reason = f"Rechazo de autoinscripción: {reason.strip()}"
        voter.reviewed_by = admin_user.id

        await AuditService.log_event(
            db=db,
            action="VOTER_SELF_REGISTRATION_REJECTED",
            entity_type="voter",
            entity_id=str(voter.id),
            actor_role=admin_user.role.value,
            actor_id=admin_user.id,
            organization_id=voter.organization_id,
            election_id=election_id,
            payload={
                "document_id": voter.document_id,
                "full_name": voter.full_name,
                "reason": reason.strip(),
            },
        )
        await db.commit()
        await db.refresh(voter)
        return voter

    @staticmethod
    async def list_pending_voters(
        db: AsyncSession,
        election_id: uuid.UUID,
    ) -> list[Voter]:
        stmt = (
            select(Voter)
            .options(selectinload(Voter.node), selectinload(Voter.group))
            .where(
                Voter.election_id == election_id,
                Voter.status == VoterStatus.PENDING_APPROVAL,
            )
            .order_by(Voter.created_at.asc())
        )
        return list((await db.execute(stmt)).scalars().all())
