"""
GeoAdmin Pro - Serviços de Persistência e Auditoria de Jobs CAD

Oferece armazenamento unificado para o status dos jobs cartográficos assíncronos
enviados para a engine VERTEXROSEA, com contingência automática.
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from integracoes.arquivos_projeto import registrar_evento_cartografico

logger = logging.getLogger("geoadmin.jobs_cad")

def registrar_job_cad(
    sb,
    projeto_id: str,
    vertex_job_id: str,
    status: str = "pending",
    formatos: List[str] = None
) -> Dict[str, Any]:
    """
    Registra um novo Job CAD no banco de dados.
    
    1. Tenta gravar na tabela dedicada public.jobs_cad (Médio/Longo Prazo).
    2. Como contingência/auditoria (Curto Prazo), registra um evento_cartografico.
    """
    if formatos is None:
        formatos = ["dxf", "fcstd"]
        
    job_registro = {
        "projeto_id": projeto_id,
        "vertex_job_id": vertex_job_id,
        "status": status,
        "formato_saida": formatos,
    }
    
    sucesso_tabela = False
    resposta_data = {}
    
    # ─── 1. Gravar na tabela dedicada jobs_cad ─────────────────────
    try:
        res = sb.table("jobs_cad").insert(job_registro).execute()
        if res.data:
            resposta_data = res.data[0]
            sucesso_tabela = True
            logger.info("Job CAD %s persistido na tabela dedicada 'jobs_cad'.", vertex_job_id)
    except Exception as e:
        logger.warning(
            "Tabela dedicada 'jobs_cad' não disponível ou falhou (%s). Prosseguindo com fallback de auditoria...",
            e
        )
        
    # ─── 2. Gravar fallback em eventos_cartograficos ──────────────
    try:
        registrar_evento_cartografico(
            sb,
            projeto_id=projeto_id,
            arquivo_id=None,
            tipo_evento="promocao_base_oficial",
            origem="sistema",
            observacao=f"Job CAD registrado via VERTEXROSEA. Status: {status}",
            payload={
                "vertex_job_id": vertex_job_id,
                "status": status,
                "formatos": formatos,
                "jobs_cad_sucesso": sucesso_tabela
            }
        )
    except Exception as e:
        logger.error("Falha ao registrar auditoria de job em eventos_cartograficos: %s", e)
        
    return resposta_data if sucesso_tabela else job_registro


def atualizar_status_job_cad(
    sb,
    vertex_job_id: str,
    status: str,
    warnings: Optional[List[str]] = None
) -> bool:
    """
    Atualiza o status de processamento de um Job CAD.
    """
    atualizacao = {
        "status": status,
        "warnings": warnings or [],
        "atualizado_em": datetime.now(timezone.utc).isoformat()
    }
    
    # ─── 1. Atualizar tabela dedicada jobs_cad ─────────────────────
    try:
        res = sb.table("jobs_cad").update(atualizacao).eq("vertex_job_id", vertex_job_id).execute()
        if res.data:
            logger.info("Status do Job %s atualizado para %s na tabela jobs_cad.", vertex_job_id, status)
            return True
    except Exception as e:
        logger.warning("Falha ao atualizar status do Job %s na tabela jobs_cad: %s", vertex_job_id, e)
        
    return False
