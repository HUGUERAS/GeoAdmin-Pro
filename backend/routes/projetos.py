"""
GeoAdmin Pro — Rotas de Projetos

GET  /projetos              → lista todos os projetos
GET  /projetos/{id}         → projeto com seus pontos
PATCH /projetos/{id}        → atualiza metadados (numero_job, municipio, etc.)
POST /projetos              → cria novo projeto
"""

from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/projetos", tags=["Projetos"])


# ── Schemas ────────────────────────────────────────────────────────────────────

class ProjetoCreate(BaseModel):
    nome: str
    zona_utm: str = "23S"
    status: str = "medicao"
    numero_job: Optional[str] = None
    municipio: Optional[str] = None
    estado: Optional[str] = None
    cliente_id: Optional[str] = None


class ProjetoUpdate(BaseModel):
    nome: Optional[str] = None
    numero_job: Optional[str] = None
    municipio: Optional[str] = None
    estado: Optional[str] = None
    status: Optional[str] = None
    zona_utm: Optional[str] = None


# ── Helpers ────────────────────────────────────────────────────────────────────

def _get_supabase():
    from main import get_supabase
    return get_supabase()


def _projeto_ou_404(sb, projeto_id: str) -> dict:
    res = sb.table("projetos").select("*").eq("id", projeto_id).maybe_single().execute()
    if not res.data:
        raise HTTPException(status_code=404, detail={"erro": "Projeto não encontrado", "codigo": 404})
    return res.data


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.get("", summary="Listar todos os projetos")
def listar_projetos():
    sb = _get_supabase()
    res = sb.table("vw_projetos_completo").select("*").order("criado_em", desc=True).execute()
    return {"total": len(res.data), "projetos": res.data}


@router.post("", summary="Criar novo projeto", status_code=201)
def criar_projeto(payload: ProjetoCreate):
    sb = _get_supabase()
    dados = payload.model_dump(exclude_none=True)
    res = sb.table("projetos").insert(dados).execute()
    if not res.data:
        raise HTTPException(status_code=500, detail={"erro": "Falha ao criar projeto", "codigo": 500})
    return res.data[0]


@router.get("/{projeto_id}", summary="Buscar projeto com seus pontos")
def buscar_projeto(projeto_id: str):
    sb = _get_supabase()
    projeto = _projeto_ou_404(sb, projeto_id)

    # Aliases para o app mobile
    projeto["projeto_nome"] = projeto.get("nome", "")

    # Busca nome do cliente
    if projeto.get("cliente_id"):
        cli = sb.table("clientes").select("nome, municipio").eq("id", projeto["cliente_id"]).maybe_single().execute()
        if cli.data:
            projeto["cliente_nome"] = cli.data.get("nome", "")
            projeto.setdefault("municipio", cli.data.get("municipio", ""))

    # Pontos do projeto
    pontos_res = (
        sb.table("pontos")
        .select("id, nome, altitude_m, descricao, codigo")
        .eq("projeto_id", projeto_id)
        .execute()
    )
    projeto["pontos"] = pontos_res.data
    projeto["total_pontos"] = len(pontos_res.data)
    return projeto


@router.patch("/{projeto_id}", summary="Atualizar metadados do projeto")
def atualizar_projeto(projeto_id: str, payload: ProjetoUpdate):
    sb = _get_supabase()
    _projeto_ou_404(sb, projeto_id)

    dados = payload.model_dump(exclude_none=True)
    if not dados:
        raise HTTPException(status_code=400, detail={"erro": "Nenhum campo para atualizar", "codigo": 400})

    res = sb.table("projetos").update(dados).eq("id", projeto_id).execute()
    return res.data[0]
