"""
Endpoints de exportação para Métrica TOPO.
"""

import logging

from fastapi import APIRouter, HTTPException, Depends
from middleware.auth import verificar_token
from fastapi.responses import Response

from .pacote import gerar_manifesto_metrica, preparar_zip_metrica
from .utils import nome_arquivo

logger = logging.getLogger("geoadmin.exportacao")

router = APIRouter(prefix="/projetos", tags=["Exportação"], dependencies=[Depends(verificar_token)])


@router.get("/{projeto_id}/metrica/manifesto", summary="Obter manifesto JSON para o bridge do Métrica")
def obter_manifesto_metrica(projeto_id: str, supabase=None):
    """
    Retorna manifesto JSON do pacote para integração com Métrica TOPO.
    """
    from main import get_supabase as _get
    from integracoes.integracao_metrica import gerar_pacote_metrica

    sb = supabase or _get()
    try:
        pacote = gerar_pacote_metrica(sb, projeto_id)
    except ValueError as e:
        codigo = str(e)[:9]
        raise HTTPException(
            status_code=404 if "401" in codigo or "404" in codigo else 500,
            detail={"erro": str(e), "codigo": codigo},
        )

    manifesto, _ = gerar_manifesto_metrica(sb, projeto_id, pacote)
    return manifesto


@router.post(
    "/{projeto_id}/metrica/preparar",
    summary="Gerar pacote completo para Métrica TOPO",
    response_class=Response,
)
def preparar_metrica(projeto_id: str, supabase=None):
    """
    Gera os 4 arquivos do projeto em um ZIP para download imediato.

    Retorna: ZIP com:
      - *.txt  (pontos em formato texto)
      - *.csv  (pontos em CSV separador ;)
      - *.dxf  (arquivo CAD)
      - *.kml  (Google Earth)
      - COMO_USAR_NO_METRICA.txt (instruções)
    """
    from main import get_supabase as _get
    from integracoes.integracao_metrica import gerar_pacote_metrica

    sb = supabase or _get()

    try:
        pacote = gerar_pacote_metrica(sb, projeto_id)
    except ValueError as e:
        codigo = str(e)[:9]
        raise HTTPException(
            status_code=404 if "401" in codigo or "404" in codigo else 500,
            detail={"erro": str(e), "codigo": codigo},
        )

    return preparar_zip_metrica(sb, projeto_id, pacote)


@router.get("/{projeto_id}/metrica/txt", summary="Baixar pontos em TXT")
def baixar_txt(projeto_id: str, supabase=None):
    """
    Retorna arquivo TXT com coordenadas dos pontos.
    """
    from main import get_supabase as _get
    from integracoes.integracao_metrica import (
        _buscar_projeto,
        _buscar_pontos,
        gerar_txt,
    )

    sb = supabase or _get()
    projeto = _buscar_projeto(sb, projeto_id)
    pontos = _buscar_pontos(sb, projeto_id)
    conteudo = gerar_txt(pontos, projeto)
    nome = nome_arquivo(
        projeto.get("projeto_nome", ""), projeto.get("numero_job", ""), "txt"
    )
    return Response(
        content=conteudo.encode("utf-8"),
        media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{nome}"'},
    )


@router.get("/{projeto_id}/metrica/csv", summary="Baixar pontos em CSV")
def baixar_csv(projeto_id: str, sep: str = ";", supabase=None):
    """
    Retorna arquivo CSV com coordenadas dos pontos.
    """
    from main import get_supabase as _get
    from integracoes.integracao_metrica import (
        _buscar_projeto,
        _buscar_pontos,
        gerar_csv,
    )

    sb = supabase or _get()
    projeto = _buscar_projeto(sb, projeto_id)
    pontos = _buscar_pontos(sb, projeto_id)
    conteudo = gerar_csv(pontos, projeto, separador=sep)
    nome = nome_arquivo(
        projeto.get("projeto_nome", ""), projeto.get("numero_job", ""), "csv"
    )
    return Response(
        content=conteudo.encode("utf-8"),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{nome}"'},
    )


@router.get("/{projeto_id}/metrica/kml", summary="Baixar KML para Google Earth")
def baixar_kml(projeto_id: str, supabase=None):
    """
    Retorna arquivo KML com perímetro para visualização no Google Earth.
    """
    from main import get_supabase as _get
    from integracoes.integracao_metrica import (
        _buscar_projeto,
        _buscar_pontos,
        gerar_kml,
    )

    sb = supabase or _get()
    projeto = _buscar_projeto(sb, projeto_id)
    pontos = _buscar_pontos(sb, projeto_id)
    conteudo = gerar_kml(pontos, projeto)
    nome = nome_arquivo(
        projeto.get("projeto_nome", ""), projeto.get("numero_job", ""), "kml"
    )
    return Response(
        content=conteudo.encode("utf-8"),
        media_type="application/vnd.google-earth.kml+xml",
        headers={"Content-Disposition": f'attachment; filename="{nome}"'},
    )


@router.get("/{projeto_id}/metrica/dxf", summary="Baixar arquivo DXF para AutoCAD/Métrica")
def baixar_dxf(projeto_id: str, supabase=None):
    """
    Retorna arquivo DXF com perímetro para uso em CAD.
    """
    from main import get_supabase as _get
    from integracoes.integracao_metrica import (
        _buscar_projeto,
        _buscar_pontos,
        gerar_dxf,
    )

    sb = supabase or _get()
    projeto = _buscar_projeto(sb, projeto_id)
    pontos = _buscar_pontos(sb, projeto_id)
    try:
        conteudo = gerar_dxf(pontos, projeto)
    except RuntimeError as e:
        raise HTTPException(
            status_code=500, detail={"erro": str(e), "codigo": 501}
        )
    nome = nome_arquivo(
        projeto.get("projeto_nome", ""), projeto.get("numero_job", ""), "dxf"
    )
    return Response(
        content=conteudo,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{nome}"'},
    )
