"""
Rutas API y WebSocket para Monitoreo en Tiempo Real (S2-04)
"""
import asyncio
import logging
import uuid
from typing import Annotated
from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_time_provider, require_roles
from app.core.security import decode_access_token
from app.core.time import TimeProvider
from app.db.models.user import User, UserRole
from app.db.session import async_session_factory, get_db_session
from app.modules.realtime.manager import ws_manager
from app.modules.realtime.schemas import LiveDashboardSnapshot
from app.modules.realtime.service import RealtimeMonitoringService

logger = logging.getLogger("votoseguro.realtime.router")

router = APIRouter(tags=["Monitoreo en Tiempo Real (WebSockets)"])


@router.get(
    "/elections/{election_id}/live-metrics",
    response_model=LiveDashboardSnapshot,
    summary="Obtener Métricas de Monitoreo en Vivo (REST Fallback - S2-04)",
)
async def get_live_metrics_endpoint(
    election_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[
        User,
        Depends(
            require_roles(
                UserRole.PLATFORM_ADMIN,
                UserRole.ADMIN_GENERAL,
                UserRole.ADMIN_SEGMENT,
                UserRole.OBSERVER,
            )
        ),
    ],
    time_provider: Annotated[TimeProvider, Depends(get_time_provider)],
):
    """
    S2-04: Retorna las métricas en tiempo real de avance del padrón, participación
    por grupo/nodo y curva de votos por hora (filtrada según el alcance de ADMIN_SEGMENT).
    INVARIANTE #11: Resultados sellados hasta VOTING_CLOSED. Cero votos por candidato.
    """
    return await RealtimeMonitoringService.get_live_dashboard_snapshot(
        db=db,
        election_id=election_id,
        user=current_user,
        time_provider=time_provider,
    )


@router.websocket("/elections/{election_id}/live")
async def live_monitoring_websocket(
    websocket: WebSocket,
    election_id: uuid.UUID,
    token: str = Query(default=""),
):
    """
    S2-04: Conexión WebSocket para recepción continua de actualizaciones en tiempo real.
    Valida el token JWT en el handshake y transmite el snapshot inicial y difusiones.
    """
    user: User | None = None
    if token:
        try:
            payload = decode_access_token(token)
            user_id_str = payload.get("sub")
            if user_id_str:
                async with async_session_factory() as session:
                    user = await session.get(User, uuid.UUID(user_id_str))
        except Exception as e:
            logger.warning(f"[WS] Token inválido en handshake WebSocket: {e}")
            await websocket.close(code=1008)
            return

    await ws_manager.connect(websocket, election_id, user)

    # Enviar snapshot inicial
    try:
        async with async_session_factory() as session:
            initial_snapshot = await RealtimeMonitoringService.get_live_dashboard_snapshot(
                db=session,
                election_id=election_id,
                user=user,
            )
            await websocket.send_json({
                "type": "INITIAL_SNAPSHOT",
                "data": initial_snapshot.model_dump(mode="json"),
            })

        # Mantener escucha de mensajes / ping-pong
        while True:
            # Esperar mensajes del cliente (ej. {"type": "PING"})
            try:
                data = await asyncio.wait_for(websocket.receive_json(), timeout=15.0)
                if data.get("type") == "PING":
                    await websocket.send_json({"type": "PONG"})
            except asyncio.TimeoutError:
                # Pulso periódico cada 15s si la conexión está inactiva
                async with async_session_factory() as session:
                    heartbeat_snap = await RealtimeMonitoringService.get_live_dashboard_snapshot(
                        db=session,
                        election_id=election_id,
                        user=user,
                    )
                    await websocket.send_json({
                        "type": "PULSE_SNAPSHOT",
                        "data": heartbeat_snap.model_dump(mode="json"),
                    })
    except WebSocketDisconnect:
        await ws_manager.disconnect(websocket, election_id)
    except Exception as exc:
        logger.error(f"[WS] Error en sesión WebSocket: {exc}")
        await ws_manager.disconnect(websocket, election_id)
