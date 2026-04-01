"""
GeoAdmin Pro — Rotas de Pontos

POST /pontos          → insere 1 ponto (com dedup por local_id)
POST /pontos/sync     → batch upsert (offline → online)
GET  /pontos/{id}     → busca ponto por ID
DELETE /pontos/{id}   → soft-delete
"""

import logging
from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends
from middleware.auth import verificar_token
from pydantic import BaseModel

logger = logging.getLogger("geoadmin.pontos")

router = APIRouter(prefix="/pontos", tags=["Pontos"], dependencies=[Depends(verificar_token)])


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


class SyncItemResultado(BaseModel):
    local_id: Optional[str] = None
    nome: str
    status: str
    ponto_id: Optional[str] = None
    erro: Optional[str] = None


# ── Helpers ────────────────────────────────────────────────────────────────────

def _get_supabase():
    from main import get_supabase
    return get_supabase()


def _buscar_existente_por_local_id(sb, local_id: Optional[str]):
    if not local_id:
        return None

    res = (
        sb.table("pontos")
        .select("id")
        .eq("local_id", local_id)
        .maybe_single()
        .execute()
    )
    return res.data


def _normalizar_ponto(payload: PontoCreate) -> dict:
    dados = payload.model_dump(exclude_none=True)
    dados.setdefault("criado_em", datetime.now(timezone.utc).isoformat())

    # ── Correção de altitude elipsoidal → ortométrica (IBGE HNOR 2020) ────────
    # Pontos coletados via Bluetooth NMEA chegam com altitude elipsoidal (WGS84).
    # O backend aplica a correção IBGE para garantir compatibilidade com INCRA.
    # H_ortometrica = h_elipsoidal − N_HNOR2020
    if (
        dados.get("origem") == "bluetooth"
        and dados.get("lat") and dados.get("lon")
        and dados.get("cota") is not None
    ):
        try:
            from integracoes.geoid import corrigir_altitude
            resultado = corrigir_altitude(
                lat=float(dados["lat"]),
                lon=float(dados["lon"]),
                h_elipsoidal=float(dados["cota"]),
                modelo="hnor2020",
            )
            dados["cota"]      = resultado["h_ortometrica"]
            dados["altitude_m"] = resultado["h_ortometrica"]
            dados["_geoide_aplicado"] = True
            dados["_ondulacao_N"]     = resultado["ondulacao_N"]
        except Exception as exc:
            # Geoide não disponível ou ponto fora da cobertura — mantém altitude original
            logger.warning("Falha ao aplicar geoide para ponto %s: %s", dados.get("nome"), exc)
            dados.setdefault("altitude_m", dados.get("cota"))
    else:
        dados.setdefault("altitude_m", dados.get("cota"))

    return dados


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.post("", summary="Inserir um ponto", status_code=201)
def criar_ponto(payload: PontoCreate):
    sb = _get_supabase()

    # Dedup: verifica se local_id já existe
    existente = _buscar_existente_por_local_id(sb, payload.local_id)
    if existente:
        return {**existente, "duplicado": True}

    dados = _normalizar_ponto(payload)

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
    itens: list[dict] = []

    # Batch: coleta todos os local_ids e faz uma única query para buscar duplicados
    local_ids_payload = [p.local_id for p in payload.pontos if p.local_id]
    existentes_mapa = {}

    if local_ids_payload:
        res_existentes = (
            sb.table("pontos")
            .select("id, local_id")
            .in_("local_id", local_ids_payload)
            .execute()
        )
        existentes_mapa = {item["local_id"]: item for item in (res_existentes.data or [])}

    for p in payload.pontos:
        try:
            # Dedup por local_id usando mapa pre-carregado
            existente = existentes_mapa.get(p.local_id)
            if existente:
                duplicados += 1
                itens.append(
                    SyncItemResultado(
                        local_id=p.local_id,
                        nome=p.nome,
                        status="duplicado",
                        ponto_id=existente.get("id"),
                    ).model_dump()
                )
                continue

            dados = _normalizar_ponto(p)
            res = sb.table("pontos").insert(dados).execute()
            if res.data:
                sincronizados += 1
                itens.append(
                    SyncItemResultado(
                        local_id=p.local_id,
                        nome=p.nome,
                        status="sincronizado",
                        ponto_id=res.data[0].get("id"),
                    ).model_dump()
                )
            else:
                itens.append(
                    SyncItemResultado(
                        local_id=p.local_id,
                        nome=p.nome,
                        status="erro",
                        erro="sem retorno",
                    ).model_dump()
                )
        except Exception as exc:
            itens.append(
                SyncItemResultado(
                    local_id=p.local_id,
                    nome=p.nome,
                    status="erro",
                    erro=str(exc),
                ).model_dump()
            )

    erros = [item for item in itens if item["status"] == "erro"]
    sincronizados_local_ids = [
        item["local_id"] for item in itens
        if item["status"] == "sincronizado" and item.get("local_id")
    ]
    duplicados_local_ids = [
        item["local_id"] for item in itens
        if item["status"] == "duplicado" and item.get("local_id")
    ]
    erro_local_ids = [
        item["local_id"] for item in itens
        if item["status"] == "erro" and item.get("local_id")
    ]

    return {
        "sincronizados": sincronizados,
        "duplicados": duplicados,
        "erros": erros,
        "total_recebido": len(payload.pontos),
        "itens": itens,
        "sincronizados_local_ids": sincronizados_local_ids,
        "duplicados_local_ids": duplicados_local_ids,
        "erro_local_ids": erro_local_ids,
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
