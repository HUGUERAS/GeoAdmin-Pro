import json
from services.agents.pendencias import (
    resumir_pendencias_projeto,
    listar_lotes_sem_participante,
    listar_magic_links_pendentes
)

def build_pendencias_prompt() -> str:
    return """Você é o Agente de Pendências Operacionais do GeoAdmin Pro.
Seu objetivo é analisar os dados de pendências do projeto condominial e responder de forma executiva, clara e focada em próximos passos.
Nunca invente dados. Use as ferramentas disponíveis para extrair a real situação dos lotes, magic links e confrontações.
"""

def get_pendencias_tools() -> list:
    return [
        {
            "name": "resumir_pendencias",
            "description": "Obtem o resumo operacional agregado do projeto: total de lotes, quantos estão sem participante, magic links pendentes, etc.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "projeto_id": {"type": "string", "description": "UUID do projeto"}
                },
                "required": ["projeto_id"]
            }
        },
        {
            "name": "listar_lotes_sem_dono",
            "description": "Retorna a lista de lotes que ainda aguardam vinculação de um participante",
            "input_schema": {
                "type": "object",
                "properties": {
                    "projeto_id": {"type": "string", "description": "UUID do projeto"}
                },
                "required": ["projeto_id"]
            }
        },
        {
            "name": "sugerir_mensagem_participante",
            "description": "Cria um rascunho de mensagem para o canal externo (whatsapp ou hermes) para notificar o cliente sobre pendencias. O bot nao envia a mensagem, apenas cria o rascunho (draft) para aprovacao do gerente.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "projeto_id": {"type": "string", "description": "UUID do projeto"},
                    "lote_id": {"type": "string", "description": "UUID do lote (area_id) opcional se a mensagem for especifica do lote"},
                    "telefone": {"type": "string", "description": "Telefone do participante (opcional, pode vir do banco)"},
                    "canal": {"type": "string", "description": "whatsapp ou hermes"},
                    "conteudo": {"type": "string", "description": "O texto simpatico e direto da mensagem a ser enviada"}
                },
                "required": ["projeto_id", "canal", "conteudo"]
            }
        }
    ]

def handle_pendencias_query(projeto_id: str, message: str, sb, sessao_id: str = None) -> str:
    from main import _get_anthropic_client
    client = _get_anthropic_client()
    
    from services.agents.memory import carregar_historico_mensagens
    historico = carregar_historico_mensagens(sb, sessao_id, limite=10) if sessao_id else []
    
    messages = []
    for msg in historico:
        role = "assistant" if msg['role'] == "assistant" else "user"
        messages.append({"role": role, "content": msg['conteudo']})
    
    messages.append({"role": "user", "content": message})
    
    system_prompt = build_pendencias_prompt()
    tools = get_pendencias_tools()

    try:
        response = client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=1024,
            system=system_prompt,
            messages=messages,
            tools=tools
        )

        if response.stop_reason == "tool_use":
            tool_use = next(block for block in response.content if block.type == "tool_use")
            tool_name = tool_use.name
            
            if tool_name == "resumir_pendencias":
                resultado = resumir_pendencias_projeto(sb, projeto_id)
            elif tool_name == "listar_lotes_sem_dono":
                resultado = listar_lotes_sem_participante(sb, projeto_id)
            elif tool_name == "sugerir_mensagem_participante":
                from services.notifications import enfileirar_mensagem
                resultado = enfileirar_mensagem(
                    sb=sb,
                    projeto_id=tool_use.input.get("projeto_id"),
                    canal=tool_use.input.get("canal"),
                    conteudo=tool_use.input.get("conteudo"),
                    telefone=tool_use.input.get("telefone"),
                    lote_id=tool_use.input.get("lote_id"),
                    sessao_id=sessao_id,
                    agente='bot_pendencias'
                )
            else:
                resultado = {"erro": "Ferramenta desconhecida"}
            
            messages.append({"role": "assistant", "content": response.content})
            messages.append({
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": tool_use.id,
                        "content": json.dumps(resultado, ensure_ascii=False)
                    }
                ]
            })
            
            final_response = client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=1024,
                system=system_prompt,
                messages=messages
            )
            return final_response.content[0].text
        else:
            return response.content[0].text
    except Exception as e:
        return f"Erro ao processar sua solicitação operacional: {str(e)}"
