"""
Operações de geração de resumos e checklists para clientes.
"""

from collections import defaultdict
from datetime import timedelta
from typing import Any

from .utils import (
    cadastro_basico_ok,
    data_referencia,
    normalizar_cliente,
    parse_iso,
    query_segura,
    status_documentacao,
)


def carregar_perimetros_ativos_por_projeto(projetos: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Carrega perímetros ativos para cada projeto."""
    from routes.perimetros import buscar_perimetro_ativo

    resultado: dict[str, dict[str, Any]] = {}
    for projeto in projetos:
        projeto_id = projeto.get("id")
        if not projeto_id:
            continue
        perimetro = query_segura(lambda: buscar_perimetro_ativo(projeto_id), None)
        if perimetro:
            resultado[projeto_id] = perimetro
    return resultado


def montar_resumos_clientes(
    clientes: list[dict[str, Any]],
    projetos: list[dict[str, Any]],
    formularios: list[dict[str, Any]],
    documentos: list[dict[str, Any]],
    confrontantes: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Monta resumos para lista de clientes."""
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
        cliente = normalizar_cliente(cliente_bruto)
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
            "status_documentacao": status_documentacao(
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

    resumos.sort(key=data_referencia, reverse=True)
    return resumos


def montar_checklist_projeto(
    cliente: dict[str, Any],
    projeto: dict[str, Any],
    perimetro_ativo: dict[str, Any] | None,
) -> dict[str, Any]:
    """Monta checklist de tarefas para um projeto."""
    itens = [
        {
            "id": "cadastro_cliente",
            "label": "Cadastro basico do cliente",
            "ok": cadastro_basico_ok(cliente),
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


def montar_alertas(
    cliente: dict[str, Any],
    projetos: list[dict[str, Any]],
    checklist: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Monta alertas e avisos para o cliente."""
    alertas: list[dict[str, Any]] = []
    if not cadastro_basico_ok(cliente):
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


def montar_timeline(
    cliente: dict[str, Any],
    projetos: list[dict[str, Any]],
    documentos: list[dict[str, Any]],
    confrontantes: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Monta timeline de eventos do cliente."""
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
            expira = parse_iso(projeto.get("magic_link_expira"))
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


def resolver_projeto_geometria(projeto_id: str | None, projetos: list[dict[str, Any]]) -> str | None:
    """Resolve qual projeto usar para geometria de referência."""
    if projeto_id:
        return projeto_id
    if len(projetos) == 1:
        return projetos[0].get("id")
    return projetos[0].get("id") if projetos else None


def comparativo_geometria(
    geometria: dict[str, Any] | None,
    projeto_id: str | None,
    perimetros_por_projeto: dict[str, dict[str, Any]],
) -> dict[str, Any] | None:
    """Monta comparativo entre geometria de referência e perímetro técnico."""
    from integracoes.referencia_cliente import comparar_com_perimetro_referencia

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
