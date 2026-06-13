import os
import json
import anthropic
from services.agents.bot_condominio import handle_condominio_query
from services.agents.bot_magic_links import handle_magic_link_query
from services.agents.bot_pendencias import handle_pendencias_query
from services.agents.bot_documentos import handle_documentos_query

def _get_anthropic_client() -> anthropic.Anthropic:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY não configurada")
    return anthropic.Anthropic(api_key=api_key)

def handle_orchestrator_query(projeto_id: str, message: str, sb, sessao_id: str = None) -> str:
    message_lower = message.lower()
    
    doc_keywords = ['documento', 'upload', 'comprovante', 'rg', 'cpf', 'procuração', 'termo', 'checklist']
    if any(k in message_lower for k in doc_keywords):
        return handle_documentos_query(projeto_id, message, sb, sessao_id)

    client = _get_anthropic_client()
    
    from services.agents.memory import carregar_historico_mensagens
    historico = carregar_historico_mensagens(sb, sessao_id, limite=10) if sessao_id else []
    
    messages = []
    # Injetar contexto histórico
    for msg in historico:
        role = "assistant" if msg['role'] in ('assistant', 'tool') else "user"
        # Para evitar erros de API com empty contents ou roles mal formados, mantemos simples:
        messages.append({"role": role, "content": msg.get('conteudo', '')})

    messages.append({
        "role": "user",
        "content": f"Mensagem atual (Projeto ID {projeto_id}):\n'{message}'"
    })

    tools = [
        {
            "name": "delegate_to_condominio",
            "description": "Delega a pergunta para o bot de condomínio. Use isso quando a pergunta for sobre lotes em geral, mapa ou andamento histórico do projeto.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "reason": {"type": "string", "description": "Motivo do redirecionamento."}
                },
                "required": ["reason"]
            }
        },
        {
            "name": "delegate_to_magic_links",
            "description": "Delega a pergunta para o bot de magic links. Use isso quando a pergunta for sobre formulários enviados, consultar links gerados ou reenviar link.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "reason": {"type": "string", "description": "Motivo do redirecionamento."}
                },
                "required": ["reason"]
            }
        },
        {
            "name": "delegate_to_pendencias",
            "description": "Delega a pergunta para o bot operacional. Use isso para diagnóstico: gargalos, resumo de pendências, quem falta assinar, lotes sem dono, ou qual o próximo passo.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "reason": {"type": "string", "description": "Motivo do redirecionamento."}
                },
                "required": ["reason"]
            }
        }
    ]

    system_prompt = (
        "Você é o Bot Orquestrador do GeoAdmin. "
        "Analise o histórico e a intenção da mensagem atual para redirecionar ao agente especialista correto usando as ferramentas. "
        "Se for cumprimento ou algo geral, responda você mesmo."
    )

    response = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=1024,
        system=system_prompt,
        tools=tools,
        messages=messages
    )

    if response.stop_reason == "tool_use":
        for content_block in response.content:
            if content_block.type == "tool_use":
                if content_block.name == "delegate_to_condominio":
                    return handle_condominio_query(projeto_id, message, sb, sessao_id)
                elif content_block.name == "delegate_to_magic_links":
                    return handle_magic_link_query(projeto_id, message, sb, sessao_id)
                elif content_block.name == "delegate_to_pendencias":
                    return handle_pendencias_query(projeto_id, message, sb, sessao_id)

    return response.content[0].text
