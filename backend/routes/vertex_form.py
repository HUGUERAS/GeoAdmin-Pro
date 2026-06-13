"""
VERTEX — compatibilidade: links antigos /formulario/foto redirecionam
para o formulario oficial do GeoAdmin (/formulario/cliente).
"""
from __future__ import annotations

from fastapi import APIRouter, Query
from fastapi.responses import RedirectResponse

router = APIRouter(tags=["VERTEX Formulario"])


@router.get("/formulario/foto", summary="Redireciona para o formulario oficial")
def formulario_foto_redirect(token: str = Query(...)):
    return RedirectResponse(url=f"/formulario/cliente?token={token}", status_code=307)
