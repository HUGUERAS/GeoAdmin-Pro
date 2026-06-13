"""
GeoAdmin Pro — Rota de Chat com Agentes/Bots

POST /chat  → pergunta em linguagem natural para o orquestrador
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from middleware.auth import verificar_token

from services.agents.orchestrator import handle_orchestrator_query

router = APIRouter(prefix="/chat", tags=["Chat com Bots"], dependencies=[Depends(verificar_token)])

class ChatRequest(BaseModel):
    mensagem: str
    projeto_id: str
    sessao_id: str | None = None
    lote_id: str | None = None
    participante_id: str | None = None
    canal: str | None = 'mobile'

class ChatResponse(BaseModel):
    sessao_id: str
    resposta: str
    agente_id: str | None
    metadados: dict | None

def _get_supabase():
    from main import get_supabase
    return get_supabase()

@router.post("", response_model=ChatResponse)
def enviar_mensagem(payload: ChatRequest):
    mensagem = payload.mensagem.strip()
    projeto_id = payload.projeto_id.strip()
    sessao_id_req = payload.sessao_id.strip() if payload.sessao_id else None
    lote_id = payload.lote_id.strip() if payload.lote_id else None
    participante_id = payload.participante_id.strip() if payload.participante_id else None
    canal = payload.canal.strip() if payload.canal else 'mobile'

    if not mensagem:
        raise HTTPException(status_code=400, detail={"erro": "A mensagem não pode estar vazia", "codigo": 400})
    if not projeto_id:
        raise HTTPException(status_code=400, detail={"erro": "projeto_id é obrigatório", "codigo": 400})

    sb = _get_supabase()

    try:
        from services.agents.memory import buscar_ou_criar_sessao, salvar_mensagem
        
        # 1. Obter ou criar sessão
        sessao_id = buscar_ou_criar_sessao(
            sb, projeto_id, sessao_id_req, lote_id, participante_id, canal
        )

        # 2. Salvar mensagem do usuário
        salvar_mensagem(
            sb=sb, sessao_id=sessao_id, projeto_id=projeto_id, 
            role='user', conteudo=mensagem,
            lote_id=lote_id, participante_id=participante_id
        )

        # 3. Processar (Passamos a sessão para o orquestrador buscar o histórico internamente)
        resposta_texto = handle_orchestrator_query(projeto_id, mensagem, sb, sessao_id)

        # 4. Salvar resposta do assistente
        agente_id = 'orquestrador' # Poderíamos extrair dinamicamente depois
        salvar_mensagem(
            sb=sb, sessao_id=sessao_id, projeto_id=projeto_id, 
            role='assistant', conteudo=resposta_texto, agente=agente_id,
            lote_id=lote_id, participante_id=participante_id
        )

        return ChatResponse(
            sessao_id=sessao_id, 
            resposta=resposta_texto, 
            agente_id=agente_id, 
            metadados={"canal": canal}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail={"erro": f"Erro interno ao processar a mensagem no bot: {str(e)}", "codigo": 500})

@router.get('/sessoes/{sessao_id}/mensagens')
def buscar_historico(sessao_id: str, projeto_id: str = None):
    sb = _get_supabase()
    from services.agents.memory import carregar_historico_mensagens, buscar_ou_criar_sessao
    if not sessao_id or sessao_id == 'recente':
        if not projeto_id:
            return []
        sessao_id = buscar_ou_criar_sessao(sb, projeto_id)
        if not sessao_id:
            return []
            
    mensagens = carregar_historico_mensagens(sb, sessao_id)
    return {"sessao_id": sessao_id, "mensagens": mensagens}

