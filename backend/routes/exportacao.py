"""
GeoAdmin Pro — Endpoint de exportação para Métrica TOPO

Endpoints:
- POST /projetos/{id}/metrica/preparar  → ZIP com TXT, CSV, DXF, KML + README
- GET  /projetos/{id}/metrica/txt
- GET  /projetos/{id}/metrica/csv
- GET  /projetos/{id}/metrica/dxf
- GET  /projetos/{id}/metrica/kml

IMPORTANTE:
- Este módulo depende de uma função `get_supabase()` definida em `backend.main`
  que deve retornar um cliente válido do Supabase.
"""

import io
import zipfile
import logging
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

logger = logging.getLogger("geoadmin.exportacao")

router = APIRouter(prefix="/projetos", tags=["Exportação"])


def _nome_arquivo(projeto_nome: str, numero_job: str, extensao: str) -> str:
    """Gera nome de arquivo seguro para download."""
    job = numero_job or "sem-job"
    nome = (projeto_nome or "Projeto").replace(" ", "_").replace("/", "-")[:30]
    return f"GeoAdmin_{job}_{nome}.{extensao}" if extensao else f"GeoAdmin_{job}_{nome}."


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
    from main import get_supabase as _get  # import tardio para evitar ciclos
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

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        base = _nome_arquivo(pacote.projeto_nome, pacote.numero_job, "")

        zf.writestr(f"{base}txt", pacote.txt.encode("utf-8"))
        zf.writestr(f"{base}csv", pacote.csv.encode("utf-8"))
        zf.writestr(f"{base}kml", pacote.kml.encode("utf-8"))

        if pacote.dxf:
            zf.writestr(f"{base}dxf", pacote.dxf)

        readme = _gerar_readme(pacote)
        zf.writestr("COMO_USAR_NO_METRICA.txt", readme.encode("utf-8"))

    zip_buffer.seek(0)
    nome_zip = _nome_arquivo(pacote.projeto_nome, pacote.numero_job, "zip")

    logger.info(
        "Pacote Métrica gerado: '%s' (%d pts) — %d bytes",
        pacote.projeto_nome,
        pacote.total_pontos,
        len(zip_buffer.getvalue()),
    )

    headers = {
        "Content-Disposition": f'attachment; filename="{nome_zip}"',
        "X-Avisos": str(len(pacote.avisos)),
    }
    if pacote.avisos:
        headers["X-Aviso-Detalhes"] = " | ".join(pacote.avisos[:3])

    return Response(
        content=zip_buffer.getvalue(),
        media_type="application/zip",
        headers=headers,
    )


@router.get("/{projeto_id}/metrica/txt", summary="Baixar pontos em TXT")
def baixar_txt(projeto_id: str, supabase=None):
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
    nome = _nome_arquivo(
        projeto.get("projeto_nome", ""), projeto.get("numero_job", ""), "txt"
    )
    return Response(
        content=conteudo.encode("utf-8"),
        media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{nome}"'},
    )


@router.get("/{projeto_id}/metrica/csv", summary="Baixar pontos em CSV")
def baixar_csv(projeto_id: str, sep: str = ";", supabase=None):
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
    nome = _nome_arquivo(
        projeto.get("projeto_nome", ""), projeto.get("numero_job", ""), "csv"
    )
    return Response(
        content=conteudo.encode("utf-8"),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{nome}"'},
    )


@router.get("/{projeto_id}/metrica/kml", summary="Baixar KML para Google Earth")
def baixar_kml(projeto_id: str, supabase=None):
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
    nome = _nome_arquivo(
        projeto.get("projeto_nome", ""), projeto.get("numero_job", ""), "kml"
    )
    return Response(
        content=conteudo.encode("utf-8"),
        media_type="application/vnd.google-earth.kml+xml",
        headers={"Content-Disposition": f'attachment; filename="{nome}"'},
    )


@router.get("/{projeto_id}/metrica/dxf", summary="Baixar arquivo DXF para AutoCAD/Métrica")
def baixar_dxf(projeto_id: str, supabase=None):
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
    nome = _nome_arquivo(
        projeto.get("projeto_nome", ""), projeto.get("numero_job", ""), "dxf"
    )
    return Response(
        content=conteudo,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{nome}"'},
    )


def _gerar_readme(pacote) -> str:
    avisos_txt = (
        "\n".join(f"  ! {a}" for a in pacote.avisos)
        if pacote.avisos
        else "  Nenhum aviso."
    )
    return f"""
GEOADMIN PRO — PACOTE PARA MÉTRICA TOPO
========================================
Projeto: {pacote.projeto_nome}
Job:     {pacote.numero_job}
Pontos:  {pacote.total_pontos}

COMO IMPORTAR NO MÉTRICA TOPO
-----------------------------
.txt  → Arquivo > Importar Pontos > "Nome,código,n,e,elev(*.txt)"
        (formato: Nome,Código,Norte,Este,Elevação — vírgula, ponto decimal)

.csv  → Arquivo > Importar Pontos > "Nome,código,n,e,elev(*.csv)"
        (mesmo formato, extensão .csv — use este se o .txt não aparecer)

.csv (Excel) → Abrir no Excel BR (separador ;, vírgula decimal)
        NÃO use este para importar no Métrica TOPO

.dxf  → Abrir em: AutoCAD ou diretamente no Métrica TOPO
.kml  → Abrir no Google Earth para conferir a posição do lote

ATENÇÃO
-------
Todos os dados vieram do GeoAdmin Pro.
Não edite os arquivos manualmente — qualquer correção deve ser
feita no app e um novo pacote gerado.

AVISOS DESTE PACOTE
-------------------
{avisos_txt}

Gerado por GeoAdmin Pro — {pacote.projeto_nome}
""".strip()

