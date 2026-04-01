from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Depends
from middleware.auth import verificar_token
from pydantic import BaseModel

router = APIRouter(prefix="/perimetros", tags=["perimetros"], dependencies=[Depends(verificar_token)])


class Vertice(BaseModel):
    lon: float
    lat: float
    nome: Optional[str] = None


class PerimetroCreate(BaseModel):
    projeto_id: str
    nome: str
    tipo: str  # 'original' | 'editado'
    vertices: List[Vertice]


def _get_supabase():
    from main import get_supabase

    return get_supabase()


def _serialize_perimetro(row: Optional[dict]) -> Optional[dict]:
    if not row:
        return None

    return {
        "id": row.get("id"),
        "nome": row.get("nome"),
        "tipo": row.get("tipo"),
        "criado_em": row.get("criado_em"),
        "vertices": row.get("vertices_json") or [],
    }


def buscar_perimetro_ativo(projeto_id: str, supabase=None) -> Optional[dict]:
    """
    Busca o perímetro ativo de um projeto em ordem de prioridade:
    definitivo > editado > original.

    Nota: Mantém 3 queries sequenciais porque a Supabase não permite
    filtros de prioridade complexos (ex: OR com ordenação por tipo).
    Uma consolidação com IN("definitivo","editado","original") não respeitaria
    a ordem de prioridade esperada (busca primeiro definitivo, se não há, editado, etc).
    """
    c = supabase or _get_supabase()

    for tipo in ("definitivo", "editado", "original"):
        res = (
            c.table("perimetros")
            .select("id, nome, tipo, vertices_json, criado_em")
            .eq("projeto_id", projeto_id)
            .eq("tipo", tipo)
            .is_("deleted_at", "null")
            .order("criado_em", desc=True)
            .limit(1)
            .execute()
        )
        if res.data:
            return _serialize_perimetro(res.data[0])

    return None


@router.get("/{projeto_id}")
def listar_perimetros(projeto_id: str):
    """Lista todos os perímetros ativos de um projeto."""
    res = (
        _get_supabase()
        .table("perimetros")
        .select("id, nome, tipo, vertices_json, criado_em")
        .eq("projeto_id", projeto_id)
        .is_("deleted_at", "null")
        .order("criado_em", desc=True)
        .execute()
    )
    return [_serialize_perimetro(row) for row in (res.data or [])]


@router.post("/")
def salvar_perimetro(payload: PerimetroCreate):
    """
    Salva um perímetro.
    Se tipo='editado', primeiro arquiva qualquer 'editado' anterior do mesmo projeto.
    Se tipo='original', só insere se ainda não existir um original para o projeto.
    """
    c = _get_supabase()

    if payload.tipo not in ("original", "editado"):
        raise HTTPException(status_code=422, detail="tipo deve ser 'original' ou 'editado'")

    if payload.tipo == "original":
        # Verificar se já existe original
        existe = (
            c.table("perimetros")
            .select("id")
            .eq("projeto_id", payload.projeto_id)
            .eq("tipo", "original")
            .is_("deleted_at", "null")
            .execute()
        )
        if existe.data:
            # Retorna o existente sem duplicar
            atual = (
                c.table("perimetros")
                .select("id, nome, tipo, vertices_json, criado_em")
                .eq("id", existe.data[0]["id"])
                .maybe_single()
                .execute()
            )
            perimetro = _serialize_perimetro(atual.data)
            return {**(perimetro or {"id": existe.data[0]["id"]}), "status": "ja_existe"}

    if payload.tipo == "editado":
        # Arquivar editados anteriores
        now = datetime.now(timezone.utc).isoformat()
        c.table("perimetros").update({"deleted_at": now}).eq(
            "projeto_id", payload.projeto_id
        ).eq("tipo", "editado").is_("deleted_at", "null").execute()

    vertices_json = [v.model_dump() for v in payload.vertices]

    res = (
        c.table("perimetros")
        .insert(
            {
                "projeto_id": payload.projeto_id,
                "nome": payload.nome,
                "tipo": payload.tipo,
                "vertices_json": vertices_json,
            }
        )
        .execute()
    )
    return _serialize_perimetro(res.data[0]) if res.data else {"status": "ok"}


@router.patch("/{perimetro_id}/definitivo")
def marcar_definitivo(perimetro_id: str):
    """Marca um perímetro como definitivo para geração de documentos.
    Arquiva qualquer outro 'definitivo' anterior do mesmo projeto.
    """
    c = _get_supabase()
    now = datetime.now(timezone.utc).isoformat()

    peri = (
        c.table("perimetros")
        .select("id, projeto_id")
        .eq("id", perimetro_id)
        .is_("deleted_at", "null")
        .execute()
    )
    if not peri.data:
        raise HTTPException(status_code=404, detail="Perímetro não encontrado")

    projeto_id = peri.data[0]["projeto_id"]

    # Arquivar definitivos anteriores deste projeto
    c.table("perimetros").update({"deleted_at": now}).eq(
        "projeto_id", projeto_id
    ).eq("tipo", "definitivo").is_("deleted_at", "null").execute()

    # Promover o atual
    c.table("perimetros").update({"tipo": "definitivo"}).eq("id", perimetro_id).execute()

    return {"status": "ok", "id": perimetro_id}


@router.delete("/{perimetro_id}")
def deletar_perimetro(perimetro_id: str):
    """Soft-delete de um perímetro."""
    now = datetime.now(timezone.utc).isoformat()
    _get_supabase().table("perimetros").update({"deleted_at": now}).eq("id", perimetro_id).execute()
    return {"status": "ok"}
