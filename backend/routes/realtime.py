import logging
import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query, HTTPException
from jose import jwt
from supabase import create_client
import os

from services.realtime.manager import manager

router = APIRouter(prefix="/ws", tags=["Realtime WebSocket"])
logger = logging.getLogger(__name__)

# Dependencia customizada porque o WS nao suporta header Bearer padrao do HTTP tao facilmente, 
# muitas vezes o token vem na URL no client ws://...
async def validar_token_ws(token: str) -> dict:
    if not token:
        raise ValueError("Token não fornecido")
        
    auth_obrigatorio = os.getenv("AUTH_OBRIGATORIO", "true").lower() == "true"
    
    try:
        url = os.getenv("SUPABASE_URL", "")
        key = os.getenv("SUPABASE_ANON_KEY") or os.getenv("SUPABASE_KEY", "")
        if not url or not key:
            if not auth_obrigatorio:
                return {"sub": "dev-local", "role": "anon"}
            raise ValueError("Supabase não configurado")

        cliente = create_client(url, key)
        resposta = cliente.auth.get_user(token)

        if not resposta or not resposta.user:
            raise ValueError("Token inválido ou expirado")

        return {
            "sub": resposta.user.id,
            "email": resposta.user.email,
            "role": resposta.user.role,
        }
    except Exception as exc:
        if not auth_obrigatorio:
            return {"sub": "dev-local", "role": "anon"}
        raise ValueError(f"Falha na validação WS: {exc}")


@router.websocket("/projetos/{projeto_id}/operacional")
async def websocket_operacional(websocket: WebSocket, projeto_id: str, token: str = Query(None)):
    try:
        usuario = await validar_token_ws(token)
    except ValueError as e:
        logger.warning(f"WS Recusado: {e}")
        await websocket.close(code=1008)
        return

    # Em um app real, aqui checaríamos se o `usuario` tem permissão no `projeto_id` especificamente
    # Como o RLS bloqueia, fazemos o mínimo aqui.
    
    await manager.connect(websocket, projeto_id)
    
    try:
        while True:
            # Mantém a conexão aberta esperando ping/mensagens do cliente, se houver
            data = await websocket.receive_text()
            # Pode processar heartbeats aqui
            if data == "ping":
                await websocket.send_text("pong")
                
    except WebSocketDisconnect:
        manager.disconnect(websocket, projeto_id)
    except Exception as e:
        logger.error(f"WS Error: {e}")
        manager.disconnect(websocket, projeto_id)
