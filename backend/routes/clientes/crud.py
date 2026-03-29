"""
Operações CRUD para clientes.
"""

from typing import Any

from fastapi import HTTPException

from .utils import (
    cliente_ou_404,
    normalizar_cliente,
    query_segura,
)


def carregar_projetos(sb, cliente_ids: list[str]) -> list[dict[str, Any]]:
    """Carrega projetos relacionados aos clientes."""
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


def carregar_formularios(sb, cliente_ids: list[str]) -> list[dict[str, Any]]:
    """Carrega formulários dos clientes."""
    if not cliente_ids:
        return []

    return query_segura(
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


def carregar_documentos(sb, projeto_ids: list[str]) -> list[dict[str, Any]]:
    """Carrega documentos gerados para os projetos."""
    if not projeto_ids:
        return []

    return query_segura(
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


def carregar_confrontantes(sb, projeto_ids: list[str]) -> list[dict[str, Any]]:
    """Carrega confrontantes para os projetos."""
    if not projeto_ids:
        return []

    return query_segura(
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


def atualizar_cliente_db(sb, cliente_id: str, dados: dict[str, Any]) -> dict[str, Any]:
    """Atualiza dados do cliente no banco."""
    if not dados:
        raise HTTPException(status_code=400, detail={"erro": "Nenhum campo para atualizar", "codigo": 400})

    res = sb.table("clientes").update(dados).eq("id", cliente_id).execute()
    if not res.data:
        raise HTTPException(status_code=500, detail={"erro": "Falha ao atualizar cliente", "codigo": 500})

    return normalizar_cliente(res.data[0])


def criar_confrontante_db(sb, cliente_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Cria novo confrontante no banco."""
    cliente_ou_404(sb, cliente_id)

    projeto = (
        sb.table("projetos")
        .select("id, cliente_id")
        .eq("id", payload["projeto_id"])
        .maybe_single()
        .execute()
    )
    if not projeto.data or projeto.data.get("cliente_id") != cliente_id:
        raise HTTPException(status_code=404, detail={"erro": "Projeto nao pertence ao cliente", "codigo": 404})

    dados = payload.copy()
    dados["origem"] = dados.get("origem") or "fase2"
    res = sb.table("confrontantes").insert(dados).execute()
    if not res.data:
        raise HTTPException(status_code=500, detail={"erro": "Falha ao criar confrontante", "codigo": 500})
    return res.data[0]


def atualizar_confrontante_db(sb, cliente_id: str, confrontante_id: str, dados: dict[str, Any]) -> dict[str, Any]:
    """Atualiza confrontante no banco."""
    from .confrontantes import validar_confrontante_cliente

    if not dados:
        raise HTTPException(status_code=400, detail={"erro": "Nenhum campo para atualizar", "codigo": 400})

    confrontante, _ = validar_confrontante_cliente(sb, cliente_id, confrontante_id)

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


def remover_confrontante_db(sb, cliente_id: str, confrontante_id: str) -> dict[str, Any]:
    """Marca confrontante como deletado (soft delete)."""
    from datetime import datetime, timezone
    from .confrontantes import validar_confrontante_cliente

    confrontante, _ = validar_confrontante_cliente(sb, cliente_id, confrontante_id)
    now = datetime.now(timezone.utc).isoformat()
    sb.table("confrontantes").update({"deleted_at": now}).eq("id", confrontante["id"]).execute()
    return {"status": "ok", "id": confrontante["id"]}
