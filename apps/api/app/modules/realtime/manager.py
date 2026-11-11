"""
Gestor de Conexiones WebSocket para Monitoreo en Tiempo Real (S2-04)
Mantiene conexiones activas, difunde eventos de activación de votantes y emisión de papeletas.
"""
import asyncio
import logging
import uuid
from typing import Any
from fastapi import WebSocket
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.user import User
from app.modules.realtime.service import RealtimeMonitoringService

logger = logging.getLogger("votoseguro.realtime")


class ConnectionManager:
    def __init__(self):
        # election_id -> list of (WebSocket, User | None)
        self.active_connections: dict[uuid.UUID, list[tuple[WebSocket, User | None]]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, election_id: uuid.UUID, user: User | None = None):
        await websocket.accept()
        async with self._lock:
            if election_id not in self.active_connections:
                self.active_connections[election_id] = []
            self.active_connections[election_id].append((websocket, user))
        logger.info(f"[WS] Cliente conectado a elección {election_id}. Total: {len(self.active_connections[election_id])}")

    async def disconnect(self, websocket: WebSocket, election_id: uuid.UUID):
        async with self._lock:
            if election_id in self.active_connections:
                self.active_connections[election_id] = [
                    (ws, u) for (ws, u) in self.active_connections[election_id] if ws != websocket
                ]
                if not self.active_connections[election_id]:
                    del self.active_connections[election_id]
        logger.info(f"[WS] Cliente desconectado de elección {election_id}.")

    async def broadcast_election(self, election_id: uuid.UUID, session_factory, time_provider=None):
        """
        Calcula el snapshot en vivo y lo transmite a los clientes conectados a la elección.
        Si hay un cliente ADMIN_SEGMENT, calcula su vista personalizada.
        """
        async with self._lock:
            listeners = list(self.active_connections.get(election_id, []))

        if not listeners:
            return

        async with session_factory() as session:
            # Caché de snapshots por usuario
            snapshots_by_role: dict[str, dict] = {}

            for ws, user in listeners:
                cache_key = str(user.id) if user and user.role.value == "ADMIN_SEGMENT" else "GLOBAL"
                if cache_key not in snapshots_by_role:
                    snapshot = await RealtimeMonitoringService.get_live_dashboard_snapshot(
                        db=session,
                        election_id=election_id,
                        user=user,
                        time_provider=time_provider,
                    )
                    snapshots_by_role[cache_key] = snapshot.model_dump(mode="json")

                payload_data = snapshots_by_role[cache_key]
                try:
                    await ws.send_json({"type": "LIVE_SNAPSHOT_UPDATE", "data": payload_data})
                except Exception as exc:
                    logger.warning(f"[WS] Error enviando a cliente: {exc}")


# Instancia singleton del gestor
ws_manager = ConnectionManager()
