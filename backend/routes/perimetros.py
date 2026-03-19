from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()
_sb = None

def sb():
    global _sb
    if _sb is None:
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")
        if not url or not key:
            raise HTTPException(status_code=500, detail="Supabase não configurado")
        _sb = create_client(url, key)
    return _sb


router = APIRouter(prefix="/perimetros", tags=["perimetros"])


class Vertice(BaseModel):
    lon: float
    lat: float
    nome: Optional[str] = None


class PerimetroCreate(BaseModel):
    projeto_id: str
    nome: str
    tipo: str  # 'original' | 'editado'
    vertices: List[Vertice]


@router.get("/{projeto_id}")
def listar_perimetros(projeto_id: str):
    """Lista todos os perímetros ativos de um projeto."""
    res = (
        sb()
        .table("perimetros")
        .select("id, nome, tipo, vertices_json, criado_em")
        .eq("projeto_id", projeto_id)
        .is_("deleted_at", "null")
        .order("criado_em")
        .execute()
    )
    return res.data or []


@router.post("/")
def salvar_perimetro(payload: PerimetroCreate):
    """
    Salva um perímetro.
    Se tipo='editado', primeiro arquiva qualquer 'editado' anterior do mesmo projeto.
    Se tipo='original', só insere se ainda não existir um original para o projeto.
    """
    c = sb()

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
            return {"id": existe.data[0]["id"], "status": "ja_existe"}

    if payload.tipo == "editado":
        # Arquivar editados anteriores
        from datetime import datetime, timezone
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
    return res.data[0] if res.data else {"status": "ok"}


@router.delete("/{perimetro_id}")
def deletar_perimetro(perimetro_id: str):
    """Soft-delete de um perímetro."""
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()
    sb().table("perimetros").update({"deleted_at": now}).eq("id", perimetro_id).execute()
    return {"status": "ok"}
