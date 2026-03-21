"""
GeoAdmin Pro — Integração Métrica TOPO
=======================================
backend/integracoes/integracao_metrica.py

Recebe um projeto_id, busca os dados do Supabase e gera
os 4 formatos que o Métrica TOPO consome:

  .txt — pontos em formato texto (Nome, Norte, Este, Cota, Código)
  .csv — mesmos dados separados por vírgula/ponto-e-vírgula
  .dxf — arquivo CAD com pontos, textos e polilinha do perímetro
  .kml — Google Earth com pontos e polígono do lote

Regra central: nenhum dado é digitado aqui.
Tudo vem do banco via projeto_id.

IMPORTANTE: esta integração depende de views já existentes no Supabase:
- vw_projetos_completo
- vw_pontos_utm
"""

import math
import csv
import io
import logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger("geoadmin.integracao_metrica")


@dataclass
class PontoExportacao:
    """Ponto normalizado para exportação — independente do formato de saída."""

    nome: str
    norte: float
    este: float
    cota: float
    codigo: str
    descricao: str
    latitude: float
    longitude: float


@dataclass
class PacoteMetrica:
    """
    Pacote completo gerado para o Métrica TOPO.
    Contém os 4 arquivos prontos para download ou execução.
    """

    projeto_nome: str
    numero_job: str
    total_pontos: int
    txt: str  # conteúdo do .txt
    csv: str  # conteúdo do .csv
    dxf: bytes  # binário do .dxf
    kml: str  # conteúdo do .kml
    avisos: list[str]


def _buscar_projeto(supabase, projeto_id: str) -> dict:
    """Busca os dados do projeto incluindo cliente."""
    try:
        res = (
            supabase.table("vw_projetos_completo")
            .select("*")
            .eq("id", projeto_id)
            .single()
            .execute()
        )
    except Exception as e:  # pragma: no cover - erro de infraestrutura
        raise ValueError(f"[ERRO-401] Projeto {projeto_id} não encontrado: {e}")

    if not res.data:
        raise ValueError(f"[ERRO-402] Projeto {projeto_id} retornou vazio.")

    return res.data


def _buscar_pontos(supabase, projeto_id: str) -> list[PontoExportacao]:
    """
    Busca os pontos do projeto via vw_pontos_utm.
    Usa a zona UTM correta de cada projeto (não hardcoded em 23S).
    """
    try:
        res = (
            supabase.table("vw_pontos_utm")
            .select("*")
            .eq("projeto_id", projeto_id)
            .is_("deleted_at", "null")
            .order("nome")
            .execute()
        )
    except Exception as e:  # pragma: no cover - erro de infraestrutura
        raise ValueError(f"[ERRO-403] Falha ao buscar pontos: {e}")

    if not res.data:
        raise ValueError(
            "[ERRO-404] Projeto não tem pontos cadastrados. "
            "Colete os pontos em campo antes de exportar."
        )

    pontos: list[PontoExportacao] = []
    for row in res.data:
        pontos.append(
            PontoExportacao(
                nome=row.get("nome", ""),
                norte=float(row.get("norte_utm") or 0),
                este=float(row.get("este_utm") or 0),
                cota=float(row.get("altitude_m") or 0),
                codigo=row.get("codigo") or "TP",
                descricao=row.get("descricao") or "",
                latitude=float(row.get("latitude") or 0),
                longitude=float(row.get("longitude") or 0),
            )
        )

    return pontos


def gerar_txt(pontos: list[PontoExportacao], projeto: dict) -> str:
    """
    Gera arquivo .txt no formato exato que o Métrica TOPO importa.

    Conforme ImportExportFormat.db (LandStar) — formato SID=1:
      Nome,código,n,e,elev(*.txt)

    Especificações (EXPORT_CUSTOM_TABLE):
      SPLIT_CHAR_NUM=0   → separador vírgula
      USER_TABLE_HEAD=0  → sem linha de cabeçalho
      DECIMAL=3          → 3 casas decimais para Norte/Este
      ELEVATION_DECIMAL=3→ 3 casas decimais para Elevação
      Ordem das colunas  → Nome, Código, Norte, Este, Elevação

    Exemplo de linha:
      P01,TP,7395200.000,423061.000,879.100

    Para importar no Métrica TOPO:
      Arquivo > Importar Pontos > "Nome,código,n,e,elev(*.txt)"
    """
    linhas: list[str] = []

    for p in pontos:
        linhas.append(
            f"{p.nome},{p.codigo},{p.norte:.3f},{p.este:.3f},{p.cota:.3f}"
        )

    return "\n".join(linhas)


def gerar_csv(
    pontos: list[PontoExportacao], projeto: dict, separador: str = ";"
) -> str:
    """
    Gera arquivo .csv compatível com Métrica TOPO — formato SID=3 (ou Excel BR).

    Colunas na ordem correta do Métrica TOPO:
      Nome, Código, Norte, Este, Elevação

    Parâmetros:
        separador: "," para Métrica TOPO (SID=3), ";" para Excel BR
    """
    saida = io.StringIO()

    if separador == ",":
        # Formato Métrica TOPO (SID=3): sem cabeçalho, ponto decimal, 3 decimais
        for p in pontos:
            saida.write(
                f"{p.nome},{p.codigo},{p.norte:.3f},{p.este:.3f},{p.cota:.3f}\n"
            )
    else:
        # Formato Excel BR: cabeçalho + vírgula como decimal
        saida.write(f"# Projeto: {projeto.get('projeto_nome', '')}\n")
        saida.write(f"# Job: {projeto.get('numero_job', '')}\n")
        saida.write(f"# Zona UTM: {projeto.get('zona_utm', '23S')}\n")
        writer = csv.writer(saida, delimiter=separador, quoting=csv.QUOTE_MINIMAL)
        writer.writerow(["Nome", "Codigo", "Norte", "Este", "Cota", "Descricao"])
        for p in pontos:
            writer.writerow(
                [
                    p.nome,
                    p.codigo,
                    f"{p.norte:.3f}".replace(".", ","),
                    f"{p.este:.3f}".replace(".", ","),
                    f"{p.cota:.3f}".replace(".", ","),
                    p.descricao,
                ]
            )

    return saida.getvalue()


def gerar_dxf(pontos: list[PontoExportacao], projeto: dict) -> bytes:
    """
    Gera arquivo DXF compatível com AutoCAD 2010+ e Métrica TOPO.

    Convenções de layers baseadas no CodeImportTemplate.csv (LandStar):
      Point1    — marcadores de ponto RTK (vermelho, PDMODE=3 = cruz+círculo)
      TEXTOS    — nomes e cotas dos pontos (branco)
      PERIMETRO — polilinha fechada do lote (vermelho, espessura 0.25mm)
      COTAS     — valores de altitude ortométrica (ciano)
      INFO      — legenda do projeto (magenta)

    Variáveis de cabeçalho DXF (referência: GDAL header.dxf / AC1018):
      $INSUNITS = 6  → metros (essencial para softwares de engenharia)
      $PDMODE   = 3  → marcador cruz (X) — padrão topográfico
      $PDSIZE   = -0.5 → tamanho relativo ao viewport (negativo = % da tela)
      $AUNITS   = 0  → ângulos em graus decimais
      $LUPREC   = 4  → 4 casas decimais em distâncias

    Requer: pip install ezdxf
    """
    try:
        import ezdxf
        from ezdxf import colors as dxf_colors
    except ImportError:  # pragma: no cover
        raise RuntimeError(
            "[ERRO-501] ezdxf não instalado. Execute: pip install ezdxf"
        )

    doc = ezdxf.new(dxfversion="R2010")
    msp = doc.modelspace()

    # ── Variáveis de cabeçalho (padrão GDAL + topografia) ─────────────────────
    doc.header["$INSUNITS"] = 6      # metros
    doc.header["$PDMODE"]   = 3      # ponto como cruz (X)
    doc.header["$PDSIZE"]   = 0.0    # tamanho auto pelo zoom
    doc.header["$AUNITS"]   = 0      # graus decimais
    doc.header["$AUPREC"]   = 4
    doc.header["$LUPREC"]   = 4
    doc.header["$LUNITS"]   = 2      # unidades decimais

    # ── Estilo de texto (romans.shx disponível em fonts/) ─────────────────────
    style = doc.styles.new("TOPO")
    style.dxf.font = "romans.shx"
    style.dxf.width = 0.8  # fator de largura condensada

    # ── Layers (convenção CodeImportTemplate.csv + norma ABNT) ────────────────
    doc.layers.add("Point1",    color=1)   # vermelho  — pontos topográficos
    doc.layers.add("TEXTOS",    color=7)   # branco    — nomes dos pontos
    doc.layers.add("PERIMETRO", color=1)   # vermelho  — linha de limite
    doc.layers.add("COTAS",     color=4)   # ciano     — valores de altitude
    doc.layers.add("INFO",      color=6)   # magenta   — legenda

    # Espessura de linha no layer PERIMETRO (0.25 mm = LW_025)
    doc.layers.get("PERIMETRO").dxf.lineweight = 25

    # ── Estimativa de altura do texto proporcional ao levantamento ────────────
    if len(pontos) >= 2:
        northings = [p.norte for p in pontos]
        eastings  = [p.este  for p in pontos]
        span = max(
            max(northings) - min(northings),
            max(eastings)  - min(eastings),
            1.0,
        )
        altura_texto = max(0.5, span * 0.003)
    else:
        altura_texto = 1.0

    offset_texto = altura_texto * 0.4  # deslocamento do rótulo em relação ao ponto

    # ── Pontos, nomes e cotas ─────────────────────────────────────────────────
    for p in pontos:
        # Marcador de ponto (PDMODE=3 → cruz)
        msp.add_point(
            (p.este, p.norte, p.cota),
            dxfattribs={"layer": "Point1"},
        )

        # Nome do ponto (acima-direita do marcador)
        msp.add_text(
            p.nome,
            dxfattribs={
                "layer":  "TEXTOS",
                "style":  "TOPO",
                "height": altura_texto,
                "insert": (p.este + offset_texto, p.norte + offset_texto, p.cota),
            },
        )

        # Cota ortométrica (abaixo-direita do marcador)
        msp.add_text(
            f"{p.cota:.4f}m",
            dxfattribs={
                "layer":  "COTAS",
                "style":  "TOPO",
                "height": altura_texto * 0.75,
                "insert": (p.este + offset_texto, p.norte - altura_texto, p.cota),
            },
        )

    # ── Polilinha do perímetro ────────────────────────────────────────────────
    if len(pontos) >= 3:
        coords_2d = [(p.este, p.norte) for p in pontos]
        msp.add_lwpolyline(
            coords_2d,
            dxfattribs={"layer": "PERIMETRO", "closed": True},
        )

    # ── Legenda do projeto (canto inferior esquerdo) ──────────────────────────
    if pontos:
        min_e = min(p.este  for p in pontos) - altura_texto * 5
        min_n = min(p.norte for p in pontos) - altura_texto * 12

        info_linhas = [
            f"PROJETO: {projeto.get('projeto_nome', '').upper()}",
            f"JOB:     {projeto.get('numero_job', '')}",
            f"CLIENTE: {projeto.get('cliente_nome', '')}",
            f"ZONA:    {projeto.get('zona_utm', '23S')} | PONTOS: {len(pontos)}",
            f"DATUM:   SIRGAS 2000 / UTM",
            "GERADO POR: GeoAdmin Pro",
        ]

        for i, linha in enumerate(info_linhas):
            msp.add_text(
                linha,
                dxfattribs={
                    "layer":  "INFO",
                    "style":  "TOPO",
                    "height": altura_texto * 0.7,
                    "insert": (min_e, min_n - i * altura_texto * 1.4),
                },
            )

    # ezdxf >= 1.0 escreve em stream de TEXTO (StringIO), não binário
    texto_buffer = io.StringIO()
    doc.write(texto_buffer)
    return texto_buffer.getvalue().encode("utf-8")


def _xml(texto: str) -> str:
    """Escapa caracteres especiais para XML."""
    return (
        (texto or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def gerar_kml(pontos: list[PontoExportacao], projeto: dict) -> str:
    """
    Gera arquivo KML para visualização no Google Earth.

    Contém:
      - Marcadores individuais para cada ponto (com balão de informação)
      - Polígono do perímetro do lote
      - Pasta organizada por projeto

    Coordenadas em WGS84 (latitude/longitude) — os pontos já têm
    lat/lon armazenados no banco em SRID 4674 (SIRGAS 2000).
    Para distâncias curtas a diferença SIRGAS/WGS84 é < 1mm.
    """
    nome_projeto = projeto.get("projeto_nome", "Projeto")
    numero_job = projeto.get("numero_job", "")
    cliente = projeto.get("cliente_nome", "")
    zona = projeto.get("zona_utm", "23S")

    linhas: list[str] = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<kml xmlns="http://www.opengis.net/kml/2.2">',
        "<Document>",
        f"  <name>{_xml(nome_projeto)}</name>",
        f"  <description>Job: {_xml(numero_job)} | Cliente: {_xml(cliente)} | Zona: {zona}</description>",
        "",
        '  <Style id="ponto_rtk">',
        "    <IconStyle>",
        "      <color>ff0055ff</color>",
        "      <scale>0.8</scale>",
        "      <Icon><href>http://maps.google.com/mapfiles/kml/shapes/placemark_circle.png</href></Icon>",
        "    </IconStyle>",
        "    <LabelStyle><scale>0.7</scale></LabelStyle>",
        "  </Style>",
        "",
        '  <Style id="perimetro">',
        "    <LineStyle><color>ff0000ff</color><width>2</width></LineStyle>",
        "    <PolyStyle><color>330000ff</color></PolyStyle>",
        "  </Style>",
        "",
        f"  <Folder><name>Pontos — {_xml(nome_projeto)}</name>",
    ]

    # Marcadores de ponto
    for p in pontos:
        descricao_html = (
            f"<![CDATA["
            f"<b>{p.nome}</b><br/>"
            f"Norte: {p.norte:.3f} m<br/>"
            f"Este: {p.este:.3f} m<br/>"
            f"Cota: {p.cota:.4f} m<br/>"
            f"Código: {p.codigo}"
            f"]]>")
        linhas += [
            "    <Placemark>",
            f"      <name>{_xml(p.nome)}</name>",
            f"      <description>{descricao_html}</description>",
            "      <styleUrl>#ponto_rtk</styleUrl>",
            "      <Point>",
            f"        <coordinates>{p.longitude:.8f},{p.latitude:.8f},{p.cota:.4f}</coordinates>",
            "      </Point>",
            "    </Placemark>",
        ]

    linhas.append("  </Folder>")

    # Polígono do perímetro
    if len(pontos) >= 3:
        coords_poly = " ".join(
            f"{p.longitude:.8f},{p.latitude:.8f},{p.cota:.4f}" for p in pontos
        )
        # Fechar o anel
        p0 = pontos[0]
        coords_poly += (
            f" {p0.longitude:.8f},{p0.latitude:.8f},{p0.cota:.4f}"
        )

        linhas += [
            "  <Placemark>",
            f"    <name>Perímetro — {_xml(nome_projeto)}</name>",
            "    <styleUrl>#perimetro</styleUrl>",
            "    <Polygon>",
            "      <altitudeMode>clampToGround</altitudeMode>",
            "      <outerBoundaryIs><LinearRing>",
            f"        <coordinates>{coords_poly}</coordinates>",
            "      </LinearRing></outerBoundaryIs>",
            "    </Polygon>",
            "  </Placemark>",
        ]

    linhas += [
        "</Document>",
        "</kml>",
    ]

    return "\n".join(linhas)


def gerar_pacote_metrica(supabase, projeto_id: str) -> PacoteMetrica:
    """
    Ponto de entrada principal.
    Busca os dados do banco e gera os 4 arquivos em uma única chamada.
    """
    avisos: list[str] = []

    # 1. Buscar dados
    projeto = _buscar_projeto(supabase, projeto_id)
    pontos = _buscar_pontos(supabase, projeto_id)

    logger.info(
        "Gerando pacote Métrica para projeto '%s' (%d pontos)",
        projeto.get("projeto_nome"),
        len(pontos),
    )

    # 2. Validações e avisos (não fatais)
    if not projeto.get("numero_job"):
        avisos.append(
            "Projeto sem número de job — o campo 'numero_job' está vazio. "
            "Preencha no app antes de protocolar no INCRA."
        )

    if len(pontos) < 3:
        avisos.append(
            f"Projeto com apenas {len(pontos)} ponto(s). "
            "Um polígono válido requer mínimo 3 pontos."
        )

    # 3. Gerar os 4 formatos
    txt_content = gerar_txt(pontos, projeto)
    csv_content = gerar_csv(pontos, projeto, separador=";")

    try:
        dxf_content = gerar_dxf(pontos, projeto)
    except RuntimeError as e:
        dxf_content = b""
        avisos.append(str(e))

    kml_content = gerar_kml(pontos, projeto)

    return PacoteMetrica(
        projeto_nome=projeto.get("projeto_nome", ""),
        numero_job=projeto.get("numero_job", ""),
        total_pontos=len(pontos),
        txt=txt_content,
        csv=csv_content,
        dxf=dxf_content,
        kml=kml_content,
        avisos=avisos,
    )

