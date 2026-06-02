"""
GeoAdmin Pro - Serviços de Persistência e Auditoria de Jobs CAD

Oferece armazenamento unificado para o status dos jobs cartográficos assíncronos
enviados para a engine VERTEXROSEA, com contingência automática e controle rígido de auditoria.
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from integracoes.arquivos_projeto import registrar_evento_cartografico

logger = logging.getLogger("geoadmin.jobs_cad")

def registrar_job_cad(
    sb,
    projeto_id: str,
    arquivo_id_origem: Optional[str],
    vertex_job_id: str,
    tipo_job: str,
    payload_json: Dict[str, Any],
    status: str = "pending"
) -> Dict[str, Any]:
    """
    Registra um novo Job CAD no banco de dados.
    
    1. Tenta gravar na tabela dedicada public.jobs_cad (Médio/Longo Prazo).
    2. Como contingência/auditoria (Curto Prazo), registra um evento_cartografico.
    """
    job_registro = {
        "projeto_id": projeto_id,
        "arquivo_id_origem": arquivo_id_origem,
        "vertex_job_id": vertex_job_id,
        "tipo_job": tipo_job,
        "payload_json": payload_json,
        "status": status,
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
            arquivo_id=arquivo_id_origem,
            tipo_evento="promocao_base_oficial",
            origem="sistema",
            observacao=f"Job CAD registrado ({tipo_job}) via VERTEXROSEA. Status: {status}",
            payload={
                "vertex_job_id": vertex_job_id,
                "status": status,
                "tipo_job": tipo_job,
                "payload_json": payload_json,
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
    erro: Optional[str] = None,
    warnings: Optional[List[str]] = None,
    artefatos_json: Optional[Dict[str, Any]] = None
) -> bool:
    """
    Atualiza o status de processamento de um Job CAD.
    """
    agora = datetime.now(timezone.utc).isoformat()
    atualizacao = {
        "status": status,
        "warnings": warnings or [],
        "erro": erro,
        "artefatos_json": artefatos_json,
        "atualizado_em": agora
    }
    if status in ("done", "failed"):
        atualizacao["concluido_em"] = agora
    
    # ─── 1. Atualizar tabela dedicada jobs_cad ─────────────────────
    try:
        res = sb.table("jobs_cad").update(atualizacao).eq("vertex_job_id", vertex_job_id).execute()
        if res.data:
            logger.info("Status do Job %s atualizado para %s na tabela jobs_cad.", vertex_job_id, status)
            return True
    except Exception as e:
        logger.warning("Falha ao atualizar status do Job %s na tabela jobs_cad: %s", vertex_job_id, e)
        
    return False
