"""
GeoAdmin Pro — Rotas de Pontos

POST /pontos          → insere 1 ponto (com dedup por local_id)
POST /pontos/sync     → batch upsert (offline → online)
GET  /pontos/{id}     → busca ponto por ID
DELETE /pontos/{id}   → soft-delete
"""

from typing import Optional, List
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/pontos", tags=["Pontos"])


# ── Schemas ────────────────────────────────────────────────────────────────────

class PontoCreate(BaseModel):
    projeto_id: str
    nome: str
    lat: float
    lon: float
    norte: float
    este: float
    cota: float
    codigo: str = "TP"
    status_gnss: str = "Fixo"
    satelites: int = 0
    pdop: float = 0.0
    sigma_e: float = 0.0
    sigma_n: float = 0.0
    sigma_u: float = 0.0
    origem: str = "gnss"          # "gnss" | "bluetooth" | "manual"
    local_id: Optional[str] = None  # UUID do dispositivo para dedup
    coletado_em: Optional[str] = None  # ISO timestamp do dispositivo


class SyncPayload(BaseModel):
    pontos: List[PontoCreate]


# ── Helpers ────────────────────────────────────────────────────────────────────

def _get_supabase():
    from main import get_supabase
    return get_supabase()


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.post("", summary="Inserir um ponto", status_code=201)
def criar_ponto(payload: PontoCreate):
    sb = _get_supabase()

    # Dedup: verifica se local_id já existe
    if payload.local_id:
        existente = (
            sb.table("pontos")
            .select("id")
            .eq("local_id", payload.local_id)
            .maybe_single()
            .execute()
        )
        if existente.data:
            return {**existente.data, "duplicado": True}

    dados = payload.model_dump(exclude_none=True)
    dados.setdefault("criado_em", datetime.now(timezone.utc).isoformat())

    res = sb.table("pontos").insert(dados).execute()
    if not res.data:
        raise HTTPException(
            status_code=500,
            detail={"erro": "Falha ao inserir ponto", "codigo": 500}
        )
    return res.data[0]


@router.post("/sync", summary="Sincronizar pontos coletados offline")
def sincronizar_pontos(payload: SyncPayload):
    sb = _get_supabase()
    sincronizados = 0
    duplicados = 0
    erros: list = []

    for p in payload.pontos:
        try:
            # Dedup por local_id
            if p.local_id:
                existente = (
                    sb.table("pontos")
                    .select("id")
                    .eq("local_id", p.local_id)
                    .maybe_single()
                    .execute()
                )
                if existente.data:
                    duplicados += 1
                    continue

            dados = p.model_dump(exclude_none=True)
            dados.setdefault("criado_em", datetime.now(timezone.utc).isoformat())
            res = sb.table("pontos").insert(dados).execute()
            if res.data:
                sincronizados += 1
            else:
                erros.append({"local_id": p.local_id, "nome": p.nome, "erro": "sem retorno"})
        except Exception as exc:
            erros.append({"local_id": p.local_id, "nome": p.nome, "erro": str(exc)})

    return {
        "sincronizados": sincronizados,
        "duplicados": duplicados,
        "erros": erros,
        "total_recebido": len(payload.pontos),
    }


@router.get("/{ponto_id}", summary="Buscar ponto por ID")
def buscar_ponto(ponto_id: str):
    sb = _get_supabase()
    res = sb.table("pontos").select("*").eq("id", ponto_id).maybe_single().execute()
    if not res.data:
        raise HTTPException(
            status_code=404,
            detail={"erro": "Ponto não encontrado", "codigo": 404}
        )
    return res.data


@router.delete("/{ponto_id}", summary="Remover ponto (soft-delete)")
def deletar_ponto(ponto_id: str):
    sb = _get_supabase()
    res = sb.table("pontos").select("id").eq("id", ponto_id).maybe_single().execute()
    if not res.data:
        raise HTTPException(
            status_code=404,
            detail={"erro": "Ponto não encontrado", "codigo": 404}
        )
    sb.table("pontos").update(
        {"deleted_at": datetime.now(timezone.utc).isoformat()}
    ).eq("id", ponto_id).execute()
    return {"ok": True, "id": ponto_id}
