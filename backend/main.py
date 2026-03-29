import sys, os
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

from fastapi import FastAPI, HTTPException, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Any

from dotenv import load_dotenv
from supabase import create_client, Client

# Importa o middleware de autenticação
from middleware.auth import verificar_token

# Carrega origens CORS permitidas do ambiente
load_dotenv()
_origens_padrao = [
    "http://localhost:8081",
    "http://localhost:19006",
    "http://localhost:8000",
]
_origens_permitidas = os.getenv("ALLOWED_ORIGINS", ",".join(_origens_padrao)).split(",")

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

app.add_middleware(
  CORSMiddleware,
  allow_origins=[origem.strip() for origem in _origens_permitidas],
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


@app.get("/health")
def health() -> Dict[str, str]:
  return {"status": "ok"}


_supabase_client: Client | None = None


def get_supabase() -> Client:
  """
  Retorna um cliente Supabase configurado via variáveis de ambiente.

  Espera encontrar:
  - SUPABASE_URL
  - SUPABASE_KEY  (use a anon key ou service key conforme o caso)

  Você pode definir essas variáveis em um arquivo `.env` dentro de `backend/`
  (carregado automaticamente pelo python-dotenv) ou diretamente no ambiente.
  """
  global _supabase_client

  if _supabase_client is not None:
    return _supabase_client

  # Carrega variáveis de ambiente de backend/.env, se existir
  load_dotenv()

  url = os.getenv("SUPABASE_URL")
  key = os.getenv("SUPABASE_KEY")

  if not url or not key:
    raise HTTPException(
      status_code=500,
      detail={
        "erro": (
          "Supabase não configurado. Defina SUPABASE_URL e SUPABASE_KEY "
          "no arquivo backend/.env ou no ambiente do servidor."
        ),
        "codigo": 500,
      },
    )

  _supabase_client = create_client(url, key)
  return _supabase_client
