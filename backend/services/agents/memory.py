import logging
from typing import Any

logger = logging.getLogger(__name__)

def buscar_ou_criar_sessao(
    sb, 
    projeto_id: str, 
    sessao_id: str | None = None, 
    lote_id: str | None = None, 
    participante_id: str | None = None,
    canal: str = 'mobile',
    contexto: dict | None = None
) -> str:
    """Retorna o ID da sessão existente ou cria uma nova se não existir ou se não for informada."""
    if sessao_id:
        try:
            resposta = sb.table('chat_sessoes').select('id').eq('id', sessao_id).is_('deleted_at', 'null').limit(1).execute()
            dados = getattr(resposta, 'data', None) or []
            if dados:
                return str(dados[0]['id'])
        except Exception as e:
            logger.warning(f"Erro ao buscar sessao {sessao_id}: {e}")
    else:
        # Busca a sessão mais recente do projeto para continuar a conversa
        try:
            consulta = sb.table('chat_sessoes').select('id').eq('projeto_id', projeto_id).is_('deleted_at', 'null')
            if lote_id: consulta = consulta.eq('lote_id', lote_id)
            if participante_id: consulta = consulta.eq('participante_id', participante_id)
            if canal: consulta = consulta.eq('canal', canal)
            
            resposta = consulta.order('criado_em', desc=True).limit(1).execute()
            dados = getattr(resposta, 'data', None) or []
            if dados:
                return str(dados[0]['id'])
        except Exception as e:
            logger.warning(f"Erro ao buscar sessao recente do projeto {projeto_id}: {e}")

    # Cria nova
    try:
        nova_sessao = {
            'projeto_id': projeto_id,
            'lote_id': lote_id,
            'participante_id': participante_id,
            'canal': canal,
            'contexto': contexto or {}
        }
        resposta = sb.table('chat_sessoes').insert(nova_sessao).execute()
        dados = getattr(resposta, 'data', None) or []
        if dados:
            return str(dados[0]['id'])
    except Exception as e:
        logger.error(f"Erro ao criar sessao de chat: {e}")
    
    return ""

def salvar_mensagem(
    sb, 
    sessao_id: str, 
    projeto_id: str,
    role: str, 
    conteudo: str, 
    agente: str | None = None,
    lote_id: str | None = None,
    participante_id: str | None = None,
    payload: dict | None = None,
    metadados: dict | None = None
) -> bool:
    if not sessao_id or not projeto_id:
        return False
        
    try:
        mensagem = {
            'sessao_id': sessao_id,
            'projeto_id': projeto_id,
            'lote_id': lote_id,
            'participante_id': participante_id,
            'role': role,
            'conteudo': conteudo,
            'agente': agente,
            'payload': payload,
            'metadados': metadados or {}
        }
        sb.table('chat_mensagens').insert(mensagem).execute()
        return True
    except Exception as e:
        logger.error(f"Erro ao salvar mensagem: {e}")
        return False

def carregar_historico_mensagens(sb, sessao_id: str, limite: int = 50) -> list[dict[str, Any]]:
    if not sessao_id:
        return []
        
    try:
        resposta = (
            sb.table('chat_mensagens')
            .select('*')
            .eq('sessao_id', sessao_id)
            .is_('deleted_at', 'null')
            .order('criado_em', desc=True)
            .limit(limite)
            .execute()
        )
        dados = getattr(resposta, 'data', None) or []
        return list(reversed(dados)) # Retorna na ordem cronológica (mais antigas primeiro)
    except Exception as e:
        logger.error(f"Erro ao buscar histórico: {e}")
        return []
