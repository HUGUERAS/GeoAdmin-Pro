import logging
import asyncio
from typing import Dict, List, Any
from fastapi import WebSocket

logger = logging.getLogger(__name__)

class RealtimeManager:
    def __init__(self):
        # Mapeia projeto_id para uma lista de WebSockets conectados
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, projeto_id: str):
        await websocket.accept()
        if projeto_id not in self.active_connections:
            self.active_connections[projeto_id] = []
        self.active_connections[projeto_id].append(websocket)
        logger.info(f"Nova conexao WS aceita no projeto {projeto_id}. Total: {len(self.active_connections[projeto_id])}")

    def disconnect(self, websocket: WebSocket, projeto_id: str):
        if projeto_id in self.active_connections:
            if websocket in self.active_connections[projeto_id]:
                self.active_connections[projeto_id].remove(websocket)
            if not self.active_connections[projeto_id]:
                del self.active_connections[projeto_id]
        logger.info(f"Conexao WS fechada no projeto {projeto_id}")

    async def broadcast_to_project(self, projeto_id: str, event_type: str, data: Dict[str, Any] = None):
        if projeto_id not in self.active_connections:
            return
            
        payload = {
            "type": event_type,
            "project_id": projeto_id,
            "data": data or {}
        }
        
        # Desconecta clientes mortos de forma segura
        disconnected = []
        for connection in self.active_connections[projeto_id]:
            try:
                await connection.send_json(payload)
            except Exception as e:
                logger.warning(f"Falha ao enviar WS payload: {e}")
                disconnected.append(connection)
                
        for connection in disconnected:
            self.disconnect(connection, projeto_id)

manager = RealtimeManager()

def publish_event(projeto_id: str, event_type: str, data: Dict[str, Any] = None):
    """
    Função Helper para ser usada por partes sincronas do FastAPI ou via run_in_executor.
    Isso agenda o broadcast no event loop principal.
    """
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(manager.broadcast_to_project(projeto_id, event_type, data))
    except RuntimeError:
        # Se não houver loop rodando (ex: testes soltos), apenas ignora ou mocka
        pass
