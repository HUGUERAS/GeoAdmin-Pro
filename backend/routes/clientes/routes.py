"""
Endpoints da API de Clientes e Documentação.
"""

from collections import defaultdict
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

from .crud import (
    atualizar_cliente_db,
    atualizar_confrontante_db,
    carregar_confrontantes,
    carregar_documentos,
    carregar_formularios,
    carregar_projetos,
    criar_confrontante_db,
    remover_confrontante_db,
)
from .resumos import (
    carregar_perimetros_ativos_por_projeto,
    comparativo_geometria,
    montar_alertas,
    montar_checklist_projeto,
    montar_resumos_clientes,
    montar_timeline,
    resolver_projeto_geometria,
)
from .utils import (
    cliente_ou_404,
    get_supabase,
    normalizar_cliente,
)


# === Pydantic Models ===

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


from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile, Depends
from middleware.auth import verificar_token

# === Router ===

router = APIRouter(prefix="/clientes", tags=["Clientes & Documentacao"], dependencies=[Depends(verificar_token)])


# === Endpoints: Listagem e Detalhe ===

@router.get("", summary="Listar clientes com resumo documental")
def listar_clientes(busca: str | None = Query(None), limite: int = 50, deslocamento: int = 0):
    """Lista clientes com resumo de documentação."""
    sb = get_supabase()
    clientes = sb.table("clientes").select("*").range(deslocamento, deslocamento + limite - 1).execute().data or []
    cliente_ids = [c["id"] for c in clientes if c.get("id")]
    projetos = carregar_projetos(sb, cliente_ids)
    projeto_ids = [p["id"] for p in projetos if p.get("id")]
    formularios = carregar_formularios(sb, cliente_ids)
    documentos = carregar_documentos(sb, projeto_ids)
    confrontantes = carregar_confrontantes(sb, projeto_ids)

    resumos = montar_resumos_clientes(clientes, projetos, formularios, documentos, confrontantes)

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
    """Retorna detalhes completos do cliente."""
    sb = get_supabase()
    cliente = normalizar_cliente(cliente_ou_404(sb, cliente_id))
    projetos = carregar_projetos(sb, [cliente_id])
    projeto_ids = [p["id"] for p in projetos if p.get("id")]
    formularios = carregar_formularios(sb, [cliente_id])
    documentos = carregar_documentos(sb, projeto_ids)
    confrontantes = carregar_confrontantes(sb, projeto_ids)
    perimetros_por_projeto = carregar_perimetros_ativos_por_projeto(projetos)

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
        checklist.append(montar_checklist_projeto(cliente, projeto_detalhe, perimetro_ativo))

    resumo = montar_resumos_clientes([cliente], projetos, formularios, documentos, confrontantes)[0]
    alertas = montar_alertas(cliente, projetos_detalhe, checklist)
    timeline = montar_timeline(cliente, projetos_detalhe, documentos, confrontantes)

    confrontantes_detalhe = []
    for confrontante in confrontantes:
        projeto = projetos_por_id.get(confrontante.get("projeto_id"), {})
        confrontantes_detalhe.append({
            **confrontante,
            "projeto_nome": projeto.get("projeto_nome"),
        })

    geometria_referencia = obter_geometria_referencia(sb, cliente_id)
    projeto_geometria = resolver_projeto_geometria(
        geometria_referencia.get("projeto_id") if geometria_referencia else None,
        projetos_detalhe,
    )
    geometria_referencia = comparativo_geometria(geometria_referencia, projeto_geometria, perimetros_por_projeto)

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


# === Endpoints: CRUD de Cliente ===

@router.patch("/{cliente_id}", summary="Atualizar cadastro do cliente")
def atualizar_cliente(cliente_id: str, payload: ClienteUpdate):
    """Atualiza dados do cliente."""
    sb = get_supabase()
    cliente_ou_404(sb, cliente_id)
    dados = payload.model_dump(exclude_none=True)
    return atualizar_cliente_db(sb, cliente_id, dados)


# === Endpoints: Confrontantes ===

@router.post("/{cliente_id}/confrontantes", summary="Criar confrontante do cliente")
def criar_confrontante(cliente_id: str, payload: ConfrontanteCreate):
    """Cria novo confrontante para o cliente."""
    sb = get_supabase()
    dados = payload.model_dump()
    return criar_confrontante_db(sb, cliente_id, dados)


@router.patch("/{cliente_id}/confrontantes/{confrontante_id}", summary="Atualizar confrontante")
def atualizar_confrontante(cliente_id: str, confrontante_id: str, payload: ConfrontanteUpdate):
    """Atualiza dados de um confrontante."""
    sb = get_supabase()
    dados = payload.model_dump(exclude_none=True)
    return atualizar_confrontante_db(sb, cliente_id, confrontante_id, dados)


@router.delete("/{cliente_id}/confrontantes/{confrontante_id}", summary="Remover confrontante")
def remover_confrontante(cliente_id: str, confrontante_id: str):
    """Remove confrontante (soft delete)."""
    sb = get_supabase()
    return remover_confrontante_db(sb, cliente_id, confrontante_id)


# === Endpoints: Geometria de Referência ===

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
    """Helper para salvar geometria de referência com comparativo."""
    cliente = normalizar_cliente(cliente_ou_404(sb, cliente_id))
    projetos = carregar_projetos(sb, [cliente_id])
    projeto_final = resolver_projeto_geometria(projeto_id, projetos)
    perimetros = carregar_perimetros_ativos_por_projeto(projetos)
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
    """Salva geometria de referência desenhada manualmente."""
    sb = get_supabase()
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
    """Importa geometria de referência a partir de texto."""
    sb = get_supabase()
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
    """Importa geometria de referência a partir de arquivo."""
    sb = get_supabase()
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
    """Remove geometria de referência do cliente."""
    sb = get_supabase()
    cliente_ou_404(sb, cliente_id)

    removido = remover_geometria_referencia(sb, cliente_id)
    if not removido:
        raise HTTPException(status_code=404, detail={"erro": "Nenhuma referencia encontrada para remover", "codigo": 404})

    return {"status": "ok", "cliente_id": cliente_id}
