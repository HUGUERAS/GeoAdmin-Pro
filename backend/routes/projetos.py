"""
GeoAdmin Pro — Rotas de Projetos

GET  /projetos                      -> lista projetos com visão de dashboard
POST /projetos                      -> cria novo projeto (com cliente opcional)
GET  /projetos/{id}                 -> projeto enriquecido com areas, confrontacoes e documentos
PATCH /projetos/{id}                -> atualiza metadados
GET  /projetos/{id}/areas           -> lista areas conhecidas do projeto
POST /projetos/{id}/areas           -> cria area do projeto
PATCH /projetos/{id}/areas/{area_id} -> atualiza area do projeto
GET  /projetos/{id}/confrontacoes   -> detecta confrontacoes entre areas
GET  /projetos/{id}/confrontacoes/cartas -> gera ZIP de cartas de confrontacao
"""

from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

from integracoes.areas_projeto import (
    detectar_confrontacoes,
    gerar_cartas_confrontacao_zip,
    salvar_area_projeto,
    sintetizar_areas_do_projeto,
)
from integracoes.referencia_cliente import obter_geometria_referencia
from routes.clientes.resumos import montar_checklist_projeto
from routes.clientes.utils import query_segura, status_documentacao

router = APIRouter(prefix="/projetos", tags=["Projetos"])

TIPOS_PROCESSO_VALIDOS = {"INCRA_SIGEF", "SEAPA", "AMBOS"}


def _validar_tipo_processo(tipo_processo: str | None) -> str | None:
    if tipo_processo is None:
        return None
    valor = tipo_processo.strip().upper()
    if valor not in TIPOS_PROCESSO_VALIDOS:
        raise HTTPException(status_code=422, detail={"erro": "tipo_processo invalido", "codigo": 422})
    return valor


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
    origem_tipo: str = "manual"
    geometria_esboco: list[VerticePayload] = []
    geometria_final: list[VerticePayload] = []


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
    origem_tipo: Optional[str] = None
    geometria_esboco: Optional[list[VerticePayload]] = None
    geometria_final: Optional[list[VerticePayload]] = None


def _get_supabase():
    from main import get_supabase
    return get_supabase()


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


def _enriquecer_projeto(sb, projeto_id: str) -> dict[str, Any]:
    projeto = _projeto_ou_404(sb, projeto_id)
    cliente = _cliente_primario(sb, projeto.get("cliente_id"))
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
    areas = sintetizar_areas_do_projeto(
        projeto=projeto,
        cliente=cliente,
        perimetro_ativo=perimetro_ativo,
        geometria_referencia=geometria_referencia,
    )
    confrontacoes = detectar_confrontacoes(areas)

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
    projeto["clientes"] = [cliente] if cliente else []
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
    projeto["resumo_geo"] = {
        "areas_total": len(areas),
        "confrontacoes_total": len(confrontacoes),
        "confrontantes_total": len(confrontantes),
        "esbocos_total": sum(1 for area in areas if area.get("tipo_geometria_ativa") == "esboco"),
        "geometrias_finais_total": sum(1 for area in areas if area.get("tipo_geometria_ativa") == "final"),
    }
    return projeto


@router.get("", summary="Listar todos os projetos")
def listar_projetos(limite: int = 50, deslocamento: int = 0):
    sb = _get_supabase()
    res = sb.table("vw_projetos_completo").select("*").order("criado_em", desc=True).range(deslocamento, deslocamento + limite - 1).execute()
    projetos = res.data or []
    return {"total": len(projetos), "projetos": projetos}


@router.post("", summary="Criar novo projeto", status_code=201)
def criar_projeto(payload: ProjetoCreate):
    sb = _get_supabase()
    cliente_id = _resolver_cliente_para_criacao(sb, payload)
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
    link_payload = None
    if payload.gerar_magic_link and cliente_id:
        from routes.documentos import gerar_magic_link

        try:
            link_payload = gerar_magic_link(projeto_id, supabase=sb)
        except Exception:
            link_payload = None

    projeto = _enriquecer_projeto(sb, projeto_id)
    if link_payload:
        projeto["magic_link"] = link_payload
    return projeto


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


@router.get("/{projeto_id}/areas", summary="Listar areas conhecidas do projeto")
def listar_areas(projeto_id: str):
    sb = _get_supabase()
    projeto = _projeto_ou_404(sb, projeto_id)
    cliente = _cliente_primario(sb, projeto.get("cliente_id"))
    perimetro_ativo = _perimetro_ativo(sb, projeto_id)
    geometria_referencia = obter_geometria_referencia(sb, projeto.get("cliente_id")) if projeto.get("cliente_id") else None
    areas = sintetizar_areas_do_projeto(
        projeto=projeto,
        cliente=cliente,
        perimetro_ativo=perimetro_ativo,
        geometria_referencia=geometria_referencia,
    )
    return {"total": len(areas), "areas": areas}


@router.post("/{projeto_id}/areas", summary="Criar area do projeto", status_code=201)
def criar_area(projeto_id: str, payload: AreaProjetoPayload):
    sb = _get_supabase()
    projeto = _projeto_ou_404(sb, projeto_id)
    area = salvar_area_projeto(
        projeto_id=projeto_id,
        cliente_id=payload.cliente_id or projeto.get("cliente_id"),
        nome=payload.nome,
        proprietario_nome=payload.proprietario_nome or projeto.get("cliente_nome"),
        municipio=payload.municipio or projeto.get("municipio"),
        estado=payload.estado or projeto.get("estado"),
        comarca=payload.comarca or projeto.get("comarca"),
        matricula=payload.matricula or projeto.get("matricula"),
        ccir=payload.ccir,
        car=payload.car,
        observacoes=payload.observacoes,
        origem_tipo=payload.origem_tipo,
        geometria_esboco=[item.model_dump() for item in payload.geometria_esboco],
        geometria_final=[item.model_dump() for item in payload.geometria_final],
    )
    return area


@router.patch("/{projeto_id}/areas/{area_id}", summary="Atualizar area do projeto")
def atualizar_area(projeto_id: str, area_id: str, payload: AreaProjetoUpdate):
    sb = _get_supabase()
    projeto = _projeto_ou_404(sb, projeto_id)
    areas = sintetizar_areas_do_projeto(
        projeto=projeto,
        cliente=_cliente_primario(sb, projeto.get("cliente_id")),
        perimetro_ativo=_perimetro_ativo(sb, projeto_id),
        geometria_referencia=obter_geometria_referencia(sb, projeto.get("cliente_id")) if projeto.get("cliente_id") else None,
    )
    area_atual = next((item for item in areas if item.get("id") == area_id), None)
    if not area_atual or str(area_id).endswith("-ref") or str(area_id).endswith("-tec"):
        raise HTTPException(status_code=404, detail={"erro": "Area editavel nao encontrada", "codigo": 404})

    if payload.tipo_processo is not None:
        payload.tipo_processo = _validar_tipo_processo(payload.tipo_processo)
    dados = payload.model_dump(exclude_none=True)
    return salvar_area_projeto(
        projeto_id=projeto_id,
        cliente_id=dados.get("cliente_id") or area_atual.get("cliente_id") or projeto.get("cliente_id"),
        nome=dados.get("nome") or area_atual.get("nome") or "Area sem nome",
        proprietario_nome=dados.get("proprietario_nome") or area_atual.get("proprietario_nome"),
        municipio=dados.get("municipio") or area_atual.get("municipio"),
        estado=dados.get("estado") or area_atual.get("estado"),
        comarca=dados.get("comarca") or area_atual.get("comarca"),
        matricula=dados.get("matricula") or area_atual.get("matricula"),
        ccir=dados.get("ccir") or area_atual.get("ccir"),
        car=dados.get("car") or area_atual.get("car"),
        observacoes=dados.get("observacoes") or area_atual.get("observacoes"),
        origem_tipo=dados.get("origem_tipo") or area_atual.get("origem_tipo") or "manual",
        geometria_esboco=[item.model_dump() for item in (payload.geometria_esboco or [])] if payload.geometria_esboco is not None else area_atual.get("geometria_esboco"),
        geometria_final=[item.model_dump() for item in (payload.geometria_final or [])] if payload.geometria_final is not None else area_atual.get("geometria_final"),
        anexos=area_atual.get("anexos") or [],
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
    }


@router.get("/{projeto_id}/confrontacoes/cartas", summary="Gerar cartas de confrontacao em ZIP")
def baixar_cartas_confrontacao(projeto_id: str):
    sb = _get_supabase()
    projeto = _enriquecer_projeto(sb, projeto_id)
    zip_bytes = gerar_cartas_confrontacao_zip(
        projeto=projeto,
        areas=projeto["areas"],
        confrontacoes=projeto["confrontacoes"],
    )
    nome = f"Cartas_Confrontacao_{(projeto.get('projeto_nome') or 'Projeto').replace(' ', '_')[:30]}.zip"
    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{nome}"'},
    )
