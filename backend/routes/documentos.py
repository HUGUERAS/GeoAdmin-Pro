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

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, Response
from pydantic import BaseModel

from integracoes.areas_projeto import anexar_arquivos_area, salvar_area_projeto
from integracoes.referencia_cliente import (
    comparar_com_perimetro_referencia,
    importar_vertices_por_formato,
    salvar_geometria_referencia,
)
from routes.perimetros import buscar_perimetro_ativo

logger = logging.getLogger("geoadmin.documentos")
router = APIRouter(tags=["Documentos GPRF"])


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


def _get_supabase():
    from main import get_supabase as _get
    return _get()


def _erro_schema(exc: Exception, trecho: str) -> bool:
    return trecho.lower() in str(exc).lower()


def _resolver_app_url() -> str:
    for chave in ("APP_URL", "PUBLIC_APP_URL", "PUBLIC_BASE_URL"):
        valor = (os.environ.get(chave) or "").strip()
        if valor:
            return valor.rstrip("/")

    railway = (os.environ.get("RAILWAY_PUBLIC_DOMAIN") or "").strip()
    if railway:
        return f"https://{railway.lstrip('/')}".rstrip("/")

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


def _payload_cliente_formulario(
    dados: DadosFormulario,
    *,
    preferir_cpf_cnpj: bool = True,
) -> dict[str, Any]:
    payload = {
        "nome": dados.nome,
        "rg": dados.rg,
        "estado_civil": _normalizar_estado_civil(dados.estado_civil),
        "profissao": dados.profissao,
        "telefone": dados.telefone,
        "email": dados.email,
        "conjuge_nome": dados.conjuge_nome,
        "conjuge_cpf": dados.conjuge_cpf,
        "endereco": dados.endereco,
        "endereco_numero": dados.endereco_numero,
        "municipio": dados.municipio,
        "cep": dados.cep,
        "formulario_ok": True,
        "formulario_em": datetime.now(timezone.utc).isoformat(),
    }
    if preferir_cpf_cnpj:
        payload["cpf_cnpj"] = dados.cpf
    else:
        payload["cpf"] = dados.cpf
    return payload


def _atualizar_cliente_formulario(sb, cliente_id: str, dados: DadosFormulario) -> None:
    ultimo_erro: Exception | None = None
    for preferir_cpf_cnpj in (True, False):
        try:
            (
                sb.table("clientes")
                .update(_payload_cliente_formulario(dados, preferir_cpf_cnpj=preferir_cpf_cnpj))
                .eq("id", cliente_id)
                .execute()
            )
            return
        except Exception as exc:
            ultimo_erro = exc
            coluna = "cpf_cnpj" if preferir_cpf_cnpj else "cpf"
            if _erro_schema(exc, f"'{coluna}' column"):
                continue
            raise

    if ultimo_erro:
        raise ultimo_erro


def _validar_token(sb, token: str) -> tuple[dict[str, Any], str | None]:
    cliente_res = (
        sb.table("clientes")
        .select("id, nome, magic_link_expira, magic_link_token, formulario_ok, formulario_em")
        .eq("magic_link_token", token)
        .maybe_single()
        .execute()
    )
    cliente = cliente_res.data
    if not cliente:
        raise HTTPException(401, {"erro": "[ERRO-601] Token inválido.", "codigo": 601})

    expira = cliente.get("magic_link_expira")
    if expira and datetime.fromisoformat(expira.replace("Z", "+00:00")) < datetime.now(timezone.utc):
        raise HTTPException(401, {"erro": "[ERRO-602] Link expirado. Solicite um novo link.", "codigo": 602})

    projeto_res = (
        sb.table("projetos")
        .select("id, nome, municipio, estado, comarca, matricula, cliente_id")
        .eq("cliente_id", cliente["id"])
        .is_("deleted_at", "null")
        .order("criado_em", desc=True)
        .limit(1)
        .execute()
    )
    projeto = projeto_res.data[0] if projeto_res.data else None
    return cliente, projeto.get("id") if projeto else None


def _contexto_token(sb, token: str) -> dict[str, Any]:
    cliente, projeto_id = _validar_token(sb, token)
    projeto = None
    if projeto_id:
        projeto = (
            sb.table("vw_projetos_completo")
            .select("id, projeto_nome, municipio, estado, status")
            .eq("id", projeto_id)
            .maybe_single()
            .execute()
            .data
        )
    return {
        "cliente": {
            "id": cliente.get("id"),
            "nome": cliente.get("nome"),
            "formulario_ok": cliente.get("formulario_ok"),
            "formulario_em": cliente.get("formulario_em"),
            "magic_link_expira": cliente.get("magic_link_expira"),
        },
        "projeto": projeto,
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


@router.post("/projetos/{projeto_id}/magic-link", summary="Gerar link do formulário para o cliente")
def gerar_magic_link(projeto_id: str, supabase=None):
    sb = supabase or _get_supabase()

    try:
        res = sb.table("vw_projetos_completo").select("id, projeto_nome, cliente_id, cliente_nome").eq("id", projeto_id).single().execute()
    except Exception:
        raise HTTPException(404, {"erro": "[ERRO-401] Projeto não encontrado.", "codigo": 401})

    projeto = res.data
    cliente_id = projeto.get("cliente_id")
    if not cliente_id:
        raise HTTPException(422, {"erro": "[ERRO-102] Projeto sem cliente vinculado.", "codigo": 102})

    token = str(uuid.uuid4())
    expira = datetime.now(timezone.utc) + timedelta(days=7)
    sb.table("clientes").update({
        "magic_link_token": token,
        "magic_link_expira": expira.isoformat(),
    }).eq("id", cliente_id).execute()

    base_url = _resolver_app_url()
    link = f"{base_url}/formulario/cliente?token={token}"

    logger.info("Magic Link gerado para projeto '%s'", projeto["projeto_nome"])

    return {
        "link": link,
        "expira_em": expira.strftime("%d/%m/%Y às %H:%M"),
        "cliente_nome": projeto.get("cliente_nome"),
        "projeto_nome": projeto.get("projeto_nome"),
        "mensagem_whatsapp": (
            f"Olá {projeto.get('cliente_nome', '')}!\n\n"
            f"Para darmos andamento ao processo de regularização do imóvel *{projeto.get('projeto_nome', '')}*, "
            "preciso que você preencha um formulário com seus dados e um esboço simples da área.\n\n"
            f"Acesse pelo celular: {link}\n\n"
            "O link expira em 7 dias.\n\n"
            "Qualquer dúvida é só chamar!"
        ),
    }


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
    cliente, projeto_id = _validar_token(sb, token)
    cliente_id = cliente["id"]

    payload_raw, uploads, geo_upload = await _extrair_payload_request(request)
    dados = _normalizar_payload(payload_raw)

    _atualizar_cliente_formulario(sb, cliente_id, dados)

    if projeto_id:
        sb.table("projetos").update({
            "nome_imovel": dados.nome_imovel,
            "municipio": dados.municipio_imovel,
            "comarca": dados.comarca,
            "matricula": dados.matricula,
            "tempo_posse_anos": dados.tempo_posse_anos,
        }).eq("id", projeto_id).execute()

        for conf in dados.confrontantes:
            if not conf.get("nome"):
                continue
            sb.table("confrontantes").insert({
                "projeto_id": projeto_id,
                "lado": conf.get("lado", "Outros"),
                "nome": conf.get("nome"),
                "cpf": conf.get("cpf", ""),
                "nome_imovel": conf.get("nome_imovel", ""),
                "matricula": conf.get("matricula", ""),
                "tipo": conf.get("tipo", "particular"),
                "origem": "formulario_cliente",
            }).execute()

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

    area_nome = dados.area_nome or dados.nome_imovel or "Área principal"
    area = salvar_area_projeto(
        projeto_id=projeto_id or f"cliente-{cliente_id}",
        cliente_id=cliente_id,
        nome=area_nome,
        proprietario_nome=dados.nome,
        municipio=dados.municipio_imovel or dados.municipio,
        estado=None,
        comarca=dados.comarca,
        matricula=dados.matricula,
        ccir=dados.ccir,
        car=dados.car,
        observacoes=dados.observacoes,
        origem_tipo="formulario_cliente",
        geometria_esboco=vertices,
    )

    if dados.croqui_svg:
        uploads.append(("croqui_cliente.svg", dados.croqui_svg.encode("utf-8"), "image/svg+xml"))

    anexos = anexar_arquivos_area(area_id=area["id"], cliente_id=cliente_id, arquivos=uploads)

    if vertices:
        _salvar_referencia_cliente(sb, cliente_id, projeto_id, area_nome, vertices)

    logger.info(
        "Formulario recebido do cliente %s — projeto=%s confrontantes=%s anexos=%s vertices=%s",
        cliente_id,
        projeto_id,
        len(dados.confrontantes),
        len(anexos),
        len(vertices),
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
    }


@router.post("/projetos/{projeto_id}/gerar-documentos", summary="Gerar ZIP com os 7 documentos GPRF", response_class=Response)
def gerar_documentos(projeto_id: str, supabase=None):
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
def listar_documentos(projeto_id: str, supabase=None):
    sb = supabase or _get_supabase()

    try:
        res = sb.table("documentos_gerados").select("*").eq("projeto_id", projeto_id).order("gerado_em", desc=True).execute()
    except Exception as e:
        raise HTTPException(500, {"erro": f"[ERRO-502] {e}", "codigo": 502})

    return {"total": len(res.data), "documentos": res.data}
