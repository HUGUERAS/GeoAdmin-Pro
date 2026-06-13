"""
GeoAdmin Pro — Endpoints Magic Link + Geração de Documentos
backend/routes/documentos.py

POST /projetos/{id}/magic-link           -> gera link e envia para cliente
GET  /formulario/cliente                 -> serve o formulário HTML
GET  /formulario/cliente/contexto        -> retorna contexto do token
POST /formulario/cliente                 -> recebe dados preenchidos pelo cliente (json ou multipart)
POST /projetos/{id}/gerar-documentos     -> gera ZIP com os 7 docs GPRF
GET  /projetos/{id}/documentos           -> lista docs gerados
"""

import json
import logging
import os
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query, Request, Depends
from middleware.auth import verificar_token
from fastapi.responses import HTMLResponse, Response
from pydantic import BaseModel, Field, ValidationError

from integracoes.areas_projeto import anexar_arquivos_area, salvar_area_projeto
from integracoes.projeto_clientes import (
    gerar_magic_link_participante,
    listar_participantes_projeto,
    obter_vinculo_por_token,
    registrar_evento_magic_link,
    salvar_participantes_projeto,
)
from integracoes.referencia_cliente import (
    comparar_com_perimetro_referencia,
    importar_vertices_por_formato,
    salvar_geometria_referencia,
)
from routes.perimetros import buscar_perimetro_ativo
from services.magic_link import MagicLinkService
from services.ocr_vision import ocr_documentos

logger = logging.getLogger("geoadmin.documentos")
router = APIRouter(tags=["Documentos GPRF"])


class GerarMagicLinksLotePayload(BaseModel):
    projeto_cliente_ids: list[str] = Field(default_factory=list)
    area_ids: list[str] = Field(default_factory=list)
    codigo_lotes: list[str] = Field(default_factory=list)
    dias: int = 7
    canal: str = "whatsapp"
    autor: Optional[str] = None
    somente_habilitados: bool = True


class DadosFormulario(BaseModel):
    nome: str
    cpf: str
    rg: str
    estado_civil: str
    profissao: Optional[str] = ""
    telefone: str
    email: Optional[str] = ""
    conjuge_nome: Optional[str] = ""
    conjuge_cpf: Optional[str] = ""
    endereco: str
    endereco_numero: Optional[str] = ""
    municipio: str
    cep: Optional[str] = ""
    nome_imovel: str
    municipio_imovel: str
    endereco_imovel: Optional[str] = ""
    endereco_imovel_numero: Optional[str] = ""
    cep_imovel: Optional[str] = ""
    comarca: Optional[str] = ""
    matricula: Optional[str] = ""
    tempo_posse_anos: Optional[int] = None
    confrontantes: list = []
    area_nome: Optional[str] = ""
    ccir: Optional[str] = ""
    car: Optional[str] = ""
    observacoes: Optional[str] = ""
    croqui_coords: Optional[str] = ""
    croqui_svg: Optional[str] = ""
    croqui_pontos_json: Optional[str] = ""
    croqui_mapa_status: Optional[str] = ""


def _get_supabase():
    from main import get_supabase as _get
    return _get()


def _erro_schema(exc: Exception, trecho: str) -> bool:
    return trecho.lower() in str(exc).lower()


def _erro_schema_compat(exc: Exception) -> bool:
    texto = str(exc).lower()
    return any(
        marcador in texto
        for marcador in (
            "column does not exist",
            "missing response",
            "pgrst204",
            "pgrst205",
            "42703",
        )
    )


def _erro_documento_duplicado(exc: Exception) -> bool:
    texto = str(exc).lower()
    return (
        'duplicate key value violates unique constraint' in texto
        and ('cpf_cnpj' in texto or 'clientes_cpf_key' in texto or '(cpf)=' in texto or '(cpf_cnpj)=' in texto)
    )


def _normalizar_documento(valor: str | None) -> str:
    return ''.join(ch for ch in str(valor or '') if ch.isdigit())


def _resolver_app_url() -> str:
    for chave in ("APP_URL", "PUBLIC_APP_URL", "PUBLIC_BASE_URL"):
        valor = (os.environ.get(chave) or "").strip()
        if valor:
            return valor.rstrip("/")

    vercel = (os.environ.get("VERCEL_URL") or "").strip()
    if vercel:
        return f"https://{vercel.lstrip('/')}".rstrip("/")

    return "http://127.0.0.1:8000"


def _normalizar_estado_civil(valor: str) -> str:
    chave = (valor or "").strip().lower()
    mapa = {
        "solteiro": "solteiro",
        "solteiro(a)": "solteiro",
        "casado": "casado",
        "casado(a)": "casado",
        "divorciado": "divorciado",
        "divorciado(a)": "divorciado",
        "viuvo": "viuvo",
        "viúvo": "viuvo",
        "viuvo(a)": "viuvo",
        "viúvo(a)": "viuvo",
        "uniao_estavel": "uniao_estavel",
        "união estável": "uniao_estavel",
    }
    return mapa.get(chave, chave)


def _payload_projeto_formulario(dados: DadosFormulario) -> dict[str, Any]:
    return {
        "nome_imovel": dados.nome_imovel,
        "municipio": dados.municipio_imovel,
        "comarca": dados.comarca,
        "matricula": dados.matricula,
        "tempo_posse_anos": dados.tempo_posse_anos,
        "endereco_imovel": dados.endereco_imovel,
        "endereco_imovel_numero": dados.endereco_imovel_numero,
        "cep_imovel": dados.cep_imovel,
    }


def _atualizar_projeto_formulario(sb, projeto_id: str, dados: DadosFormulario) -> None:
    payload = _payload_projeto_formulario(dados)
    colunas_opcionais = {"endereco_imovel", "endereco_imovel_numero", "cep_imovel"}

    while True:
        try:
            (
                sb.table("projetos")
                .update(payload)
                .eq("id", projeto_id)
                .execute()
            )
            return
        except Exception as exc:
            removidas = [
                coluna for coluna in list(colunas_opcionais)
                if coluna in payload and _erro_schema(exc, f"'{coluna}' column")
            ]
            if not removidas:
                removidas = [
                    coluna for coluna in list(colunas_opcionais)
                    if coluna in payload and coluna.lower() in str(exc).lower()
                ]
            if removidas:
                for coluna in removidas:
                    payload.pop(coluna, None)
                    colunas_opcionais.discard(coluna)
                continue
            raise


def _payload_cliente_formulario(
    dados: DadosFormulario,
    *,
    preferir_cpf_cnpj: bool = True,
) -> dict[str, Any]:
    cpf_normalizado = _normalizar_documento(dados.cpf)
    conjuge_cpf = _normalizar_documento(dados.conjuge_cpf)
    payload = {
        "nome": dados.nome,
        "rg": dados.rg,
        "estado_civil": _normalizar_estado_civil(dados.estado_civil),
        "profissao": dados.profissao,
        "telefone": dados.telefone,
        "email": dados.email,
        "conjuge_nome": dados.conjuge_nome,
        "conjuge_cpf": conjuge_cpf or None,
        "endereco": dados.endereco,
        "endereco_numero": dados.endereco_numero,
        "municipio": dados.municipio,
        "cep": dados.cep,
        "formulario_ok": True,
        "formulario_em": datetime.now(timezone.utc).isoformat(),
    }
    if preferir_cpf_cnpj:
        payload["cpf_cnpj"] = cpf_normalizado
    else:
        payload["cpf"] = cpf_normalizado
    return payload


def _buscar_cliente_por_documento_formulario(sb, cpf: str) -> dict[str, Any] | None:
    valores: list[str] = []
    for valor in (_normalizar_documento(cpf), str(cpf or '').strip()):
        if valor and valor not in valores:
            valores.append(valor)

    for campo in ("cpf_cnpj", "cpf"):
        for valor in valores:
            try:
                resposta = (
                    sb.table("clientes")
                    .select("id, deleted_at")
                    .eq(campo, valor)
                    .limit(1)
                    .execute()
                )
                dados = getattr(resposta, "data", None) or []
                cliente = dados[0] if dados else None
            except Exception as exc:
                if _erro_schema(exc, f"'{campo}' column"):
                    continue
                raise
            if cliente:
                return cliente
    return None


def _reaproveitar_cliente_existente_formulario(sb, cliente_atual_id: str, cliente_existente_id: str, dados: DadosFormulario) -> str:
    resposta_cliente_atual = (
        sb.table("clientes")
        .select("magic_link_token, magic_link_expira")
        .eq("id", cliente_atual_id)
        .limit(1)
        .execute()
    )
    dados_cliente_atual = getattr(resposta_cliente_atual, "data", None) or []
    cliente_atual = dados_cliente_atual[0] if dados_cliente_atual else {}

    ultimo_erro: Exception | None = None
    for preferir_cpf_cnpj in (True, False):
        try:
            payload = _payload_cliente_formulario(dados, preferir_cpf_cnpj=preferir_cpf_cnpj)
            payload["deleted_at"] = None
            if cliente_atual.get("magic_link_token"):
                payload["magic_link_token"] = cliente_atual.get("magic_link_token")
                payload["magic_link_expira"] = cliente_atual.get("magic_link_expira")
            (
                sb.table("clientes")
                .update(payload)
                .eq("id", cliente_existente_id)
                .execute()
            )
            (
                sb.table("projetos")
                .update({"cliente_id": cliente_existente_id})
                .eq("cliente_id", cliente_atual_id)
                .is_("deleted_at", "null")
                .execute()
            )
            try:
                (
                    sb.table("projeto_clientes")
                    .update({"cliente_id": cliente_existente_id})
                    .eq("cliente_id", cliente_atual_id)
                    .is_("deleted_at", "null")
                    .execute()
                )
            except Exception as exc:
                if "projeto_clientes" not in str(exc).lower():
                    raise
            (
                sb.table("clientes")
                .update({"magic_link_token": None, "magic_link_expira": None})
                .eq("id", cliente_atual_id)
                .execute()
            )
            return cliente_existente_id
        except Exception as exc:
            ultimo_erro = exc
            coluna = "cpf_cnpj" if preferir_cpf_cnpj else "cpf"
            if _erro_schema(exc, f"'{coluna}' column"):
                continue
            raise

    if ultimo_erro:
        raise ultimo_erro
    return cliente_existente_id

def _atualizar_cliente_formulario(sb, cliente_id: str, dados: DadosFormulario) -> str:
    ultimo_erro: Exception | None = None
    for preferir_cpf_cnpj in (True, False):
        try:
            (
                sb.table("clientes")
                .update(_payload_cliente_formulario(dados, preferir_cpf_cnpj=preferir_cpf_cnpj))
                .eq("id", cliente_id)
                .execute()
            )
            return cliente_id
        except Exception as exc:
            ultimo_erro = exc
            if dados.cpf and _erro_documento_duplicado(exc):
                cliente_existente = _buscar_cliente_por_documento_formulario(sb, dados.cpf)
                if cliente_existente and cliente_existente.get("id") != cliente_id:
                    return _reaproveitar_cliente_existente_formulario(sb, cliente_id, cliente_existente["id"], dados)
                raise HTTPException(
                    409,
                    {
                        "erro": "Este CPF já está vinculado a outro cadastro. Revise o documento informado ou contate o responsável técnico.",
                        "codigo": 409,
                    },
                )
            coluna = "cpf_cnpj" if preferir_cpf_cnpj else "cpf"
            if _erro_schema(exc, f"'{coluna}' column"):
                continue
            raise

    if ultimo_erro:
        raise ultimo_erro
    return cliente_id


def _resolver_contexto_legacy_cliente(sb, cliente_id: str) -> tuple[str | None, dict[str, Any] | None]:
    try:
        resposta_vinculos = (
            sb.table("projeto_clientes")
            .select("id, projeto_id, cliente_id, papel, principal, recebe_magic_link, ordem, area_id, magic_link_token, magic_link_expira")
            .eq("cliente_id", cliente_id)
            .is_("deleted_at", "null")
            .execute()
        )
        vinculos = getattr(resposta_vinculos, "data", None) or []
    except Exception as exc:
        if "projeto_clientes" in str(exc).lower():
            vinculos = []
        else:
            raise

    if len(vinculos) == 1:
        vinculo = vinculos[0]
        return vinculo.get("projeto_id"), vinculo
    if len(vinculos) > 1:
        raise HTTPException(409, {
            "erro": "[ERRO-603] Este link antigo ficou ambíguo porque o cliente participa de mais de um projeto. Solicite um novo link individual.",
            "codigo": 603,
        })

    projeto_res = (
        sb.table("projetos")
        .select("id")
        .eq("cliente_id", cliente_id)
        .is_("deleted_at", "null")
        .order("criado_em", desc=True)
        .execute()
    )
    projetos = getattr(projeto_res, "data", None) or []
    if len(projetos) == 1:
        return projetos[0].get("id"), None
    if len(projetos) > 1:
        raise HTTPException(409, {
            "erro": "[ERRO-603] Este link antigo ficou ambíguo porque o cliente tem mais de um projeto ativo. Solicite um novo link individual.",
            "codigo": 603,
        })
    return None, None



def _garantir_vinculo_legacy_cliente(
    sb,
    *,
    cliente: dict[str, Any],
    projeto_id: str | None,
    vinculo: dict[str, Any] | None,
    token: str,
) -> tuple[str | None, dict[str, Any] | None]:
    if not projeto_id:
        return None, None

    if not vinculo:
        participantes = salvar_participantes_projeto(
            sb,
            projeto_id,
            [{
                "cliente_id": cliente.get("id"),
                "nome": cliente.get("nome"),
                "cpf": cliente.get("cpf") or cliente.get("cpf_cnpj"),
                "telefone": cliente.get("telefone"),
                "email": cliente.get("email"),
                "papel": "principal",
                "principal": True,
                "recebe_magic_link": True,
                "ordem": 0,
                "area_id": None,
            }],
        )
        vinculo = next((item for item in participantes if str(item.get("cliente_id")) == str(cliente.get("id"))), None)

    if not vinculo or not vinculo.get("id"):
        raise HTTPException(409, {
            "erro": "[ERRO-603] Este link antigo precisa ser substituído por um novo link individual.",
            "codigo": 603,
        })

    expira = cliente.get("magic_link_expira")
    (
        sb.table("projeto_clientes")
        .update({
            "magic_link_token": token,
            "magic_link_expira": expira,
        })
        .eq("id", vinculo.get("id"))
        .execute()
    )
    (
        sb.table("clientes")
        .update({
            "magic_link_token": None,
            "magic_link_expira": None,
        })
        .eq("id", cliente.get("id"))
        .execute()
    )
    registrar_evento_magic_link(
        sb,
        projeto_id=projeto_id,
        projeto_cliente_id=vinculo.get("id"),
        cliente_id=cliente.get("id"),
        area_id=vinculo.get("area_id"),
        token=token,
        tipo_evento="legado",
        canal="interno",
        autor="migracao_legacy",
        expira_em=expira,
        payload={"migrado_de_cliente": True},
    )

    vinculo["magic_link_token"] = token
    vinculo["magic_link_expira"] = expira
    return projeto_id, vinculo
def _validar_token(sb, token: str) -> tuple[dict[str, Any], str | None, dict[str, Any] | None]:
    """
    Valida token Magic Link usando o serviço centralizado.
    
    Mantido para compatibilidade com fluxos existentes.
    """
    vinculo = obter_vinculo_por_token(sb, token)
    if vinculo:
        resposta_cliente = (
            sb.table("clientes")
            .select("*")
            .eq("id", vinculo.get("cliente_id"))
            .maybe_single()
            .execute()
        )
        cliente = getattr(resposta_cliente, "data", None)
        if not cliente:
            raise HTTPException(404, {"erro": "[ERRO-601] Link invalido.", "codigo": 601})
        return cliente, vinculo.get("projeto_id"), vinculo

    resposta_cliente = (
        sb.table("clientes")
        .select("*")
        .eq("magic_link_token", token)
        .maybe_single()
        .execute()
    )
    cliente = getattr(resposta_cliente, "data", None)
    if not cliente:
        raise HTTPException(404, {"erro": "[ERRO-601] Link invalido ou expirado.", "codigo": 601})

    projeto_id, vinculo_legacy = _resolver_contexto_legacy_cliente(sb, str(cliente.get("id")))
    projeto_id, vinculo_legacy = _garantir_vinculo_legacy_cliente(
        sb,
        cliente=cliente,
        projeto_id=projeto_id,
        vinculo=vinculo_legacy,
        token=token,
    )
    return cliente, projeto_id, vinculo_legacy


def _carregar_area_contexto(sb, area_id: str | None) -> dict[str, Any] | None:
    if not area_id:
        return None
    try:
        resposta = (
            sb.table("areas_projeto")
            .select("id, nome, municipio, estado, proprietario_nome, origem_tipo, geometria_final, geometria_esboco, resumo_esboco, resumo_final, codigo_lote, quadra, setor, status_operacional, status_documental")
            .eq("id", area_id)
            .maybe_single()
            .execute()
        )
    except Exception as exc:
        if not _erro_schema_compat(exc) and "areas_projeto" not in str(exc).lower():
            raise
        try:
            resposta = (
                sb.table("areas_projeto")
                .select("id, nome, tipo, area_m2, geometria_final, geometria_esboco, metadados, criado_em, atualizado_em")
                .eq("id", area_id)
                .maybe_single()
                .execute()
            )
        except Exception as exc_fallback:
            if _erro_schema_compat(exc_fallback) or "areas_projeto" in str(exc_fallback).lower():
                return None
            raise
    area = getattr(resposta, "data", None)
    if not area:
        return None
    identificacao = " · ".join([
        item
        for item in (
            area.get("quadra") and f"Qd. {area.get('quadra')}",
            area.get("codigo_lote") and f"Lt. {area.get('codigo_lote')}",
            area.get("setor"),
        )
        if item
    ])
    area["identificacao_lote"] = identificacao or area.get("nome")
    return area


def _participante_base(participantes: list[dict[str, Any]], *, projeto_cliente_id: str | None = None, cliente_id: str | None = None) -> dict[str, Any] | None:
    if projeto_cliente_id:
        return next((item for item in participantes if str(item.get("id")) == str(projeto_cliente_id)), None)
    if cliente_id:
        return next((item for item in participantes if str(item.get("cliente_id")) == str(cliente_id)), None)
    return next((item for item in participantes if item.get("principal")), None) or next((item for item in participantes if item.get("recebe_magic_link")), None) or (participantes[0] if participantes else None)


def _contexto_token(sb, token: str) -> dict[str, Any]:
    cliente, projeto_id, vinculo = _validar_token(sb, token)
    projeto = None
    if projeto_id:
        resposta_projeto = (
            sb.table("vw_projetos_completo")
            .select("id, projeto_nome, municipio, estado, status")
            .eq("id", projeto_id)
            .maybe_single()
            .execute()
        )
        projeto = getattr(resposta_projeto, "data", None)
    area = _carregar_area_contexto(sb, vinculo.get("area_id") if vinculo else None)
    lote = None
    if area:
        lote = {
            "area_id": area.get("id"),
            "codigo_lote": area.get("codigo_lote"),
            "quadra": area.get("quadra"),
            "setor": area.get("setor"),
            "identificacao": area.get("identificacao_lote"),
            "status_operacional": area.get("status_operacional"),
            "status_documental": area.get("status_documental"),
        }
    return {
        "cliente": {
            "id": cliente.get("id"),
            "nome": cliente.get("nome"),
            "formulario_ok": cliente.get("formulario_ok"),
            "formulario_em": cliente.get("formulario_em"),
            "magic_link_expira": (vinculo or {}).get("magic_link_expira") or cliente.get("magic_link_expira"),
        },
        "projeto": projeto,
        "participante": {
            "id": vinculo.get("id"),
            "papel": vinculo.get("papel"),
            "principal": bool(vinculo.get("principal")),
            "area_id": vinculo.get("area_id"),
            "cliente_id": vinculo.get("cliente_id"),
            "recebe_magic_link": bool(vinculo.get("recebe_magic_link")),
        } if vinculo else None,
        "area": area,
        "lote": lote,
        "mensagem": "Preencha seus dados e desenhe um esboço aproximado da área para agilizar a regularização.",
    }

def _arquivo_formulario_path() -> str:
    return os.path.join(os.path.dirname(__file__), "..", "static", "formulario_cliente.html")


def _extensao_para_formato(filename: str | None) -> str | None:
    nome = (filename or "").lower()
    if nome.endswith(".geojson") or nome.endswith(".json"):
        return "geojson"
    if nome.endswith(".kml"):
        return "kml"
    if nome.endswith(".csv"):
        return "csv"
    if nome.endswith(".txt"):
        return "txt"
    if nome.endswith(".zip"):
        return "zip"
    return None


def _complementar_payload_de_anexos(
    payload: dict[str, Any],
    uploads: list[tuple[str, bytes, str | None]],
) -> None:
    """Complemento interno: tenta extrair CPF/RG/nome das fotos enviadas."""
    imagens = [b for (_n, b, ct) in uploads if b]
    if not imagens:
        return
    try:
        campos = ocr_documentos(imagens)
    except Exception as exc:
        logger.warning("complemento documento falhou: %s", exc)
        return
    if campos.get("cpf") and not str(payload.get("cpf") or "").strip():
        payload["cpf"] = campos["cpf"]
    if campos.get("rg") and not str(payload.get("rg") or "").strip():
        payload["rg"] = campos["rg"]
    if campos.get("nome") and not str(payload.get("nome") or "").strip():
        payload["nome"] = campos["nome"]


async def _extrair_payload_request(request: Request) -> tuple[dict[str, Any], list[tuple[str, bytes, str | None]], tuple[str, bytes, str | None] | None]:
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        payload = await request.json()
        return payload, [], None

    form = await request.form()
    payload: dict[str, Any] = {}
    uploads: list[tuple[str, bytes, str | None]] = []
    geo_upload: tuple[str, bytes, str | None] | None = None

    for chave, valor in form.multi_items():
        if hasattr(valor, "filename"):
            conteudo = await valor.read()
            if not conteudo:
                continue
            item = (valor.filename or chave, conteudo, getattr(valor, "content_type", None))
            if chave == "arquivo_geometria":
                geo_upload = item
            else:
                uploads.append(item)
            continue
        payload[chave] = valor

    confrontantes_raw = payload.get("confrontantes_json") or payload.get("confrontantes")
    if isinstance(confrontantes_raw, str) and confrontantes_raw.strip():
        try:
            payload["confrontantes"] = json.loads(confrontantes_raw)
        except Exception:
            payload["confrontantes"] = []
    else:
        payload["confrontantes"] = []

    return payload, uploads, geo_upload


def _parse_int(value: Any) -> int | None:
    texto = str(value or "").strip()
    if not texto:
        return None
    try:
        return int(texto)
    except ValueError:
        return None


def _normalizar_ponto_croqui(item: Any) -> dict[str, float] | None:
    if isinstance(item, dict):
        lat_raw = item.get("lat") or item.get("latitude") or item.get("y")
        lon_raw = item.get("lon") or item.get("lng") or item.get("longitude") or item.get("x")
    elif isinstance(item, (list, tuple)) and len(item) >= 2:
        lat_raw, lon_raw = item[0], item[1]
    else:
        return None

    try:
        lat = float(str(lat_raw).replace(",", "."))
        lon = float(str(lon_raw).replace(",", "."))
    except (TypeError, ValueError):
        return None

    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        return None
    return {"lat": round(lat, 8), "lon": round(lon, 8)}


def _parse_pontos_croqui_json(valor: Any) -> list[dict[str, float]]:
    if not valor:
        return []
    try:
        payload = json.loads(valor) if isinstance(valor, str) else valor
    except Exception:
        return []
    if isinstance(payload, dict):
        payload = payload.get("pontos") or payload.get("points") or []
    if not isinstance(payload, list):
        return []
    pontos = [_normalizar_ponto_croqui(item) for item in payload]
    return [ponto for ponto in pontos if ponto]


def _parse_pontos_croqui_texto(valor: str | None) -> list[dict[str, float]]:
    pontos: list[dict[str, float]] = []
    for linha in str(valor or "").splitlines():
        texto = linha.strip()
        if not texto:
            continue
        partes = [parte for parte in texto.replace(";", ",").replace("\t", ",").replace(" ", ",").split(",") if parte]
        if len(partes) < 2:
            continue
        try:
            a = float(partes[0].replace(",", "."))
            b = float(partes[1].replace(",", "."))
        except ValueError:
            continue
        if abs(a) <= 90 and abs(b) <= 180:
            pontos.append({"lat": round(a, 8), "lon": round(b, 8)})
        elif abs(a) <= 180 and abs(b) <= 90:
            pontos.append({"lat": round(b, 8), "lon": round(a, 8)})
    return pontos


def _anexo_pontos_croqui(pontos: list[dict[str, float]], status: str | None) -> tuple[str, bytes, str]:
    features: list[dict[str, Any]] = []
    for index, ponto in enumerate(pontos, start=1):
        features.append({
            "type": "Feature",
            "properties": {"ordem": index, "origem": "formulario_cliente"},
            "geometry": {"type": "Point", "coordinates": [ponto["lon"], ponto["lat"]]},
        })
    if len(pontos) >= 2:
        features.append({
            "type": "Feature",
            "properties": {"origem": "formulario_cliente", "tipo": "linha_aproximada"},
            "geometry": {"type": "LineString", "coordinates": [[p["lon"], p["lat"]] for p in pontos]},
        })
    payload = {
        "type": "FeatureCollection",
        "properties": {
            "origem": "formulario_cliente",
            "status_mapa": status or "pontos_marcados",
            "pontos_total": len(pontos),
        },
        "features": features,
    }
    return (
        "croqui_pontos_cliente.geojson",
        json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        "application/geo+json",
    )


def _normalizar_payload(payload: dict[str, Any]) -> DadosFormulario:
    bruto = {**payload}
    bruto["confrontantes"] = payload.get("confrontantes") or []
    bruto["tempo_posse_anos"] = _parse_int(payload.get("tempo_posse_anos"))
    return DadosFormulario(**bruto)


def _salvar_referencia_cliente(sb, cliente_id: str, projeto_id: str | None, nome: str, vertices: list[dict[str, Any]]):
    comparativo = None
    if projeto_id:
        perimetro = buscar_perimetro_ativo(projeto_id, supabase=sb)
        if perimetro and (perimetro.get("vertices") or []):
            comparativo = comparar_com_perimetro_referencia(vertices, perimetro.get("vertices") or [], perimetro.get("tipo"))

    return salvar_geometria_referencia(
        sb=sb,
        cliente_id=cliente_id,
        projeto_id=projeto_id,
        nome=nome,
        origem_tipo="formulario_cliente",
        formato="texto",
        arquivo_nome=None,
        vertices=vertices,
        comparativo=comparativo,
    )


def _sincronizar_confrontantes_formulario(sb, projeto_id: str, cliente_id: str, confrontantes: list[dict[str, Any]]) -> None:
    origem_cliente = f"formulario_cliente:{cliente_id}"
    agora = datetime.now(timezone.utc).isoformat()
    try:
        resposta = (
            sb.table("confrontantes")
            .select("id, origem")
            .eq("projeto_id", projeto_id)
            .is_("deleted_at", "null")
            .execute()
        )
        existentes = getattr(resposta, "data", None) or []
    except Exception:
        existentes = []

    for item in existentes:
        origem = str(item.get("origem") or "").strip().lower()
        if origem in {"formulario_cliente", origem_cliente.lower()}:
            (
                sb.table("confrontantes")
                .update({"deleted_at": agora})
                .eq("id", item.get("id"))
                .execute()
            )

    novos = []
    for conf in confrontantes:
        if not conf.get("nome"):
            continue
        novos.append({
            "projeto_id": projeto_id,
            "lado": conf.get("lado", "Outros"),
            "nome": conf.get("nome"),
            "cpf": conf.get("cpf", ""),
            "nome_imovel": conf.get("nome_imovel", ""),
            "matricula": conf.get("matricula", ""),
            "tipo": conf.get("tipo", "particular"),
            "origem": origem_cliente,
        })
    if novos:
        sb.table("confrontantes").insert(novos).execute()


@router.post("/projetos/{projeto_id}/magic-link", summary="Gerar link do formulário para o cliente")
def gerar_magic_link(
    projeto_id: str,
    cliente_id: str | None = None,
    projeto_cliente_id: str | None = None,
    dias: int = 7,
    canal: str = "whatsapp",
    autor: str | None = None,
    supabase=None,
    _usuario: dict = Depends(verificar_token),
):
    """
    Endpoint interno para gerar Magic Link.
    
    Utiliza o serviço MagicLinkService para centralizar a lógica de geração.
    """
    sb = supabase or _get_supabase()
    res_proj = (
        sb.table("vw_projetos_completo")
        .select("*")
        .eq("id", projeto_id)
        .maybe_single()
        .execute()
    )
    projeto = res_proj.data if res_proj else None
    if not projeto:
        raise HTTPException(404, {"erro": "[ERRO-401] Projeto nao encontrado.", "codigo": 401})

    participante = gerar_magic_link_participante(
        sb,
        projeto_id,
        cliente_id=cliente_id,
        projeto_cliente_id=projeto_cliente_id,
        dias=dias,
        espelhar_token_cliente_legacy=True,
    )
    if not participante:
        raise HTTPException(422, {"erro": "Nao ha participante elegivel para gerar link.", "codigo": 422})

    cliente_final = participante.get("cliente_id") or cliente_id or projeto.get("cliente_id")
    token = participante.get("magic_link_token")
    expira = participante.get("magic_link_expira")
    link = f"{_resolver_app_url()}/formulario/cliente?token={token}"

    # Obter nome do cliente para a mensagem do WhatsApp
    cliente_nome = projeto.get("cliente_nome") or ""
    if participante.get("nome"):
        cliente_nome = participante.get("nome")
    elif cliente_final:
        try:
            cliente_info = sb.table("clientes").select("nome").eq("id", cliente_final).maybe_single().execute().data
            if cliente_info:
                cliente_nome = cliente_info.get("nome") or cliente_nome
        except Exception:
            pass

    mensagem_whatsapp = (
        f"Olá {cliente_nome or ''}!\n\n"
        f"Para darmos andamento ao processo de regularização do imóvel *{projeto.get('projeto_nome', '')}*, "
        "preciso que você preencha um formulário com seus dados e um esboço simples da área.\n\n"
        f"Acesse pelo celular: {link}\n\n"
        "O link expira em 7 dias.\n\n"
        "Qualquer dúvida é só chamar!"
    )

    registrar_evento_magic_link(
        sb,
        projeto_id=projeto_id,
        projeto_cliente_id=participante.get("id"),
        cliente_id=cliente_final,
        area_id=participante.get("area_id"),
        token=token,
        tipo_evento="gerado",
        canal=canal,
        autor=autor,
        expira_em=expira,
        payload={"projeto_nome": projeto.get("projeto_nome")},
    )
    return {
        "url": link,
        "link": link,
        "mensagem_whatsapp": mensagem_whatsapp,
        "token": token,
        "expira_em": expira,
        "projeto_id": projeto_id,
        "cliente_id": cliente_final,
        "projeto_cliente_id": participante.get("id"),
        "area_id": participante.get("area_id"),
    }



@router.post("/projetos/{projeto_id}/magic-links/lote", summary="Gerar magic links em lote por participante/lote")
def gerar_magic_links_lote(
    projeto_id: str,
    payload: GerarMagicLinksLotePayload,
    supabase=None,
    _usuario: dict = Depends(verificar_token),
):
    sb = supabase or _get_supabase()
    try:
        projeto = sb.table("vw_projetos_completo").select("id, projeto_nome").eq("id", projeto_id).single().execute().data
    except Exception:
        raise HTTPException(404, {"erro": "[ERRO-401] Projeto não encontrado.", "codigo": 401})

    participantes = listar_participantes_projeto(sb, projeto_id)
    if not participantes:
        raise HTTPException(422, {"erro": "Nao ha participantes vinculados para gerar links em lote.", "codigo": 422})

    areas_por_codigo: dict[str, str] = {}
    if payload.codigo_lotes:
        try:
            resposta_areas = sb.table("areas_projeto").select("id, codigo_lote").eq("projeto_id", projeto_id).is_("deleted_at", "null").execute()
            for area in getattr(resposta_areas, "data", None) or []:
                codigo = str(area.get("codigo_lote") or "").strip().lower()
                if codigo:
                    areas_por_codigo[codigo] = str(area.get("id"))
        except Exception:
            areas_por_codigo = {}

    area_ids = {str(item) for item in payload.area_ids if item}
    area_ids.update({areas_por_codigo.get(str(item).strip().lower()) for item in payload.codigo_lotes if areas_por_codigo.get(str(item).strip().lower())})
    area_ids.discard(None)
    projeto_cliente_ids = {str(item) for item in payload.projeto_cliente_ids if item}

    selecionados = []
    for participante in participantes:
        if projeto_cliente_ids and str(participante.get("id")) not in projeto_cliente_ids:
            continue
        if area_ids and str(participante.get("area_id") or '') not in area_ids:
            continue
        if payload.somente_habilitados and not participante.get("recebe_magic_link"):
            continue
        selecionados.append(participante)

    if not selecionados:
        raise HTTPException(422, {"erro": "Nenhum participante elegível encontrado para geração em lote.", "codigo": 422})

    links = []
    for participante in selecionados:
        link = gerar_magic_link(
            projeto_id,
            cliente_id=participante.get("cliente_id"),
            projeto_cliente_id=participante.get("id"),
            dias=payload.dias,
            canal=payload.canal,
            autor=payload.autor,
            supabase=sb,
        )
        links.append({
            **link,
            "cliente_id": participante.get("cliente_id"),
            "projeto_cliente_id": participante.get("id"),
            "area_id": participante.get("area_id"),
        })

    return {"total": len(links), "links": links, "projeto_nome": projeto.get("projeto_nome")}


@router.get("/projetos/{projeto_id}/magic-links/eventos", summary="Listar histórico de envio de magic links")
def listar_historico_magic_links(
    projeto_id: str,
    projeto_cliente_id: str | None = None,
    area_id: str | None = None,
    limite: int = 100,
    supabase=None,
    _usuario: dict = Depends(verificar_token),
):
    """
    Lista eventos de Magic Link usando o serviço centralizado.
    """
    sb = supabase or _get_supabase()
    service = MagicLinkService(sb)
    eventos = service.listar_eventos(
        projeto_id,
        projeto_cliente_id=projeto_cliente_id,
        area_id=area_id,
        limite=limite,
    )
    return {"total": len(eventos), "eventos": eventos}


@router.get("/formulario/cliente/contexto", summary="Obter contexto do magic link")
def contexto_formulario_cliente(token: str = Query(...)):
    sb = _get_supabase()
    return _contexto_token(sb, token)


@router.get("/formulario/cliente", response_class=HTMLResponse, summary="Formulário HTML para o cliente preencher")
def formulario_cliente(token: str = Query(...)):
    sb = _get_supabase()
    _contexto_token(sb, token)
    html_path = _arquivo_formulario_path()
    try:
        with open(html_path, encoding="utf-8") as f:
            return HTMLResponse(f.read())
    except FileNotFoundError:
        raise HTTPException(404, "Formulário não encontrado.")


@router.post("/formulario/cliente", summary="Receber dados preenchidos pelo cliente")
async def receber_formulario(request: Request, token: str = Query(...), supabase=None):
    sb = supabase or _get_supabase()
    cliente, projeto_id, vinculo = _validar_token(sb, token)
    cliente_id = cliente["id"]

    payload_raw, uploads, geo_upload = await _extrair_payload_request(request)
    _complementar_payload_de_anexos(payload_raw, uploads)
    try:
        dados = _normalizar_payload(payload_raw)
    except ValidationError as exc:
        campos = [erro.get("loc", [None])[-1] for erro in exc.errors()]
        raise HTTPException(422, {
            "erro": "Confira os campos obrigatórios do formulário antes de enviar.",
            "campos": campos,
            "codigo": 422,
        })

    cliente_id = _atualizar_cliente_formulario(sb, cliente_id, dados)

    if projeto_id:
        _atualizar_projeto_formulario(sb, projeto_id, dados)
        _sincronizar_confrontantes_formulario(sb, projeto_id, cliente_id, dados.confrontantes)

    pontos_croqui = _parse_pontos_croqui_json(dados.croqui_pontos_json)
    if not pontos_croqui and dados.croqui_coords:
        pontos_croqui = _parse_pontos_croqui_texto(dados.croqui_coords)

    vertices: list[dict[str, Any]] = []
    if dados.croqui_coords:
        try:
            vertices = importar_vertices_por_formato("txt", dados.croqui_coords)
        except ValueError:
            vertices = []

    if not vertices and geo_upload:
        formato = _extensao_para_formato(geo_upload[0])
        if formato:
            try:
                vertices = importar_vertices_por_formato(formato, geo_upload[1])
            except ValueError:
                vertices = []
            else:
                uploads.append(geo_upload)

    if vertices and not pontos_croqui:
        pontos_croqui = [{"lat": float(item["lat"]), "lon": float(item["lon"])} for item in vertices]

    area_nome = dados.area_nome or dados.nome_imovel or "Área principal"
    area_contexto = _carregar_area_contexto(sb, (vinculo or {}).get("area_id")) if vinculo else None
    area = salvar_area_projeto(
        projeto_id=projeto_id or f"cliente-{cliente_id}",
        cliente_id=cliente_id,
        nome=area_nome,
        proprietario_nome=dados.nome,
        municipio=dados.municipio_imovel or dados.municipio,
        estado=(area_contexto or {}).get("estado"),
        comarca=dados.comarca,
        matricula=dados.matricula,
        ccir=dados.ccir,
        car=dados.car,
        observacoes=dados.observacoes,
        status_operacional="croqui_recebido" if (vertices or pontos_croqui) else "cliente_vinculado",
        status_documental="formulario_ok",
        origem_tipo="formulario_cliente",
        geometria_esboco=vertices,
        area_id=(vinculo or {}).get("area_id"),
    )

    if dados.croqui_svg:
        uploads.append(("croqui_cliente.svg", dados.croqui_svg.encode("utf-8"), "image/svg+xml"))
    if pontos_croqui:
        uploads.append(_anexo_pontos_croqui(pontos_croqui, dados.croqui_mapa_status))

    anexos = anexar_arquivos_area(area_id=area["id"], cliente_id=cliente_id, arquivos=uploads)

    if vinculo and vinculo.get("id") and not vinculo.get("area_id") and projeto_id:
        try:
            (
                sb.table("projeto_clientes")
                .update({"area_id": area["id"]})
                .eq("id", vinculo.get("id"))
                .execute()
            )
        except Exception as exc:
            if "projeto_clientes" not in str(exc).lower():
                raise

    if vertices:
        _salvar_referencia_cliente(sb, cliente_id, projeto_id, area_nome, vertices)

    if projeto_id:
        try:
            registrar_evento_magic_link(
                sb,
                projeto_id=projeto_id,
                projeto_cliente_id=(vinculo or {}).get("id"),
                cliente_id=cliente_id,
                area_id=area.get("id") or (vinculo or {}).get("area_id"),
                token=token,
                tipo_evento="consumido",
                canal="interno",
                autor="formulario_cliente",
                expira_em=(vinculo or {}).get("magic_link_expira") or cliente.get("magic_link_expira"),
                payload={
                    "vertices_recebidos": len(vertices),
                    "pontos_croqui_recebidos": len(pontos_croqui),
                    "mapa_status": dados.croqui_mapa_status or None,
                    "anexos_total": len(anexos),
                    "confrontantes_total": len(dados.confrontantes),
                },
            )
        except Exception as exc:
            logger.warning("Falha ao registrar consumo do magic link: %s", exc)

    logger.info(
        "Formulario recebido do cliente %s — projeto=%s confrontantes=%s anexos=%s vertices=%s pontos_croqui=%s",
        cliente_id,
        projeto_id,
        len(dados.confrontantes),
        len(anexos),
        len(vertices),
        len(pontos_croqui),
    )

    return {
        "ok": True,
        "mensagem": "Dados recebidos com sucesso. Obrigado!",
        "area": {
            "id": area["id"],
            "nome": area.get("nome"),
            "status_geometria": area.get("status_geometria"),
            "anexos_total": len(anexos),
        },
        "vertices_recebidos": len(vertices),
        "pontos_croqui_recebidos": len(pontos_croqui),
    }


@router.post("/projetos/{projeto_id}/gerar-documentos", summary="Gerar ZIP com os 7 documentos GPRF", response_class=Response)
def gerar_documentos(projeto_id: str, supabase=None, _usuario: dict = Depends(verificar_token)):
    from integracoes.gerador_documentos import gerar_todos_documentos

    sb = supabase or _get_supabase()

    try:
        res = sb.table("vw_formulario_cliente").select("formulario_ok, cliente_nome, projeto_nome").eq("projeto_id", projeto_id).single().execute()
    except Exception:
        raise HTTPException(404, {"erro": "[ERRO-401] Projeto não encontrado.", "codigo": 401})

    dados_check = res.data
    if not dados_check.get("formulario_ok"):
        raise HTTPException(422, {
            "erro": "[ERRO-103] Cliente ainda não preencheu o formulário. Envie o Magic Link primeiro via POST /projetos/{id}/magic-link.",
            "codigo": 103,
        })

    try:
        zip_bytes = gerar_todos_documentos(sb, projeto_id)
    except ValueError as e:
        raise HTTPException(422, {"erro": str(e), "codigo": 104})
    except Exception as e:
        raise HTTPException(500, {"erro": f"[ERRO-501] Falha ao gerar documentos: {e}", "codigo": 501})

    nome = f"GPRF_{dados_check.get('projeto_nome', 'projeto').replace(' ', '_')[:25]}.zip"
    logger.info("Documentos GPRF gerados: %s (%s bytes)", nome, len(zip_bytes))

    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{nome}"'},
    )


@router.get("/projetos/{projeto_id}/documentos", summary="Listar documentos gerados do projeto")
def listar_documentos(projeto_id: str, supabase=None, _usuario: dict = Depends(verificar_token)):
    sb = supabase or _get_supabase()

    try:
        res = sb.table("documentos_gerados").select("*").eq("projeto_id", projeto_id).order("gerado_em", desc=True).execute()
    except Exception as e:
        raise HTTPException(500, {"erro": f"[ERRO-502] {e}", "codigo": 502})

    return {"total": len(res.data), "documentos": res.data}
