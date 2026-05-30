"""
VERTEX — Endpoint de lead do bot WhatsApp.

POST /vertex/lead
  Entrada (JSON): { "telefone": "5561...", "nome"?: "...", "cpf"?: "..." }
  Header opcional de seguranca: X-Vertex-Secret (validado se VERTEX_LEAD_SECRET estiver setado)

Fluxo:
  1. Acha/cria o cliente (tolerante ao schema do banco LIVE).
  2. Vincula ao projeto "Acampamento Jose Wilker".
  3. Gera o magic link e devolve a URL pronta para o cliente preencher o formulario.

Projetado para o banco LIVE jrlrlsotwsiidglcbifo (schema sem owner_id/tipo_pessoa),
por isso usa insercao minima e tolerante, sem reaproveitar _payload_cliente.
"""

from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

logger = logging.getLogger("vertex.lead")
router = APIRouter(tags=["VERTEX Lead"])

# Cada lead do WhatsApp vira o SEU proprio projeto (modelo GeoAdmin: 1 projeto por
# cliente/area). O assentamento Jose Wilker e referenciado no nome/descricao.
ASSENTAMENTO_NOME = os.getenv("VERTEX_ASSENTAMENTO", "Jose Wilker")
ASSENTAMENTO_MUNICIPIO = os.getenv("VERTEX_MUNICIPIO", "Sobradinho")
ASSENTAMENTO_UF = os.getenv("VERTEX_UF", "DF")
ASSENTAMENTO_DESCRICAO = os.getenv(
    "VERTEX_DESCRICAO",
    "Lead WhatsApp - Assentamento Jose Wilker (Edital ETR 03/2026)",
)
ASSENTAMENTO_PROJETO_ID = os.getenv(
    "VERTEX_ASSENTAMENTO_PROJETO_ID",
    "a56b5fd1-cfa3-4855-ab29-6863dcaf5cc5",
).strip()
MAGIC_LINK_DIAS = int(os.getenv("VERTEX_MAGIC_LINK_DIAS", "30"))


class LeadPayload(BaseModel):
    telefone: str = Field(..., min_length=8, description="Telefone do cliente (com DDD)")
    nome: Optional[str] = ""
    cpf: Optional[str] = ""


def _get_supabase():
    from main import get_supabase as _get
    return _get()


def _resolver_app_url() -> str:
    for chave in ("APP_URL", "PUBLIC_APP_URL", "PUBLIC_BASE_URL"):
        valor = (os.environ.get(chave) or "").strip()
        if valor:
            return valor.rstrip("/")
    vercel = (os.environ.get("VERCEL_URL") or "").strip()
    if vercel:
        return f"https://{vercel.lstrip('/')}".rstrip("/")
    return "http://127.0.0.1:8000"


def _so_digitos(valor: str | None) -> str:
    return "".join(ch for ch in str(valor or "") if ch.isdigit())


def _dados(resposta: Any) -> list[dict[str, Any]]:
    return getattr(resposta, "data", None) or []


def _verificar_segredo(request: Request) -> None:
    segredo_esperado = (os.getenv("VERTEX_LEAD_SECRET") or "").strip()
    if not segredo_esperado:
        return  # sem segredo configurado -> aberto (compat)
    enviado = (request.headers.get("x-vertex-secret") or "").strip()
    if enviado != segredo_esperado:
        raise HTTPException(401, {"erro": "Segredo invalido", "codigo": 401})


def _achar_cliente_por_telefone(sb, telefone: str) -> dict[str, Any] | None:
    tel = _so_digitos(telefone)
    if not tel:
        return None
    try:
        resposta = (
            sb.table("clientes")
            .select("id, nome, telefone, magic_link_token")
            .eq("telefone", tel)
            .is_("deleted_at", "null")
            .limit(1)
            .execute()
        )
    except Exception:
        return None
    dados = _dados(resposta)
    return dados[0] if dados else None


def _criar_cliente_tolerante(sb, nome: str, telefone: str, cpf: str) -> str:
    """Insere cliente tentando do payload mais completo ao mais minimo,
    para funcionar em qualquer variacao de schema."""
    tel = _so_digitos(telefone)
    doc = _so_digitos(cpf)
    nome_final = (nome or "").strip() or "Cliente WhatsApp"

    tentativas = [
        {"nome": nome_final, "telefone": tel, "cpf_cnpj": doc or None},
        {"nome": nome_final, "telefone": tel, "cpf": doc or None},
        {"nome": nome_final, "telefone": tel},
    ]
    ultimo_erro: Exception | None = None
    for payload in tentativas:
        try:
            resposta = sb.table("clientes").insert(payload).execute()
            dados = _dados(resposta)
            if dados:
                return str(dados[0]["id"])
        except Exception as exc:
            ultimo_erro = exc
            continue
    if ultimo_erro:
        raise ultimo_erro
    raise RuntimeError("Nao foi possivel criar o cliente")


def _achar_vinculo_principal_do_cliente(sb, cliente_id: str) -> dict[str, Any] | None:
    """Reaproveita o projeto/vinculo principal que o cliente ja tem (se houver)."""
    try:
        resposta = (
            sb.table("projeto_clientes")
            .select("id, projeto_id, area_id, magic_link_token")
            .eq("cliente_id", cliente_id)
            .eq("principal", True)
            .is_("deleted_at", "null")
            .limit(1)
            .execute()
        )
    except Exception:
        return None
    dados = _dados(resposta)
    return dados[0] if dados else None


def _criar_projeto_lead(sb, nome: str, telefone: str, cliente_id: str) -> str:
    """Cria um projeto dedicado para o lead (1 projeto por cliente, modelo GeoAdmin)."""
    rotulo = (nome or "").strip() or _so_digitos(telefone) or "lead"
    nome_proj = f"{ASSENTAMENTO_NOME} - {rotulo}"
    tentativas = [
        {
            "nome": nome_proj,
            "municipio": ASSENTAMENTO_MUNICIPIO,
            "estado": ASSENTAMENTO_UF,
            "descricao": ASSENTAMENTO_DESCRICAO,
            "cliente_id": cliente_id,
        },
        {"nome": nome_proj, "municipio": ASSENTAMENTO_MUNICIPIO, "estado": ASSENTAMENTO_UF, "cliente_id": cliente_id},
        {"nome": nome_proj, "cliente_id": cliente_id},
        {"nome": nome_proj},
    ]
    ultimo_erro: Exception | None = None
    for payload in tentativas:
        try:
            resposta = sb.table("projetos").insert(payload).execute()
            dados = _dados(resposta)
            if dados:
                return str(dados[0]["id"])
        except Exception as exc:
            ultimo_erro = exc
            continue
    if ultimo_erro:
        raise ultimo_erro
    raise RuntimeError("Nao foi possivel criar o projeto do lead")


def _resolver_area_referencia(sb) -> str | None:
    """Tenta achar um recorte/base para o mapa do cliente."""
    area_fixa = (os.getenv("VERTEX_AREA_ID") or "").strip()
    if area_fixa:
        return area_fixa
    if not ASSENTAMENTO_PROJETO_ID:
        return None
    try:
        resposta = (
            sb.table("areas_projeto")
            .select("id, geometria_final, geometria_esboco")
            .eq("projeto_id", ASSENTAMENTO_PROJETO_ID)
            .is_("deleted_at", "null")
            .limit(100)
            .execute()
        )
    except Exception as exc:
        logger.warning("Nao foi possivel resolver area de referencia: %s", exc)
        return None
    areas = _dados(resposta)
    if not areas:
        return None
    # Prefere area com geometria para o mapa.
    for area in areas:
        if area.get("geometria_final") or area.get("geometria_esboco"):
            return str(area.get("id"))
    return str(areas[0].get("id")) if areas[0].get("id") else None


def _criar_vinculo(sb, projeto_id: str, cliente_id: str, area_id: str | None = None) -> str:
    registro = {
        "projeto_id": projeto_id,
        "cliente_id": cliente_id,
        "papel": "principal",
        "principal": True,
        "recebe_magic_link": True,
        "ordem": 0,
        "deleted_at": None,
    }
    if area_id:
        registro["area_id"] = area_id
    resposta = sb.table("projeto_clientes").insert(registro).execute()
    dados = _dados(resposta)
    if not dados:
        raise RuntimeError("Falha ao vincular cliente ao projeto")
    return str(dados[0]["id"])


def _gerar_token(sb, projeto_cliente_id: str, cliente_id: str) -> tuple[str, str]:
    token = str(uuid.uuid4())
    expira = (datetime.now(timezone.utc) + timedelta(days=MAGIC_LINK_DIAS)).isoformat()
    sb.table("projeto_clientes").update(
        {"magic_link_token": token, "magic_link_expira": expira}
    ).eq("id", projeto_cliente_id).execute()
    try:
        sb.table("clientes").update(
            {"magic_link_token": token, "magic_link_expira": expira}
        ).eq("id", cliente_id).execute()
    except Exception:
        pass
    return token, expira


@router.post("/vertex/lead", summary="Gera magic link do formulario para um lead do WhatsApp")
async def vertex_lead(payload: LeadPayload, request: Request):
    _verificar_segredo(request)
    sb = _get_supabase()

    cliente = _achar_cliente_por_telefone(sb, payload.telefone)
    vinculo = None
    if cliente:
        cliente_id = str(cliente["id"])
        vinculo = _achar_vinculo_principal_do_cliente(sb, cliente_id)
    else:
        cliente_id = _criar_cliente_tolerante(sb, payload.nome or "", payload.telefone, payload.cpf or "")

    area_ref_id = _resolver_area_referencia(sb)

    if vinculo:
        projeto_id = str(vinculo["projeto_id"])
        projeto_cliente_id = str(vinculo["id"])
        if area_ref_id and not vinculo.get("area_id"):
            try:
                sb.table("projeto_clientes").update({"area_id": area_ref_id}).eq("id", projeto_cliente_id).execute()
            except Exception as exc:
                logger.warning("Falha ao atualizar area_id no vinculo principal: %s", exc)
    else:
        projeto_id = _criar_projeto_lead(sb, payload.nome or "", payload.telefone, cliente_id)
        projeto_cliente_id = _criar_vinculo(sb, projeto_id, cliente_id, area_id=area_ref_id)

    token, expira = _gerar_token(sb, projeto_cliente_id, cliente_id)
    url = f"{_resolver_app_url()}/formulario/cliente?token={token}"

    logger.info("vertex_lead: cliente=%s projeto_cliente=%s token gerado", cliente_id, projeto_cliente_id)
    return {
        "ok": True,
        "url": url,
        "token": token,
        "expira_em": expira,
        "projeto_id": projeto_id,
        "cliente_id": cliente_id,
        "projeto_cliente_id": projeto_cliente_id,
    }
