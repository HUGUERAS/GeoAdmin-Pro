#!/usr/bin/env python3
"""
GeoAdmin Pro — Importação em lote de pontos das pastas de trabalho

Formatos suportados:
  - TXT  Metrica TOPO (4 ou 5 campos CSV)  -> UTM, precisa conversao
  - KML  Google Earth / software geodesico  -> lon/lat direto
  - DXF  AutoCAD / Metrica exportado        -> UTM, precisa conversao

Uso:
    cd backend
    pip install pyproj ezdxf
    python scripts/importar_pontos.py            # importa tudo
    python scripts/importar_pontos.py --dry-run  # so mostra o que faria
    python scripts/importar_pontos.py --projeto "abadia"  # so um projeto
"""

import os, sys, argparse
from pathlib import Path

# Garante que o backend/ está no path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

from supabase import create_client

PASTA_BASE   = Path(r"D:\pastas de trabalho")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
BATCH_SIZE   = 500


# ── Parser ───────────────────────────────────────────────────────────────────

def parse_metrica(caminho: Path) -> list[dict]:
    """
    Lê arquivo Métrica TOPO (4 ou 5 campos) e retorna lista de pontos.
    Formato: nome, [codigo,] norte, este, altitude
    """
    pontos = []
    try:
        with open(caminho, encoding="latin-1", errors="ignore") as f:
            for linha in f:
                linha = linha.strip()
                if not linha or linha[0] in ("*", "#", ";", "["):
                    continue
                c = [x.strip() for x in linha.split(",")]
                try:
                    if len(c) == 5:
                        nome, cod, norte, este, alt = c
                    elif len(c) == 4:
                        nome, norte, este, alt = c
                        cod = ""
                    else:
                        continue

                    n, e, a = float(norte), float(este), float(alt)

                    # Valida faixa UTM Brasil
                    if not (6_000_000 < n < 10_500_000 and 100_000 < e < 900_000):
                        continue

                    pontos.append({
                        "nome":       nome,
                        "codigo":     cod or None,
                        "norte":      n,
                        "este":       e,
                        "altitude_m": a,
                    })
                except ValueError:
                    pass
    except Exception:
        pass
    return pontos


def parse_kml(caminho: Path) -> list[dict]:
    """
    Le KML e retorna pontos ja em coordenadas geograficas (lon, lat).
    Pontos retornados tem ja_geo=True.
    """
    import xml.etree.ElementTree as ET
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
                nome = f"PT{i+1:04d}"

            coord_el = pm.find(f".//{{{NS}}}coordinates")
            if coord_el is None or not coord_el.text:
                continue

            try:
                parts = coord_el.text.strip().split(",")
                lon, lat = float(parts[0]), float(parts[1])
                alt = float(parts[2]) if len(parts) > 2 else 0.0

                # Valida faixa Brasil
                if not (-75.0 < lon < -28.0 and -35.0 < lat < 6.0):
                    continue

                pontos.append({
                    "nome":       nome,
                    "codigo":     None,
                    "altitude_m": round(alt, 3),
                    "lon":        round(lon, 9),
                    "lat":        round(lat, 9),
                    "ja_geo":     True,
                })
                i += 1
            except (ValueError, IndexError):
                pass
    except Exception:
        pass
    return pontos


def parse_dxf(caminho: Path) -> list[dict]:
    """
    Le DXF (AutoCAD / Metrica exportado) e retorna pontos em UTM.
    Pontos retornados tem ja_geo=False.
    """
    pontos = []
    try:
        import ezdxf
        doc = ezdxf.readfile(str(caminho))
        msp = doc.modelspace()

        # Coleta TEXT/MTEXT para tentar associar nomes aos pontos por posicao
        textos: list[tuple[float, float, str]] = []
        for ent in msp:
            if ent.dxftype() in ("TEXT", "MTEXT"):
                try:
                    ins = ent.dxf.insert
                    txt = (ent.dxf.text if ent.dxftype() == "TEXT"
                           else ent.plain_mtext()).strip()
                    if txt:
                        textos.append((ins.x, ins.y, txt))
                except Exception:
                    pass

        def nome_proximo(x: float, y: float, tol: float = 2.0) -> str:
            melhor, dist_min = "", tol
            for tx, ty, txt in textos:
                d = ((tx - x) ** 2 + (ty - y) ** 2) ** 0.5
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

                # Valida faixa UTM Brasil
                if not (6_000_000 < y < 10_500_000 and 100_000 < x < 900_000):
                    continue

                nome = nome_proximo(x, y) or f"PT{i+1:04d}"
                pontos.append({
                    "nome":       nome,
                    "codigo":     None,
                    "norte":      y,
                    "este":       x,
                    "altitude_m": round(z, 3),
                    "ja_geo":     False,
                })
                i += 1
            except Exception:
                pass
    except Exception:
        pass
    return pontos


def melhor_arquivo(pasta: Path) -> tuple[Path | None, list[dict]]:
    """
    Encontra o arquivo de pontos mais completo na pasta.
    Suporta TXT (Metrica), KML e DXF.
    Prioriza arquivos com 'pont' no nome e mais linhas validas.
    """
    penalizar = {"memorial", "config", "log", "planilha", "equiv",
                 "vertices", "vertex", "rinex", "relatorio"}
    candidatos = []

    for root, _, files in os.walk(pasta):
        for f in files:
            fl = f.lower()
            path = Path(root) / f

            if fl.endswith(".txt"):
                pontos = parse_metrica(path)
            elif fl.endswith(".kml"):
                pontos = parse_kml(path)
            elif fl.endswith(".dxf"):
                pontos = parse_dxf(path)
            else:
                continue

            if not pontos:
                continue

            score = len(pontos)
            if "pont" in fl:
                score += 10_000
            for p in penalizar:
                if p in fl:
                    score -= 5_000
                    break
            # TXT Metrica preferido; KML/DXF como fallback
            if fl.endswith(".kml") or fl.endswith(".dxf"):
                score -= 200
            candidatos.append((score, path, pontos))

    if not candidatos:
        return None, []
    candidatos.sort(reverse=True)
    _, path, pontos = candidatos[0]
    return path, pontos


# ── Conversão UTM → Geográfico ────────────────────────────────────────────

_transformers: dict = {}

def utm_para_geo(este: float, norte: float, zona_utm: str = "23S"):
    """Converte UTM SIRGAS 2000 → graus decimais (lon, lat)."""
    from pyproj import Transformer

    zona_utm = zona_utm.upper()
    if zona_utm not in _transformers:
        num = int("".join(c for c in zona_utm if c.isdigit()))
        hem = zona_utm[-1]
        # SIRGAS 2000 UTM: zonas sul 31978-31985, zonas norte 31972-31977
        epsg = (31960 + num) if hem == "S" else (31960 + num - 30)
        _transformers[zona_utm] = Transformer.from_crs(epsg, 4674, always_xy=True)

    lon, lat = _transformers[zona_utm].transform(este, norte)
    return round(lon, 9), round(lat, 9)


# ── Import principal ──────────────────────────────────────────────────────

def importar_projeto(sb, projeto: dict, dry_run: bool) -> int:
    nome  = projeto["nome"]
    zona  = (projeto.get("zona_utm") or "23S").upper()
    pasta = PASTA_BASE / nome

    if not pasta.exists():
        print(f"  SKIP  {nome!r} — pasta não encontrada")
        return 0

    # Verifica se já tem pontos
    res = sb.table("pontos").select("id", count="exact") \
            .eq("projeto_id", projeto["id"]).limit(1).execute()
    if res.count and res.count > 0:
        print(f"  SKIP  {nome!r} — já tem {res.count} pontos")
        return 0

    arquivo, pontos = melhor_arquivo(pasta)
    if not pontos:
        print(f"  VAZIO {nome!r} — nenhum arquivo de pontos válido")
        return 0

    print(f"  {'DRY ' if dry_run else '    '}{nome!r}: "
          f"{len(pontos)} pts de '{arquivo.name}'", end="")

    if dry_run:
        print()
        return 0

    # Converte e insere
    batch, erros = [], 0
    for p in pontos:
        try:
            if p.get("ja_geo"):
                lon, lat = p["lon"], p["lat"]
            else:
                lon, lat = utm_para_geo(p["este"], p["norte"], zona)
            batch.append({
                "projeto_id": projeto["id"],
                "nome":       p["nome"],
                "codigo":     p["codigo"],
                "altitude_m": p["altitude_m"],
                "coordenada": f"SRID=4674;POINT({lon} {lat})",
            })
        except Exception as ex:
            if erros == 0:
                print(f"\n    ERRO EXEMPLO: {p} -> {ex}")
            erros += 1

    for i in range(0, len(batch), BATCH_SIZE):
        sb.table("pontos").insert(batch[i:i + BATCH_SIZE]).execute()

    print(f" -> {len(batch)} importados" + (f", {erros} erro(s)" if erros else ""))
    return len(batch)


def main():
    parser = argparse.ArgumentParser(description="Importa pontos para o GeoAdmin Pro")
    parser.add_argument("--dry-run",  action="store_true",
                        help="Só mostra o que seria importado, sem gravar")
    parser.add_argument("--projeto",  type=str, default=None,
                        help="Importa apenas este projeto (pelo nome)")
    args = parser.parse_args()

    if not SUPABASE_URL or not SUPABASE_KEY:
        print("ERRO: SUPABASE_URL e SUPABASE_KEY devem estar no backend/.env")
        sys.exit(1)

    try:
        from pyproj import Transformer  # noqa: F401
    except ImportError:
        print("ERRO: pyproj não instalado. Execute: pip install pyproj")
        sys.exit(1)

    sb = create_client(SUPABASE_URL, SUPABASE_KEY)
    res = sb.table("projetos").select("id, nome, zona_utm").execute()
    projetos = res.data

    if args.projeto:
        projetos = [p for p in projetos if p["nome"].lower() == args.projeto.lower()]
        if not projetos:
            print(f"Projeto '{args.projeto}' não encontrado no banco.")
            sys.exit(1)

    print(f"\nGeoAdmin Pro — Importação de Pontos"
          f"{' [DRY RUN]' if args.dry_run else ''}")
    print(f"Projetos: {len(projetos)} | Base: {PASTA_BASE}\n")

    total = 0
    for proj in projetos:
        total += importar_projeto(sb, proj, args.dry_run)

    print(f"\nTotal importado: {total} pontos")


if __name__ == "__main__":
    main()
