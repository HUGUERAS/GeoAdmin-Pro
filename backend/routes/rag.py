"""
GeoAdmin Pro — RAG: Consulta de Normas INCRA

POST /rag/consultar  → pergunta em linguagem natural → resposta baseada nas normas INCRA
"""

import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/rag", tags=["RAG Normas INCRA"])

SYSTEM_PROMPT = """Você é assistente técnico especializado em georreferenciamento e regularização fundiária rural no Brasil.
Responda com base exclusivamente nos trechos das normas INCRA fornecidos abaixo.
Seja objetivo e preciso. Cite sempre a norma e o artigo/item de referência.
Se a informação não estiver nos trechos fornecidos, diga: "Não encontrei essa informação nas normas indexadas."
"""


class ConsultaRequest(BaseModel):
    pergunta: str
    projeto_id: str | None = None


class ConsultaResponse(BaseModel):
    resposta: str
    fonte: str
    trecho: str


def _get_anthropic():
    import anthropic
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=500,
            detail={"erro": "ANTHROPIC_API_KEY não configurada", "codigo": 500}
        )
    return anthropic.Anthropic(api_key=api_key)


def _get_supabase():
    from main import get_supabase
    return get_supabase()


@router.post("/consultar", response_model=ConsultaResponse)
def consultar_normas(payload: ConsultaRequest):
    if not payload.pergunta.strip():
        raise HTTPException(status_code=400, detail={"erro": "Pergunta não pode estar vazia", "codigo": 400})

    client = _get_anthropic()
    sb = _get_supabase()

    # 1. Gera embedding da pergunta via voyage-3
    emb_resp = client.embeddings.create(
        model="voyage-3",
        input=[payload.pergunta],
    )
    vetor = emb_resp.embeddings[0].embedding

    # 2. Busca chunks mais relevantes por similaridade coseno
    chunks = sb.rpc(
        "buscar_normas",
        {"query_embedding": vetor, "match_count": 3}
    ).execute()

    if not chunks.data:
        return ConsultaResponse(
            resposta="Nenhuma norma INCRA foi indexada ainda. Execute o script backend/scripts/indexar_normas.py primeiro.",
            fonte="—",
            trecho="",
        )

    # 3. Monta contexto com os top-3 chunks
    contexto = "\n\n---\n\n".join(
        f"[{c['fonte']}]\n{c['texto']}" for c in chunks.data
    )

    # 4. Chama claude-sonnet-4-6 com o contexto
    msg = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": f"NORMAS INCRA:\n{contexto}\n\nPERGUNTA: {payload.pergunta}"
            }
        ]
    )

    resposta = msg.content[0].text
    top = chunks.data[0]

    return ConsultaResponse(
        resposta=resposta,
        fonte=top["fonte"],
        trecho=top["texto"][:300] + ("..." if len(top["texto"]) > 300 else ""),
    )
