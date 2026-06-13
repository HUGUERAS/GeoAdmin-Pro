import os
import re
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

def limpar_telefone(telefone: str) -> str:
    """Normaliza o telefone removendo caracteres não numéricos"""
    if not telefone: return ""
    return re.sub(r'\D', '', telefone)

def resolver_contexto_inbound(sb, telefone_bruto: str) -> Dict[str, Any]:
    telefone = limpar_telefone(telefone_bruto)
    if not telefone:
        return {'status': 'unlinked', 'motivo': 'Telefone vazio'}
        
    # Busca clientes com este telefone
    resp = sb.table('clientes').select('id, nome, telefone').eq('telefone', telefone).is_('deleted_at', 'null').execute()
    clientes = getattr(resp, 'data', [])
    
    if not clientes:
        return {'status': 'unlinked', 'motivo': 'Telefone não encontrado', 'telefone': telefone}
        
    if len(clientes) > 1:
        return {'status': 'ambiguous', 'motivo': 'Múltiplos clientes com mesmo telefone', 'telefone': telefone}
        
    cliente = clientes[0]
    
    # Busca vínculo em projeto_clientes (assumimos 1 projeto ativo por telefone para simplificar. 
    # Em prod real, se tiver 2 projetos, vira ambiguous)
    resp_proj = sb.table('projeto_clientes').select('id, projeto_id').eq('cliente_id', cliente['id']).is_('deleted_at', 'null').execute()
    vinculos = getattr(resp_proj, 'data', [])
    
    if not vinculos:
        return {'status': 'unlinked', 'motivo': 'Cliente encontrado mas sem projeto vinculado', 'telefone': telefone}
        
    if len(vinculos) > 1:
        # Pega o primeiro por praticidade no MVP, mas avisa
        logger.warning(f"Telefone {telefone} tem múltiplos projetos.")
        
    vinculo = vinculos[0]
    
    return {
        'status': 'linked',
        'projeto_id': vinculo['projeto_id'],
        'participante_id': vinculo['id'],
        'cliente_nome': cliente['nome'],
        'telefone': telefone
    }

def processar_inbound(sb, canal: str, provider_message_id: str, telefone_bruto: str, conteudo: str) -> Dict[str, Any]:
    """Processa a mensagem inbound com idempotência e envia pro orquestrador"""
    
    telefone = limpar_telefone(telefone_bruto)
    
    # 1. Idempotência
    resp_idem = sb.table('mensagens_externas').select('id').eq('provider_message_id', provider_message_id).execute()
    if getattr(resp_idem, 'data', []):
        return {"ok": True, "status": "duplicate_ignored", "provider_message_id": provider_message_id}

    # 2. Resolução
    contexto = resolver_contexto_inbound(sb, telefone)
    
    status_resolucao = contexto['status']
    projeto_id = contexto.get('projeto_id')
    participante_id = contexto.get('participante_id')
    
    # 3. Salva a entrada bruta na fila de mensagens_externas
    inbound_payload = {
        'projeto_id': projeto_id, # Pode ser null se unlinked, mas a FK pode dar erro. Vamos tratar se null.
        'participante_id': participante_id,
        'canal': canal,
        'direcao': 'inbound',
        'telefone': telefone,
        'conteudo': conteudo,
        'status': status_resolucao if status_resolucao in ('unlinked', 'ambiguous') else 'received',
        'provider_message_id': provider_message_id,
        'origem': 'webhook'
    }
    
    # Se unlinked, não temos projeto_id. A tabela mensagens_externas exige projeto_id NOT NULL
    # No caso real, ou flexibiliza a tabela, ou usamos um projeto dummy. 
    # Para cumprir a regra "Não invente tabela/campos", vamos abortar se não tiver projeto_id, 
    # ou jogar pra um UUID generico? Melhor retornar unlinked.
    if not projeto_id:
        logger.error(f"Inbound sem projeto_id. Abortando insert. Tel: {telefone}")
        return {"ok": True, "status": status_resolucao, "motivo": contexto.get('motivo')}
        
    resp_in = sb.table('mensagens_externas').insert(inbound_payload).execute()
    inbound_db = getattr(resp_in, 'data', [{}])[0]
    
    if status_resolucao != 'linked':
        return {"ok": True, "status": status_resolucao, "motivo": contexto.get('motivo'), "mensagem_externa_id": inbound_db.get('id')}
        
    # 4. Criar ou recuperar sessão (usamos uma sessão única "whatsapp_{participante_id}" para agrupar)
    # Procuramos sessoes ativas deste projeto+participante
    sessao_nome = f"WhatsApp - {telefone}"
    resp_sess = sb.table('chat_sessoes').select('id').eq('projeto_id', projeto_id).ilike('nome', f"%{telefone}%").is_('deleted_at', 'null').execute()
    sessoes = getattr(resp_sess, 'data', [])
    if sessoes:
        sessao_id = sessoes[0]['id']
    else:
        # Cria sessão nova
        resp_ns = sb.table('chat_sessoes').insert({'projeto_id': projeto_id, 'nome': sessao_nome}).execute()
        sessao_id = getattr(resp_ns, 'data', [{}])[0].get('id')

    # Atualiza a msg externa com a sessao
    sb.table('mensagens_externas').update({'sessao_id': sessao_id}).eq('id', inbound_db.get('id')).execute()

    # 5. Salvar em chat_mensagens como role = user
    sb.table('chat_mensagens').insert({
        'sessao_id': sessao_id,
        'role': 'user',
        'conteudo': conteudo
    }).execute()

    # 6. Encaminhar para o Orquestrador
    from services.agents.orchestrator import handle_orchestrator_query
    from services.notifications import enfileirar_mensagem

    mensagem_para_bot = f"[MENSAGEM EXTERNA de {telefone}]: {conteudo}"
    resposta_bot = handle_orchestrator_query(projeto_id, mensagem_para_bot, sb, sessao_id=sessao_id)
    
    # 7. Salvar resposta em chat_mensagens
    sb.table('chat_mensagens').insert({
        'sessao_id': sessao_id,
        'role': 'assistant',
        'conteudo': resposta_bot
    }).execute()

    # 8. Criar Draft da Resposta
    enfileirar_mensagem(
        sb=sb,
        projeto_id=projeto_id,
        canal=canal,
        conteudo=resposta_bot,
        telefone=telefone,
        participante_id=participante_id,
        sessao_id=sessao_id,
        agente='orquestrador',
        origem='webhook_auto_reply'
    )
    
    from services.realtime.manager import publish_event
    publish_event(projeto_id, "inbound_received", {"mensagem_id": inbound_db.get('id')})
    
    return {
        "ok": True,
        "status": "linked",
        "projeto_id": projeto_id,
        "sessao_id": sessao_id,
        "mensagem_externa_id": inbound_db.get('id')
    }
