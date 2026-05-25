import sys
import os

# Adiciona o diretório backend ao path para imports relativos
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ── Banco de dados PROJ local (operação offline / sem internet) ────────────────
# O proj.db contém todas as definições CRS (SIRGAS2000, SAD69, UTM, etc.)
# sem necessidade de rede.
# Definir PROJ_DATA *antes* de importar pyproj para que ele use o banco local.
# Configure via variável de ambiente PROJ_DATA, ou deixe vazio para usar valor padrão do pyproj.
_proj_data_dir = os.getenv("PROJ_DATA")
if _proj_data_dir and os.path.isdir(_proj_data_dir):
    os.environ["PROJ_DATA"] = _proj_data_dir
# ──────────────────────────────────────────────────────────────────────────────

from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import Dict, Any

from dotenv import load_dotenv

# Importa configurações e dependências do core
from core import settings, get_supabase
from core.observabilidade import (
    setup_logging,
    ObservabilityMiddleware,
    create_health_check_details,
)

# Importa o middleware de autenticação
from middleware import verificar_token, limiter

# Carrega variáveis de ambiente
load_dotenv()

# Configura logging estruturado
setup_logging(json_logs=settings.APP_ENV == "production")

# ── Rotas
# Para proteger um endpoint com autenticação, adicione o seguinte ao seus handlers:
#     usuario: dict = Depends(verificar_token)
# Exemplo:
#     @router.get("/exemplo")
#     def exemplo(usuario: dict = Depends(verificar_token)):
#         print(f"Usuário autenticado: {usuario['sub']}")

from routes.exportacao import router as exportacao_router
from routes.metrica_simples import router as metrica_router
from routes.projetos import router as projetos_router
from routes.clientes import router as clientes_router
from routes.documentos import router as docs_router
from routes.pontos import router as pontos_router
# RAG removido do backend principal — rodar separadamente quando necessário
# from routes.rag import router as rag_router
from routes.perimetros import router as perimetros_router
from routes.geo import router as geo_router
from routes.importar import router as importar_router
from routes.catalogo import router as catalogo_router

app = FastAPI(title="GeoAdmin Pro - Backend MVP")
app.state.limiter = limiter

# Adiciona middleware de observabilidade (logging estruturado, correlation_id, métricas)
app.add_middleware(ObservabilityMiddleware)

app.add_middleware(
  CORSMiddleware,
  allow_origins=settings.allowed_origins,
  allow_origin_regex=settings.cors_origin_regex,
  allow_methods=["*"],
  allow_headers=["*"],
)

_static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
if os.path.isdir(_static_dir):
  app.mount("/static", StaticFiles(directory=_static_dir), name="static")

app.include_router(projetos_router)
app.include_router(clientes_router)
app.include_router(exportacao_router)
app.include_router(metrica_router)
app.include_router(docs_router)
app.include_router(pontos_router)
# app.include_router(rag_router)  # RAG desativado — módulo isolado
app.include_router(perimetros_router)
app.include_router(geo_router)
app.include_router(importar_router)
app.include_router(catalogo_router)


import logging as _logging
_logger_main = _logging.getLogger("geoadmin.main")


@app.exception_handler(Exception)
async def _handler_erro_global(request: Request, exc: Exception) -> JSONResponse:
    """Garante que exceções não capturadas retornem JSON (não text/plain do Starlette)."""
    if isinstance(exc, HTTPException):
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
    _logger_main.error("Exceção não tratada em %s: %s", request.url.path, exc, exc_info=True)
    return JSONResponse(
        status_code=500,
            content={"erro": "Erro interno", "codigo": 500},
    )


@app.get("/health")
def health() -> Dict[str, Any]:
    """
    Endpoint de health check profundo.

    Retorna status da aplicação, banco de dados e métricas básicas.
    Inclui correlation_id para rastreamento.
    """
    from core.observabilidade import get_correlation_id

    health_details = create_health_check_details()
    health_details["correlation_id"] = get_correlation_id()

    return health_details
