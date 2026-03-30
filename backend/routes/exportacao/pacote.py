"""
Montagem e assembly do pacote ZIP para exportação.
"""

from dataclasses import asdict
from datetime import datetime, timezone
import io
import logging
import zipfile
from typing import Any

from fastapi import HTTPException
from fastapi.responses import Response

from .geojson_utils import arquivo_geojson
from .utils import nome_arquivo, query_segura, serializar_json, slug_seguro, valor_header_seguro

logger = logging.getLogger("geoadmin.exportacao")


def coletar_contexto_pacote(sb, projeto_id: str, pacote) -> dict[str, Any]:
    """
    Coleta contexto completo do projeto para o pacote de exportação.
    """
    from integracoes.integracao_metrica import _buscar_pontos, _buscar_projeto
    from integracoes.referencia_cliente import obter_geometria_referencia
    from routes.perimetros import buscar_perimetro_ativo

    projeto = _buscar_projeto(sb, projeto_id)
    pontos = [asdict(item) for item in _buscar_pontos(sb, projeto_id)]
    cliente = None
    cliente_id = projeto.get("cliente_id")

    if cliente_id:
        cliente = query_segura(
            lambda: (
                sb.table("clientes")
                .select("*")
                .eq("id", cliente_id)
                .maybe_single()
                .execute()
                .data
            ),
            None,
        )

    confrontantes = query_segura(
        lambda: (
            sb.table("confrontantes")
            .select("id, projeto_id, lado, tipo, nome, cpf, nome_imovel, matricula, origem, criado_em")
            .eq("projeto_id", projeto_id)
            .is_("deleted_at", "null")
            .order("criado_em", desc=False)
            .execute()
            .data
            or []
        ),
        [],
    )

    documentos = query_segura(
        lambda: (
            sb.table("documentos_gerados")
            .select("id, tipo, gerado_em")
            .eq("projeto_id", projeto_id)
            .is_("deleted_at", "null")
            .order("gerado_em", desc=True)
            .execute()
            .data
            or []
        ),
        [],
    )

    perimetro_ativo = query_segura(lambda: buscar_perimetro_ativo(projeto_id, supabase=sb), None)
    geometria_referencia = (
        query_segura(lambda: obter_geometria_referencia(sb, cliente_id), None) if cliente_id else None
    )

    return {
        "projeto": projeto,
        "cliente": cliente,
        "pontos": pontos,
        "confrontantes": confrontantes,
        "documentos": documentos,
        "perimetro_ativo": perimetro_ativo,
        "geometria_referencia": geometria_referencia,
        "resumo": {
            "pontos_total": len(pontos),
            "confrontantes_total": len(confrontantes),
            "documentos_total": len(documentos),
            "perimetro_tipo": perimetro_ativo.get("tipo") if perimetro_ativo else None,
            "referencia_cliente": bool(geometria_referencia),
            "avisos_total": len(pacote.avisos),
        },
    }


def montar_manifesto_pacote(
    contexto: dict[str, Any],
    pacote,
    pasta_trabalho: str,
    arquivos: dict[str, str],
) -> dict[str, Any]:
    """
    Monta o manifesto JSON do pacote.
    """
    projeto = contexto["projeto"]
    cliente = contexto["cliente"]
    perimetro = contexto["perimetro_ativo"]
    referencia = contexto["geometria_referencia"]

    checklist = [
        {
            "id": "importar_pontos",
            "label": "Importar pontos TXT/CSV no Métrica",
            "ok": bool(contexto["pontos"]),
            "arquivo_preferencial": arquivos.get("pontos_txt"),
        },
        {
            "id": "abrir_dxf",
            "label": "Abrir o arquivo DXF do perímetro",
            "ok": bool(arquivos.get("perimetro_dxf")),
            "arquivo_preferencial": arquivos.get("perimetro_dxf"),
        },
        {
            "id": "conferir_confrontantes",
            "label": "Conferir confrontantes no CAD e documentos",
            "ok": bool(contexto["confrontantes"]),
            "arquivo_preferencial": arquivos.get("confrontantes_json"),
        },
        {
            "id": "conferir_referencia_cliente",
            "label": "Comparar referência do cliente com o perímetro técnico",
            "ok": bool(referencia),
            "arquivo_preferencial": arquivos.get("referencia_cliente_geojson"),
        },
    ]

    return {
        "schema": "geoadmin.metrica.bridge.v1",
        "gerado_em": datetime.now(timezone.utc).isoformat(),
        "pasta_trabalho_sugerida": pasta_trabalho,
        "projeto": {
            "id": projeto.get("id"),
            "nome": projeto.get("projeto_nome") or projeto.get("nome"),
            "numero_job": projeto.get("numero_job"),
            "municipio": projeto.get("municipio"),
            "estado": projeto.get("estado"),
            "zona_utm": projeto.get("zona_utm"),
            "status": projeto.get("status"),
            "cliente_id": projeto.get("cliente_id"),
            "cliente_nome": projeto.get("cliente_nome"),
            "area_ha": projeto.get("area_ha"),
            "matricula": projeto.get("matricula"),
        },
        "cliente": cliente,
        "imovel": {
            "nome": projeto.get("nome_imovel") or projeto.get("projeto_nome") or projeto.get("nome"),
            "municipio": projeto.get("municipio"),
            "estado": projeto.get("estado"),
            "matricula": projeto.get("matricula"),
            "comarca": projeto.get("comarca"),
            "area_ha": projeto.get("area_ha"),
        },
        "resumo": contexto["resumo"],
        "arquivos": arquivos,
        "documentos": contexto["documentos"],
        "checklist": checklist,
        "avisos": pacote.avisos,
        "perimetro_ativo": {
            "id": perimetro.get("id") if perimetro else None,
            "nome": perimetro.get("nome") if perimetro else None,
            "tipo": perimetro.get("tipo") if perimetro else None,
            "vertices_total": len((perimetro or {}).get("vertices") or []),
        },
        "referencia_cliente": {
            "nome": referencia.get("nome") if referencia else None,
            "origem_tipo": referencia.get("origem_tipo") if referencia else None,
            "arquivo_nome": referencia.get("arquivo_nome") if referencia else None,
            "formato": referencia.get("formato") if referencia else None,
            "resumo": referencia.get("resumo") if referencia else None,
            "comparativo": referencia.get("comparativo") if referencia else None,
        },
    }


def gerar_manifesto_metrica(sb, projeto_id: str, pacote) -> tuple[dict[str, Any], dict[str, Any]]:
    """
    Gera manifesto e contexto do pacote Métrica.
    """
    contexto = coletar_contexto_pacote(sb, projeto_id, pacote)
    base = nome_arquivo(pacote.projeto_nome, pacote.numero_job, "")
    pasta_trabalho = slug_seguro(f"{pacote.numero_job or 'sem-job'}-{pacote.projeto_nome}")
    arquivos = {
        "pontos_txt": f"{base}txt",
        "pontos_csv": f"{base}csv",
        "perimetro_kml": f"{base}kml",
        "perimetro_dxf": f"{base}dxf" if pacote.dxf else "",
        "readme": "COMO_USAR_NO_METRICA.txt",
        "manifesto": "manifesto.json",
        "projeto_json": "dados/projeto.json",
        "cliente_json": "dados/cliente.json",
        "confrontantes_json": "dados/confrontantes.json",
        "documentos_json": "dados/documentos.json",
        "pontos_json": "dados/pontos.json",
        "perimetro_geojson": "dados/perimetro_ativo.geojson",
        "referencia_cliente_geojson": "dados/referencia_cliente.geojson",
    }
    manifesto = montar_manifesto_pacote(contexto, pacote, pasta_trabalho, arquivos)
    return manifesto, contexto


def gerar_readme(pacote) -> str:
    """
    Gera arquivo README com instruções de uso no Métrica TOPO.
    """
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


def preparar_zip_metrica(sb, projeto_id: str, pacote) -> Response:
    """
    Prepara e retorna ZIP com pacote completo para Métrica TOPO.
    """
    manifesto, contexto = gerar_manifesto_metrica(sb, projeto_id, pacote)
    base = nome_arquivo(pacote.projeto_nome, pacote.numero_job, "")

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(f"{base}txt", pacote.txt.encode("utf-8"))
        zf.writestr(f"{base}csv", pacote.csv.encode("utf-8"))
        zf.writestr(f"{base}kml", pacote.kml.encode("utf-8"))

        if pacote.dxf:
            zf.writestr(f"{base}dxf", pacote.dxf)

        readme = gerar_readme(pacote)
        zf.writestr("COMO_USAR_NO_METRICA.txt", readme.encode("utf-8"))
        zf.writestr("manifesto.json", serializar_json(manifesto))
        zf.writestr("dados/projeto.json", serializar_json(contexto["projeto"]))
        zf.writestr("dados/cliente.json", serializar_json(contexto["cliente"]))
        zf.writestr("dados/confrontantes.json", serializar_json(contexto["confrontantes"]))
        zf.writestr("dados/documentos.json", serializar_json(contexto["documentos"]))
        zf.writestr("dados/pontos.json", serializar_json(contexto["pontos"]))

        perimetro_geojson = arquivo_geojson(
            (contexto["perimetro_ativo"] or {}).get("vertices"),
            propriedades={
                "tipo": (contexto["perimetro_ativo"] or {}).get("tipo"),
                "nome": (contexto["perimetro_ativo"] or {}).get("nome"),
            },
        )
        if perimetro_geojson:
            zf.writestr("dados/perimetro_ativo.geojson", perimetro_geojson)

        referencia_geojson = arquivo_geojson(
            (contexto["geometria_referencia"] or {}).get("vertices"),
            propriedades={
                "origem_tipo": (contexto["geometria_referencia"] or {}).get("origem_tipo"),
                "nome": (contexto["geometria_referencia"] or {}).get("nome"),
            },
        )
        if referencia_geojson:
            zf.writestr("dados/referencia_cliente.geojson", referencia_geojson)

    zip_buffer.seek(0)
    nome_zip = nome_arquivo(pacote.projeto_nome, pacote.numero_job, "zip")

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
        detalhes = " | ".join(pacote.avisos[:3])
        headers["X-Aviso-Detalhes"] = valor_header_seguro(detalhes)

    return Response(
        content=zip_buffer.getvalue(),
        media_type="application/zip",
        headers=headers,
    )
