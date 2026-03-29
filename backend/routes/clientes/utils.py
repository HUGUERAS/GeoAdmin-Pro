"""
Utilitários compartilhados para o módulo de clientes.
"""

from datetime import datetime
import logging
from typing import Any

from fastapi import HTTPException

logger = logging.getLogger("geoadmin.clientes")


def get_supabase():
    """Obtém instância do cliente Supabase."""
    from main import get_supabase
    return get_supabase()


def data_referencia(item: dict[str, Any]) -> str:
    """Extrai data de referência do item."""
    return item.get("criado_em") or item.get("created_at") or ""


def parse_iso(valor: str | None) -> datetime | None:
    """Faz parse de string ISO 8601 para datetime."""
    if not valor:
        return None
    try:
        return datetime.fromisoformat(valor.replace("Z", "+00:00"))
    except Exception as exc:
        logger.warning("Falha ao fazer parse ISO do valor '%s': %s", valor, exc)
        return None


def cliente_ou_404(sb, cliente_id: str) -> dict[str, Any]:
    """Busca cliente ou levanta HTTPException 404."""
    res = sb.table("clientes").select("*").eq("id", cliente_id).maybe_single().execute()
    if not res.data:
        raise HTTPException(status_code=404, detail={"erro": "Cliente nao encontrado", "codigo": 404})
    return res.data


def query_segura(fetcher, padrao):
    """Executa query com fallback seguro em caso de erro."""
    try:
        return fetcher()
    except Exception as exc:
        logger.warning("Falha em consulta auxiliar de clientes: %s", exc)
        return padrao


def normalizar_cliente(cliente: dict[str, Any]) -> dict[str, Any]:
    """Normaliza dados do cliente para formato consistente."""
    return {
        **cliente,
        "cpf": cliente.get("cpf") or cliente.get("cpf_cnpj"),
        "criado_em": data_referencia(cliente),
    }


def status_documentacao(projetos: list[dict[str, Any]], formulario_ok: bool, documentos_total: int) -> str:
    """Determina status de documentação do cliente."""
    if not projetos:
        return "sem_projetos"
    if not formulario_ok:
        return "pendente_formulario"
    if documentos_total == 0:
        return "pronto_para_documentar"
    return "documentacao_em_andamento"


def cadastro_basico_ok(cliente: dict[str, Any]) -> bool:
    """Verifica se cadastro básico do cliente está completo."""
    return bool((cliente.get("nome") or "").strip()) and bool(
        (cliente.get("cpf") or "").strip()
        or (cliente.get("telefone") or "").strip()
        or (cliente.get("email") or "").strip()
    )


def confrontante_do_cliente_ou_404(sb, cliente_id: str, confrontante_id: str) -> tuple[dict[str, Any], dict[str, Any]]:
    """Busca confrontante e valida que pertence ao cliente."""
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
