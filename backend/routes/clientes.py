"""
GeoAdmin Pro - Rotas de Clientes & Documentacao
"""

from collections import defaultdict
from datetime import datetime, timedelta, timezone
import logging
from typing import Any, Optional

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile
from pydantic import BaseModel

from integracoes.referencia_cliente import (
    comparar_com_perimetro_referencia,
    importar_vertices_por_formato,
    obter_geometria_referencia,
    remover_geometria_referencia,
    salvar_geometria_referencia,
)


router = APIRouter(prefix="/clientes", tags=["Clientes & Documentacao"])
logger = logging.getLogger("geoadmin.clientes")


class ClienteUpdate(BaseModel):
    nome: Optional[str] = None
    cpf: Optional[str] = None
    rg: Optional[str] = None
    estado_civil: Optional[str] = None
    profissao: Optional[str] = None
    telefone: Optional[str] = None
    email: Optional[str] = None
    endereco: Optional[str] = None
    endereco_numero: Optional[str] = None
    municipio: Optional[str] = None
    estado: Optional[str] = None
    setor: Optional[str] = None
    cep: Optional[str] = None
    conjuge_nome: Optional[str] = None
    conjuge_cpf: Optional[str] = None


class ConfrontanteCreate(BaseModel):
    projeto_id: str
    lado: str = "Outros"
    tipo: str = "particular"
    nome: str
    cpf: Optional[str] = None
    nome_imovel: Optional[str] = None
    matricula: Optional[str] = None
    origem: Optional[str] = None


class ConfrontanteUpdate(BaseModel):
    projeto_id: Optional[str] = None
    lado: Optional[str] = None
    tipo: Optional[str] = None
    nome: Optional[str] = None
    cpf: Optional[str] = None
    nome_imovel: Optional[str] = None
    matricula: Optional[str] = None
    origem: Optional[str] = None


class VerticePayload(BaseModel):
    lon: float
    lat: float


class GeometriaManualPayload(BaseModel):
    projeto_id: Optional[str] = None
    nome: Optional[str] = None
    vertices: list[VerticePayload]


class GeometriaTextoPayload(BaseModel):
    projeto_id: Optional[str] = None
    nome: Optional[str] = None
    formato: str
    conteudo: str


def _get_supabase():
    from main import get_supabase

    return get_supabase()


def _data_referencia(item: dict[str, Any]) -> str:
    return item.get("criado_em") or item.get("created_at") or ""


def _parse_iso(valor: str | None) -> datetime | None:
    if not valor:
        return None
    try:
        return datetime.fromisoformat(valor.replace("Z", "+00:00"))
    except Exception:
        return None


def _cliente_ou_404(sb, cliente_id: str) -> dict[str, Any]:
    res = sb.table("clientes").select("*").eq("id", cliente_id).maybe_single().execute()
    if not res.data:
        raise HTTPException(status_code=404, detail={"erro": "Cliente nao encontrado", "codigo": 404})
    return res.data


def _query_segura(fetcher, padrao):
    try:
        return fetcher()
    except Exception as exc:
        logger.warning("Falha em consulta auxiliar de clientes: %s", exc)
        return padrao


def _normalizar_cliente(cliente: dict[str, Any]) -> dict[str, Any]:
    return {
        **cliente,
        "cpf": cliente.get("cpf") or cliente.get("cpf_cnpj"),
        "criado_em": _data_referencia(cliente),
    }


def _status_documentacao(projetos: list[dict[str, Any]], formulario_ok: bool, documentos_total: int) -> str:
    if not projetos:
        return "sem_projetos"
    if not formulario_ok:
        return "pendente_formulario"
    if documentos_total == 0:
        return "pronto_para_documentar"
    return "documentacao_em_andamento"


def _carregar_projetos(sb, cliente_ids: list[str]) -> list[dict[str, Any]]:
    if not cliente_ids:
        return []

    return (
        sb.table("vw_projetos_completo")
        .select("id, cliente_id, projeto_nome, status, municipio, estado, area_ha, total_pontos, criado_em")
        .in_("cliente_id", cliente_ids)
        .order("criado_em", desc=True)
        .execute()
        .data
        or []
    )


def _carregar_formularios(sb, cliente_ids: list[str]) -> list[dict[str, Any]]:
    if not cliente_ids:
        return []

    return _query_segura(
        lambda: (
            sb.table("vw_formulario_cliente")
            .select("projeto_id, cliente_id, formulario_ok, formulario_em, magic_link_expira")
            .in_("cliente_id", cliente_ids)
            .execute()
            .data
            or []
        ),
        [],
    )


def _carregar_documentos(sb, projeto_ids: list[str]) -> list[dict[str, Any]]:
    if not projeto_ids:
        return []

    return _query_segura(
        lambda: (
            sb.table("documentos_gerados")
            .select("id, projeto_id, tipo, gerado_em")
            .in_("projeto_id", projeto_ids)
            .is_("deleted_at", "null")
            .order("gerado_em", desc=True)
            .execute()
            .data
            or []
        ),
        [],
    )


def _carregar_confrontantes(sb, projeto_ids: list[str]) -> list[dict[str, Any]]:
    if not projeto_ids:
        return []

    return _query_segura(
        lambda: (
            sb.table("confrontantes")
            .select("id, projeto_id, lado, tipo, nome, cpf, nome_imovel, matricula, origem, criado_em")
            .in_("projeto_id", projeto_ids)
            .is_("deleted_at", "null")
            .order("criado_em", desc=True)
            .execute()
            .data
            or []
        ),
        [],
    )


def _cadastro_basico_ok(cliente: dict[str, Any]) -> bool:
    return bool((cliente.get("nome") or "").strip()) and bool(
        (cliente.get("cpf") or "").strip()
        or (cliente.get("telefone") or "").strip()
        or (cliente.get("email") or "").strip()
    )


def _perimetros_ativos_por_projeto(projetos: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    from routes.perimetros import buscar_perimetro_ativo

    resultado: dict[str, dict[str, Any]] = {}
    for projeto in projetos:
        projeto_id = projeto.get("id")
        if not projeto_id:
            continue
        perimetro = _query_segura(lambda: buscar_perimetro_ativo(projeto_id), None)
        if perimetro:
            resultado[projeto_id] = perimetro
    return resultado


def _montar_resumos_clientes(
    clientes: list[dict[str, Any]],
    projetos: list[dict[str, Any]],
    formularios: list[dict[str, Any]],
    documentos: list[dict[str, Any]],
    confrontantes: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    projetos_por_cliente: dict[str, list[dict[str, Any]]] = defaultdict(list)
    formularios_por_projeto = {item["projeto_id"]: item for item in formularios if item.get("projeto_id")}
    documentos_por_projeto: dict[str, list[dict[str, Any]]] = defaultdict(list)
    confrontantes_por_projeto: dict[str, int] = defaultdict(int)

    for projeto in projetos:
        cliente_id = projeto.get("cliente_id")
        if cliente_id:
            projetos_por_cliente[cliente_id].append(projeto)

    for documento in documentos:
        projeto_id = documento.get("projeto_id")
        if projeto_id:
            documentos_por_projeto[projeto_id].append(documento)

    for confrontante in confrontantes:
        projeto_id = confrontante.get("projeto_id")
        if projeto_id:
            confrontantes_por_projeto[projeto_id] += 1

    resumos: list[dict[str, Any]] = []
    for cliente_bruto in clientes:
        cliente = _normalizar_cliente(cliente_bruto)
        projetos_cliente = projetos_por_cliente.get(cliente["id"], [])
        documentos_total = 0
        confrontantes_total = 0
        ultimo_documento_em = cliente.get("formulario_em")

        for projeto in projetos_cliente:
            docs = documentos_por_projeto.get(projeto["id"], [])
            documentos_total += len(docs)
            confrontantes_total += confrontantes_por_projeto.get(projeto["id"], 0)
            for doc in docs:
                data_doc = doc.get("gerado_em")
                if data_doc and (not ultimo_documento_em or data_doc > ultimo_documento_em):
                    ultimo_documento_em = data_doc

        resumo = {
            **cliente,
            "projetos_total": len(projetos_cliente),
            "documentos_total": documentos_total,
            "confrontantes_total": confrontantes_total,
            "ultimo_projeto_status": projetos_cliente[0].get("status") if projetos_cliente else None,
            "ultimo_documento_em": ultimo_documento_em,
            "status_documentacao": _status_documentacao(
                projetos_cliente,
                bool(cliente.get("formulario_ok")),
                documentos_total,
            ),
        }

        for projeto in projetos_cliente:
            form = formularios_por_projeto.get(projeto["id"])
            if not form:
                continue
            data_form = form.get("formulario_em")
            if data_form and (not resumo.get("formulario_em") or data_form > resumo["formulario_em"]):
                resumo["formulario_em"] = data_form
            if form.get("magic_link_expira") and not resumo.get("magic_link_expira"):
                resumo["magic_link_expira"] = form.get("magic_link_expira")

        resumos.append(resumo)

    resumos.sort(key=_data_referencia, reverse=True)
    return resumos


def _montar_checklist_projeto(
    cliente: dict[str, Any],
    projeto: dict[str, Any],
    perimetro_ativo: dict[str, Any] | None,
) -> dict[str, Any]:
    itens = [
        {
            "id": "cadastro_cliente",
            "label": "Cadastro basico do cliente",
            "ok": _cadastro_basico_ok(cliente),
            "descricao": "Nome e ao menos um contato ou CPF cadastrados.",
        },
        {
            "id": "magic_link",
            "label": "Magic link enviado",
            "ok": bool(projeto.get("magic_link_expira")),
            "descricao": "Link de formulario enviado ao cliente.",
        },
        {
            "id": "formulario",
            "label": "Formulario preenchido",
            "ok": bool(projeto.get("formulario_ok")),
            "descricao": "Cliente concluiu o formulario documental.",
        },
        {
            "id": "confrontantes",
            "label": "Confrontantes cadastrados",
            "ok": (projeto.get("confrontantes_total") or 0) > 0,
            "descricao": "Ao menos um vizinho ou confrontante registrado.",
        },
        {
            "id": "perimetro_tecnico",
            "label": "Perimetro tecnico validado",
            "ok": bool(perimetro_ativo and (perimetro_ativo.get("vertices") or [])),
            "descricao": "Perimetro tecnico ativo salvo para comparacao e documentos.",
        },
        {
            "id": "documentos",
            "label": "Documentos gerados",
            "ok": (projeto.get("documentos_total") or 0) > 0,
            "descricao": "Ja existe ao menos um documento gerado para o projeto.",
        },
    ]

    concluidos = sum(1 for item in itens if item["ok"])
    total = len(itens)
    pendencias = [item["label"] for item in itens if not item["ok"]]

    if concluidos == total:
        status = "ok"
    elif concluidos == 0:
        status = "pendente"
    else:
        status = "em_andamento"

    return {
        "projeto_id": projeto.get("id"),
        "projeto_nome": projeto.get("projeto_nome"),
        "status": status,
        "concluidos": concluidos,
        "total": total,
        "progresso_percentual": round((concluidos / total) * 100, 1) if total else 0,
        "pendencias": pendencias,
        "itens": itens,
    }


def _montar_alertas(
    cliente: dict[str, Any],
    projetos: list[dict[str, Any]],
    checklist: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    alertas: list[dict[str, Any]] = []
    if not _cadastro_basico_ok(cliente):
        alertas.append({
            "nivel": "alto",
            "tipo": "cadastro_cliente",
            "titulo": "Cadastro do cliente incompleto",
            "descricao": "Preencha nome e ao menos um contato ou CPF para destravar a documentacao.",
        })

    checklist_por_projeto = {item["projeto_id"]: item for item in checklist}
    for projeto in projetos:
        lista = checklist_por_projeto.get(projeto.get("id"))
        if not lista:
            continue
        faltando = {item["id"]: item for item in lista["itens"] if not item["ok"]}

        if "formulario" in faltando:
            alertas.append({
                "nivel": "alto",
                "tipo": "formulario",
                "projeto_id": projeto.get("id"),
                "projeto_nome": projeto.get("projeto_nome"),
                "titulo": "Formulario do cliente pendente",
                "descricao": f"O projeto {projeto.get('projeto_nome')} ainda aguarda preenchimento pelo magic link.",
            })
        if "confrontantes" in faltando:
            alertas.append({
                "nivel": "medio",
                "tipo": "confrontantes",
                "projeto_id": projeto.get("id"),
                "projeto_nome": projeto.get("projeto_nome"),
                "titulo": "Confrontantes ainda nao cadastrados",
                "descricao": f"O projeto {projeto.get('projeto_nome')} precisa dos vizinhos para a parte declaratoria.",
            })
        if "perimetro_tecnico" in faltando:
            alertas.append({
                "nivel": "medio",
                "tipo": "perimetro",
                "projeto_id": projeto.get("id"),
                "projeto_nome": projeto.get("projeto_nome"),
                "titulo": "Perimetro tecnico nao encontrado",
                "descricao": f"Salve o perimetro tecnico ativo de {projeto.get('projeto_nome')} para comparar com a referencia do cliente.",
            })
        if "documentos" in faltando and projeto.get("formulario_ok"):
            alertas.append({
                "nivel": "baixo",
                "tipo": "documentos",
                "projeto_id": projeto.get("id"),
                "projeto_nome": projeto.get("projeto_nome"),
                "titulo": "Projeto pronto para gerar documentos",
                "descricao": f"{projeto.get('projeto_nome')} ja tem formulario e pode seguir para a geracao documental.",
            })

    ordem = {"alto": 0, "medio": 1, "baixo": 2}
    alertas.sort(key=lambda item: ordem.get(item["nivel"], 99))
    return alertas


def _montar_timeline(
    cliente: dict[str, Any],
    projetos: list[dict[str, Any]],
    documentos: list[dict[str, Any]],
    confrontantes: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    projetos_por_id = {projeto["id"]: projeto for projeto in projetos if projeto.get("id")}
    eventos: list[dict[str, Any]] = []

    if cliente.get("criado_em"):
        eventos.append({
            "tipo": "cliente_criado",
            "titulo": "Cliente entrou na base",
            "descricao": f"Cadastro iniciado para {cliente.get('nome') or 'cliente sem nome'}.",
            "em": cliente.get("criado_em"),
        })

    for projeto in projetos:
        if projeto.get("criado_em"):
            eventos.append({
                "tipo": "projeto_criado",
                "projeto_id": projeto.get("id"),
                "titulo": "Projeto vinculado ao cliente",
                "descricao": projeto.get("projeto_nome"),
                "em": projeto.get("criado_em"),
            })

        if projeto.get("magic_link_expira"):
            expira = _parse_iso(projeto.get("magic_link_expira"))
            enviado_em = (expira - timedelta(days=7)).isoformat() if expira else projeto.get("magic_link_expira")
            eventos.append({
                "tipo": "magic_link",
                "projeto_id": projeto.get("id"),
                "titulo": "Magic link enviado",
                "descricao": f"Formulario liberado para {projeto.get('projeto_nome')}.",
                "em": enviado_em,
            })

        if projeto.get("formulario_em"):
            eventos.append({
                "tipo": "formulario",
                "projeto_id": projeto.get("id"),
                "titulo": "Formulario recebido",
                "descricao": f"Cliente concluiu o formulario do projeto {projeto.get('projeto_nome')}.",
                "em": projeto.get("formulario_em"),
            })

    for confrontante in confrontantes:
        projeto = projetos_por_id.get(confrontante.get("projeto_id"))
        eventos.append({
            "tipo": "confrontante",
            "projeto_id": confrontante.get("projeto_id"),
            "titulo": "Confrontante registrado",
            "descricao": f"{confrontante.get('nome')} em {projeto.get('projeto_nome') if projeto else 'projeto sem nome'}.",
            "em": confrontante.get("criado_em"),
        })

    for documento in documentos:
        projeto = projetos_por_id.get(documento.get("projeto_id"))
        eventos.append({
            "tipo": "documento",
            "projeto_id": documento.get("projeto_id"),
            "titulo": "Documento gerado",
            "descricao": f"{documento.get('tipo')} em {projeto.get('projeto_nome') if projeto else 'projeto sem nome'}.",
            "em": documento.get("gerado_em"),
        })

    eventos = [item for item in eventos if item.get("em")]
    eventos.sort(key=lambda item: item.get("em") or "", reverse=True)
    return eventos


def _resolver_projeto_geometria(projeto_id: str | None, projetos: list[dict[str, Any]]) -> str | None:
    if projeto_id:
        return projeto_id
    if len(projetos) == 1:
        return projetos[0].get("id")
    return projetos[0].get("id") if projetos else None


def _comparativo_geometria(
    geometria: dict[str, Any] | None,
    projeto_id: str | None,
    perimetros_por_projeto: dict[str, dict[str, Any]],
) -> dict[str, Any] | None:
    if not geometria or not projeto_id:
        return geometria

    perimetro = perimetros_por_projeto.get(projeto_id)
    if not perimetro:
        return geometria

    comparativo = comparar_com_perimetro_referencia(
        geometria.get("vertices") or [],
        perimetro.get("vertices") or [],
        perimetro.get("tipo"),
    )
    return {**geometria, "comparativo": comparativo, "projeto_id": projeto_id}


def _confrontante_do_cliente_ou_404(sb, cliente_id: str, confrontante_id: str) -> tuple[dict[str, Any], dict[str, Any]]:
    confronto = (
        sb.table("confrontantes")
        .select("id, projeto_id, lado, tipo, nome, cpf, nome_imovel, matricula, origem, criado_em, deleted_at")
        .eq("id", confrontante_id)
        .maybe_single()
        .execute()
    )
    if not confronto.data or confronto.data.get("deleted_at"):
        raise HTTPException(status_code=404, detail={"erro": "Confrontante nao encontrado", "codigo": 404})

    projeto = (
        sb.table("projetos")
        .select("id, cliente_id, nome")
        .eq("id", confronto.data["projeto_id"])
        .maybe_single()
        .execute()
    )
    if not projeto.data or projeto.data.get("cliente_id") != cliente_id:
        raise HTTPException(status_code=404, detail={"erro": "Confrontante nao pertence ao cliente informado", "codigo": 404})

    return confronto.data, projeto.data


@router.get("", summary="Listar clientes com resumo documental")
def listar_clientes(busca: str | None = Query(None)):
    sb = _get_supabase()
    clientes = sb.table("clientes").select("*").execute().data or []
    cliente_ids = [c["id"] for c in clientes if c.get("id")]
    projetos = _carregar_projetos(sb, cliente_ids)
    projeto_ids = [p["id"] for p in projetos if p.get("id")]
    formularios = _carregar_formularios(sb, cliente_ids)
    documentos = _carregar_documentos(sb, projeto_ids)
    confrontantes = _carregar_confrontantes(sb, projeto_ids)

    resumos = _montar_resumos_clientes(clientes, projetos, formularios, documentos, confrontantes)

    if busca:
        termo = busca.strip().lower()
        resumos = [
            item for item in resumos
            if termo in (item.get("nome") or "").lower()
            or termo in (item.get("telefone") or "").lower()
            or termo in (item.get("email") or "").lower()
            or termo in (item.get("cpf") or "").lower()
        ]

    return {"total": len(resumos), "clientes": resumos}


@router.get("/{cliente_id}", summary="Detalhar cliente com projetos, checklist e timeline")
def detalhar_cliente(cliente_id: str):
    sb = _get_supabase()
    cliente = _normalizar_cliente(_cliente_ou_404(sb, cliente_id))
    projetos = _carregar_projetos(sb, [cliente_id])
    projeto_ids = [p["id"] for p in projetos if p.get("id")]
    formularios = _carregar_formularios(sb, [cliente_id])
    documentos = _carregar_documentos(sb, projeto_ids)
    confrontantes = _carregar_confrontantes(sb, projeto_ids)
    perimetros_por_projeto = _perimetros_ativos_por_projeto(projetos)

    formularios_por_projeto = {item["projeto_id"]: item for item in formularios if item.get("projeto_id")}
    documentos_por_projeto: dict[str, list[dict[str, Any]]] = defaultdict(list)
    confrontantes_por_projeto: dict[str, list[dict[str, Any]]] = defaultdict(list)
    projetos_por_id = {projeto["id"]: projeto for projeto in projetos if projeto.get("id")}

    for documento in documentos:
        projeto_id = documento.get("projeto_id")
        if projeto_id:
            documentos_por_projeto[projeto_id].append(documento)

    for confrontante in confrontantes:
        projeto_id = confrontante.get("projeto_id")
        if projeto_id:
            confrontantes_por_projeto[projeto_id].append(confrontante)

    projetos_detalhe: list[dict[str, Any]] = []
    checklist: list[dict[str, Any]] = []

    for projeto in projetos:
        docs = documentos_por_projeto.get(projeto["id"], [])
        form = formularios_por_projeto.get(projeto["id"], {})
        perimetro_ativo = perimetros_por_projeto.get(projeto["id"])

        projeto_detalhe = {
            **projeto,
            "documentos_total": len(docs),
            "documentos_tipos": sorted({doc.get("tipo") for doc in docs if doc.get("tipo")}),
            "ultimo_documento_em": max((doc.get("gerado_em") or "" for doc in docs), default=None),
            "confrontantes_total": len(confrontantes_por_projeto.get(projeto["id"], [])),
            "formulario_ok": bool(form.get("formulario_ok") if form else cliente.get("formulario_ok")),
            "formulario_em": form.get("formulario_em") or cliente.get("formulario_em"),
            "magic_link_expira": form.get("magic_link_expira") or cliente.get("magic_link_expira"),
            "perimetro_tecnico_ok": bool(perimetro_ativo and (perimetro_ativo.get("vertices") or [])),
            "perimetro_tecnico_tipo": perimetro_ativo.get("tipo") if perimetro_ativo else None,
        }
        projetos_detalhe.append(projeto_detalhe)
        checklist.append(_montar_checklist_projeto(cliente, projeto_detalhe, perimetro_ativo))

    resumo = _montar_resumos_clientes([cliente], projetos, formularios, documentos, confrontantes)[0]
    alertas = _montar_alertas(cliente, projetos_detalhe, checklist)
    timeline = _montar_timeline(cliente, projetos_detalhe, documentos, confrontantes)

    confrontantes_detalhe = []
    for confrontante in confrontantes:
        projeto = projetos_por_id.get(confrontante.get("projeto_id"), {})
        confrontantes_detalhe.append({
            **confrontante,
            "projeto_nome": projeto.get("projeto_nome"),
        })

    geometria_referencia = obter_geometria_referencia(sb, cliente_id)
    projeto_geometria = _resolver_projeto_geometria(
        geometria_referencia.get("projeto_id") if geometria_referencia else None,
        projetos_detalhe,
    )
    geometria_referencia = _comparativo_geometria(geometria_referencia, projeto_geometria, perimetros_por_projeto)

    return {
        "cliente": cliente,
        "projetos": projetos_detalhe,
        "resumo": resumo,
        "confrontantes": confrontantes_detalhe,
        "checklist": checklist,
        "alertas": alertas,
        "timeline": timeline,
        "geometria_referencia": geometria_referencia,
    }


@router.patch("/{cliente_id}", summary="Atualizar cadastro do cliente")
def atualizar_cliente(cliente_id: str, payload: ClienteUpdate):
    sb = _get_supabase()
    _cliente_ou_404(sb, cliente_id)

    dados = payload.model_dump(exclude_none=True)
    if not dados:
        raise HTTPException(status_code=400, detail={"erro": "Nenhum campo para atualizar", "codigo": 400})

    res = sb.table("clientes").update(dados).eq("id", cliente_id).execute()
    if not res.data:
        raise HTTPException(status_code=500, detail={"erro": "Falha ao atualizar cliente", "codigo": 500})

    return _normalizar_cliente(res.data[0])


@router.post("/{cliente_id}/confrontantes", summary="Criar confrontante do cliente")
def criar_confrontante(cliente_id: str, payload: ConfrontanteCreate):
    sb = _get_supabase()
    _cliente_ou_404(sb, cliente_id)

    projeto = (
        sb.table("projetos")
        .select("id, cliente_id")
        .eq("id", payload.projeto_id)
        .maybe_single()
        .execute()
    )
    if not projeto.data or projeto.data.get("cliente_id") != cliente_id:
        raise HTTPException(status_code=404, detail={"erro": "Projeto nao pertence ao cliente", "codigo": 404})

    dados = payload.model_dump()
    dados["origem"] = dados.get("origem") or "fase2"
    res = sb.table("confrontantes").insert(dados).execute()
    if not res.data:
        raise HTTPException(status_code=500, detail={"erro": "Falha ao criar confrontante", "codigo": 500})
    return res.data[0]


@router.patch("/{cliente_id}/confrontantes/{confrontante_id}", summary="Atualizar confrontante")
def atualizar_confrontante(cliente_id: str, confrontante_id: str, payload: ConfrontanteUpdate):
    sb = _get_supabase()
    confrontante, _ = _confrontante_do_cliente_ou_404(sb, cliente_id, confrontante_id)

    dados = payload.model_dump(exclude_none=True)
    if not dados:
        raise HTTPException(status_code=400, detail={"erro": "Nenhum campo para atualizar", "codigo": 400})

    projeto_id = dados.get("projeto_id")
    if projeto_id:
        projeto = (
            sb.table("projetos")
            .select("id, cliente_id")
            .eq("id", projeto_id)
            .maybe_single()
            .execute()
        )
        if not projeto.data or projeto.data.get("cliente_id") != cliente_id:
            raise HTTPException(status_code=404, detail={"erro": "Projeto nao pertence ao cliente", "codigo": 404})

    res = sb.table("confrontantes").update(dados).eq("id", confrontante["id"]).execute()
    if not res.data:
        raise HTTPException(status_code=500, detail={"erro": "Falha ao atualizar confrontante", "codigo": 500})
    return res.data[0]


@router.delete("/{cliente_id}/confrontantes/{confrontante_id}", summary="Remover confrontante")
def remover_confrontante(cliente_id: str, confrontante_id: str):
    sb = _get_supabase()
    confrontante, _ = _confrontante_do_cliente_ou_404(sb, cliente_id, confrontante_id)
    now = datetime.now(timezone.utc).isoformat()
    sb.table("confrontantes").update({"deleted_at": now}).eq("id", confrontante["id"]).execute()
    return {"status": "ok", "id": confrontante["id"]}


def _salvar_referencia(
    sb,
    cliente_id: str,
    projeto_id: str | None,
    nome: str | None,
    origem_tipo: str,
    formato: str,
    arquivo_nome: str | None,
    vertices: list[dict[str, Any]],
) -> dict[str, Any]:
    cliente = _normalizar_cliente(_cliente_ou_404(sb, cliente_id))
    projetos = _carregar_projetos(sb, [cliente_id])
    projeto_final = _resolver_projeto_geometria(projeto_id, projetos)
    perimetros = _perimetros_ativos_por_projeto(projetos)
    comparativo = None
    if projeto_final and perimetros.get(projeto_final):
        comparativo = comparar_com_perimetro_referencia(
            vertices,
            perimetros[projeto_final].get("vertices") or [],
            perimetros[projeto_final].get("tipo"),
        )

    return salvar_geometria_referencia(
        sb=sb,
        cliente_id=cliente["id"],
        projeto_id=projeto_final,
        nome=nome,
        origem_tipo=origem_tipo,
        formato=formato,
        arquivo_nome=arquivo_nome,
        vertices=vertices,
        comparativo=comparativo,
    )


@router.post("/{cliente_id}/geometria-referencia/manual", summary="Salvar referencia desenhada manualmente")
def salvar_geometria_manual(cliente_id: str, payload: GeometriaManualPayload):
    sb = _get_supabase()
    vertices = [item.model_dump() for item in payload.vertices]
    if len(vertices) < 3:
        raise HTTPException(status_code=422, detail={"erro": "A referencia precisa de ao menos 3 vertices.", "codigo": 422})
    return _salvar_referencia(
        sb=sb,
        cliente_id=cliente_id,
        projeto_id=payload.projeto_id,
        nome=payload.nome or "Croqui manual",
        origem_tipo="manual",
        formato="manual",
        arquivo_nome=None,
        vertices=vertices,
    )


@router.post("/{cliente_id}/geometria-referencia/importar-texto", summary="Importar referencia do cliente via texto")
def importar_geometria_texto(cliente_id: str, payload: GeometriaTextoPayload):
    sb = _get_supabase()
    try:
        vertices = importar_vertices_por_formato(payload.formato, payload.conteudo)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail={"erro": str(exc), "codigo": 422})

    return _salvar_referencia(
        sb=sb,
        cliente_id=cliente_id,
        projeto_id=payload.projeto_id,
        nome=payload.nome or f"Importacao {payload.formato.upper()}",
        origem_tipo="importacao_texto",
        formato=payload.formato,
        arquivo_nome=None,
        vertices=vertices,
    )


@router.post("/{cliente_id}/geometria-referencia/importar", summary="Importar referencia do cliente por arquivo")
async def importar_geometria_arquivo(
    cliente_id: str,
    arquivo: UploadFile = File(...),
    projeto_id: str | None = Form(None),
    nome: str | None = Form(None),
    formato: str | None = Form(None),
):
    sb = _get_supabase()
    arquivo_nome = arquivo.filename or "referencia"
    formato_final = (formato or arquivo_nome.split(".")[-1]).lower()
    if formato_final == "json":
        formato_final = "geojson"

    conteudo = await arquivo.read()
    try:
        payload = conteudo if formato_final in {"zip", "shpzip"} else conteudo.decode("utf-8", errors="replace")
        vertices = importar_vertices_por_formato(formato_final, payload)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail={"erro": str(exc), "codigo": 422})

    return _salvar_referencia(
        sb=sb,
        cliente_id=cliente_id,
        projeto_id=projeto_id,
        nome=nome or arquivo_nome,
        origem_tipo="arquivo",
        formato=formato_final,
        arquivo_nome=arquivo_nome,
        vertices=vertices,
    )


@router.delete("/{cliente_id}/geometria-referencia", summary="Remover referencia de geometria do cliente")
def excluir_geometria_referencia(cliente_id: str):
    sb = _get_supabase()
    _cliente_ou_404(sb, cliente_id)

    removido = remover_geometria_referencia(sb, cliente_id)
    if not removido:
        raise HTTPException(status_code=404, detail={"erro": "Nenhuma referencia encontrada para remover", "codigo": 404})

    return {"status": "ok", "cliente_id": cliente_id}
