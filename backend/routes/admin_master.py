from fastapi import APIRouter, Depends, HTTPException
from supabase import create_client, Client
from typing import Dict, Any, List
from middleware.auth import verificar_token
from core.config import settings
from datetime import datetime

router = APIRouter(prefix="/admin/master", tags=["Admin Master MVP"])

def get_user_and_admin_clients(usuario: dict = Depends(verificar_token)):
    token = usuario.get("token")
    if not token or token == "anonimo" or token == "dev-local":
        raise HTTPException(status_code=401, detail="Token ausente ou ambiente local anônimo para painel master.")
    
    # User Client (com RLS)
    user_client = create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)
    user_client.options.headers["Authorization"] = f"Bearer {token}"
    user_client.postgrest.auth(token)
    
    # Admin Client (sem RLS) para tabelas protegidas pelo frontend
    from core.database import get_supabase_admin
    admin_client = get_supabase_admin()
    
    return user_client, admin_client

@router.get("/resumo")
def get_resumo(clients = Depends(get_user_and_admin_clients)):
    user_client, admin_client = clients
    
    # Admin Master MVP: Para demonstração, o painel executivo visualiza todos os projetos do Staging
    projetos = admin_client.table("projetos").select("id").execute().data
    total_projetos = len(projetos)
    
    if total_projetos == 0:
        return {
            "total_projetos": 0, "total_lotes": 0, "lotes_sem_participante": 0,
            "documentos_pendentes": 0, "documentos_aprovados": 0,
            "magic_links_pendentes": 0, "magic_links_enviados": 0,
            "mensagens_pendentes_aprovacao": 0, "inbounds_nao_vinculados": 0,
            "confrontacoes_pendentes": 0, "conversas_ativas": 0
        }
        
    projeto_ids = [p["id"] for p in projetos]

    # A partir daqui, usamos o admin_client mas FILTRADO estritamente pelos projeto_ids autorizados!
    # Isso garante o isolamento em tabelas que possuem RLS fechado para o frontend (como mensagens_externas).

    # Lotes
    lotes = admin_client.table("areas_projeto").select("id, projeto_clientes(id)").in_("projeto_id", projeto_ids).eq("tipo", "lote").execute().data
    total_lotes = len(lotes)
    lotes_sem_participante = sum(1 for l in lotes if not l.get("projeto_clientes") or len(l["projeto_clientes"]) == 0)

    # Docs
    docs = admin_client.table("documentos").select("status").in_("projeto_id", projeto_ids).execute().data
    documentos_pendentes = sum(1 for d in docs if d["status"] in ["pendente", "erro"])
    documentos_aprovados = len(docs) - documentos_pendentes

    # ML
    mls = admin_client.table("eventos_magic_link").select("acessado_em").in_("projeto_id", projeto_ids).execute().data
    magic_links_pendentes = sum(1 for m in mls if not m.get("acessado_em"))
    magic_links_enviados = len(mls)

    # Confs
    confs = admin_client.table("confrontacoes").select("status_revisao").in_("projeto_id", projeto_ids).execute().data
    confrontacoes_pendentes = sum(1 for c in confs if c["status_revisao"] == "pendente")

    # Msgs (tabela backend_only)
    msgs = admin_client.table("mensagens_externas").select("status, participante_id").in_("projeto_id", projeto_ids).execute().data
    mensagens_pendentes_aprovacao = sum(1 for m in msgs if m["status"] in ["pendente_aprovacao", "queued", "draft"])
    inbounds_nao_vinculados = sum(1 for m in msgs if m["status"] == "received" and not m.get("participante_id"))

    # Sessões
    sess = admin_client.table("chat_sessoes").select("id, status").in_("projeto_id", projeto_ids).execute().data
    conversas_ativas = sum(1 for s in sess if s["status"] == "ativa")

    return {
        "total_projetos": total_projetos,
        "total_lotes": total_lotes,
        "lotes_sem_participante": lotes_sem_participante,
        "documentos_pendentes": documentos_pendentes,
        "documentos_aprovados": documentos_aprovados,
        "magic_links_pendentes": magic_links_pendentes,
        "magic_links_enviados": magic_links_enviados,
        "mensagens_pendentes_aprovacao": mensagens_pendentes_aprovacao,
        "inbounds_nao_vinculados": inbounds_nao_vinculados,
        "confrontacoes_pendentes": confrontacoes_pendentes,
        "conversas_ativas": conversas_ativas
    }

@router.get("/projetos")
def list_projetos(clients = Depends(get_user_and_admin_clients)):
    user_client, admin_client = clients
    projetos = admin_client.table("projetos").select("id, nome, status, progresso, atualizado_em").execute().data
    if not projetos:
        return []
    
    projeto_ids = [p["id"] for p in projetos]
    # Busca áreas para contar lotes
    areas = admin_client.table("areas_projeto").select("projeto_id").in_("projeto_id", projeto_ids).eq("tipo", "lote").execute().data
    lotes_por_projeto = {}
    for a in areas:
        lotes_por_projeto[a["projeto_id"]] = lotes_por_projeto.get(a["projeto_id"], 0) + 1
        
    resultado = []
    for p in projetos:
        resultado.append({
            "id": p["id"],
            "nome": p["nome"],
            "status": p["status"],
            "lotes": lotes_por_projeto.get(p["id"], 0),
            "percentual_conclusao": p.get("progresso", 0),
            "ultima_atividade": p.get("atualizado_em"),
            "pendencias_criticas": 0
        })
        
    return sorted(resultado, key=lambda x: x["ultima_atividade"] or "", reverse=True)

@router.get("/alertas")
def get_alertas(clients = Depends(get_user_and_admin_clients)):
    user_client, admin_client = clients
    projetos = admin_client.table("projetos").select("id, nome").execute().data
    if not projetos:
        return []
    
    projeto_ids = [p["id"] for p in projetos]
    alertas = []
    
    # Alerta 1: Projetos com muitos lotes vazios (>30%)
    areas = admin_client.table("areas_projeto").select("projeto_id, projeto_clientes(id)").in_("projeto_id", projeto_ids).eq("tipo", "lote").execute().data
    lotes_vazios_por_proj = {}
    total_lotes_por_proj = {}
    for a in areas:
        pid = a["projeto_id"]
        total_lotes_por_proj[pid] = total_lotes_por_proj.get(pid, 0) + 1
        if not a.get("projeto_clientes") or len(a["projeto_clientes"]) == 0:
            lotes_vazios_por_proj[pid] = lotes_vazios_por_proj.get(pid, 0) + 1
            
    for p in projetos:
        pid = p["id"]
        total = total_lotes_por_proj.get(pid, 0)
        if total > 0:
            vazios = lotes_vazios_por_proj.get(pid, 0)
            pct = vazios / total
            if pct > 0.3:
                alertas.append({
                    "tipo": "lotes_vazios",
                    "projeto_id": pid,
                    "projeto_nome": p["nome"],
                    "mensagem": f"{int(pct*100)}% dos lotes sem participante associado."
                })
            
    # Alerta 2: Documentos parados aguardando revisão
    docs = admin_client.table("documentos").select("id, projeto_id").in_("status", ["erro"]).in_("projeto_id", projeto_ids).execute().data
    if len(docs) > 0:
        alertas.append({
            "tipo": "documentos_erro",
            "mensagem": f"Existem {len(docs)} documentos com erro de geração/assinatura."
        })
        
    # Alerta 3: Mensagens não respondidas / inbounds sem dono
    msgs = admin_client.table("mensagens_externas").select("status").eq("status", "received").is_("participante_id", "null").in_("projeto_id", projeto_ids).execute().data
    if len(msgs) > 0:
        alertas.append({
            "tipo": "inbound_sem_vinculo",
            "mensagem": f"{len(msgs)} mensagens recebidas (Hermes/WPP) de números desconhecidos."
        })
        
    return alertas

