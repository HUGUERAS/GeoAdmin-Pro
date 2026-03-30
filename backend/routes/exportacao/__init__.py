"""
GeoAdmin Pro — Módulo de exportação para Métrica TOPO.

Endpoints:
- POST /projetos/{id}/metrica/preparar  → ZIP com TXT, CSV, DXF, KML + manifesto
- GET  /projetos/{id}/metrica/manifesto
- GET  /projetos/{id}/metrica/txt
- GET  /projetos/{id}/metrica/csv
- GET  /projetos/{id}/metrica/dxf
- GET  /projetos/{id}/metrica/kml

IMPORTANTE:
- Este módulo depende de uma função `get_supabase()` definida em `backend.main`
  que deve retornar um cliente válido do Supabase.
"""

from .routes import router

__all__ = ["router"]
