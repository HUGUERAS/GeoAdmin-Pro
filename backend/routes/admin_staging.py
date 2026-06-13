import os
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from scripts.seed_piloto_condominial import gerar_seed_piloto_condominial
# Supondo que check_staging_connection possa ser encapsulado ou refeito,
# mas para simplicidade, vamos importar algo para testes E2E se necessário.

router = APIRouter(prefix="/admin/staging", tags=["Admin Staging (Terminal-Free)"])

def verify_staging_tools():
    if os.environ.get("STAGING_TOOLS_ENABLED", "false").lower() != "true":
        raise HTTPException(status_code=403, detail="Staging tools disabled. Set STAGING_TOOLS_ENABLED=true.")

class SeedConfig(BaseModel):
    projeto: str = "Piloto Condominial MVP"
    lotes: int = 50
    percentual_sem_participante: int = 20
    percentual_documentos_pendentes: int = 30
    percentual_magic_links: int = 50
    percentual_confrontacoes_pendentes: int = 10
    dry_run: bool = True

@router.post("/seed/execute")
async def run_seed(config: SeedConfig, _ = Depends(verify_staging_tools)):
    """
    Executa o seed parametrizado sem necessidade de terminal.
    Deixe dry_run=True para simular, ou mude para False para persistir.
    """
    # Converter BaseModel para dict e executar
    result = gerar_seed_piloto_condominial(config.dict())
    return result

@router.post("/e2e/run")
async def run_e2e(_ = Depends(verify_staging_tools)):
    """
    Executa bateria de testes E2E básicos.
    Retorna JSON com o status de saúde da orquestração.
    """
    # Esta rota é um placeholder estrutural. A execução completa do test_e2e_smoke.py
    # poderia ser encapsulada como função pura no futuro.
    return {
        "status": "not_implemented_yet",
        "message": "A função E2E pura será mapeada em futuras iterações."
    }

@router.get("/schema/check")
async def check_schema(_ = Depends(verify_staging_tools)):
    """
    Valida as configurações do banco staging.
    (Idealmente chama as verificações do check_staging_connection.py refatorado).
    """
    return {
        "message": "Use a validação visual SUPABASE_SQL_VALIDATE.md no Supabase Editor para checar as migrations de forma 100% livre de código."
    }
