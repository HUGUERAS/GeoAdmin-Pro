import os
import json
import anthropic

def _get_anthropic_client() -> anthropic.Anthropic:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY não configurada")
    return anthropic.Anthropic(api_key=api_key)

def listar_links_gerados(sb, projeto_id: str) -> dict:
    from integracoes.projeto_clientes import listar_participantes_projeto
    try:
        participantes = listar_participantes_projeto(sb, projeto_id)
        links = [
            {
                "nome": p.get("nome"),
                "papel": p.get("papel"),
                "magic_link_token": p.get("magic_link_token")
            }
            for p in participantes if p.get("magic_link_token")
        ]
        return {"total_links": len(links), "detalhes": links}
    except Exception as e:
        return {"erro": str(e)}

def handle_magic_link_query(projeto_id: str, message: str, sb, sessao_id: str = None) -> str:
    client = _get_anthropic_client()
    
    tools = [
        {
            "name": "listar_links_gerados",
            "description": "Lista todos os participantes do projeto que já possuem um magic link gerado.",
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
        "Você é o Bot de Magic Links do GeoAdmin. "
        "Sua função é auxiliar no acompanhamento e gestão dos formulários enviados aos clientes. "
        "Você pode listar quem já recebeu o link mágico consultando a ferramenta listar_links_gerados. "
        "Seja proativo e educado."
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
                if content_block.name == "listar_links_gerados":
                    pid = content_block.input.get("projeto_id", projeto_id)
                    tool_result = json.dumps(listar_links_gerados(sb, pid))
                    
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
