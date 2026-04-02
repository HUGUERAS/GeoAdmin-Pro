"""
GeoAdmin Pro — Cálculos geodésicos

Endpoints:
  POST /geo/area                  → área e perímetro de polígono UTM
  POST /geo/converter/utm-geo     → UTM → Geográfico (SIRGAS 2000)
  POST /geo/converter/geo-utm     → Geográfico → UTM (SIRGAS 2000)
  POST /geo/intersecao            → interseção de duas semiretas
  POST /geo/distancia-ponto-linha → distância ponto a segmento de reta
  POST /geo/rotacao               → rotação de pontos UTM
  POST /geo/subdivisao            → subdivisão de polígono por área alvo
  POST /geo/altitude/corrigir     → altitude elipsoidal → ortométrica (IBGE geoide)
  GET  /geo/altitude/modelos      → lista modelos de geoide disponíveis
"""

import math
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, Request
from middleware.auth import verificar_token
from middleware.limiter import limiter
from pydantic import BaseModel
from shapely.geometry import Polygon

router = APIRouter(prefix="/geo", tags=["geo"], dependencies=[Depends(verificar_token)])


class PontoUTM(BaseModel):
    norte: float
    este: float


# ─── Inverso ──────────────────────────────────────────────────────────────────

class InversoRequest(BaseModel):
    p1: PontoUTM
    p2: PontoUTM

@router.post("/inverso")
def calcular_inverso(payload: InversoRequest):
    """Distância e azimute entre dois pontos UTM (problema inverso)."""
    dn = payload.p2.norte - payload.p1.norte
    de = payload.p2.este  - payload.p1.este
    distancia = math.sqrt(dn * dn + de * de)
    az_rad = math.atan2(de, dn)
    az_deg = math.degrees(az_rad) % 360
    # Converter graus decimais → graus/minutos/segundos
    g = int(az_deg)
    mf = (az_deg - g) * 60
    m = int(mf)
    s = round((mf - m) * 60, 1)
    return {
        "distancia_m": round(distancia, 4),
        "azimute_graus": round(az_deg, 8),
        "azimute_gms": f"{g}°{str(m).zfill(2)}'{str(s).zfill(4)}\"",
        "delta_norte": round(dn, 4),
        "delta_este": round(de, 4),
    }


# ─── Área ──────────────────────────────────────────────────────────────────────

class AreaRequest(BaseModel):
    pontos: List[PontoUTM]

@router.post("/area")
@limiter.limit("30/minute")
def calcular_area(request: Request, payload: AreaRequest):
    pts = payload.pontos
    if len(pts) < 3:
        raise HTTPException(422, "Mínimo de 3 pontos.")
    n = len(pts)
    area = 0.0
    perim = 0.0
    for i in range(n):
        j = (i + 1) % n
        area += pts[i].este * pts[j].norte - pts[j].este * pts[i].norte
        dx = pts[j].este - pts[i].este
        dy = pts[j].norte - pts[i].norte
        perim += math.sqrt(dx * dx + dy * dy)
    area = abs(area) / 2.0
    return {
        "area_m2": round(area, 4),
        "area_ha": round(area / 10_000, 6),
        "perimetro_m": round(perim, 4),
    }


# ─── Conversão UTM ↔ Geográfico ────────────────────────────────────────────────

class UtmParaGeoRequest(BaseModel):
    norte: float
    este: float
    fuso: int
    hemisferio: str = "S"

class GeoParaUtmRequest(BaseModel):
    lat: float
    lon: float
    fuso: Optional[int] = None

@router.post("/converter/utm-geo")
def utm_para_geo(payload: UtmParaGeoRequest):
    try:
        from pyproj import Transformer
        h = "+south" if payload.hemisferio.upper() == "S" else ""
        crs_utm = f"+proj=utm +zone={payload.fuso} {h} +ellps=GRS80 +no_defs"
        t = Transformer.from_crs(crs_utm, "EPSG:4674", always_xy=True)
        lon, lat = t.transform(payload.este, payload.norte)
        return {"lat": round(lat, 8), "lon": round(lon, 8), "fuso": payload.fuso}
    except Exception as exc:
        raise HTTPException(500, str(exc))

@router.post("/converter/geo-utm")
def geo_para_utm(payload: GeoParaUtmRequest):
    try:
        from pyproj import Transformer
        fuso = payload.fuso or int((payload.lon + 180) / 6) + 1
        h = "+south" if payload.lat < 0 else ""
        crs_utm = f"+proj=utm +zone={fuso} {h} +ellps=GRS80 +no_defs"
        t = Transformer.from_crs("EPSG:4674", crs_utm, always_xy=True)
        este, norte = t.transform(payload.lon, payload.lat)
        return {"norte": round(norte, 3), "este": round(este, 3), "fuso": fuso}
    except Exception as exc:
        raise HTTPException(500, str(exc))


# ─── Interseção ────────────────────────────────────────────────────────────────

class SemiretaInput(BaseModel):
    norte: float
    este: float
    azimute: float  # graus decimais

class IntersecaoRequest(BaseModel):
    p1: SemiretaInput
    p2: SemiretaInput

@router.post("/intersecao")
def calcular_intersecao(payload: IntersecaoRequest):
    a1 = math.radians(payload.p1.azimute)
    a2 = math.radians(payload.p2.azimute)
    dx1, dy1 = math.sin(a1), math.cos(a1)
    dx2, dy2 = math.sin(a2), math.cos(a2)
    det = dx1 * (-dy2) + dx2 * dy1
    if abs(det) < 1e-10:
        raise HTTPException(422, "Semiretas paralelas — sem interseção única.")
    de = payload.p2.este - payload.p1.este
    dn = payload.p2.norte - payload.p1.norte
    t1 = (de * (-dy2) + dx2 * dn) / det
    return {
        "norte": round(payload.p1.norte + t1 * dy1, 3),
        "este": round(payload.p1.este + t1 * dx1, 3),
    }


# ─── Distância Ponto-Linha ─────────────────────────────────────────────────────

class DistPontoLinhaRequest(BaseModel):
    ponto: PontoUTM
    linha_a: PontoUTM
    linha_b: PontoUTM

@router.post("/distancia-ponto-linha")
def distancia_ponto_linha(payload: DistPontoLinhaRequest):
    px, py = payload.ponto.este, payload.ponto.norte
    ax, ay = payload.linha_a.este, payload.linha_a.norte
    bx, by = payload.linha_b.este, payload.linha_b.norte
    dx, dy = bx - ax, by - ay
    len2 = dx * dx + dy * dy
    if len2 < 1e-12:
        raise HTTPException(422, "Pontos A e B são coincidentes.")
    t = ((px - ax) * dx + (py - ay) * dy) / len2
    fx = ax + t * dx
    fy = ay + t * dy
    dist = math.sqrt((px - fx) ** 2 + (py - fy) ** 2)
    return {
        "distancia_m": round(dist, 4),
        "pe_perpendicular": {"norte": round(fy, 3), "este": round(fx, 3)},
        "dentro_do_segmento": 0.0 <= t <= 1.0,
    }


# ─── Rotação ───────────────────────────────────────────────────────────────────

class RotacaoRequest(BaseModel):
    pontos: List[PontoUTM]
    angulo_graus: float
    origem: Optional[PontoUTM] = None

@router.post("/rotacao")
def rotacionar(payload: RotacaoRequest):
    if not payload.pontos:
        raise HTTPException(422, "Nenhum ponto fornecido.")
    if payload.origem:
        ox, oy = payload.origem.este, payload.origem.norte
    else:
        ox = sum(p.este for p in payload.pontos) / len(payload.pontos)
        oy = sum(p.norte for p in payload.pontos) / len(payload.pontos)
    r = math.radians(payload.angulo_graus)
    cr, sr = math.cos(r), math.sin(r)
    resultado = []
    for p in payload.pontos:
        de, dn = p.este - ox, p.norte - oy
        resultado.append({
            "este": round(ox + de * cr - dn * sr, 3),
            "norte": round(oy + de * sr + dn * cr, 3),
        })
    return {"pontos": resultado, "origem": {"este": round(ox, 3), "norte": round(oy, 3)}}


# ─── Subdivisão ────────────────────────────────────────────────────────────────

class SubdivisaoRequest(BaseModel):
    vertices: List[PontoUTM]
    area_alvo_m2: float

@router.post("/subdivisao")
@limiter.limit("15/minute")
def subdividir(request: Request, payload: SubdivisaoRequest):  # noqa: C901
    verts = payload.vertices
    n = len(verts)
    if n < 3:
        raise HTTPException(422, "Mínimo de 3 vértices.")

    def shoelace(pts) -> float:
        m = len(pts)
        s = 0.0
        for i in range(m):
            j = (i + 1) % m
            s += pts[i]["este"] * pts[j]["norte"] - pts[j]["este"] * pts[i]["norte"]
        return abs(s) / 2.0

    def to_dict(p):
        return {"este": p.este, "norte": p.norte}

    vd = [to_dict(v) for v in verts]
    area_total = shoelace(vd)

    # Validação: área não pode ser zero (polígono degenerado: vértices colineares ou duplicados)
    if area_total <= 0:
        raise HTTPException(422, "Polígono degenerado (área zero). Verifique se há vértices duplicados ou colineares.")

    # Validação: verificar auto-interseção usando shapely
    try:
        coords = [(v["este"], v["norte"]) for v in vd]
        poly = Polygon(coords)
        if not poly.is_valid:
            raise HTTPException(422, "Polígono com auto-interseção. Verifique a ordem dos vértices.")
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(422, f"Erro ao validar polígono: {exc}")

    if payload.area_alvo_m2 <= 0 or payload.area_alvo_m2 >= area_total:
        raise HTTPException(
            422,
            f"Área alvo ({payload.area_alvo_m2:.2f} m²) deve ser entre 0 e {area_total:.2f} m².",
        )

    for k in range(1, n - 1):
        def sub_area(t: float, k=k) -> float:
            px = vd[k]["este"] + t * (vd[(k + 1) % n]["este"] - vd[k]["este"])
            py = vd[k]["norte"] + t * (vd[(k + 1) % n]["norte"] - vd[k]["norte"])
            sub = vd[: k + 1] + [{"este": px, "norte": py}]
            return shoelace(sub)

        a0, a1 = sub_area(0.0), sub_area(1.0)
        alvo = payload.area_alvo_m2
        if not (min(a0, a1) <= alvo <= max(a0, a1)):
            continue
        lo, hi = 0.0, 1.0
        for _ in range(60):
            mid = (lo + hi) / 2.0
            if sub_area(mid) < alvo:
                lo = mid
            else:
                hi = mid
        t_sol = (lo + hi) / 2.0
        px = vd[k]["este"] + t_sol * (vd[(k + 1) % n]["este"] - vd[k]["este"])
        py = vd[k]["norte"] + t_sol * (vd[(k + 1) % n]["norte"] - vd[k]["norte"])
        return {
            "ponto_corte": {"norte": round(py, 3), "este": round(px, 3)},
            "aresta_inicio": k,
            "aresta_fim": (k + 1) % n,
            "area_parte1_m2": round(alvo, 4),
            "area_parte2_m2": round(area_total - alvo, 4),
            "area_total_m2": round(area_total, 4),
        }

    raise HTTPException(422, "Não foi possível encontrar a linha de divisão. Verifique a orientação dos vértices (anti-horário).")


# ─── Correção de Altitude (Geoide IBGE) ────────────────────────────────────────

class AltitudeCorrRequest(BaseModel):
    lat: float            # latitude decimal (negativo = Sul)
    lon: float            # longitude decimal (negativo = Oeste)
    h_elipsoidal: float   # altitude elipsoidal GPS em metros
    modelo: str = "hnor2020"  # "hnor2020" | "mapgeo2010"

@router.post("/altitude/corrigir",
             summary="Altitude elipsoidal → ortométrica",
             description=(
                 "Converte a altitude elipsoidal do receptor GPS/RTK para altitude "
                 "ortométrica (referência ao geoide IBGE). Usa o modelo HGEO HNOR 2020 "
                 "por padrão (recomendado pelo INCRA para georreferenciamento).\n\n"
                 "**Fórmula:** H = h − N  onde N é a ondulação do geoide."
             ))
def corrigir_altitude_endpoint(payload: AltitudeCorrRequest):
    try:
        from integracoes.geoid import corrigir_altitude
        return corrigir_altitude(
            lat=payload.lat,
            lon=payload.lon,
            h_elipsoidal=payload.h_elipsoidal,
            modelo=payload.modelo,  # type: ignore[arg-type]
        )
    except FileNotFoundError as exc:
        raise HTTPException(404, str(exc))
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    except Exception as exc:
        raise HTTPException(500, f"Erro ao aplicar geoide: {exc}")


@router.get("/altitude/modelos",
            summary="Lista modelos de geoide disponíveis")
def listar_modelos_geoide():
    from integracoes.geoid import listar_modelos
    return {"modelos": listar_modelos()}
