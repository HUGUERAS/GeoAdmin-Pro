"""
GeoAdmin Pro — Rotas de Projetos

GET  /projetos                             -> lista projetos com visão de dashboard
POST /projetos                             -> cria novo projeto (com cliente opcional)
GET  /projetos/{id}                        -> projeto enriquecido com areas, confrontacoes e documentos
PATCH /projetos/{id}                       -> atualiza metadados
GET  /projetos/{id}/clientes               -> lista participantes do projeto
GET  /projetos/{id}/arquivos               -> lista arquivos cartograficos do projeto
POST /projetos/{id}/arquivos               -> envia arquivo para a bandeja cartografica
GET  /projetos/{id}/arquivos/exportar      -> gera ZIP dos arquivos do projeto
GET  /projetos/{id}/areas                  -> lista areas conhecidas do projeto
POST /projetos/{id}/areas                  -> cria area do projeto
PATCH /projetos/{id}/areas/{area_id}       -> atualiza area do projeto
GET  /projetos/{id}/confrontacoes          -> detecta confrontacoes entre areas
GET  /projetos/{id}/confrontacoes/cartas   -> gera ZIP de cartas de confrontacao
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, Field

from integracoes.arquivos_projeto import (
    exportar_arquivos_projeto_zip,
    listar_arquivos_projeto,
    listar_eventos_cartograficos,
    migrar_arquivos_locais_para_storage,
    promover_arquivo_base_oficial,
    salvar_arquivo_projeto,
)
from integracoes.areas_projeto import (
    aplicar_revisoes_confrontacao,
    detectar_confrontacoes,
    gerar_cartas_confrontacao_zip,
    importar_areas_projeto_em_lote,
    importar_lotes_por_formato,
    listar_areas_projeto,
    listar_revisoes_confrontacao,
    montar_painel_lotes,
    salvar_area_projeto,
    salvar_revisoes_confrontacao,
    sintetizar_areas_do_projeto,
)
from integracoes.projeto_clientes import (
    listar_participantes_projeto,
    listar_eventos_magic_link,
    normalizar_participantes_entrada,
    resolver_cliente_participante,
    salvar_participantes_projeto,
    salvar_participantes_projeto_em_lote,
)
from integracoes.referencia_cliente import obter_geometria_referencia
from routes.clientes.resumos import montar_checklist_projeto
from routes.clientes.utils import query_segura, status_documentacao

router = APIRouter(prefix="/projetos", tags=["Projetos"])

TIPOS_PROCESSO_VALIDOS = {"INCRA_SIGEF", "SEAPA", "AMBOS"}


class ParticipanteProjetoPayload(BaseModel):
    cliente_id: Optional[str] = None
    nome: Optional[str] = None
    cpf: Optional[str] = None
    telefone: Optional[str] = None
    papel: str = "outro"
    principal: bool = False
    recebe_magic_link: Optional[bool] = None
    gerar_magic_link: Optional[bool] = None
    ordem: Optional[int] = None
    area_id: Optional[str] = None


class ProjetoCreate(BaseModel):
    nome: str
    zona_utm: str = "23S"
    status: str = "medicao"
    numero_job: Optional[str] = None
    municipio: Optional[str] = None
    estado: Optional[str] = None
    cliente_id: Optional[str] = None
    cliente_nome: Optional[str] = None
    cliente_cpf: Optional[str] = None
    cliente_telefone: Optional[str] = None
    gerar_magic_link: bool = False
    tipo_processo: Optional[str] = None
    participantes: list[ParticipanteProjetoPayload] = Field(default_factory=list)


class ProjetoUpdate(BaseModel):
    nome: Optional[str] = None
    numero_job: Optional[str] = None
    municipio: Optional[str] = None
    estado: Optional[str] = None
    status: Optional[str] = None
    zona_utm: Optional[str] = None
    tipo_processo: Optional[str] = None


class VerticePayload(BaseModel):
    lon: float
    lat: float


class AreaParticipantePayload(BaseModel):
    cliente_id: Optional[str] = None
    nome: Optional[str] = None
    cpf: Optional[str] = None
    telefone: Optional[str] = None
    papel: str = "outro"
    principal: bool = False
    recebe_magic_link: bool = False
    ordem: Optional[int] = None


class AreaProjetoPayload(BaseModel):
    cliente_id: Optional[str] = None
    nome: str
    proprietario_nome: Optional[str] = None
    municipio: Optional[str] = None
    estado: Optional[str] = None
    comarca: Optional[str] = None
    matricula: Optional[str] = None
    ccir: Optional[str] = None
    car: Optional[str] = None
    observacoes: Optional[str] = None
    codigo_lote: Optional[str] = None
    quadra: Optional[str] = None
    setor: Optional[str] = None
    status_operacional: Optional[str] = None
    status_documental: Optional[str] = None
    origem_tipo: str = "manual"
    geometria_esboco: list[VerticePayload] = Field(default_factory=list)
    geometria_final: list[VerticePayload] = Field(default_factory=list)
    participantes_area: list[AreaParticipantePayload] = Field(default_factory=list)


class AreaProjetoUpdate(BaseModel):
    cliente_id: Optional[str] = None
    nome: Optional[str] = None
    proprietario_nome: Optional[str] = None
    municipio: Optional[str] = None
    estado: Optional[str] = None
    comarca: Optional[str] = None
    matricula: Optional[str] = None
    ccir: Optional[str] = None
    car: Optional[str] = None
    observacoes: Optional[str] = None
    codigo_lote: Optional[str] = None
    quadra: Optional[str] = None
    setor: Optional[str] = None
    status_operacional: Optional[str] = None
    status_documental: Optional[str] = None
    origem_tipo: Optional[str] = None
    geometria_esboco: Optional[list[VerticePayload]] = None
    geometria_final: Optional[list[VerticePayload]] = None
    participantes_area: Optional[list[AreaParticipantePayload]] = None


class ImportacaoLotePayload(BaseModel):
    area_id: Optional[str] = None
    nome: Optional[str] = None
    cliente_id: Optional[str] = None
    proprietario_nome: Optional[str] = None
    municipio: Optional[str] = None
    estado: Optional[str] = None
    comarca: Optional[str] = None
    matricula: Optional[str] = None
    ccir: Optional[str] = None
    car: Optional[str] = None
    observacoes: Optional[str] = None
    codigo_lote: Optional[str] = None
    quadra: Optional[str] = None
    setor: Optional[str] = None
    status_operacional: Optional[str] = None
    status_documental: Optional[str] = None
    origem_tipo: Optional[str] = None
    geometria_esboco: list[VerticePayload] = Field(default_factory=list)
    geometria_final: list[VerticePayload] = Field(default_factory=list)
    participantes_area: list[AreaParticipantePayload] = Field(default_factory=list)


class ImportacaoLotesRequest(BaseModel):
    lotes: list[ImportacaoLotePayload] = Field(default_factory=list)
    atualizar_existentes: bool = True


class VinculoLotePayload(BaseModel):
    area_id: Optional[str] = None
    codigo_lote: Optional[str] = None
    quadra: Optional[str] = None
    setor: Optional[str] = None
    participantes: list[AreaParticipantePayload] = Field(default_factory=list)


class VinculosLoteRequest(BaseModel):
    vinculos: list[VinculoLotePayload] = Field(default_factory=list)


class PromoverArquivoPayload(BaseModel):
    autor: Optional[str] = None
    observacao: Optional[str] = None
    classificacao_destino: Optional[str] = None


class RevisaoConfrontacaoPayload(BaseModel):
    confronto_id: str
    status_revisao: str = "confirmada"
    tipo_relacao: str = "interna"
    observacao: Optional[str] = None
    autor: Optional[str] = None


class RevisoesConfrontacaoRequest(BaseModel):
    revisoes: list[RevisaoConfrontacaoPayload] = Field(default_factory=list)


def _get_supabase():
    from main import get_supabase
    return get_supabase()



def _validar_tipo_processo(tipo_processo: str | None) -> str | None:
    if tipo_processo is None:
        return None
    valor = tipo_processo.strip().upper()
    if valor not in TIPOS_PROCESSO_VALIDOS:
        raise HTTPException(status_code=422, detail={"erro": "tipo_processo invalido", "codigo": 422})
    return valor



def _erro_schema(exc: Exception, trecho: str) -> bool:
    return trecho.lower() in str(exc).lower()



def _payload_cliente_compativel(
    *,
    nome: str,
    cpf: str | None,
    telefone: str | None,
    preferir_cpf_cnpj: bool = True,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "nome": nome or "Cliente sem nome",
        "telefone": telefone or None,
    }
    if preferir_cpf_cnpj:
        payload["cpf_cnpj"] = cpf or None
    else:
        payload["cpf"] = cpf or None
    return payload



def _buscar_cliente_por_documento(sb, cpf: str) -> dict[str, Any] | None:
    for campo in ("cpf_cnpj", "cpf"):
        try:
            cliente = (
                sb.table("clientes")
                .select("id")
                .eq(campo, cpf)
                .maybe_single()
                .execute()
                .data
            )
        except Exception as exc:
            if _erro_schema(exc, f"'{campo}' column"):
                continue
            raise
        if cliente:
            return cliente
    return None



def _criar_cliente_compativel(sb, *, nome: str, cpf: str | None, telefone: str | None) -> str:
    ultimo_erro: Exception | None = None
    for preferir_cpf_cnpj in (True, False):
        try:
            res = sb.table("clientes").insert(
                _payload_cliente_compativel(
                    nome=nome,
                    cpf=cpf,
                    telefone=telefone,
                    preferir_cpf_cnpj=preferir_cpf_cnpj,
                )
            ).execute()
        except Exception as exc:
            ultimo_erro = exc
            coluna = "cpf_cnpj" if preferir_cpf_cnpj else "cpf"
            if _erro_schema(exc, f"'{coluna}' column"):
                continue
            raise
        if res.data:
            return res.data[0]["id"]

    if ultimo_erro:
        raise ultimo_erro
    raise HTTPException(status_code=500, detail={"erro": "Falha ao criar cliente do projeto", "codigo": 500})



def _inserir_projeto_compativel(sb, dados: dict[str, Any]):
    payload = dict(dados)
    try:
        return sb.table("projetos").insert(payload).execute()
    except Exception as exc:
        if payload.get("tipo_processo") is not None and _erro_schema(exc, "'tipo_processo' column"):
            payload.pop("tipo_processo", None)
            return sb.table("projetos").insert(payload).execute()
        raise



def _atualizar_projeto_compativel(sb, projeto_id: str, dados: dict[str, Any]):
    payload = dict(dados)
    try:
        return sb.table("projetos").update(payload).eq("id", projeto_id).execute()
    except Exception as exc:
        if payload.get("tipo_processo") is not None and _erro_schema(exc, "'tipo_processo' column"):
            payload.pop("tipo_processo", None)
            return sb.table("projetos").update(payload).eq("id", projeto_id).execute()
        raise



def _projeto_ou_404(sb, projeto_id: str) -> dict[str, Any]:
    res = sb.table("vw_projetos_completo").select("*").eq("id", projeto_id).single().execute()
    if res is None or not res.data:
        raise HTTPException(status_code=404, detail={"erro": "Projeto nao encontrado", "codigo": 404})
    return res.data



def _cliente_primario(sb, cliente_id: str | None) -> dict[str, Any] | None:
    if not cliente_id:
        return None
    return query_segura(
        lambda: (
            sb.table("clientes")
            .select("*")
            .eq("id", cliente_id)
            .maybe_single()
            .execute()
            .data
        ),
        None,
    )



def _documentos_projeto(sb, projeto_id: str) -> list[dict[str, Any]]:
    return query_segura(
        lambda: (
            sb.table("documentos_gerados")
            .select("id, tipo, gerado_em")
            .eq("projeto_id", projeto_id)
            .is_("deleted_at", "null")
            .order("gerado_em", desc=True)
            .execute()
            .data
            or []
        ),
        [],
    )



def _confrontantes_projeto(sb, projeto_id: str) -> list[dict[str, Any]]:
    return query_segura(
        lambda: (
            sb.table("confrontantes")
            .select("id, projeto_id, lado, tipo, nome, cpf, nome_imovel, matricula, origem, criado_em")
            .eq("projeto_id", projeto_id)
            .is_("deleted_at", "null")
            .order("criado_em", desc=False)
            .execute()
            .data
            or []
        ),
        [],
    )



def _formulario_projeto(sb, projeto_id: str, cliente_id: str | None) -> dict[str, Any] | None:
    if not cliente_id:
        return None
    return query_segura(
        lambda: (
            sb.table("vw_formulario_cliente")
            .select("projeto_id, cliente_id, formulario_ok, formulario_em, magic_link_expira")
            .eq("projeto_id", projeto_id)
            .maybe_single()
            .execute()
            .data
        ),
        None,
    )



def _perimetro_ativo(sb, projeto_id: str) -> dict[str, Any] | None:
    from routes.perimetros import buscar_perimetro_ativo

    return query_segura(lambda: buscar_perimetro_ativo(projeto_id, supabase=sb), None)



def _resolver_cliente_para_criacao(sb, payload: ProjetoCreate) -> str | None:
    if payload.cliente_id:
        return payload.cliente_id

    nome = (payload.cliente_nome or "").strip()
    cpf = (payload.cliente_cpf or "").strip()
    telefone = (payload.cliente_telefone or "").strip()
    if not (nome or cpf or telefone):
        return None

    if cpf:
        cliente_existente = query_segura(lambda: _buscar_cliente_por_documento(sb, cpf), None)
        if cliente_existente:
            return cliente_existente.get("id")

    try:
        return _criar_cliente_compativel(
            sb,
            nome=nome or "Cliente sem nome",
            cpf=cpf or None,
            telefone=telefone or None,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail={"erro": f"Falha ao criar cliente do projeto: {exc}", "codigo": 500})



def _participantes_payload(payload: ProjetoCreate) -> list[dict[str, Any]]:
    participantes = [item.model_dump(exclude_none=True) for item in payload.participantes]
    legado = {
        "cliente_id": payload.cliente_id,
        "cliente_nome": payload.cliente_nome,
        "cliente_cpf": payload.cliente_cpf,
        "cliente_telefone": payload.cliente_telefone,
        "gerar_magic_link": payload.gerar_magic_link,
    }
    return normalizar_participantes_entrada(participantes, legado=legado)



def _participantes_area_payload(participantes_area: list[AreaParticipantePayload] | None) -> list[dict[str, Any]]:
    return [item.model_dump(exclude_none=True) for item in (participantes_area or [])]


def _cliente_area_payload(
    *,
    cliente_id: str | None,
    participantes_area: list[dict[str, Any]],
    fallback: str | None,
) -> str | None:
    if cliente_id:
        return cliente_id
    participante_com_cliente = next((item for item in participantes_area if item.get("cliente_id")), None)
    if participante_com_cliente:
        return participante_com_cliente.get("cliente_id")
    return fallback


def _proprietario_area_payload(
    *,
    proprietario_nome: str | None,
    participantes_area: list[dict[str, Any]],
    fallback: str | None,
) -> str | None:
    if proprietario_nome:
        return proprietario_nome
    participante_principal = next((item for item in participantes_area if item.get("principal") and item.get("nome")), None)
    if participante_principal:
        return participante_principal.get("nome")
    participante_nomeado = next((item for item in participantes_area if item.get("nome")), None)
    if participante_nomeado:
        return participante_nomeado.get("nome")
    return fallback


def _chave_lote_referencia(*, codigo_lote: str | None, quadra: str | None, setor: str | None) -> str | None:
    codigo = (codigo_lote or '').strip().lower()
    quadra_valor = (quadra or '').strip().lower()
    setor_valor = (setor or '').strip().lower()
    if not any((codigo, quadra_valor, setor_valor)):
        return None
    return f"{quadra_valor}::{codigo}::{setor_valor}"


def _resolver_area_por_referencia(areas: list[dict[str, Any]], *, area_id: str | None = None, codigo_lote: str | None = None, quadra: str | None = None, setor: str | None = None) -> dict[str, Any] | None:
    if area_id:
        return next((item for item in areas if str(item.get('id')) == str(area_id)), None)
    chave_alvo = _chave_lote_referencia(codigo_lote=codigo_lote, quadra=quadra, setor=setor)
    if not chave_alvo:
        return None
    for area in areas:
        chave_area = _chave_lote_referencia(codigo_lote=area.get('codigo_lote'), quadra=area.get('quadra'), setor=area.get('setor'))
        if chave_area == chave_alvo:
            return area
    return None


def _cliente_principal_do_payload(sb, participantes: list[dict[str, Any]], payload: ProjetoCreate) -> str | None:
    if participantes:
        principal = next((item for item in participantes if item.get("principal")), None) or participantes[0]
        cliente_id = resolver_cliente_participante(sb, principal)
        principal["cliente_id"] = cliente_id
        principal["papel"] = "principal"
        return cliente_id
    return _resolver_cliente_para_criacao(sb, payload)



def _gerar_magic_links_iniciais(sb, projeto_id: str, participantes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not participantes:
        return []

    from routes.documentos import gerar_magic_link

    links: list[dict[str, Any]] = []
    participantes_ativos = [item for item in participantes if item.get("recebe_magic_link")]
    for participante in participantes_ativos:
        try:
            link = gerar_magic_link(
                projeto_id,
                cliente_id=participante.get("cliente_id"),
                projeto_cliente_id=participante.get("id"),
                supabase=sb,
            )
        except Exception:
            continue
        if link:
            links.append({
                **link,
                "papel": participante.get("papel"),
                "principal": bool(participante.get("principal")),
                "cliente_id": participante.get("cliente_id"),
                "projeto_cliente_id": participante.get("id"),
            })
    return links



def _reverter_criacao_projeto(sb, projeto_id: str) -> None:
    agora = datetime.now(timezone.utc).isoformat()
    try:
        (
            sb.table("projeto_clientes")
            .update({"deleted_at": agora})
            .eq("projeto_id", projeto_id)
            .is_("deleted_at", "null")
            .execute()
        )
    except Exception as exc:
        if "projeto_clientes" not in str(exc).lower():
            raise

    try:
        _atualizar_projeto_compativel(sb, projeto_id, {"deleted_at": agora})
    except Exception:
        try:
            sb.table("projetos").update({"deleted_at": agora}).eq("id", projeto_id).execute()
        except Exception:
            pass



def _resumo_lotes(areas: list[dict[str, Any]]) -> dict[str, Any]:
    totais_operacionais: dict[str, int] = {}
    totais_documentais: dict[str, int] = {}
    sem_participante = 0
    prontos = 0
    com_geometria = 0

    for area in areas:
        status_operacional = area.get("status_operacional") or "aguardando_cliente"
        status_documental = area.get("status_documental") or "pendente"
        totais_operacionais[status_operacional] = totais_operacionais.get(status_operacional, 0) + 1
        totais_documentais[status_documental] = totais_documentais.get(status_documental, 0) + 1
        if not (area.get("participantes_area") or area.get("cliente_id")):
            sem_participante += 1
        if area.get("status_geometria") in {"apenas_esboco", "geometria_final"}:
            com_geometria += 1
        if status_operacional in {"geometria_final", "peca_pronta"} and status_documental in {"documentacao_ok", "peca_pronta"}:
            prontos += 1

    return {
        "total": len(areas),
        "sem_participante": sem_participante,
        "com_geometria": com_geometria,
        "prontos": prontos,
        "pendentes": max(len(areas) - prontos, 0),
        "por_status_operacional": totais_operacionais,
        "por_status_documental": totais_documentais,
    }



def _resumo_lotes_lista(sb, projeto_ids: list[str]) -> dict[str, dict[str, Any]]:
    if not projeto_ids:
        return {}
    try:
        consulta = sb.table("areas_projeto").select("id, projeto_id, cliente_id, status_operacional, status_documental, geometria_esboco, geometria_final").is_("deleted_at", "null")
        if len(projeto_ids) == 1:
            consulta = consulta.eq("projeto_id", projeto_ids[0])
        else:
            consulta = consulta.in_("projeto_id", projeto_ids)
        itens = consulta.execute().data or []
    except Exception:
        return {}

    participantes_por_area: set[str] = set()
    try:
        resposta_participantes = sb.table("area_clientes").select("area_id").is_("deleted_at", "null").execute().data or []
        participantes_por_area = {str(item.get("area_id")) for item in resposta_participantes if item.get("area_id")}
    except Exception:
        participantes_por_area = set()

    por_projeto: dict[str, list[dict[str, Any]]] = {projeto_id: [] for projeto_id in projeto_ids}
    for item in itens:
        area = {
            "id": item.get("id"),
            "projeto_id": item.get("projeto_id"),
            "cliente_id": item.get("cliente_id"),
            "status_operacional": item.get("status_operacional"),
            "status_documental": item.get("status_documental"),
            "geometria_esboco": item.get("geometria_esboco") or [],
            "geometria_final": item.get("geometria_final") or [],
        }
        area["status_geometria"] = "geometria_final" if area["geometria_final"] else ("apenas_esboco" if area["geometria_esboco"] else "sem_geometria")
        if str(area.get("id")) in participantes_por_area:
            area["participantes_area"] = [{"area_id": area["id"]}]
        por_projeto.setdefault(str(item.get("projeto_id")), []).append(area)

    return {projeto_id: _resumo_lotes(areas) for projeto_id, areas in por_projeto.items() if areas}



def _enriquecer_projeto(sb, projeto_id: str) -> dict[str, Any]:
    projeto = _projeto_ou_404(sb, projeto_id)
    cliente = _cliente_primario(sb, projeto.get("cliente_id"))
    participantes = listar_participantes_projeto(sb, projeto_id, cliente_principal=cliente)
    pontos_res = (
        sb.table("vw_pontos_geo")
        .select("id, nome, altitude_m, descricao, codigo, lon, lat")
        .eq("projeto_id", projeto_id)
        .execute()
    )
    pontos = pontos_res.data or []
    perimetro_ativo = _perimetro_ativo(sb, projeto_id)
    formulario = _formulario_projeto(sb, projeto_id, projeto.get("cliente_id"))
    documentos = _documentos_projeto(sb, projeto_id)
    confrontantes = _confrontantes_projeto(sb, projeto_id)
    geometria_referencia = obter_geometria_referencia(sb, projeto.get("cliente_id")) if projeto.get("cliente_id") else None
    arquivos_cartograficos = listar_arquivos_projeto(sb, projeto_id)
    arquivos_eventos = listar_eventos_cartograficos(sb, projeto_id, limite=50)
    magic_links_historico = listar_eventos_magic_link(sb, projeto_id, limite=50)
    areas = sintetizar_areas_do_projeto(
        projeto=projeto,
        cliente=cliente,
        perimetro_ativo=perimetro_ativo,
        geometria_referencia=geometria_referencia,
        sb=sb,
        participantes_projeto=participantes,
    )
    revisoes_confrontacao = listar_revisoes_confrontacao(sb, projeto_id)
    confrontacoes_detectadas = detectar_confrontacoes(areas)
    confrontacoes = aplicar_revisoes_confrontacao(confrontacoes_detectadas, revisoes_confrontacao)

    checklist = montar_checklist_projeto(
        cliente or {},
        {
            **projeto,
            "documentos_total": len(documentos),
            "confrontantes_total": len(confrontantes),
            "formulario_ok": bool((formulario or {}).get("formulario_ok") or (cliente or {}).get("formulario_ok")),
            "formulario_em": (formulario or {}).get("formulario_em") or (cliente or {}).get("formulario_em"),
            "magic_link_expira": (formulario or {}).get("magic_link_expira") or (cliente or {}).get("magic_link_expira"),
        },
        perimetro_ativo,
    )

    projeto["projeto_nome"] = projeto.get("nome", "")
    projeto["pontos"] = pontos
    projeto["total_pontos"] = len(pontos)
    projeto["perimetro_ativo"] = perimetro_ativo
    projeto["cliente"] = cliente
    projeto["clientes"] = participantes or ([cliente] if cliente else [])
    projeto["participantes"] = participantes
    projeto["formulario"] = formulario or {
        "formulario_ok": bool((cliente or {}).get("formulario_ok")),
        "formulario_em": (cliente or {}).get("formulario_em"),
        "magic_link_expira": (cliente or {}).get("magic_link_expira"),
    }
    projeto["documentos"] = documentos
    projeto["documentos_resumo"] = {
        "total": len(documentos),
        "tipos": sorted({doc.get("tipo") for doc in documentos if doc.get("tipo")}),
        "ultimo_documento_em": documentos[0].get("gerado_em") if documentos else None,
    }
    projeto["confrontantes"] = confrontantes
    projeto["areas"] = areas
    projeto["confrontacoes"] = confrontacoes
    projeto["geometria_referencia"] = geometria_referencia
    projeto["checklist_documental"] = checklist
    projeto["status_documentacao"] = status_documentacao(
        [projeto],
        bool((projeto["formulario"] or {}).get("formulario_ok")),
        len(documentos),
    )
    projeto["arquivos_cartograficos"] = arquivos_cartograficos
    projeto["arquivos_eventos"] = arquivos_eventos
    projeto["magic_links_historico"] = magic_links_historico
    projeto["arquivos_resumo"] = {
        "total": len(arquivos_cartograficos),
        "base_oficial_total": sum(1 for item in arquivos_cartograficos if item.get("base_oficial")),
        "eventos_total": len(arquivos_eventos),
        "por_classificacao": {
            chave: sum(1 for item in arquivos_cartograficos if item.get("classificacao") == chave)
            for chave in sorted({item.get("classificacao") for item in arquivos_cartograficos if item.get("classificacao")})
        },
    }
    projeto["magic_links_resumo"] = {
        "total_eventos": len(magic_links_historico),
        "gerados": sum(1 for item in magic_links_historico if item.get("tipo_evento") in {"gerado", "reenviado"}),
        "consumidos": sum(1 for item in magic_links_historico if item.get("tipo_evento") == "consumido"),
        "ultimos_eventos": magic_links_historico[:10],
    }
    projeto["resumo_geo"] = {
        "areas_total": len(areas),
        "confrontacoes_total": len(confrontacoes),
        "confrontantes_total": len(confrontantes),
        "esbocos_total": sum(1 for area in areas if area.get("tipo_geometria_ativa") == "esboco"),
        "geometrias_finais_total": sum(1 for area in areas if area.get("tipo_geometria_ativa") == "final"),
        "participantes_total": len(participantes),
        "arquivos_total": len(arquivos_cartograficos),
    }
    projeto["resumo_lotes"] = _resumo_lotes(areas)
    projeto["painel_lotes"] = montar_painel_lotes(areas)
    projeto["confrontacoes_resumo"] = _resumo_confrontacoes(confrontacoes, confrontantes)
    projeto["prontidao_piloto"] = _prontidao_piloto(projeto)
    return projeto


@router.get("", summary="Listar todos os projetos")
def listar_projetos(limite: int = 50, deslocamento: int = 0):
    limite = min(max(int(limite), 1), 500)
    deslocamento = max(int(deslocamento), 0)
    sb = _get_supabase()
    res = sb.table("vw_projetos_completo").select("*").order("criado_em", desc=True).range(deslocamento, deslocamento + limite - 1).execute()
    projetos = res.data or []
    resumo_por_projeto = _resumo_lotes_lista(sb, [str(item.get("id")) for item in projetos if item.get("id")])
    for projeto in projetos:
        resumo_lotes = resumo_por_projeto.get(str(projeto.get("id")))
        if resumo_lotes:
            projeto["resumo_lotes"] = resumo_lotes
            projeto["areas_total"] = resumo_lotes.get("total")
            projeto["lotes_prontos"] = resumo_lotes.get("prontos")
            projeto["lotes_pendentes"] = resumo_lotes.get("pendentes")
    return {"total": len(projetos), "projetos": projetos}


@router.post("", summary="Criar novo projeto", status_code=201)
def criar_projeto(payload: ProjetoCreate):
    sb = _get_supabase()
    participantes = _participantes_payload(payload)
    cliente_id = _cliente_principal_do_payload(sb, participantes, payload)
    tipo_processo = _validar_tipo_processo(payload.tipo_processo)
    dados = {
        "nome": payload.nome,
        "zona_utm": payload.zona_utm,
        "status": payload.status,
        "numero_job": payload.numero_job,
        "municipio": payload.municipio,
        "estado": payload.estado,
        "cliente_id": cliente_id,
        "tipo_processo": tipo_processo,
    }
    dados = {chave: valor for chave, valor in dados.items() if valor is not None}
    res = _inserir_projeto_compativel(sb, dados)
    if not res.data:
        raise HTTPException(status_code=500, detail={"erro": "Falha ao criar projeto", "codigo": 500})

    projeto_id = res.data[0]["id"]
    try:
        participantes_salvos = salvar_participantes_projeto(sb, projeto_id, participantes) if participantes else []
        principal_salvo = next((item for item in participantes_salvos if item.get("principal")), None)
        cliente_principal_id = principal_salvo.get("cliente_id") if principal_salvo else cliente_id
        if cliente_principal_id and cliente_principal_id != cliente_id:
            _atualizar_projeto_compativel(sb, projeto_id, {"cliente_id": cliente_principal_id})

        magic_links = _gerar_magic_links_iniciais(sb, projeto_id, participantes_salvos or participantes)
        projeto = _enriquecer_projeto(sb, projeto_id)
        if magic_links:
            projeto["magic_links"] = magic_links
            projeto["magic_link"] = next((item for item in magic_links if item.get("principal")), magic_links[0])
        return projeto
    except HTTPException:
        _reverter_criacao_projeto(sb, projeto_id)
        raise
    except Exception as exc:
        _reverter_criacao_projeto(sb, projeto_id)
        raise HTTPException(
            status_code=500,
            detail={
                "erro": f"Falha ao concluir a criação do projeto. O cadastro foi revertido para evitar dados parciais: {exc}",
                "codigo": 500,
            },
        ) from exc


@router.get("/{projeto_id}", summary="Buscar projeto com dados operacionais")
def buscar_projeto(projeto_id: str):
    sb = _get_supabase()
    return _enriquecer_projeto(sb, projeto_id)


@router.patch("/{projeto_id}", summary="Atualizar metadados do projeto")
def atualizar_projeto(projeto_id: str, payload: ProjetoUpdate):
    sb = _get_supabase()
    _projeto_ou_404(sb, projeto_id)

    if payload.tipo_processo is not None:
        payload.tipo_processo = _validar_tipo_processo(payload.tipo_processo)
    dados = payload.model_dump(exclude_none=True)
    if not dados:
        raise HTTPException(status_code=400, detail={"erro": "Nenhum campo para atualizar", "codigo": 400})

    res = _atualizar_projeto_compativel(sb, projeto_id, dados)
    if not res.data:
        raise HTTPException(status_code=500, detail={"erro": "Falha ao atualizar projeto", "codigo": 500})
    return _enriquecer_projeto(sb, projeto_id)


@router.get("/{projeto_id}/clientes", summary="Listar participantes do projeto")
@router.get("/{projeto_id}/participantes", include_in_schema=False)
def listar_participantes(projeto_id: str):
    sb = _get_supabase()
    projeto = _projeto_ou_404(sb, projeto_id)
    participantes = listar_participantes_projeto(sb, projeto_id, cliente_principal=_cliente_primario(sb, projeto.get("cliente_id")))
    return {"total": len(participantes), "clientes": participantes, "participantes": participantes}


@router.get("/{projeto_id}/arquivos", summary="Listar arquivos cartograficos do projeto")
def arquivos_do_projeto(projeto_id: str):
    sb = _get_supabase()
    _projeto_ou_404(sb, projeto_id)
    arquivos = listar_arquivos_projeto(sb, projeto_id)
    return {"total": len(arquivos), "arquivos": arquivos}


@router.post("/{projeto_id}/arquivos", summary="Enviar arquivo para a base cartografica", status_code=201)
async def enviar_arquivo_projeto(
    projeto_id: str,
    arquivo: UploadFile = File(...),
    nome: str | None = Form(None),
    nome_arquivo: str | None = Form(None),
    origem: str = Form("topografo"),
    classificacao: str = Form("referencia_visual"),
    mime_type: str | None = Form(None),
    cliente_id: str | None = Form(None),
    area_id: str | None = Form(None),
):
    sb = _get_supabase()
    _projeto_ou_404(sb, projeto_id)
    conteudo = await arquivo.read()
    if not conteudo:
        raise HTTPException(status_code=422, detail={"erro": "Arquivo vazio", "codigo": 422})

    registro = salvar_arquivo_projeto(
        sb,
        projeto_id=projeto_id,
        nome_arquivo=nome_arquivo or nome or arquivo.filename or "arquivo",
        conteudo=conteudo,
        origem=origem,
        classificacao=classificacao,
        cliente_id=cliente_id,
        area_id=area_id,
        mime_type=mime_type or arquivo.content_type,
    )
    return registro


@router.get("/{projeto_id}/arquivos/exportar", summary="Exportar bandeja cartografica em ZIP")
def exportar_arquivos(projeto_id: str):
    sb = _get_supabase()
    projeto = _projeto_ou_404(sb, projeto_id)
    zip_bytes = exportar_arquivos_projeto_zip(sb, projeto_id)
    nome = f"Arquivos_Projeto_{(projeto.get('nome') or 'Projeto').replace(' ', '_')[:30]}.zip"
    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{nome}"'},
    )


@router.get("/{projeto_id}/arquivos/eventos", summary="Listar auditoria cartografica do projeto")
def listar_eventos_arquivos(projeto_id: str, limite: int = 100):
    sb = _get_supabase()
    _projeto_ou_404(sb, projeto_id)
    eventos = listar_eventos_cartograficos(sb, projeto_id, limite=limite)
    return {"total": len(eventos), "eventos": eventos}


@router.post("/{projeto_id}/arquivos/{arquivo_id}/promover", summary="Promover arquivo para base oficial")
def promover_arquivo(projeto_id: str, arquivo_id: str, payload: PromoverArquivoPayload):
    sb = _get_supabase()
    _projeto_ou_404(sb, projeto_id)
    try:
        arquivo = promover_arquivo_base_oficial(
            sb,
            projeto_id=projeto_id,
            arquivo_id=arquivo_id,
            autor=payload.autor,
            observacao=payload.observacao,
            classificacao_destino=payload.classificacao_destino,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail={"erro": str(exc), "codigo": 404})
    return arquivo


@router.post("/{projeto_id}/arquivos/migrar-legado", summary="Migrar arquivos antigos do fallback local para Supabase Storage")
def migrar_arquivos_legados(projeto_id: str, limite: int = 100, autor: str | None = None):
    sb = _get_supabase()
    _projeto_ou_404(sb, projeto_id)
    return migrar_arquivos_locais_para_storage(sb, projeto_id=projeto_id, limite=limite, autor=autor)


@router.get("/{projeto_id}/lotes/painel", summary="Listar painel operacional por lote")
def painel_lotes(projeto_id: str):
    sb = _get_supabase()
    projeto = _enriquecer_projeto(sb, projeto_id)
    return {
        "total": len(projeto.get("painel_lotes") or []),
        "resumo_lotes": projeto.get("resumo_lotes"),
        "lotes": projeto.get("painel_lotes") or [],
    }


@router.post("/{projeto_id}/areas/importar", summary="Importar areas/lotes em lote", status_code=201)
def importar_areas_json(projeto_id: str, payload: ImportacaoLotesRequest):
    sb = _get_supabase()
    _projeto_ou_404(sb, projeto_id)
    resultado = importar_areas_projeto_em_lote(
        projeto_id=projeto_id,
        lotes=[item.model_dump(exclude_none=True) for item in payload.lotes],
        atualizar_existentes=payload.atualizar_existentes,
        sb=sb,
    )
    return {**resultado, "resumo_lotes": _resumo_lotes(resultado.get("areas") or [])}


@router.post("/{projeto_id}/areas/importar-arquivo", summary="Importar arquivo de lotes/areas", status_code=201)
async def importar_areas_arquivo(
    projeto_id: str,
    arquivo: UploadFile = File(...),
    formato: str | None = Form(None),
    atualizar_existentes: bool = Form(True),
    salvar_na_bandeja: bool = Form(True),
    autor: str | None = Form(None),
):
    sb = _get_supabase()
    _projeto_ou_404(sb, projeto_id)
    conteudo = await arquivo.read()
    if not conteudo:
        raise HTTPException(status_code=422, detail={"erro": "Arquivo vazio", "codigo": 422})

    formato_arquivo = (formato or (arquivo.filename or '').split('.')[-1]).lower()
    try:
        interpretado = importar_lotes_por_formato(formato_arquivo, conteudo)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail={"erro": str(exc), "codigo": 422})

    registro_arquivo = None
    if salvar_na_bandeja:
        registro_arquivo = salvar_arquivo_projeto(
            sb,
            projeto_id=projeto_id,
            nome_arquivo=arquivo.filename or f'importacao-lotes.{formato_arquivo}',
            conteudo=conteudo,
            origem='topografo',
            classificacao='camada_auxiliar',
            mime_type=arquivo.content_type,
            autor=autor,
        )

    resultado = importar_areas_projeto_em_lote(
        projeto_id=projeto_id,
        lotes=interpretado.get('lotes') or [],
        atualizar_existentes=bool(atualizar_existentes),
        sb=sb,
    )
    return {
        **resultado,
        "parcial": bool(interpretado.get('parcial')),
        "mensagem": interpretado.get('mensagem'),
        "arquivo_importado": registro_arquivo,
    }


@router.post("/{projeto_id}/areas/vinculos-lote", summary="Vincular participantes em lote por area/lote")
def vincular_participantes_lote(projeto_id: str, payload: VinculosLoteRequest):
    sb = _get_supabase()
    _projeto_ou_404(sb, projeto_id)
    participantes = listar_participantes_projeto(sb, projeto_id)
    areas = listar_areas_projeto(projeto_id, sb=sb, participantes_projeto=participantes)
    vinculos_normalizados: list[dict[str, Any]] = []
    areas_afetadas: list[str] = []

    for vinculo in payload.vinculos:
        area = _resolver_area_por_referencia(
            areas,
            area_id=vinculo.area_id,
            codigo_lote=vinculo.codigo_lote,
            quadra=vinculo.quadra,
            setor=vinculo.setor,
        )
        if not area:
            continue
        participantes_area = [item.model_dump(exclude_none=True) for item in vinculo.participantes]
        if not participantes_area:
            continue
        vinculos_normalizados.append({
            "area_id": area.get("id"),
            "participantes": participantes_area,
        })
        areas_afetadas.append(str(area.get("id")))

    if not vinculos_normalizados:
        raise HTTPException(status_code=422, detail={"erro": "Nenhum vinculo de lote valido foi informado", "codigo": 422})

    resultado_vinculos = salvar_participantes_projeto_em_lote(sb, projeto_id, vinculos_normalizados)
    areas_atualizadas = listar_areas_projeto(projeto_id, sb=sb, participantes_projeto=listar_participantes_projeto(sb, projeto_id))
    lotes_afetados = [item for item in montar_painel_lotes(areas_atualizadas) if str(item.get('area_id')) in set(areas_afetadas)]
    return {
        "vinculos_total": len(vinculos_normalizados),
        "areas_afetadas": len(set(areas_afetadas)),
        "participantes_projeto_total": len(resultado_vinculos.get("participantes_projeto") or []),
        "participantes_area": resultado_vinculos.get("participantes_area") or {},
        "lotes": lotes_afetados,
    }


@router.get("/{projeto_id}/areas", summary="Listar areas conhecidas do projeto")
def listar_areas(projeto_id: str):
    sb = _get_supabase()
    projeto = _projeto_ou_404(sb, projeto_id)
    cliente = _cliente_primario(sb, projeto.get("cliente_id"))
    perimetro_ativo = _perimetro_ativo(sb, projeto_id)
    geometria_referencia = obter_geometria_referencia(sb, projeto.get("cliente_id")) if projeto.get("cliente_id") else None
    participantes = listar_participantes_projeto(sb, projeto_id, cliente_principal=cliente)
    areas = sintetizar_areas_do_projeto(
        projeto=projeto,
        cliente=cliente,
        perimetro_ativo=perimetro_ativo,
        geometria_referencia=geometria_referencia,
        sb=sb,
        participantes_projeto=participantes,
    )
    return {"total": len(areas), "areas": areas}


@router.post("/{projeto_id}/areas", summary="Criar area do projeto", status_code=201)
def criar_area(projeto_id: str, payload: AreaProjetoPayload):
    sb = _get_supabase()
    projeto = _projeto_ou_404(sb, projeto_id)
    participantes_area = _participantes_area_payload(payload.participantes_area)
    area = salvar_area_projeto(
        projeto_id=projeto_id,
        cliente_id=_cliente_area_payload(
            cliente_id=payload.cliente_id,
            participantes_area=participantes_area,
            fallback=projeto.get("cliente_id"),
        ),
        nome=payload.nome,
        proprietario_nome=_proprietario_area_payload(
            proprietario_nome=payload.proprietario_nome,
            participantes_area=participantes_area,
            fallback=projeto.get("cliente_nome"),
        ),
        municipio=payload.municipio or projeto.get("municipio"),
        estado=payload.estado or projeto.get("estado"),
        comarca=payload.comarca or projeto.get("comarca"),
        matricula=payload.matricula or projeto.get("matricula"),
        ccir=payload.ccir,
        car=payload.car,
        observacoes=payload.observacoes,
        codigo_lote=payload.codigo_lote,
        quadra=payload.quadra,
        setor=payload.setor,
        status_operacional=payload.status_operacional,
        status_documental=payload.status_documental,
        origem_tipo=payload.origem_tipo,
        geometria_esboco=[item.model_dump() for item in payload.geometria_esboco],
        geometria_final=[item.model_dump() for item in payload.geometria_final],
        participantes_area=participantes_area,
    )
    return area


@router.patch("/{projeto_id}/areas/{area_id}", summary="Atualizar area do projeto")
def atualizar_area(projeto_id: str, area_id: str, payload: AreaProjetoUpdate):
    sb = _get_supabase()
    projeto = _projeto_ou_404(sb, projeto_id)
    cliente_principal = _cliente_primario(sb, projeto.get("cliente_id"))
    participantes = listar_participantes_projeto(sb, projeto_id, cliente_principal=cliente_principal)
    areas = sintetizar_areas_do_projeto(
        projeto=projeto,
        cliente=cliente_principal,
        perimetro_ativo=_perimetro_ativo(sb, projeto_id),
        geometria_referencia=obter_geometria_referencia(sb, projeto.get("cliente_id")) if projeto.get("cliente_id") else None,
        sb=sb,
        participantes_projeto=participantes,
    )
    area_atual = next((item for item in areas if item.get("id") == area_id), None)
    if not area_atual or str(area_id).endswith("-ref") or str(area_id).endswith("-tec"):
        raise HTTPException(status_code=404, detail={"erro": "Area editavel nao encontrada", "codigo": 404})

    dados = payload.model_dump(exclude_none=True)
    participantes_area = _participantes_area_payload(payload.participantes_area) if payload.participantes_area is not None else (area_atual.get("participantes_area") or [])
    return salvar_area_projeto(
        projeto_id=projeto_id,
        cliente_id=_cliente_area_payload(
            cliente_id=dados.get("cliente_id"),
            participantes_area=participantes_area,
            fallback=area_atual.get("cliente_id") or projeto.get("cliente_id"),
        ),
        nome=dados.get("nome") or area_atual.get("nome") or "Area sem nome",
        proprietario_nome=_proprietario_area_payload(
            proprietario_nome=dados.get("proprietario_nome") or area_atual.get("proprietario_nome"),
            participantes_area=participantes_area,
            fallback=area_atual.get("proprietario_nome") or projeto.get("cliente_nome"),
        ),
        municipio=dados.get("municipio") or area_atual.get("municipio"),
        estado=dados.get("estado") or area_atual.get("estado"),
        comarca=dados.get("comarca") or area_atual.get("comarca"),
        matricula=dados.get("matricula") or area_atual.get("matricula"),
        ccir=dados.get("ccir") or area_atual.get("ccir"),
        car=dados.get("car") or area_atual.get("car"),
        observacoes=dados.get("observacoes") or area_atual.get("observacoes"),
        codigo_lote=dados.get("codigo_lote") if "codigo_lote" in dados else area_atual.get("codigo_lote"),
        quadra=dados.get("quadra") if "quadra" in dados else area_atual.get("quadra"),
        setor=dados.get("setor") if "setor" in dados else area_atual.get("setor"),
        status_operacional=dados.get("status_operacional") if "status_operacional" in dados else area_atual.get("status_operacional"),
        status_documental=dados.get("status_documental") if "status_documental" in dados else area_atual.get("status_documental"),
        origem_tipo=dados.get("origem_tipo") or area_atual.get("origem_tipo") or "manual",
        geometria_esboco=[item.model_dump() for item in (payload.geometria_esboco or [])] if payload.geometria_esboco is not None else area_atual.get("geometria_esboco"),
        geometria_final=[item.model_dump() for item in (payload.geometria_final or [])] if payload.geometria_final is not None else area_atual.get("geometria_final"),
        anexos=area_atual.get("anexos") or [],
        participantes_area=participantes_area,
        area_id=area_id,
    )


@router.get("/{projeto_id}/confrontacoes", summary="Detectar confrontacoes entre areas do projeto")
def listar_confrontacoes(projeto_id: str):
    sb = _get_supabase()
    projeto = _enriquecer_projeto(sb, projeto_id)
    return {
        "total": len(projeto["confrontacoes"]),
        "confrontacoes": projeto["confrontacoes"],
        "areas_total": len(projeto["areas"]),
        "resumo": projeto.get("confrontacoes_resumo") or {},
    }


@router.post("/{projeto_id}/confrontacoes/revisar", summary="Revisar confrontacoes detectadas")
def revisar_confrontacoes(projeto_id: str, payload: RevisoesConfrontacaoRequest):
    sb = _get_supabase()
    _projeto_ou_404(sb, projeto_id)
    if not payload.revisoes:
        raise HTTPException(status_code=422, detail={"erro": "Nenhuma revisao informada", "codigo": 422})
    revisoes = salvar_revisoes_confrontacao(
        sb,
        projeto_id,
        [item.model_dump(exclude_none=True) for item in payload.revisoes],
    )
    projeto = _enriquecer_projeto(sb, projeto_id)
    return {
        "revisoes": revisoes,
        "confrontacoes": projeto.get("confrontacoes") or [],
        "resumo": projeto.get("confrontacoes_resumo") or {},
    }


@router.get("/{projeto_id}/metricas-piloto", summary="Métricas do piloto condominial")
def metricas_piloto(projeto_id: str):
    """
    Retorna KPIs do piloto condominial para monitoramento em tempo real:
    - lotes_cadastrados: total de áreas/lotes no projeto
    - lotes_com_participante: lotes com ao menos um participante vinculado
    - magic_links_enviados: total de eventos de envio de magic link
    - formularios_preenchidos: lotes cujo participante preencheu o formulário
    - lotes_com_croqui: lotes com geometria de esboço ou final recebida
    - lotes_com_confrontantes_ok: lotes com status documental >= confrontantes_ok
    - lotes_prontos: lotes com status operacional e documental finais
    - por_status_operacional: contagem por status operacional
    - por_status_documental: contagem por status documental
    """
    sb = _get_supabase()

    # Áreas do projeto
    res_areas = (
        sb.table("areas_projeto")
        .select(
            "id, status_operacional, status_documental, "
            "origem_tipo, resumo_esboco, resumo_final"
        )
        .eq("projeto_id", projeto_id)
        .is_("deleted_at", "null")
        .execute()
    )
    areas = getattr(res_areas, "data", None) or []

    # Participantes por área (area_clientes)
    area_ids = [a["id"] for a in areas]
    participantes_por_area: dict[str, int] = {}
    if area_ids:
        res_ac = (
            sb.table("area_clientes")
            .select("area_id")
            .in_("area_id", area_ids)
            .is_("deleted_at", "null")
            .execute()
        )
        for row in (getattr(res_ac, "data", None) or []):
            aid = row["area_id"]
            participantes_por_area[aid] = participantes_por_area.get(aid, 0) + 1

    # Formulários preenchidos: busca clientes vinculados ao projeto com formulario_ok
    res_pc = (
        sb.table("projeto_clientes")
        .select("cliente_id, area_id")
        .eq("projeto_id", projeto_id)
        .is_("deleted_at", "null")
        .execute()
    )
    vinculos = getattr(res_pc, "data", None) or []
    cliente_ids = list({v["cliente_id"] for v in vinculos if v.get("cliente_id")})
    formularios_ok_ids: set[str] = set()
    if cliente_ids:
        res_cli = (
            sb.table("clientes")
            .select("id, formulario_ok")
            .in_("id", cliente_ids)
            .eq("formulario_ok", True)
            .execute()
        )
        formularios_ok_ids = {r["id"] for r in (getattr(res_cli, "data", None) or [])}

    # Áreas com formulário preenchido
    areas_com_formulario: set[str] = set()
    for v in vinculos:
        if v.get("cliente_id") in formularios_ok_ids and v.get("area_id"):
            areas_com_formulario.add(v["area_id"])

    # Eventos de magic link enviados
    res_ev = (
        sb.table("eventos_magic_link")
        .select("id", count="exact")
        .eq("projeto_id", projeto_id)
        .in_("tipo_evento", ["gerado", "reenviado"])
        .is_("deleted_at", "null")
        .execute()
    )
    magic_links_enviados = getattr(res_ev, "count", None) or len(getattr(res_ev, "data", None) or [])

    # Contabilizar KPIs por área
    STATUS_DOCUMENTAL_COM_CONFRONTANTES = {"confrontantes_ok", "documentacao_ok", "peca_pronta"}
    STATUS_OPERACIONAL_COM_CROQUI = {"croqui_recebido", "geometria_final", "peca_pronta"}

    lotes_com_participante = 0
    lotes_com_croqui = 0
    lotes_com_confrontantes_ok = 0
    lotes_prontos = 0
    por_status_operacional: dict[str, int] = {}
    por_status_documental: dict[str, int] = {}

    for area in areas:
        aid = area["id"]
        so = area.get("status_operacional") or "aguardando_cliente"
        sd = area.get("status_documental") or "pendente"
        por_status_operacional[so] = por_status_operacional.get(so, 0) + 1
        por_status_documental[sd] = por_status_documental.get(sd, 0) + 1

        if participantes_por_area.get(aid, 0) > 0:
            lotes_com_participante += 1
        if so in STATUS_OPERACIONAL_COM_CROQUI:
            lotes_com_croqui += 1
        if sd in STATUS_DOCUMENTAL_COM_CONFRONTANTES:
            lotes_com_confrontantes_ok += 1
        if so in {"geometria_final", "peca_pronta"} and sd in {"documentacao_ok", "peca_pronta"}:
            lotes_prontos += 1

    return {
        "projeto_id": projeto_id,
        "calculado_em": datetime.now(timezone.utc).isoformat(),
        "lotes_cadastrados": len(areas),
        "lotes_com_participante": lotes_com_participante,
        "magic_links_enviados": magic_links_enviados,
        "formularios_preenchidos": len(areas_com_formulario),
        "lotes_com_croqui": lotes_com_croqui,
        "lotes_com_confrontantes_ok": lotes_com_confrontantes_ok,
        "lotes_prontos": lotes_prontos,
        "por_status_operacional": por_status_operacional,
        "por_status_documental": por_status_documental,
    }


@router.get("/{projeto_id}/confrontacoes/cartas", summary="Gerar cartas de confrontacao em ZIP")
def baixar_cartas_confrontacao(projeto_id: str, area_ids: list[str] | None = None, somente_confirmadas: bool = False):
    sb = _get_supabase()
    projeto = _enriquecer_projeto(sb, projeto_id)
    confrontacoes = _filtrar_confrontacoes_para_cartas(
        projeto["confrontacoes"],
        area_ids=area_ids,
        somente_confirmadas=somente_confirmadas,
    )
    zip_bytes = gerar_cartas_confrontacao_zip(
        projeto=projeto,
        areas=projeto["areas"],
        confrontacoes=confrontacoes,
    )
    nome = f"Cartas_Confrontacao_{(projeto.get('projeto_nome') or 'Projeto').replace(' ', '_')[:30]}.zip"
    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{nome}"'},
    )
