from fastapi import APIRouter, Depends, HTTPException, Request
from middleware.auth import verificar_token
from main import get_supabase
from services.notifications import listar_mensagens_externas_projeto, aprovar_mensagem, enviar_mensagem_aprovada, enfileirar_mensagem
from pydantic import BaseModel

router = APIRouter(prefix="/projetos", tags=["Mensagens Externas"], dependencies=[Depends(verificar_token)])

class DraftPayload(BaseModel):
    canal: str
    conteudo: str
    telefone: str = None
    lote_id: str = None
    participante_id: str = None

@router.post("/{projeto_id}/mensagens-externas/draft")
def criar_draft(projeto_id: str, payload: DraftPayload):
    sb = get_supabase()
    result = enfileirar_mensagem(
        sb=sb,
        projeto_id=projeto_id,
        canal=payload.canal,
        conteudo=payload.conteudo,
        telefone=payload.telefone,
        lote_id=payload.lote_id,
        participante_id=payload.participante_id,
        origem="api_manual"
    )
    return result

@router.get("/{projeto_id}/mensagens-externas")
def listar_mensagens(projeto_id: str):
    sb = get_supabase()
    return listar_mensagens_externas_projeto(sb, projeto_id)

@router.post("/{projeto_id}/mensagens-externas/{mensagem_id}/aprovar")
def aprovar(projeto_id: str, mensagem_id: str, usuario: dict = Depends(verificar_token)):
    sb = get_supabase()
    return aprovar_mensagem(sb, mensagem_id, approved_by=usuario.get('sub'))

@router.post("/{projeto_id}/mensagens-externas/{mensagem_id}/enviar")
def enviar_aprovada(projeto_id: str, mensagem_id: str):
    sb = get_supabase()
    return enviar_mensagem_aprovada(sb, mensagem_id)

# Webhooks públicos (não dependem de JWT, usam Secret ou Token)
public_router = APIRouter(prefix="/webhooks", tags=["Webhooks"])

import os
from services.inbound_messages import processar_inbound

class WebhookPayload(BaseModel):
    provider_message_id: str
    from_telefone: str
    texto: str
    secret: str

@public_router.post("/hermes")
def webhook_hermes(payload: WebhookPayload):
    if os.getenv('WEBHOOKS_ENABLED', 'false').lower() == 'false':
        raise HTTPException(status_code=403, detail="Webhooks desabilitados")
        
    secret_real = os.getenv('HERMES_WEBHOOK_SECRET', 'dev-secret')
    if payload.secret != secret_real:
        raise HTTPException(status_code=401, detail="Secret inválido")

    sb = get_supabase()
    return processar_inbound(
        sb=sb,
        canal="hermes",
        provider_message_id=payload.provider_message_id,
        telefone_bruto=payload.from_telefone,
        conteudo=payload.texto
    )

@public_router.post("/whatsapp")
def webhook_whatsapp(payload: WebhookPayload):
    if os.getenv('WEBHOOKS_ENABLED', 'false').lower() == 'false':
        raise HTTPException(status_code=403, detail="Webhooks desabilitados")
        
    secret_real = os.getenv('WHATSAPP_WEBHOOK_SECRET', 'dev-secret')
    if payload.secret != secret_real:
        raise HTTPException(status_code=401, detail="Secret inválido")

    sb = get_supabase()
    return processar_inbound(
        sb=sb,
        canal="whatsapp",
        provider_message_id=payload.provider_message_id,
        telefone_bruto=payload.from_telefone,
        conteudo=payload.texto
    )
