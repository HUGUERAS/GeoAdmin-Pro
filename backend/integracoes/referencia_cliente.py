from __future__ import annotations

import csv
from datetime import datetime, timezone
import io
import json
from pathlib import Path
import tempfile
import zipfile
import xml.etree.ElementTree as ET
from typing import Any

from pyproj import Transformer
from shapely.geometry import MultiPolygon, Polygon, shape
from shapely.ops import transform


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
STORE_PATH = DATA_DIR / "geometrias_referencia_cliente.json"


def _agora_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _garantir_store() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not STORE_PATH.exists():
        STORE_PATH.write_text("{}", encoding="utf-8")


def _carregar_store() -> dict[str, Any]:
    _garantir_store()
    try:
        return json.loads(STORE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _salvar_store(payload: dict[str, Any]) -> None:
    _garantir_store()
    STORE_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _selecionar_maior_poligono(geometrias: list[Polygon]) -> Polygon | None:
    if not geometrias:
        return None
    return max(geometrias, key=lambda item: item.area)


def _normalizar_poligono(polygon: Polygon) -> Polygon:
    geometria = polygon
    if not geometria.is_valid:
        geometria = geometria.buffer(0)
    if isinstance(geometria, MultiPolygon):
        geometria = _selecionar_maior_poligono(list(geometria.geoms)) or geometria.geoms[0]
    if geometria.is_empty or not isinstance(geometria, Polygon):
        raise ValueError("Nao foi possivel normalizar o poligono importado.")
    return geometria


def _vertices_from_polygon(polygon: Polygon) -> list[dict[str, float]]:
    coords = list(polygon.exterior.coords)
    if len(coords) > 1 and coords[0] == coords[-1]:
        coords = coords[:-1]
    return [{"lon": float(lon), "lat": float(lat)} for lon, lat in coords]


def _polygon_from_vertices(vertices: list[dict[str, Any]]) -> Polygon:
    coords = [(float(v["lon"]), float(v["lat"])) for v in vertices]
    if len(coords) < 3:
        raise ValueError("A geometria precisa ter ao menos 3 vertices.")
    polygon = Polygon(coords)
    return _normalizar_poligono(polygon)


def _utm_epsg(lat: float, lon: float) -> int:
    fuso = int((lon + 180) // 6) + 1
    return 32700 + fuso if lat < 0 else 32600 + fuso


def resumir_vertices(vertices: list[dict[str, Any]]) -> dict[str, Any]:
    polygon_geo = _polygon_from_vertices(vertices)
    centroide = polygon_geo.centroid
    epsg = _utm_epsg(centroide.y, centroide.x)
    transformer = Transformer.from_crs("EPSG:4326", f"EPSG:{epsg}", always_xy=True)
    polygon_m = transform(transformer.transform, polygon_geo)
    min_lon, min_lat, max_lon, max_lat = polygon_geo.bounds

    return {
        "vertices_total": len(vertices),
        "area_m2": round(float(polygon_m.area), 2),
        "area_ha": round(float(polygon_m.area) / 10000, 4),
        "perimetro_m": round(float(polygon_m.length), 2),
        "centroide": {
            "lon": round(float(centroide.x), 8),
            "lat": round(float(centroide.y), 8),
        },
        "bbox": {
            "min_lon": round(float(min_lon), 8),
            "min_lat": round(float(min_lat), 8),
            "max_lon": round(float(max_lon), 8),
            "max_lat": round(float(max_lat), 8),
        },
        "epsg_calculo": epsg,
    }


def comparar_com_perimetro_referencia(
    vertices_referencia: list[dict[str, Any]],
    vertices_tecnicos: list[dict[str, Any]] | None,
    perimetro_tipo: str | None = None,
) -> dict[str, Any] | None:
    if not vertices_tecnicos or len(vertices_tecnicos) < 3:
        return None

    polygon_ref = _polygon_from_vertices(vertices_referencia)
    polygon_tec = _polygon_from_vertices(vertices_tecnicos)

    centroide = polygon_ref.centroid
    epsg = _utm_epsg(centroide.y, centroide.x)
    transformer = Transformer.from_crs("EPSG:4326", f"EPSG:{epsg}", always_xy=True)
    ref_m = transform(transformer.transform, polygon_ref)
    tec_m = transform(transformer.transform, polygon_tec)

    inter = ref_m.intersection(tec_m)
    union = ref_m.union(tec_m)
    area_ref = float(ref_m.area)
    area_tec = float(tec_m.area)
    diferenca = abs(area_ref - area_tec)
    sobreposicao = (float(inter.area) / float(union.area) * 100) if union.area else 0.0
    diferenca_percentual = (diferenca / area_tec * 100) if area_tec else None

    if sobreposicao >= 70 and (diferenca_percentual is None or diferenca_percentual <= 25):
        status = "proxima"
    elif sobreposicao >= 35:
        status = "parcial"
    else:
        status = "divergente"

    return {
        "status": status,
        "area_referencia_ha": round(area_ref / 10000, 4),
        "area_tecnica_ha": round(area_tec / 10000, 4),
        "diferenca_area_ha": round(diferenca / 10000, 4),
        "diferenca_area_percentual": round(diferenca_percentual, 2) if diferenca_percentual is not None else None,
        "sobreposicao_percentual": round(sobreposicao, 2),
        "area_intersecao_ha": round(float(inter.area) / 10000, 4),
        "perimetro_tecnico": {
            "tipo": perimetro_tipo,
            "vertices_total": len(vertices_tecnicos),
            "vertices": vertices_tecnicos,
            "area_ha": round(area_tec / 10000, 4),
            "perimetro_m": round(float(tec_m.length), 2),
        },
    }


def parse_geojson(conteudo: str) -> list[dict[str, float]]:
    payload = json.loads(conteudo)
    candidatos: list[Polygon] = []

    def registrar(geometry: dict[str, Any] | None) -> None:
        if not geometry:
            return
        geom = shape(geometry)
        if isinstance(geom, Polygon):
            candidatos.append(_normalizar_poligono(geom))
        elif isinstance(geom, MultiPolygon):
            candidatos.extend(_normalizar_poligono(item) for item in geom.geoms if not item.is_empty)

    tipo = payload.get("type")
    if tipo == "FeatureCollection":
        for feature in payload.get("features", []):
            registrar(feature.get("geometry"))
    elif tipo == "Feature":
        registrar(payload.get("geometry"))
    else:
        registrar(payload)

    poligono = _selecionar_maior_poligono(candidatos)
    if not poligono:
        raise ValueError("Nenhum poligono valido encontrado no GeoJSON.")
    return _vertices_from_polygon(poligono)


def parse_kml(conteudo: str) -> list[dict[str, float]]:
    root = ET.fromstring(conteudo)
    coordenadas: list[list[tuple[float, float]]] = []

    for node in root.findall(".//{*}coordinates"):
        bruto = (node.text or "").strip()
        if not bruto:
            continue
        pares: list[tuple[float, float]] = []
        for trecho in bruto.replace("\n", " ").split():
            partes = trecho.split(",")
            if len(partes) < 2:
                continue
            lon = float(partes[0])
            lat = float(partes[1])
            pares.append((lon, lat))
        if len(pares) >= 3:
            coordenadas.append(pares)

    if not coordenadas:
        raise ValueError("Nenhum poligono valido encontrado no KML.")

    poligono = _normalizar_poligono(Polygon(max(coordenadas, key=len)))
    return _vertices_from_polygon(poligono)


def _parse_linhas_simples(conteudo: str) -> list[dict[str, float]]:
    vertices: list[dict[str, float]] = []
    delimitadores = [",", ";", "\t", " "]

    for linha in conteudo.splitlines():
        texto = linha.strip()
        if not texto:
            continue

        partes: list[str] | None = None
        for delimitador in delimitadores:
            tentativa = [item for item in texto.split(delimitador) if item]
            if len(tentativa) >= 2:
                partes = tentativa
                break
        if not partes:
            continue

        try:
            a = float(partes[0].replace(",", "."))
            b = float(partes[1].replace(",", "."))
        except ValueError:
            continue

        if abs(a) <= 90 and abs(b) <= 180:
            lat, lon = a, b
        elif abs(a) <= 180 and abs(b) <= 90:
            lon, lat = a, b
        else:
            raise ValueError("O TXT/CSV precisa estar em coordenadas geograficas (lat/lon ou lon/lat).")

        vertices.append({"lon": float(lon), "lat": float(lat)})

    if len(vertices) < 3:
        raise ValueError("Nao foi possivel identificar vertices suficientes no TXT/CSV.")

    return _vertices_from_polygon(_polygon_from_vertices(vertices))


def parse_csv_ou_txt(conteudo: str) -> list[dict[str, float]]:
    amostra = "\n".join(conteudo.splitlines()[:5])
    try:
        dialect = csv.Sniffer().sniff(amostra or "lon,lat")
    except Exception:
        dialect = csv.excel

    reader = csv.DictReader(io.StringIO(conteudo), dialect=dialect)
    if reader.fieldnames:
        campos = {campo.lower(): campo for campo in reader.fieldnames if campo}
        campo_lon = campos.get("lon") or campos.get("longitude") or campos.get("x") or campos.get("este")
        campo_lat = campos.get("lat") or campos.get("latitude") or campos.get("y") or campos.get("norte")
        if campo_lon and campo_lat:
            vertices = []
            for row in reader:
                try:
                    vertices.append({
                        "lon": float(str(row[campo_lon]).replace(",", ".")),
                        "lat": float(str(row[campo_lat]).replace(",", ".")),
                    })
                except Exception:
                    continue
            if len(vertices) >= 3:
                return _vertices_from_polygon(_polygon_from_vertices(vertices))

    return _parse_linhas_simples(conteudo)


def parse_shp_zip(conteudo: bytes) -> list[dict[str, float]]:
    with tempfile.TemporaryDirectory() as temp_dir:
        zip_path = Path(temp_dir) / "arquivo.zip"
        zip_path.write_bytes(conteudo)
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(temp_dir)

        shp_files = list(Path(temp_dir).rglob("*.shp"))
        if not shp_files:
            raise ValueError("Nenhum arquivo .shp encontrado dentro do zip.")

        shp_path = shp_files[0]

        try:
            import shapefile  # type: ignore

            reader = shapefile.Reader(str(shp_path))
            candidatos: list[Polygon] = []
            for shape_record in reader.shapes():
                if len(shape_record.points) < 3:
                    continue
                candidatos.append(_normalizar_poligono(Polygon(shape_record.points)))
            poligono = _selecionar_maior_poligono(candidatos)
            if not poligono:
                raise ValueError("Nenhum poligono valido encontrado no shapefile.")
            return _vertices_from_polygon(poligono)
        except ImportError:
            import geopandas as gpd

            frame = gpd.read_file(shp_path)
            candidatos = []
            for geom in frame.geometry:
                if geom is None or geom.is_empty:
                    continue
                if isinstance(geom, Polygon):
                    candidatos.append(_normalizar_poligono(geom))
                elif isinstance(geom, MultiPolygon):
                    candidatos.extend(_normalizar_poligono(item) for item in geom.geoms if not item.is_empty)

            poligono = _selecionar_maior_poligono(candidatos)
            if not poligono:
                raise ValueError("Nenhum poligono valido encontrado no shapefile.")
            return _vertices_from_polygon(poligono)


def importar_vertices_por_formato(formato: str, conteudo: str | bytes) -> list[dict[str, float]]:
    chave = formato.lower().strip()
    if chave in {"geojson", "json"}:
        return parse_geojson(str(conteudo))
    if chave == "kml":
        return parse_kml(str(conteudo))
    if chave in {"csv", "txt"}:
        return parse_csv_ou_txt(str(conteudo))
    if chave in {"shpzip", "zip"}:
        if isinstance(conteudo, str):
            raise ValueError("O SHP zip precisa ser enviado como arquivo binario.")
        return parse_shp_zip(conteudo)
    raise ValueError(f"Formato {formato} nao suportado.")


def _normalizar_registro(raw: dict[str, Any] | None) -> dict[str, Any] | None:
    if not raw:
        return None

    return {
        "id": raw.get("id"),
        "cliente_id": raw.get("cliente_id"),
        "projeto_id": raw.get("projeto_id"),
        "nome": raw.get("nome"),
        "origem_tipo": raw.get("origem_tipo"),
        "arquivo_nome": raw.get("arquivo_nome"),
        "formato": raw.get("formato"),
        "vertices": raw.get("vertices") or raw.get("vertices_json") or [],
        "resumo": raw.get("resumo") or raw.get("resumo_json") or {},
        "comparativo": raw.get("comparativo") or raw.get("comparativo_json"),
        "atualizado_em": raw.get("atualizado_em") or raw.get("updated_at"),
        "persistencia": raw.get("persistencia", "arquivo_local"),
    }


def obter_geometria_referencia(sb, cliente_id: str) -> dict[str, Any] | None:
    try:
        res = (
            sb.table("geometrias_referencia_cliente")
            .select("id, cliente_id, projeto_id, nome, origem_tipo, arquivo_nome, formato, vertices_json, resumo_json, comparativo_json, atualizado_em")
            .eq("cliente_id", cliente_id)
            .is_("deleted_at", "null")
            .order("atualizado_em", desc=True)
            .limit(1)
            .maybe_single()
            .execute()
        )
        if res.data:
            registro = _normalizar_registro({**res.data, "persistencia": "supabase"})
            if registro:
                return registro
    except Exception:
        pass

    store = _carregar_store()
    return _normalizar_registro(store.get(cliente_id))


def salvar_geometria_referencia(
    sb,
    cliente_id: str,
    projeto_id: str | None,
    nome: str | None,
    origem_tipo: str,
    formato: str,
    arquivo_nome: str | None,
    vertices: list[dict[str, Any]],
    comparativo: dict[str, Any] | None,
) -> dict[str, Any]:
    resumo = resumir_vertices(vertices)
    agora = _agora_iso()
    payload = {
        "cliente_id": cliente_id,
        "projeto_id": projeto_id,
        "nome": nome or "Referencia do cliente",
        "origem_tipo": origem_tipo,
        "arquivo_nome": arquivo_nome,
        "formato": formato,
        "vertices_json": vertices,
        "resumo_json": resumo,
        "comparativo_json": comparativo,
        "atualizado_em": agora,
    }

    try:
        existente = (
            sb.table("geometrias_referencia_cliente")
            .select("id")
            .eq("cliente_id", cliente_id)
            .is_("deleted_at", "null")
            .order("atualizado_em", desc=True)
            .limit(1)
            .maybe_single()
            .execute()
        )
        if existente.data:
            res = (
                sb.table("geometrias_referencia_cliente")
                .update(payload)
                .eq("id", existente.data["id"])
                .execute()
            )
        else:
            res = sb.table("geometrias_referencia_cliente").insert(payload).execute()

        if res.data:
            return _normalizar_registro({**res.data[0], "persistencia": "supabase"}) or {}
    except Exception:
        pass

    store = _carregar_store()
    local_payload = {
        "id": store.get(cliente_id, {}).get("id") or f"{cliente_id}-referencia",
        "cliente_id": cliente_id,
        "projeto_id": projeto_id,
        "nome": nome or "Referencia do cliente",
        "origem_tipo": origem_tipo,
        "arquivo_nome": arquivo_nome,
        "formato": formato,
        "vertices": vertices,
        "resumo": resumo,
        "comparativo": comparativo,
        "atualizado_em": agora,
        "persistencia": "arquivo_local",
    }
    store[cliente_id] = local_payload
    _salvar_store(store)
    return _normalizar_registro(local_payload) or {}


def remover_geometria_referencia(sb, cliente_id: str) -> bool:
    removido = False
    agora = _agora_iso()

    try:
        existente = (
            sb.table("geometrias_referencia_cliente")
            .select("id")
            .eq("cliente_id", cliente_id)
            .is_("deleted_at", "null")
            .order("atualizado_em", desc=True)
            .limit(1)
            .maybe_single()
            .execute()
        )
        if existente.data:
            (
                sb.table("geometrias_referencia_cliente")
                .update({"deleted_at": agora, "atualizado_em": agora})
                .eq("id", existente.data["id"])
                .execute()
            )
            removido = True
    except Exception:
        pass

    store = _carregar_store()
    if cliente_id in store:
        del store[cliente_id]
        _salvar_store(store)
        removido = True

    return removido
