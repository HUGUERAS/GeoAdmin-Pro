"""
Operações relacionadas a confrontantes (vizinhos).
"""

from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException

from .utils import confrontante_do_cliente_ou_404


def validar_confrontante_cliente(sb, cliente_id: str, confrontante_id: str) -> tuple[dict[str, Any], dict[str, Any]]:
    """Alias para compatibilidade com crud.py"""
    return confrontante_do_cliente_ou_404(sb, cliente_id, confrontante_id)


def excluir_confrontante(sb, cliente_id: str, confrontante_id: str) -> dict[str, Any]:
    """Remove confrontante (soft delete)."""
    confrontante, _ = confrontante_do_cliente_ou_404(sb, cliente_id, confrontante_id)
    now = datetime.now(timezone.utc).isoformat()
    sb.table("confrontantes").update({"deleted_at": now}).eq("id", confrontante["id"]).execute()
    return {"status": "ok", "id": confrontante["id"]}
