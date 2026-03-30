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
from pydantic import BaseModel, ValidationError

from integracoes.areas_projeto import anexar_arquivos_area, salvar_area_projeto
from integracoes.projeto_clientes import gerar_magic_link_participante, obter_vinculo_por_token
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


def _get_supabase():
    from main import get_supabase as _get
    return _get()


def _erro_schema(exc: Exception, trecho: str) -> bool:
    return trecho.lower() in str(exc).lower()


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


def _validar_token(sb, token: str) -> tuple[dict[str, Any], str | None, dict[str, Any] | None]:
    vinculo = obter_vinculo_por_token(sb, token)
    if vinculo:
        expira = vinculo.get("magic_link_expira")
        if expira and datetime.fromisoformat(str(expira).replace("Z", "+00:00")) < datetime.now(timezone.utc):
            raise HTTPException(401, {"erro": "[ERRO-602] Link expirado. Solicite um novo link.", "codigo": 602})

        cliente_res = (
            sb.table("clientes")
            .select("id, nome, magic_link_expira, magic_link_token, formulario_ok, formulario_em")
            .eq("id", vinculo.get("cliente_id"))
            .maybe_single()
            .execute()
        )
        cliente = cliente_res.data
        if not cliente:
            raise HTTPException(401, {"erro": "[ERRO-601] Token inválido.", "codigo": 601})
        return cliente, vinculo.get("projeto_id"), vinculo

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
    if expira and datetime.fromisoformat(str(expira).replace("Z", "+00:00")) < datetime.now(timezone.utc):
        raise HTTPException(401, {"erro": "[ERRO-602] Link expirado. Solicite um novo link.", "codigo": 602})

    projeto_id, vinculo_legacy = _resolver_contexto_legacy_cliente(sb, cliente["id"])
    return cliente, projeto_id, vinculo_legacy


def _carregar_area_contexto(sb, area_id: str | None) -> dict[str, Any] | None:
    if not area_id:
        return None
    try:
        resposta = (
            sb.table("areas_projeto")
            .select("id, nome, municipio, estado, proprietario_nome, origem_tipo, resumo_esboco, resumo_final")
            .eq("id", area_id)
            .maybe_single()
            .execute()
        )
    except Exception as exc:
        if "areas_projeto" in str(exc).lower():
            return None
        raise
    return resposta.data

def _contexto_token(sb, token: str) -> dict[str, Any]:
    cliente, projeto_id, vinculo = _validar_token(sb, token)
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
    area = _carregar_area_contexto(sb, vinculo.get("area_id") if vinculo else None)
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
            "recebe_magic_link": bool(vinculo.get("recebe_magic_link")),
        } if vinculo else None,
        "area": area,
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
    supabase=None,
):
    sb = supabase or _get_supabase()

    try:
        res = sb.table("vw_projetos_completo").select("id, projeto_nome, cliente_id, cliente_nome").eq("id", projeto_id).single().execute()
    except Exception:
        raise HTTPException(404, {"erro": "[ERRO-401] Projeto não encontrado.", "codigo": 401})

    projeto = res.data
    participante = gerar_magic_link_participante(
        sb,
        projeto_id,
        projeto_cliente_id=projeto_cliente_id,
        cliente_id=cliente_id,
    )

    token: str | None = None
    expira = datetime.now(timezone.utc) + timedelta(days=7)
    cliente_destino_id = cliente_id or projeto.get("cliente_id")
    cliente_nome = projeto.get("cliente_nome")

    if participante:
        token = participante.get("magic_link_token")
        cliente_destino_id = participante.get("cliente_id") or cliente_destino_id
        if participante.get("magic_link_expira"):
            expira = datetime.fromisoformat(str(participante["magic_link_expira"]).replace("Z", "+00:00"))

    if cliente_destino_id:
        cliente_info = (
            sb.table("clientes")
            .select("id, nome")
            .eq("id", cliente_destino_id)
            .maybe_single()
            .execute()
            .data
        )
        if cliente_info:
            cliente_nome = cliente_info.get("nome") or cliente_nome

    if not token:
        if not cliente_destino_id:
            raise HTTPException(422, {"erro": "[ERRO-102] Projeto sem cliente vinculado.", "codigo": 102})

        token = str(uuid.uuid4())
        expira = datetime.now(timezone.utc) + timedelta(days=7)
        sb.table("clientes").update({
            "magic_link_token": token,
            "magic_link_expira": expira.isoformat(),
        }).eq("id", cliente_destino_id).execute()

    base_url = _resolver_app_url()
    link = f"{base_url}/formulario/cliente?token={token}"

    logger.info("Magic Link gerado para projeto '%s'", projeto["projeto_nome"])

    return {
        "link": link,
        "expira_em": expira.strftime("%d/%m/%Y às %H:%M"),
        "cliente_nome": cliente_nome,
        "cliente_id": cliente_destino_id,
        "projeto_cliente_id": participante.get("id") if participante else projeto_cliente_id,
        "papel": participante.get("papel") if participante else "principal",
        "projeto_nome": projeto.get("projeto_nome"),
        "mensagem_whatsapp": (
            f"Olá {cliente_nome or ''}!\n\n"
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
    cliente, projeto_id, vinculo = _validar_token(sb, token)
    cliente_id = cliente["id"]

    payload_raw, uploads, geo_upload = await _extrair_payload_request(request)
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
        area_id=(vinculo or {}).get("area_id"),
    )

    if dados.croqui_svg:
        uploads.append(("croqui_cliente.svg", dados.croqui_svg.encode("utf-8"), "image/svg+xml"))

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
