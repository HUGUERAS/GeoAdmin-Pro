"""
Utilitários compartilhados para exportação.
"""

import json
import logging
import re
import unicodedata
from typing import Any

logger = logging.getLogger("geoadmin.exportacao")


def nome_arquivo(projeto_nome: str, numero_job: str, extensao: str) -> str:
    """Gera nome de arquivo seguro para download."""
    job = numero_job or "sem-job"
    nome = (projeto_nome or "Projeto").replace(" ", "_").replace("/", "-")[:30]
    return f"GeoAdmin_{job}_{nome}.{extensao}" if extensao else f"GeoAdmin_{job}_{nome}."


def slug_seguro(texto: str) -> str:
    """Gera slug seguro a partir do texto."""
    bruto = valor_header_seguro(texto).lower().replace(" ", "-")
    slug = re.sub(r"[^a-z0-9_-]+", "-", bruto).strip("-")
    return slug or "projeto"


def valor_header_seguro(valor: str) -> str:
    """
    Normaliza valores de header para ASCII simples.

    O Starlette serializa headers em latin-1. Alguns avisos do pacote usam
    travessao unicode e acentos, o que pode derrubar a resposta ZIP inteira.
    """
    valor = valor.replace("—", "-").replace("–", "-")
    normalizado = unicodedata.normalize("NFKD", valor).encode("ascii", "ignore").decode("ascii")
    return " ".join(normalizado.split())


def serializar_json(payload: Any) -> bytes:
    """Serializa payload para bytes JSON."""
    return json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")


def query_segura(fetcher, padrao):
    """Executa query com fallback seguro em caso de erro."""
    try:
        return fetcher()
    except Exception as exc:
        logger.warning("Falha em consulta auxiliar do pacote Métrica: %s", exc)
        return padrao
