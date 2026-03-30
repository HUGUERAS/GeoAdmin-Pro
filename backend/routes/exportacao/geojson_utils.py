"""
Utilitários para geração de GeoJSON.
"""

from typing import Any

from .utils import serializar_json


def geojson_poligono(
    vertices: list[dict[str, Any]] | None,
    propriedades: dict[str, Any] | None = None
) -> dict[str, Any] | None:
    """
    Converte lista de vértices para Feature GeoJSON do tipo Polygon.
    """
    if not vertices or len(vertices) < 3:
        return None
    coords = [[float(item["lon"]), float(item["lat"])] for item in vertices]
    if coords[0] != coords[-1]:
        coords.append(coords[0])
    return {
        "type": "Feature",
        "properties": propriedades or {},
        "geometry": {
            "type": "Polygon",
            "coordinates": [coords],
        },
    }


def arquivo_geojson(
    vertices: list[dict[str, Any]] | None,
    propriedades: dict[str, Any] | None = None
) -> bytes | None:
    """
    Gera arquivo GeoJSON (FeatureCollection) a partir de vértices.
    """
    feature = geojson_poligono(vertices, propriedades=propriedades)
    if not feature:
        return None
    return serializar_json(
        {
            "type": "FeatureCollection",
            "features": [feature],
        }
    )
