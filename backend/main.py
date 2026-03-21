import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ── Banco de dados PROJ local (operação offline / sem internet) ────────────────
# O proj.db em D:\coletoraprolanddd\outras biblioteecas\proj contém todas as
# definições CRS (SIRGAS2000, SAD69, UTM, etc.) sem necessidade de rede.
# Definir PROJ_DATA *antes* de importar pyproj para que ele use o banco local.
_proj_data_dir = os.getenv(
    "PROJ_DATA",
    r"D:\coletoraprolanddd\outras biblioteecas\proj",
)
if os.path.isdir(_proj_data_dir) and "PROJ_DATA" not in os.environ:
    os.environ["PROJ_DATA"] = _proj_data_dir
# ──────────────────────────────────────────────────────────────────────────────

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any

from dotenv import load_dotenv
from supabase import create_client, Client

from routes.exportacao import router as exportacao_router
from routes.metrica_simples import router as metrica_router
from routes.projetos import router as projetos_router
from routes.documentos import router as docs_router
from routes.pontos import router as pontos_router
from routes.rag import router as rag_router
from routes.perimetros import router as perimetros_router
from routes.geo import router as geo_router
from routes.importar import router as importar_router
from routes.catalogo import router as catalogo_router

app = FastAPI(title="GeoAdmin Pro - Backend MVP")

app.add_middleware(
  CORSMiddleware,
  allow_origins=["*"],
  allow_methods=["*"],
  allow_headers=["*"],
)

_static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
if os.path.isdir(_static_dir):
  app.mount("/static", StaticFiles(directory=_static_dir), name="static")

app.include_router(projetos_router)
app.include_router(exportacao_router)
app.include_router(metrica_router)
app.include_router(docs_router)
app.include_router(pontos_router)
app.include_router(rag_router)
app.include_router(perimetros_router)
app.include_router(geo_router)
app.include_router(importar_router)
app.include_router(catalogo_router)


class InversoRequest(BaseModel):
  x1: float
  y1: float
  x2: float
  y2: float


class InversoResponse(BaseModel):
  distancia: float
  azimute_decimal: float
  azimute_dms: str


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



@app.post("/geo/inverso", response_model=InversoResponse)
def calcular_inverso(payload: InversoRequest) -> InversoResponse:
  """
  Endpoint MVP de Inverso.
  Implementação numérica precisa (pyproj/shapely) deve ser feita pelo Engenheiro Geográfico
  usando o gabarito definido na Fase 0 do Master Plan.
  """
  try:
    dx = payload.x2 - payload.x1
    dy = payload.y2 - payload.y1
    distancia = (dx ** 2 + dy ** 2) ** 0.5

    # Azimute simples em radianos -> graus (0 a 360)
    import math

    ang_rad = math.atan2(dx, dy)  # atenção: convenção simplificada
    ang_deg = math.degrees(ang_rad)
    if ang_deg < 0:
      ang_deg += 360.0

    # Converter para graus, minutos, segundos
    graus = int(ang_deg)
    minutos_float = (ang_deg - graus) * 60.0
    minutos = int(minutos_float)
    segundos = (minutos_float - minutos) * 60.0

    azimute_gms = f"{graus:02d}°{minutos:02d}'{segundos:06.3f}\""

    return InversoResponse(
      distancia=round(distancia, 6),
      azimute_decimal=round(ang_deg, 6),
      azimute_dms=azimute_gms,
    )
  except Exception as exc:  # tipo amplo apenas para MVP
    raise HTTPException(
      status_code=500,
      detail={"erro": "Falha ao calcular inverso", "codigo": 500, "detalhe": str(exc)},
    )
