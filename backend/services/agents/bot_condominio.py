import os
import json
from typing import Any
import anthropic

def _get_anthropic_client() -> anthropic.Anthropic:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY não configurada")
    return anthropic.Anthropic(api_key=api_key)

def obter_resumo_projeto(sb, projeto_id: str) -> dict:
    from integracoes.areas_projeto import listar_areas_projeto
    areas = listar_areas_projeto(projeto_id, sb=sb)
    total = len(areas)
    prontos = sum(1 for a in areas if a.get("status_documental") == "documentacao_ok")
    com_participante = sum(1 for a in areas if a.get("participantes_total", 0) > 0)
    return {
        "total_lotes": total,
        "lotes_prontos": prontos,
        "lotes_com_cliente": com_participante
    }

def handle_condominio_query(projeto_id: str, message: str, sb, sessao_id: str = None) -> str:
    client = _get_anthropic_client()
    
    tools = [
        {
            "name": "obter_resumo_projeto",
            "description": "Obtém um resumo do projeto contendo número de lotes, quantos têm participantes vinculados, e quantos estão prontos ou pendentes.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "projeto_id": {"type": "string", "description": "ID do projeto."}
                },
                "required": ["projeto_id"]
            }
        }
    ]

    messages = [
        {
            "role": "user",
            "content": f"Contexto do Projeto ID: {projeto_id}\nPergunta: {message}"
        }
    ]

    system_prompt = (
        "Você é o Bot de Projeto Condominial do GeoAdmin. "
        "Sua função é auxiliar o gestor do condomínio ou o topógrafo a entender o status do projeto. "
        "Sempre use a ferramenta obter_resumo_projeto se a pergunta for sobre o andamento geral ou a quantidade de lotes. "
        "Ao responder, seja claro, educado e utilize uma linguagem focada no status dos lotes."
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
                if content_block.name == "obter_resumo_projeto":
                    pid = content_block.input.get("projeto_id", projeto_id)
                    try:
                        resumo = obter_resumo_projeto(sb, pid)
                        tool_result = json.dumps(resumo)
                    except Exception as e:
                        tool_result = f"Erro ao buscar resumo: {str(e)}"
                    
                    messages.append({
                        "role": "assistant",
                        "content": [
                            {"type": "tool_use", "id": content_block.id, "name": content_block.name, "input": content_block.input}
                        ]
                    })
                    messages.append({
                        "role": "user",
                        "content": [
                            {"type": "tool_result", "tool_use_id": content_block.id, "content": tool_result}
                        ]
                    })
                    
                    final_response = client.messages.create(
                        model="claude-3-5-sonnet-20241022",
                        max_tokens=1024,
                        system=system_prompt,
                        tools=tools,
                        messages=messages
                    )
                    return final_response.content[0].text

    return response.content[0].text
