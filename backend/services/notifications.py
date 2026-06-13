import os
import logging
from typing import Dict, Any, List, Optional
from services.channels import get_channel_provider

logger = logging.getLogger(__name__)

def enfileirar_mensagem(
    sb,
    projeto_id: str,
    canal: str,
    conteudo: str,
    telefone: Optional[str] = None,
    destinatario_nome: Optional[str] = None,
    lote_id: Optional[str] = None,
    participante_id: Optional[str] = None,
    sessao_id: Optional[str] = None,
    agente: Optional[str] = None,
    origem: Optional[str] = 'manual'
) -> Dict[str, Any]:
    """Cria uma mensagem externa com status 'queued' ou 'draft' (pronta para aprovação)."""
    
    if not projeto_id:
        raise ValueError("projeto_id e obrigatorio para notificar")
        
    status_inicial = 'queued' if os.getenv('REQUIRE_HUMAN_APPROVAL', 'true').lower() == 'false' else 'draft'
    
    payload = {
        'projeto_id': projeto_id,
        'lote_id': lote_id,
        'participante_id': participante_id,
        'sessao_id': sessao_id,
        'canal': canal,
        'direcao': 'outbound',
        'telefone': telefone,
        'destinatario_nome': destinatario_nome,
        'conteudo': conteudo,
        'status': status_inicial,
        'agente': agente,
        'origem': origem
    }
    
    try:
        resp = sb.table('mensagens_externas').insert(payload).execute()
        dados = getattr(resp, 'data', [])
        return dados[0] if dados else {}
    except Exception as e:
        logger.error(f"Erro ao enfileirar mensagem externa: {e}")
        return {}

def aprovar_mensagem(sb, mensagem_id: str, approved_by: Optional[str] = None) -> Dict[str, Any]:
    """Marca uma mensagem como aprovada para envio."""
    try:
        agora = "now()"
        payload = {
            'status': 'approved',
            'approved_by': approved_by,
            'approved_at': agora
        }
        resp = sb.table('mensagens_externas').update(payload).eq('id', mensagem_id).execute()
        dados = getattr(resp, 'data', [])
        return dados[0] if dados else {}
    except Exception as e:
        logger.error(f"Erro ao aprovar mensagem externa {mensagem_id}: {e}")
        return {}

def enviar_mensagem_aprovada(sb, mensagem_id: str) -> Dict[str, Any]:
    """Tenta enviar a mensagem aprovada usando o canal correspondente."""
    # 1. Recupera
    resp = sb.table('mensagens_externas').select('*').eq('id', mensagem_id).is_('deleted_at', 'null').execute()
    dados = getattr(resp, 'data', [])
    if not dados:
        raise ValueError("Mensagem nao encontrada ou apagada")
    
    msg = dados[0]
    
    if msg.get('status') not in ['approved', 'queued']:
        raise ValueError(f"Mensagem em status invalido para envio: {msg.get('status')}")
        
    if not msg.get('telefone'):
        # Falha antes de enviar
        sb.table('mensagens_externas').update({'status': 'failed', 'erro': 'Sem telefone'}).eq('id', mensagem_id).execute()
        return {'sucesso': False, 'erro': 'Sem telefone'}
        
    if os.getenv("EXTERNAL_MESSAGES_ENABLED", "false").lower() == "false":
        sb.table('mensagens_externas').update({'status': 'failed', 'erro': 'Envio global desabilitado'}).eq('id', mensagem_id).execute()
        return {'sucesso': False, 'erro': 'EXTERNAL_MESSAGES_ENABLED = false'}

    # 2. Envia
    canal = msg['canal']
    provider = get_channel_provider(canal)
    
    # Define se é dry run baseado na env especifica do canal
    dry_run_env = os.getenv(f"{canal.upper()}_DRY_RUN", "true").lower() == "true"
    
    try:
        result = provider.send_message(msg['telefone'], msg['conteudo'], dry_run=dry_run_env)
        
        status_final = 'dry_run' if dry_run_env else ('sent' if result['success'] else 'failed')
        
        upd_payload = {
            'status': status_final,
            'provider_message_id': result.get('provider_message_id'),
            'erro': result.get('error'),
            'payload': result.get('payload_sent'),
            'sent_at': "now()" if result['success'] else None
        }
        
        resp_upd = sb.table('mensagens_externas').update(upd_payload).eq('id', mensagem_id).execute()
        msg_up = getattr(resp_upd, 'data', [{}])[0]
        
        from services.realtime.manager import publish_event
        publish_event(msg_up.get("projeto_id"), "external_message_status_changed", {"mensagem_id": mensagem_id, "status": status_final})
        
        return msg_up
    except Exception as e:
        logger.error(f"Erro catastrofico ao enviar: {e}")
        sb.table('mensagens_externas').update({'status': 'failed', 'erro': str(e)}).eq('id', mensagem_id).execute()
        return {'sucesso': False, 'erro': str(e)}

def listar_mensagens_externas_projeto(sb, projeto_id: str, limite: int = 50) -> List[Dict[str, Any]]:
    resp = sb.table('mensagens_externas').select('*').eq('projeto_id', projeto_id).is_('deleted_at', 'null').order('criado_em', desc=True).limit(limite).execute()
    return getattr(resp, 'data', [])

def listar_pendentes_aprovacao(sb, projeto_id: str) -> List[Dict[str, Any]]:
    resp = sb.table('mensagens_externas').select('*').eq('projeto_id', projeto_id).in_('status', ['draft', 'queued', 'approved']).is_('deleted_at', 'null').order('criado_em', desc=True).execute()
    return getattr(resp, 'data', [])
