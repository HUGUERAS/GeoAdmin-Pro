"""
GeoAdmin Pro — Importação Genérica e Unificada de Pontos Topográficos
===================================================================
backend/routes/importar_generico.py

Este módulo expõe o endpoint POST /importar/pontos/{projeto_id} para que o aplicativo
móvel ou a versão desktop possam ingerir de forma padronizada pontos a partir de arquivos
LandStar TXT/CSV, Métrica TOPO TXT/CSV, DXF ou KML.
"""

import os
import re
import math
import logging
import tempfile
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple

from fastapi import APIRouter, HTTPException, UploadFile, File, Query, Depends
from middleware.auth import verificar_token
from pydantic import BaseModel

router = APIRouter(prefix="/importar", tags=["Importação"], dependencies=[Depends(verificar_token)])
logger = logging.getLogger("geoadmin.importar_generico")


class ResultadoImportacao(BaseModel):
    projeto_id: str
    total_lidos: int
    inseridos: int
    duplicados: int
    erros_parse: List[str]
    erros_insert: List[str]
    pontos: List[dict]  # preview dos pontos processados/inseridos


# ── Tradução do Status GNSS ───────────────────────────────────────────────────
def parse_status_gnss(status_raw: str) -> str:
    status_raw = status_raw.upper().strip()
    if "FIX" in status_raw:
        return "Fixo"
    elif "FLOAT" in status_raw:
        return "Float"
    elif "SINGLE" in status_raw or "AUTON" in status_raw:
        return "Autônomo"
    return "Fixo"


# ── Extração de Qualidade do GNSS a partir da Linha de Log ───────────────────
def extrair_metadados_linha(linha: str) -> Dict[str, Any]:
    meta = {}
    status_match = re.search(r"STATUS:([A-Za-z]+)", linha, re.IGNORECASE)
    sats_match = re.search(r"SATS:(\d+)", linha, re.IGNORECASE)
    pdop_match = re.search(r"PDOP:([\d.]+)", linha, re.IGNORECASE)
    hrms_match = re.search(r"(?:HRMS|ERMS|SIGMA_E):([\d.]+)", linha, re.IGNORECASE)
    vrms_match = re.search(r"(?:VRMS|SIGMA_U|SIGMA_Z):([\d.]+)", linha, re.IGNORECASE)
    nrms_match = re.search(r"(?:NRMS|SIGMA_N):([\d.]+)", linha, re.IGNORECASE)

    if status_match:
        meta["status_gnss"] = parse_status_gnss(status_match.group(1))
    else:
        meta["status_gnss"] = "Fixo"

    if sats_match:
        meta["satelites"] = int(sats_match.group(1))
    else:
        meta["satelites"] = 0

    if pdop_match:
        meta["pdop"] = float(pdop_match.group(1))
    else:
        meta["pdop"] = 0.0

    if hrms_match:
        meta["sigma_e"] = float(hrms_match.group(1))
    else:
        meta["sigma_e"] = 0.0

    if nrms_match:
        meta["sigma_n"] = float(nrms_match.group(1))
    elif hrms_match:
        meta["sigma_n"] = float(hrms_match.group(1))
    else:
        meta["sigma_n"] = 0.0

    if vrms_match:
        meta["sigma_u"] = float(vrms_match.group(1))
    else:
        meta["sigma_u"] = 0.0

    return meta


# ── Parser TXT/CSV (LandStar / Métrica TOPO) ──────────────────────────────────
def parse_txt_topografia(caminho: Path) -> List[Dict[str, Any]]:
    pontos = []

    # 1. Testar se é formato LandStar 8.x (20 campos com DMS e vírgulas)
    landstar_match = False
    try:
        with open(caminho, encoding="utf-8", errors="ignore") as f:
            for _ in range(5):
                linha = f.readline()
                if not linha:
                    break
                if "°" in linha and ("′" in linha or "'" in linha) and len(linha.split(",")) >= 15:
                    landstar_match = True
                    break
    except Exception:
        pass

    if landstar_match:
        try:
            from integracoes.parser_landstar import parse_arquivo
            with open(caminho, encoding="utf-8", errors="ignore") as f:
                conteudo = f.read()
                pontos_ls, erros = parse_arquivo(conteudo)
                if pontos_ls:
                    for p in pontos_ls:
                        pontos.append({
                            "nome":        p.nome,
                            "codigo":      p.codigo or "TP",
                            "norte":       p.norte,
                            "este":        p.este,
                            "altitude_m":  p.cota,
                            "lat":         p.lat,
                            "lon":         p.lon,
                            "status_gnss": p.status_gnss,
                            "satelites":   p.satelites,
                            "pdop":        p.pdop,
                            "sigma_e":     p.sigma_e,
                            "sigma_n":     p.sigma_n,
                            "sigma_u":     p.sigma_u,
                            "ja_geo":      True
                        })
                    return pontos
        except Exception as exc:
            logger.warning(f"Aviso no parser LandStar: {exc}. Usando parser flexível...")

    # 2. Parser Flexível Inteligente (Métrica clássico / resplendor.txt estendido)
    try:
        with open(caminho, encoding="latin-1", errors="ignore") as f:
            for num_linha, linha in enumerate(f, start=1):
                linha = linha.strip()
                if not linha or linha[0] in ("*", "#", ";", "["):
                    continue

                separador = ";" if ";" in linha else ","
                campos = [x.strip() for x in linha.split(separador)]

                if len(campos) < 3:
                    continue

                encontrou_coordenadas = False
                norte, este, cota = 0.0, 0.0, 0.0
                idx_norte, idx_este = -1, -1

                for i in range(len(campos) - 1):
                    try:
                        val1 = float(campos[i])
                        val2 = float(campos[i+1])

                        if (6_000_000.0 < val1 < 10_500_000.0) and (100_000.0 < val2 < 900_000.0):
                            norte, este = val1, val2
                            idx_norte, idx_este = i, i+1
                            encontrou_coordenadas = True
                            break
                        elif (100_000.0 < val1 < 900_000.0) and (6_000_000.0 < val2 < 10_500_000.0):
                            este, norte = val1, val2
                            idx_este, idx_norte = i, i+1
                            encontrou_coordenadas = True
                            break
                    except ValueError:
                        continue

                if not encontrou_coordenadas:
                    continue

                nome = campos[0] if campos[0] else f"PT_L{num_linha:03d}"
                codigo = "TP"
                if len(campos) > 1 and idx_norte > 1 and idx_este > 1:
                    if campos[1] and not campos[1].replace(".", "", 1).isdigit():
                        codigo = campos[1]

                idx_cota = max(idx_norte, idx_este) + 1
                if idx_cota < len(campos):
                    try:
                        cota = float(campos[idx_cota])
                    except ValueError:
                        cota = 0.0

                meta = extrair_metadados_linha(linha)

                pontos.append({
                    "nome":        nome,
                    "codigo":      codigo,
                    "norte":       norte,
                    "este":        este,
                    "altitude_m":  cota,
                    "status_gnss": meta.get("status_gnss", "Fixo"),
                    "satelites":   meta.get("satelites", 0),
                    "pdop":        meta.get("pdop", 0.0),
                    "sigma_e":     meta.get("sigma_e", 0.0),
                    "sigma_n":     meta.get("sigma_n", 0.0),
                    "sigma_u":     meta.get("sigma_u", 0.0),
                    "ja_geo":      False
                })
    except Exception as exc:
        logger.error(f"Erro ao parsear TXT/CSV: {exc}")

    return pontos


# ── Parser KML ────────────────────────────────────────────────────────────────
def parse_kml(caminho: Path) -> List[Dict[str, Any]]:
    NS = "http://www.opengis.net/kml/2.2"
    pontos = []
    try:
        tree = ET.parse(caminho)
        root = tree.getroot()
        i = 0
        for pm in root.iter(f"{{{NS}}}Placemark"):
            nome_el = pm.find(f"{{{NS}}}name")
            nome = (nome_el.text or "").strip() if nome_el is not None else ""
            if not nome:
                nome = f"PT_KML_{i+1:03d}"

            coord_el = pm.find(f".//{{{NS}}}coordinates")
            if coord_el is None or not coord_el.text:
                continue

            try:
                parts = coord_el.text.strip().split(",")
                lon, lat = float(parts[0]), float(parts[1])
                alt = float(parts[2]) if len(parts) > 2 else 0.0

                if not (-75.0 < lon < -28.0 and -35.0 < lat < 6.0):
                    continue

                pontos.append({
                    "nome":        nome,
                    "codigo":      "KML",
                    "altitude_m":  round(alt, 3),
                    "lon":         round(lon, 9),
                    "lat":         round(lat, 9),
                    "status_gnss": "Fixo",
                    "satelites":   0,
                    "pdop":        0.0,
                    "sigma_e":     0.0,
                    "sigma_n":     0.0,
                    "sigma_u":     0.0,
                    "ja_geo":      True,
                })
                i += 1
            except (ValueError, IndexError):
                pass
    except Exception as exc:
        logger.error(f"Erro ao parsear KML: {exc}")
    return pontos


# ── Parser DXF ────────────────────────────────────────────────────────────────
def parse_dxf(caminho: Path) -> List[Dict[str, Any]]:
    pontos = []
    try:
        import ezdxf
        doc = ezdxf.readfile(str(caminho))
        msp = doc.modelspace()

        textos: List[Tuple[float, float, str]] = []
        for ent in msp:
            if ent.dxftype() in ("TEXT", "MTEXT"):
                try:
                    ins = ent.dxf.insert
                    txt = (ent.dxf.text if ent.dxftype() == "TEXT" else ent.plain_mtext()).strip()
                    if txt:
                        textos.append((ins.x, ins.y, txt))
                except Exception:
                    pass

        def buscar_nome_proximo(x: float, y: float, tol: float = 2.0) -> str:
            melhor, dist_min = "", tol
            for tx, ty, txt in textos:
                d = math.hypot(tx - x, ty - y)
                if d < dist_min:
                    dist_min, melhor = d, txt
            return melhor

        i = 0
        for ent in msp:
            if ent.dxftype() != "POINT":
                continue
            try:
                loc = ent.dxf.location
                x, y, z = loc.x, loc.y, loc.z

                if not (6_000_000.0 < y < 10_500_000.0 and 100_000.0 < x < 900_000.0):
                    continue

                nome = buscar_nome_proximo(x, y) or f"PT_DXF_{i+1:03d}"
                pontos.append({
                    "nome":        nome,
                    "codigo":      "CAD",
                    "norte":       y,
                    "este":        x,
                    "altitude_m":  round(z, 3),
                    "status_gnss": "Fixo",
                    "satelites":   0,
                    "pdop":        0.0,
                    "sigma_e":     0.0,
                    "sigma_n":     0.0,
                    "sigma_u":     0.0,
                    "ja_geo":      False,
                })
                i += 1
            except Exception:
                pass
    except Exception as exc:
        logger.warning(f"Aviso no parser DXF (ezdxf): {exc}")
    return pontos


# ── Conversor UTM → Geográfico (SIRGAS 2000) ──────────────────────────────────
_transformers: Dict[str, Any] = {}

def converter_utm_para_geo(este: float, norte: float, zona_utm: str = "23S") -> Tuple[float, float]:
    try:
        from pyproj import Transformer
    except ImportError:
        # Fallback aproximado se pyproj não estiver presente
        return -47.9292, -15.7801

    zona_utm = zona_utm.upper()
    if zona_utm not in _transformers:
        match = re.search(r"(\d+)([NS])", zona_utm)
        if not match:
            fuso, hem = 23, "S"
        else:
            fuso, hem = int(match.group(1)), match.group(2)

        epsg = (31960 + fuso) if hem == "S" else (31960 + fuso - 30)
        _transformers[zona_utm] = Transformer.from_crs(epsg, 4674, always_xy=True)

    lon, lat = _transformers[zona_utm].transform(este, norte)
    return round(lon, 9), round(lat, 9)


# ── Rota Principal de Importação Genérica ──────────────────────────────────────
@router.post(
    "/pontos/{projeto_id}",
    response_model=ResultadoImportacao,
    summary="Importar pontos (TXT/CSV/KML/DXF)",
    description=(
        "Endpoint unificado para realizar o upload e ingestão de pontos a partir de "
        "arquivos de medição bruta ou desenhos topográficos (LandStar, Métrica TOPO, DXF ou KML)."
    ),
)
async def importar_pontos_genericos(
    projeto_id: str,
    arquivo: UploadFile = File(..., description="Arquivo de pontos topográficos"),
    aplicar_geoide: bool = Query(True, description="Corrigir altitude usando o geoide"),
    apenas_preview: bool = Query(False, description="Apenas simula o parse e conversões"),
):
    from main import get_supabase

    # 1. Validar tamanho máximo (15MB)
    LIMITE_TAMANHO_BYTES = 15 * 1024 * 1024
    conteudo_bytes = await arquivo.read()
    if len(conteudo_bytes) > LIMITE_TAMANHO_BYTES:
        raise HTTPException(
            status_code=413,
            detail={
                "erro": f"Arquivo excede o limite de 15MB (tamanho: {len(conteudo_bytes)/(1024*1024):.2f}MB)",
                "codigo": 413
            }
        )

    # 2. Obter fuso UTM do projeto cadastrado
    sb = get_supabase()
    res_proj = sb.table("projetos").select("id, nome, zona_utm").eq("id", projeto_id).maybe_single().execute()
    if not res_proj.data:
        raise HTTPException(404, f"Projeto com ID '{projeto_id}' não encontrado no banco de dados.")

    projeto = res_proj.data
    zona_utm = (projeto.get("zona_utm") or "23S").upper()

    # 3. Salvar temporariamente para rodar os parsers locais
    nome_extensao = Path(arquivo.filename).suffix.lower()
    pontos_parsed = []
    erros_parse = []

    with tempfile.NamedTemporaryFile(suffix=nome_extensao, delete=False) as tmp:
        tmp.write(conteudo_bytes)
        caminho_tmp = Path(tmp.name)

    try:
        if nome_extensao in (".txt", ".csv"):
            pontos_parsed = parse_txt_topografia(caminho_tmp)
        elif nome_extensao == ".kml":
            pontos_parsed = parse_kml(caminho_tmp)
        elif nome_extensao == ".dxf":
            pontos_parsed = parse_dxf(caminho_tmp)
        else:
            erros_parse.append(f"Extensão de arquivo '{nome_extensao}' não é suportada.")
    finally:
        # Garante a limpeza do arquivo temporário
        if caminho_tmp.exists():
            os.remove(caminho_tmp)

    if not pontos_parsed:
        raise HTTPException(
            422,
            {
                "erro": "Nenhum ponto válido encontrado no arquivo ou formato incompatível.",
                "erros_parse": erros_parse
            }
        )

    # 4. Processar Payloads com Conversões e Metadados
    agora = datetime.now(timezone.utc).isoformat()
    pontos_para_inserir = []

    for p in pontos_parsed:
        try:
            if p.get("ja_geo"):
                lon, lat = p["lon"], p["lat"]
            else:
                lon, lat = converter_utm_para_geo(p["este"], p["norte"], zona_utm)

            pontos_para_inserir.append({
                "projeto_id":  projeto_id,
                "nome":        p["nome"],
                "codigo":      p["codigo"],
                "norte":       p.get("norte"),
                "este":        p.get("este"),
                "cota":        p["altitude_m"],
                "altitude_m":  p["altitude_m"],
                "lat":         lat,
                "lon":         lon,
                "status_gnss": p["status_gnss"],
                "satelites":   p["satelites"],
                "pdop":        p["pdop"],
                "sigma_e":     p["sigma_e"],
                "sigma_n":     p["sigma_n"],
                "sigma_u":     p["sigma_u"],
                "origem":      "gnss",
                "coordenada":  f"SRID=4326;POINT({lon} {lat})",
                "criado_em":   agora,
            })
        except Exception as exc:
            erros_parse.append(f"Erro de conversão no ponto {p.get('nome')}: {exc}")

    if apenas_preview:
        return ResultadoImportacao(
            projeto_id=projeto_id,
            total_lidos=len(pontos_parsed),
            inseridos=0,
            duplicados=0,
            erros_parse=erros_parse,
            erros_insert=[],
            pontos=pontos_para_inserir
        )

    # 5. Inserir no Supabase tratando duplicatas
    inseridos = 0
    duplicados = 0
    erros_insert = []
    pontos_resultado = []

    for ponto in pontos_para_inserir:
        try:
            # Evita duplicar o mesmo nome de ponto dentro do projeto
            existente = (
                sb.table("pontos")
                .select("id")
                .eq("projeto_id", projeto_id)
                .eq("nome", ponto["nome"])
                .maybe_single()
                .execute()
            )
            if existente.data:
                duplicados += 1
                continue

            res = sb.table("pontos").insert(ponto).execute()
            if res.data:
                inseridos += 1
                pontos_resultado.append(res.data[0])
            else:
                erros_insert.append(f"Ponto '{ponto['nome']}': Sem retorno de sucesso da inserção.")
        except Exception as exc:
            erros_insert.append(f"Ponto '{ponto['nome']}': {exc}")

    return ResultadoImportacao(
        projeto_id=projeto_id,
        total_lidos=len(pontos_parsed),
        inseridos=inseridos,
        duplicados=duplicados,
        erros_parse=erros_parse,
        erros_insert=erros_insert,
        pontos=pontos_resultado
    )
