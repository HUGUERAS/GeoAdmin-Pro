"""
GeoAdmin Pro — Catálogo de recursos locais do LandStar

GET /catalogo/codigos       → definições de códigos de feição (CodeImportTemplate.csv)
GET /catalogo/dispositivos  → receptores GNSS suportados (DeviceConnectionConfig.xml)
GET /catalogo/geoides       → modelos de geoide disponíveis
"""

import os
import csv
import logging
import xml.etree.ElementTree as ET
from functools import lru_cache

from fastapi import APIRouter, Depends
from middleware.auth import verificar_token

router = APIRouter(prefix="/catalogo", tags=["Catálogo"], dependencies=[Depends(verificar_token)])
logger = logging.getLogger("geoadmin.catalogo")

# Caminhos locais (configuráveis via .env)
_BASE = os.getenv(
    "CATALOGO_DIR",
    os.path.join(os.path.expanduser("~"), ".geoadmin", "catalogo"),
)
_CODIGOS_CSV  = os.path.join(_BASE, "CodeImportTemplate.csv")
_DEVICES_XML  = os.path.join(_BASE, "DeviceConnectConfig", "DeviceConnectionConfig.xml")


# ── Códigos de feição ─────────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def _carregar_codigos() -> list[dict]:
    """
    Lê CodeImportTemplate.csv — formato LandStar para definições de feição.

    Colunas: Name, DrawingType, Describe, SymbolID, SymbolSize,
             IsColorByLayer, SymbolColor, LayerName1, LayerColor, LineStyle

    DrawingType: 0 = ponto, 1 = linha, 2 = área
    """
    codigos: list[dict] = []

    # Códigos base do template LandStar
    if os.path.exists(_CODIGOS_CSV):
        try:
            with open(_CODIGOS_CSV, "r", encoding="utf-8", errors="replace") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row.get("Name"):
                        codigos.append({
                            "code":         row["Name"].strip(),
                            "drawing_type": int(row.get("DrawingType", 0)),
                            "descricao":    row.get("Describe", "").strip(),
                            "layer_dxf":    row.get("LayerName1", "Point1").strip(),
                            "cor_hex":      row.get("SymbolColor", "FF0000").strip(),
                            "line_style":   row.get("LineStyle", "CONTINUOUS").strip(),
                            "fonte":        "landstar_template",
                        })
        except Exception as e:
            logger.warning("Erro ao ler CodeImportTemplate.csv: %s", e)

    # Códigos padrão topografia (INCRA / ABNT NBR 13.133)
    codigos_padrao = [
        {"code": "TP",  "drawing_type": 0, "descricao": "Travessão / Marco",       "layer_dxf": "MARCO",    "cor_hex": "FF0000", "line_style": "CONTINUOUS", "fonte": "incra"},
        {"code": "TN",  "drawing_type": 0, "descricao": "Travessão numerado",       "layer_dxf": "MARCO",    "cor_hex": "FF0000", "line_style": "CONTINUOUS", "fonte": "incra"},
        {"code": "CER", "drawing_type": 1, "descricao": "Cerca",                   "layer_dxf": "CERCA",    "cor_hex": "FFC125", "line_style": "DASHED",     "fonte": "incra"},
        {"code": "VRT", "drawing_type": 0, "descricao": "Vértice",                 "layer_dxf": "VERTICE",  "cor_hex": "FF8000", "line_style": "CONTINUOUS", "fonte": "incra"},
        {"code": "BMB", "drawing_type": 0, "descricao": "Bench Mark / RN",         "layer_dxf": "RN",       "cor_hex": "0000FF", "line_style": "CONTINUOUS", "fonte": "incra"},
        {"code": "EST", "drawing_type": 0, "descricao": "Estação",                 "layer_dxf": "ESTACAO",  "cor_hex": "00FF00", "line_style": "CONTINUOUS", "fonte": "incra"},
        {"code": "RIO", "drawing_type": 1, "descricao": "Rio / Curso d'água",      "layer_dxf": "HIDROGRAFIA","cor_hex":"0080FF","line_style":"CONTINUOUS",  "fonte": "incra"},
        {"code": "EST_FED", "drawing_type": 1, "descricao": "Estrada federal",     "layer_dxf": "VIARIO",   "cor_hex": "808080", "line_style": "CONTINUOUS", "fonte": "incra"},
    ]

    # Adiciona padrões que não conflitam com o template
    codigos_existentes = {c["code"] for c in codigos}
    for cp in codigos_padrao:
        if cp["code"] not in codigos_existentes:
            codigos.append(cp)

    return codigos


@router.get(
    "/codigos",
    summary="Lista códigos de feição topográfica",
    description=(
        "Retorna os códigos disponíveis para classificar pontos coletados. "
        "Fonte: CodeImportTemplate.csv (LandStar) + padrões INCRA/ABNT. "
        "O campo 'layer_dxf' define em qual layer o ponto aparece no arquivo DXF exportado."
    ),
)
def listar_codigos(drawing_type: int | None = None):
    codigos = _carregar_codigos()
    if drawing_type is not None:
        codigos = [c for c in codigos if c["drawing_type"] == drawing_type]
    return {
        "total": len(codigos),
        "codigos": codigos,
        "tipos": {0: "ponto", 1: "linha", 2: "área"},
    }


# ── Receptores GNSS ───────────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def _carregar_dispositivos() -> list[dict]:
    """
    Lê DeviceConnectionConfig.xml — lista de receptores compatíveis com o LandStar.
    Retorna apenas os dispositivos RTK (type=6).
    """
    if not os.path.exists(_DEVICES_XML):
        return []

    try:
        tree = ET.parse(_DEVICES_XML)
        root = tree.getroot()
    except Exception as e:
        logger.warning("Erro ao ler DeviceConnectionConfig.xml: %s", e)
        return []

    dispositivos: list[dict] = []
    for fabricante in root.findall("Manufacturer"):
        nome_fab = fabricante.get("name", fabricante.get("type", "Desconhecido"))
        tipo_fab = fabricante.get("type", "")

        for grupo in fabricante.findall("DeviceGroup"):
            tipo_grupo = grupo.get("type", "")
            arquivo_antena = grupo.get("ante_file", "")

            for dev in grupo.findall("DeviceInfo"):
                nome_dev  = dev.get("name", dev.get("type", ""))
                tipo_dev  = dev.get("type", "")
                nome_anten = dev.get("ante_name", "")

                if not nome_dev:
                    continue

                dispositivos.append({
                    "fabricante":    nome_fab,
                    "tipo_fab":      tipo_fab,
                    "modelo":        nome_dev,
                    "tipo_conexao":  _tipo_conexao(tipo_grupo),
                    "tipo_gnss":     _tipo_gnss(tipo_grupo),
                    "antena":        nome_anten or arquivo_antena.replace(".hpc", ""),
                    "protocolo":     "Bluetooth SPP / USB / NTRIP",
                    "nmea":          True,
                })

    return dispositivos


def _tipo_conexao(tipo: str) -> str:
    return {"6": "RTK externo", "3": "Controlador embutido", "4": "Periférico NMEA", "5": "Demonstração"}.get(tipo, tipo)


def _tipo_gnss(tipo: str) -> str:
    return {"6": "RTK", "3": "Local", "4": "NMEA 0183"}.get(tipo, tipo)


@router.get(
    "/dispositivos",
    summary="Lista receptores GNSS suportados",
    description=(
        "Retorna todos os receptores compatíveis com o LandStar/GeoAdmin Pro, "
        "incluindo fabricante, modelo e protocolo. "
        "Fonte: DeviceConnectionConfig.xml do LandStar 8.x."
    ),
)
def listar_dispositivos(fabricante: str | None = None, rtk_only: bool = True):
    devs = _carregar_dispositivos()
    if rtk_only:
        devs = [d for d in devs if d["tipo_gnss"] == "RTK"]
    if fabricante:
        devs = [d for d in devs if fabricante.lower() in d["fabricante"].lower()]
    fabricantes = sorted({d["fabricante"] for d in devs})
    return {
        "total": len(devs),
        "fabricantes": fabricantes,
        "dispositivos": devs,
    }


# ── Geoides disponíveis ───────────────────────────────────────────────────────

@router.get(
    "/geoides",
    summary="Lista modelos de geoide IBGE disponíveis",
    description="Verifica quais modelos de correção de altitude estão instalados localmente.",
)
def listar_geoides():
    from integracoes.geoid import listar_modelos
    return {"modelos": listar_modelos()}
