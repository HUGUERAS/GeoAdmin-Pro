import json
from services.documentos import (
    listar_documentos_pendentes_projeto,
    gerar_checklist_documental
)
from services.notifications import enfileirar_mensagem

def handle_documentos_query(projeto_id: str, mensagem: str, sb, sessao_id: str = None) -> str:
    """
    Agente focado em gestão documental.
    Responde o que falta, gera checklist, recusa e aprova, e cobra participantes.
    """
    
    # 1. Tentar ler a intenção bruta
    msg_lower = mensagem.lower()
    
    if "gerar checklist" in msg_lower or "iniciar checklist" in msg_lower:
        novos = gerar_checklist_documental(sb, projeto_id)
        return f"Checklist base gerado para o projeto. Foram adicionados {len(novos)} novos documentos pendentes."
        
    if "cobrar" in msg_lower or "avise" in msg_lower or "lembrar" in msg_lower:
        pendentes = listar_documentos_pendentes_projeto(sb, projeto_id)
        if not pendentes:
            return "Nenhum documento pendente para cobrar no momento."
            
        # Pega o primeiro como exemplo (ideal seria extrair qual lote ele pediu)
        doc = pendentes[0]
        participante_id = doc.get('participante_id')
        lote_id = doc.get('lote_id')
        
        texto_sugerido = f"Olá! Notei que ainda falta enviar o seu {doc.get('tipo_documento')}. Por favor, anexe o quanto antes para darmos andamento à regularização."
        
        # Simula obter telefone (o Orquestrador injeta no payload, mas o Bot aqui faria lookup)
        resp_cli = sb.table('clientes').select('telefone').eq('id', doc.get('cliente_id')).execute()
        cli_data = getattr(resp_cli, 'data', [])
        telefone = cli_data[0]['telefone'] if cli_data else ""
        
        enfileirar_mensagem(
            sb=sb,
            projeto_id=projeto_id,
            canal='whatsapp',
            conteudo=texto_sugerido,
            telefone=telefone,
            participante_id=participante_id,
            sessao_id=sessao_id,
            agente='bot_documentos',
            origem='sugestao_agente'
        )
        
        return f"Criei um rascunho de cobrança para o documento '{doc.get('tipo_documento')}'. Verifique no Painel de Aprovação."

    # Default lookup de pendencias
    pendentes = listar_documentos_pendentes_projeto(sb, projeto_id)
    if not pendentes:
        return "A situação documental deste projeto está 100% resolvida. Não há pendências!"
        
    resumo = {}
    for p in pendentes:
        tipo = p['tipo_documento']
        resumo[tipo] = resumo.get(tipo, 0) + 1
        
    linhas = [f"- {qtd} {tipo}(s)" for tipo, qtd in resumo.items()]
    
    return "Encontrei as seguintes pendências documentais neste projeto:\n" + "\n".join(linhas)
