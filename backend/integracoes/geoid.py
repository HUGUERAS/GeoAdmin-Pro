"""
GeoAdmin Pro — Correção de altitude elipsoidal → ortométrica
============================================================
backend/integracoes/geoid.py

Converte altitude elipsoidal GPS (h) para altitude ortométrica (H):

    H = h - N

onde N é a ondulação do geoide interpolada para a posição (lat, lon).

Modelos suportados (arquivos locais de D:\\coletoraprolanddd\\outras biblioteecas\\Geoid):
  hnor2020   → hgeoHNOR_2020.gsf  (IBGE 2020, resolução 5' — recomendado INCRA)
  mapgeo2010 → sa2010.grd         (IBGE 2010, resolução ~10' — legado)

Formato GSF (hgeoHNOR_2020.gsf):
  Linha 1: lat_min
  Linha 2: lon_min
  Linha 3: lat_max
  Linha 4: lon_max
  Linha 5: ncols  (direção longitude)
  Linha 6: nrows  (direção latitude)
  Dados  : um valor float por linha, ordem row-major (lat → lon)

Algoritmo: interpolação bilinear.
Cobertura: Brasil e entorno [-34.96°..+5.96°] × [-74.96°..-30.04°]
"""

import os
import logging
from functools import lru_cache
from typing import Literal

logger = logging.getLogger("geoadmin.geoid")

# Localização dos arquivos de geoide — pode ser sobrescrita via .env
_GEOID_DIR = os.getenv(
    "GEOID_DIR",
    r"D:\coletoraprolanddd\outras biblioteecas\Geoid",
)

_ARQUIVOS: dict[str, str] = {
    "hnor2020":    os.path.join(_GEOID_DIR, "hgeoHNOR_2020.gsf"),
    "mapgeo2010":  os.path.join(_GEOID_DIR, "sa2010.grd"),
}

ModeloGeoide = Literal["hnor2020", "mapgeo2010"]


class _GradeGeoide:
    """Grade de ondulação N com interpolação bilinear."""

    __slots__ = (
        "lat_min", "lon_min", "lat_max", "lon_max",
        "nrows", "ncols", "step_lat", "step_lon",
        "_dados", "nome",
    )

    def __init__(
        self,
        lat_min: float, lon_min: float,
        lat_max: float, lon_max: float,
        nrows: int, ncols: int,
        dados: list[float],
        nome: str = "",
    ) -> None:
        self.lat_min = lat_min
        self.lon_min = lon_min
        self.lat_max = lat_max
        self.lon_max = lon_max
        self.nrows = nrows
        self.ncols = ncols
        self.step_lat = (lat_max - lat_min) / (nrows - 1)
        self.step_lon = (lon_max - lon_min) / (ncols - 1)
        self._dados = dados   # flat list row-major: [row0_col0, row0_col1, ..., rowN_colM]
        self.nome = nome

    def _v(self, row: int, col: int) -> float:
        return self._dados[row * self.ncols + col]

    def interpolar(self, lat: float, lon: float) -> float:
        """Ondulação geoidal N (metros) para (lat, lon) via bilinear."""
        import math as _math

        if not (self.lat_min <= lat <= self.lat_max):
            raise ValueError(
                f"Latitude {lat:.4f}° fora da cobertura do geoide {self.nome} "
                f"[{self.lat_min:.3f}° .. {self.lat_max:.3f}°]"
            )
        if not (self.lon_min <= lon <= self.lon_max):
            raise ValueError(
                f"Longitude {lon:.4f}° fora da cobertura do geoide {self.nome} "
                f"[{self.lon_min:.3f}° .. {self.lon_max:.3f}°]"
            )

        row_f = (lat - self.lat_min) / self.step_lat
        col_f = (lon - self.lon_min) / self.step_lon

        r0, c0 = int(row_f), int(col_f)
        r1 = min(r0 + 1, self.nrows - 1)
        c1 = min(c0 + 1, self.ncols - 1)
        dr, dc = row_f - r0, col_f - c0

        # Interpolação bilinear nos quatro vértices da célula
        # Ignora vértices NoData (N) usando apenas os vértices válidos
        pesos = [
            ((1 - dr) * (1 - dc), self._v(r0, c0)),
            (dr       * (1 - dc), self._v(r1, c0)),
            ((1 - dr) * dc,       self._v(r0, c1)),
            (dr       * dc,       self._v(r1, c1)),
        ]
        soma_p = soma_pn = 0.0
        for peso, val in pesos:
            if not _math.isnan(val):
                soma_p  += peso
                soma_pn += peso * val

        if soma_p == 0.0:
            raise ValueError(
                f"Posição ({lat:.4f}°, {lon:.4f}°) está sobre área sem dados "
                f"no geoide {self.nome} (oceano ou fora da cobertura terrestre)."
            )
        return soma_pn / soma_p


def _carregar_gsf(caminho: str, nome: str) -> _GradeGeoide:
    """
    Carrega arquivo no formato GSF (hgeoHNOR_2020.gsf).

    Cabeçalho (6 linhas):
      lat_min, lon_min, lat_max, lon_max,
      n_intervalos_lon, n_intervalos_lat

    ATENÇÃO: os dois últimos valores são o número de INTERVALOS (não de pontos).
      ncols = n_intervalos_lon + 1
      nrows = n_intervalos_lat + 1
    Exemplo: 539 intervalos → 540 pontos em longitude (resolução = 5' exato).

    Dados: um valor ASCII por linha, ordem row-major (lat_min→lat_max, lon_min→lon_max).
    Valor "N" = NoData (área fora da cobertura ou oceano) → armazenado como NaN.
    """
    import math as _math

    with open(caminho, "r", encoding="utf-8", errors="replace") as fh:
        linhas = [ln.strip() for ln in fh if ln.strip()]

    if len(linhas) < 7:
        raise ValueError(f"{caminho}: arquivo muito curto ({len(linhas)} linhas)")

    lat_min = float(linhas[0])
    lon_min = float(linhas[1])
    lat_max = float(linhas[2])
    lon_max = float(linhas[3])
    # Os valores são número de intervalos → somar 1 para obter número de pontos
    ncols   = int(linhas[4]) + 1
    nrows   = int(linhas[5]) + 1

    nan = _math.nan
    dados = []
    for v in linhas[6:]:
        if v == "N" or v == "n":
            dados.append(nan)
        else:
            dados.append(float(v))

    esperado = nrows * ncols
    if len(dados) != esperado:
        raise ValueError(
            f"{caminho}: esperado {esperado} valores ({nrows}×{ncols}), "
            f"obtido {len(dados)}"
        )

    nodata_count = sum(1 for v in dados if _math.isnan(v))
    logger.info(
        "Geoide '%s' carregado: %d×%d pts | lat [%.3f..%.3f]° | lon [%.3f..%.3f]° | "
        "resolução %.4f° (~%.1f') | nodata=%d",
        nome, nrows, ncols, lat_min, lat_max, lon_min, lon_max,
        (lat_max - lat_min) / (nrows - 1),
        (lat_max - lat_min) / (nrows - 1) * 60,
        nodata_count,
    )
    return _GradeGeoide(lat_min, lon_min, lat_max, lon_max, nrows, ncols, dados, nome)


@lru_cache(maxsize=4)
def _obter_grade(modelo: str) -> _GradeGeoide:
    """Carrega e armazena o modelo em cache (primeira chamada é lenta ~1-3 s)."""
    caminho = _ARQUIVOS.get(modelo)
    if not caminho:
        raise ValueError(
            f"Modelo desconhecido: {modelo!r}. "
            f"Modelos disponíveis: {list(_ARQUIVOS)}"
        )
    if not os.path.exists(caminho):
        raise FileNotFoundError(
            f"Arquivo de geoide não encontrado: {caminho}\n"
            f"Defina GEOID_DIR no arquivo backend/.env apontando para a pasta Geoid/."
        )
    return _carregar_gsf(caminho, modelo)


def corrigir_altitude(
    lat: float,
    lon: float,
    h_elipsoidal: float,
    modelo: ModeloGeoide = "hnor2020",
) -> dict:
    """
    Converte altitude elipsoidal GPS (h) → ortométrica (H) = h − N.

    Args:
        lat:          latitude decimal (negativo = Sul)
        lon:          longitude decimal (negativo = Oeste)
        h_elipsoidal: altitude elipsoidal em metros (saída bruta do receptor GPS/RTK)
        modelo:       "hnor2020" (HGEO HNOR 2020, recomendado INCRA)
                      "mapgeo2010" (MAPGEO 2010, legado)

    Returns:
        {
          "h_elipsoidal":  float,  # entrada (m)
          "ondulacao_N":   float,  # ondulação do geoide N (m)
          "h_ortometrica": float,  # H = h - N (m)
          "modelo":        str,
          "resolucao_arcmin": float,
        }
    """
    grade = _obter_grade(modelo)
    N = grade.interpolar(lat, lon)
    return {
        "h_elipsoidal":     round(h_elipsoidal, 4),
        "ondulacao_N":      round(N, 4),
        "h_ortometrica":    round(h_elipsoidal - N, 4),
        "modelo":           modelo,
        "resolucao_arcmin": round(grade.step_lat * 60, 2),
    }


def listar_modelos() -> list[dict]:
    """Retorna metadados dos modelos de geoide disponíveis."""
    resultado = []
    for nome, caminho in _ARQUIVOS.items():
        disponivel = os.path.exists(caminho)
        info: dict = {"modelo": nome, "disponivel": disponivel, "arquivo": caminho}
        if disponivel:
            try:
                grade = _obter_grade(nome)
                info.update({
                    "cobertura_lat": [grade.lat_min, grade.lat_max],
                    "cobertura_lon": [grade.lon_min, grade.lon_max],
                    "resolucao_arcmin": round(grade.step_lat * 60, 2),
                    "pontos_grade": grade.nrows * grade.ncols,
                })
            except Exception as e:
                info["erro"] = str(e)
        resultado.append(info)
    return resultado
