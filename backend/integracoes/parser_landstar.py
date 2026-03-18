"""
GeoAdmin Pro — Parser LandStar (CHC / HuaceNav)

Lê o formato TXT exportado pelo LandStar 8.x e converte para o
schema interno do GeoAdmin Pro (POST /pontos).

Formato do arquivo (20 campos separados por vírgula):
  [seq_ou_nome], [codigo],
  norte_utm, este_utm, alt_elip,
  lat_dms, lon_dms, alt_ort,
  lat_dms_antena, lon_dms_antena,
  satelites, pdop, hdop, vdop, status,
  sigma_e, sigma_n, sigma_u, sigma_2d, sigma_3d

Observação: a primeira linha costuma ser o ponto base (status=Autônomo),
sem número de sequência — campo 0 contém o nome (ex: "M45").
As demais linhas têm seq numérica no campo 0 e código da feição no campo 1.
"""

import logging
import re
from typing import Optional

from pydantic import BaseModel

logger = logging.getLogger(__name__)

# Regex para DMS: '022°39′06.09099″S' ou variantes com ' e "
_DMS_RE = re.compile(r"(\d+)[°](\d+)[′']([\d.]+)[″\"]([NSEWnsew])")

_MIN_CAMPOS = 18  # mínimo aceitável (descarta sigma_2d e sigma_3d se ausentes)


def _dms_para_decimal(dms: str) -> float:
    """Converte string DMS para graus decimais (negativo = Sul/Oeste)."""
    m = _DMS_RE.search(dms)
    if not m:
        raise ValueError(f"Formato DMS não reconhecido: {dms!r}")
    graus = int(m.group(1))
    minutos = int(m.group(2))
    segundos = float(m.group(3))
    hem = m.group(4).upper()
    decimal = graus + minutos / 60.0 + segundos / 3600.0
    if hem in ("S", "W"):
        decimal = -decimal
    return round(decimal, 9)


class PontoImportado(BaseModel):
    """Schema de saída do parser — compatível com POST /pontos."""

    nome: str
    codigo: str
    norte: float          # UTM norte (m)
    este: float           # UTM este (m)
    cota: float           # altitude ortométrica (m)
    lat: float            # graus decimais, negativo = Sul
    lon: float            # graus decimais, negativo = Oeste
    status_gnss: str      # "Fixo" | "Autônomo"
    satelites: int
    pdop: float
    sigma_e: float        # desvio padrão Este (m)
    sigma_n: float        # desvio padrão Norte (m)
    sigma_u: float        # desvio padrão Up/vertical (m)


def parse_linha(linha: str) -> Optional[PontoImportado]:
    """
    Parseia uma linha do arquivo LandStar.
    Retorna None para linhas em branco ou de cabeçalho.
    Lança ValueError se a linha tem formato inválido.
    """
    linha = linha.strip()
    if not linha or linha.startswith(("#", "*")):
        return None

    campos = linha.split(",")

    if len(campos) < _MIN_CAMPOS:
        raise ValueError(f"Esperado >= {_MIN_CAMPOS} campos, encontrado {len(campos)}")

    # Campo 0: número de sequência (int) ou nome do ponto (str, ex: "M45")
    # Campo 1: código da feição (TN, CER, BMB…) — pode estar vazio no ponto base
    if campos[0].lstrip("-").isdigit():
        seq = int(campos[0])
        codigo = campos[1].strip() if campos[1].strip() else "TP"
        nome = campos[1].strip() if campos[1].strip() else f"PT{seq:04d}"
    else:
        nome = campos[0].strip()
        codigo = campos[1].strip() if campos[1].strip() else "TP"

    norte   = float(campos[2])
    este    = float(campos[3])
    # campos[4] = altitude elipsoidal (não armazenada aqui)
    lat     = _dms_para_decimal(campos[5])
    lon     = _dms_para_decimal(campos[6])
    alt_ort = float(campos[7])
    # campos[8..9] = lat/lon da antena (fase de processamento, ignorado)
    sats    = int(float(campos[10]))   # float para tolerar "2.0"
    pdop    = float(campos[11])
    # campos[12] = HDOP, campos[13] = VDOP (não solicitados)
    status  = campos[14].strip()
    sigma_e = float(campos[15])
    sigma_n = float(campos[16])
    sigma_u = float(campos[17])
    # campos[18] = σ2D, campos[19] = σ3D (calculados, não armazenados)

    return PontoImportado(
        nome=nome,
        codigo=codigo,
        norte=norte,
        este=este,
        cota=alt_ort,
        lat=lat,
        lon=lon,
        status_gnss=status,
        satelites=sats,
        pdop=pdop,
        sigma_e=sigma_e,
        sigma_n=sigma_n,
        sigma_u=sigma_u,
    )


def parse_arquivo(conteudo: str) -> tuple[list[PontoImportado], list[str]]:
    """
    Parseia o conteúdo completo de um arquivo TXT LandStar.

    Retorna:
        pontos  — lista de PontoImportado parseados com sucesso
        erros   — lista de mensagens de erro por linha (pode estar vazia)
    """
    pontos: list[PontoImportado] = []
    erros: list[str] = []

    for i, linha in enumerate(conteudo.splitlines(), start=1):
        try:
            ponto = parse_linha(linha)
            if ponto is not None:
                pontos.append(ponto)
        except Exception as exc:
            erros.append(f"Linha {i}: {exc}")

    if erros:
        logger.warning("parser_landstar: %d erro(s) encontrado(s)", len(erros))

    return pontos, erros
