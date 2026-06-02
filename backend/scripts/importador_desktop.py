#!/usr/bin/env python3
"""
GeoAdmin Pro — Agente Importador Desktop de Topografia
======================================================
backend/scripts/importador_desktop.py

Este script executa localmente no computador do topógrafo para escanear a pasta
de trabalho local (ex: D:\\TRABALHO), reconhecer arquivos de medição bruta de
campo (LandStar TXT, Métrica TOPO CSV, KML, DXF), tratar coordenadas UTM,
e realizar a importação direta para a tabela 'pontos' do Supabase.

Ele foi aprimorado para suportar linhas estendidas com logs de precisão GNSS
(ex: 'HRMS:0.005, VRMS:0.007, STATUS:FIXED' dos arquivos resplendor.txt),
evitando que pontos de alta precisão sejam descartados.
"""

import os
import sys
import re
import math
import argparse
import unicodedata
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, Tuple, List, Dict, Any

# Garante que o diretório backend/ esteja no sys.path para carregar dependências locais se necessário
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

# Carrega dotenv local
try:
    from dotenv import load_dotenv
    load_dotenv(backend_dir / ".env")
except ImportError:
    pass

# Caminho de trabalho padrão
CAMINHO_TRABALHO_PADRAO = r"D:\TRABALHO"

# ── Cores do Terminal (ANSI Escapes) ──────────────────────────────────────────
RESET   = "\033[0m"
BOLD    = "\033[1m"
GREEN   = "\033[32m"
BLUE    = "\033[34m"
CYAN    = "\033[36m"
YELLOW  = "\033[33m"
RED     = "\033[31m"
MAGENTA = "\033[35m"

def print_banner():
    print(f"{BOLD}{CYAN}")
    print(r"   ____              _       _           _        ____                 ")
    print(r"  / ___| ___  ___   / \   __| |_ __ ___ (_)_ __  |  _ \ _ __ ___       ")
    print(r" | |  _ / _ \/ _ \ / _ \ / _` | '_ ` _ \| | '_ \ | |_) | '__/ _ \      ")
    print(r" | |_| |  __/ (_) / ___ \ (_| | | | | | | | | | ||  __/| | | (_) |     ")
    print(r"  \____|\___|\___/_/   \_\__,_|_| |_| |_|_|_| |_||_|   |_|  \___/      ")
    print(f"                                   [ Agente Importador Desktop ]{RESET}\n")

# ── Normalização de Nomes para Casamento de Pastas ────────────────────────────
def normalizar_nome(texto: str) -> str:
    """Normaliza strings removendo acentos, espaços extras e caixa alta."""
    if not texto:
        return ""
    texto = texto.lower().strip()
    texto = re.sub(r"\s+", " ", texto)
    # Remove acentos e caracteres diacríticos
    nfkd = unicodedata.normalize("NFKD", texto)
    return "".join([c for c in nfkd if not unicodedata.combining(c)])

# ── Super Parser Topográfico (TXT/CSV) ─────────────────────────────────────────
def parse_status_gnss(status_raw: str) -> str:
    """Traduz o status bruto do GNSS para o formato legível no app."""
    status_raw = status_raw.upper().strip()
    if "FIX" in status_raw:
        return "Fixo"
    elif "FLOAT" in status_raw:
        return "Float"
    elif "SINGLE" in status_raw or "AUTON" in status_raw:
        return "Autônomo"
    return "Fixo"  # Fallback comum para RTK em topografia

def extrair_metadados_linha(linha: str) -> Dict[str, Any]:
    """
    Varre a linha procurando pares chave-valor de qualidade do GNSS.
    Ex: HRMS:0.005, VRMS:0.007, STATUS:FIXED, SATS:26, PDOP:1.195
    """
    meta = {}
    
    # Regexes para busca direta de tags
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
        meta["sigma_n"] = float(hrms_match.group(1))  # Fallback se só tiver horizontal
    else:
        meta["sigma_n"] = 0.0

    if vrms_match:
        meta["sigma_u"] = float(vrms_match.group(1))
    else:
        meta["sigma_u"] = 0.0

    return meta

def parse_txt_topografia(caminho: Path) -> List[Dict[str, Any]]:
    """
    Lê arquivos TXT/CSV e extrai pontos de forma inteligente e flexível.
    Suporta:
      - Formato LandStar (20 campos com DMS).
      - Formato Métrica TOPO clássico (4 ou 5 colunas).
      - Formato Métrica TOPO estendido (com campos de qualidade GNSS/resplendor.txt).
    """
    pontos = []
    
    # ── Testar se é formato LandStar 8.x (20 campos com DMS e vírgulas) ─────────
    # LandStar usa DMS tipo 022°39′06.09099″S no campo 5 e 6
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
                            "ja_geo":      True  # Já possui lat/lon DMS convertidos no parser
                        })
                    return pontos
        except Exception as exc:
            print(f"  {YELLOW}Aviso ao rodar parser LandStar nativo: {exc}. Usando parser flexível...{RESET}")

    # ── Parser Flexível Inteligente (Métrica clássico / resplendor.txt estendido) ──
    try:
        with open(caminho, encoding="latin-1", errors="ignore") as f:
            for num_linha, linha in enumerate(f, start=1):
                linha = linha.strip()
                if not linha or linha[0] in ("*", "#", ";", "["):
                    continue

                # Aceita vírgula ou ponto-e-vírgula como delimitador
                separador = ";" if ";" in linha else ","
                campos = [x.strip() for x in linha.split(separador)]

                if len(campos) < 3:
                    continue

                # Algoritmo de varredura inteligente de colunas UTM:
                # Procura por dois valores numéricos adjacentes que representam coordenadas UTM válidas no Brasil:
                # Norte: 6.000.000 < Y < 10.500.000
                # Este: 100.000 < X < 900.000
                encontrou_coordenadas = False
                norte, este, cota = 0.0, 0.0, 0.0
                idx_norte, idx_este = -1, -1

                for i in range(len(campos) - 1):
                    try:
                        val1 = float(campos[i])
                        val2 = float(campos[i+1])

                        # Caso 1: val1 = Norte, val2 = Este
                        if (6_000_000.0 < val1 < 10_500_000.0) and (100_000.0 < val2 < 900_000.0):
                            norte, este = val1, val2
                            idx_norte, idx_este = i, i+1
                            encontrou_coordenadas = True
                            break
                        # Caso 2: val1 = Este, val2 = Norte
                        elif (100_000.0 < val1 < 900_000.0) and (6_000_000.0 < val2 < 10_500_000.0):
                            este, norte = val1, val2
                            idx_este, idx_norte = i, i+1
                            encontrou_coordenadas = True
                            break
                    except ValueError:
                        continue

                if not encontrou_coordenadas:
                    continue

                # Nome do ponto: primeiro campo não-vazio
                nome = campos[0] if campos[0] else f"PT_L{num_linha:03d}"
                
                # Código: segundo campo (se houver, e se não for a própria coordenada norte/este)
                codigo = "TP"
                if len(campos) > 1 and idx_norte > 1 and idx_este > 1:
                    if campos[1] and not campos[1].replace(".", "", 1).isdigit():
                        codigo = campos[1]

                # Cota (altitude): Geralmente o campo logo após o Norte/Este
                idx_cota = max(idx_norte, idx_este) + 1
                if idx_cota < len(campos):
                    try:
                        cota = float(campos[idx_cota])
                    except ValueError:
                        cota = 0.0

                # Extrai metadados de qualidade GNSS da linha inteira ( tags chave-valor)
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
        print(f"  {RED}Erro ao parsear arquivo {caminho.name}: {exc}{RESET}")

    return pontos

# ── Parser KML ────────────────────────────────────────────────────────────────
def parse_kml(caminho: Path) -> List[Dict[str, Any]]:
    """Lê KML e retorna pontos geográficos (lon, lat) já validados."""
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
                nome = f"PT_KML_{i+1:03d}"

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
        print(f"  {RED}Erro ao ler KML: {exc}{RESET}")
    return pontos

# ── Parser DXF ────────────────────────────────────────────────────────────────
def parse_dxf(caminho: Path) -> List[Dict[str, Any]]:
    """Lê DXF (AutoCAD / Métrica exportado) extraindo POINTs e associando rótulos."""
    pontos = []
    try:
        import ezdxf
        doc = ezdxf.readfile(str(caminho))
        msp = doc.modelspace()

        # Coleta rótulos de texto para associar aos pontos por distância
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

                # Valida faixa UTM Brasil
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
        print(f"  {YELLOW}Aviso ao ler DXF (ezdxf necessário): {exc}{RESET}")
    return pontos

# ── Seleção do Melhor Arquivo Topográfico ─────────────────────────────────────
def encontrar_melhor_arquivo(pasta: Path) -> Tuple[Optional[Path], List[Dict[str, Any]]]:
    """
    Varre recursivamente a pasta do projeto procurando o melhor arquivo de pontos.
    Pontua arquivos contendo 'pont', 'cerca', 'resplendor' e penaliza logs/rinex.
    """
    candidatos = []
    palavras_chave_favoraveis = ("pont", "cerca", "resplendor", "levantamento", "medicao")
    palavras_chave_penalizar  = ("rinex", "relatorio", "log", "config", "planilha", "equiv")

    for root, _, files in os.walk(pasta):
        for f in files:
            path = Path(root) / f
            fl = f.lower()

            # Processa de acordo com extensão
            if fl.endswith(".txt"):
                pts = parse_txt_topografia(path)
            elif fl.endswith(".kml"):
                pts = parse_kml(path)
            elif fl.endswith(".dxf"):
                pts = parse_dxf(path)
            else:
                continue

            if not pts:
                continue

            # Calcula score de prioridade do arquivo
            score = len(pts)
            
            for pc in palavras_chave_favoraveis:
                if pc in fl:
                    score += 10000
                    break
            
            for pc in palavras_chave_penalizar:
                if pc in fl:
                    score -= 5000
                    break
            
            # Formatos de texto clássicos pontuam mais do que DXF/KML por precisarem de menos conversões externas
            if fl.endswith(".kml") or fl.endswith(".dxf"):
                score -= 300

            candidatos.append((score, path, pts))

    if not candidatos:
        return None, []

    candidatos.sort(key=lambda x: x[0], reverse=True)
    return candidatos[0][1], candidatos[0][2]

# ── Conversor UTM → Geográfico (SIRGAS 2000) ──────────────────────────────────
_transformers: Dict[str, Any] = {}

def converter_utm_para_geo(este: float, norte: float, zona_utm: str = "23S") -> Tuple[float, float]:
    """Converte coordenadas planas UTM SIRGAS 2000 para graus decimais (longitude, latitude)."""
    try:
        from pyproj import Transformer
    except ImportError:
        # Fallback sem pyproj (simplificado para testes se não instalado)
        return -46.0, -15.0

    zona_utm = zona_utm.upper()
    if zona_utm not in _transformers:
        # Extrai número (fuso) e hemisfério
        match = re.search(r"(\d+)([NS])", zona_utm)
        if not match:
            fuso, hem = 23, "S"
        else:
            fuso, hem = int(match.group(1)), match.group(2)
            
        # Zonas sul: 31978-31985 (zonas 18 a 25), Zonas norte: 31972-31977
        # SIRGAS 2000 UTM Zone 23S = EPSG:31983
        epsg = (31960 + fuso) if hem == "S" else (31960 + fuso - 30)
        _transformers[zona_utm] = Transformer.from_crs(epsg, 4674, always_xy=True)

    lon, lat = _transformers[zona_utm].transform(este, norte)
    return round(lon, 9), round(lat, 9)

# ── Execução Principal da Importação ──────────────────────────────────────────
def processar_e_importar(sb, projeto: Dict[str, Any], pasta_trabalho: Path, dry_run: bool) -> int:
    """Carrega os pontos locais, valida, converte e insere no Supabase."""
    nome_proj = projeto["nome"]
    projeto_id = projeto["id"]
    zona = (projeto.get("zona_utm") or "23S").upper()
    
    # 1. Verifica se a pasta física existe
    # Procura por casamento exato ou normalizado da pasta
    caminho_projeto = pasta_trabalho / nome_proj
    if not caminho_projeto.exists():
        # Tenta buscar por correspondência normalizada entre as pastas locais
        candidatos_pastas = [p for p in pasta_trabalho.iterdir() if p.is_dir()]
        for cp in candidatos_pastas:
            if normalizar_nome(cp.name) == normalizar_nome(nome_proj):
                caminho_projeto = cp
                break
        else:
            print(f"  {YELLOW}PULADO{RESET}  '{nome_proj}': Pasta física não encontrada em '{pasta_trabalho}'")
            return 0

    # 2. Descobre se o projeto já tem pontos no banco
    res_count = sb.table("pontos").select("id", count="exact").eq("projeto_id", projeto_id).limit(1).execute()
    total_pontos_existentes = res_count.count if hasattr(res_count, "count") else len(res_count.data or [])
    if total_pontos_existentes and total_pontos_existentes > 0:
        print(f"  {BLUE}PULADO{RESET}  '{nome_proj}': Já possui {total_pontos_existentes} pontos cadastrados")
        return 0

    # 3. Busca o melhor arquivo de pontos na pasta
    arquivo_pontos, pontos_parseados = encontrar_melhor_arquivo(caminho_projeto)
    if not pontos_parseados or not arquivo_pontos:
        print(f"  {YELLOW}VAZIO{RESET}   '{nome_proj}': Nenhum arquivo de pontos válido (.txt, .csv, .kml, .dxf) encontrado")
        return 0

    print(f"  {GREEN}ENCONTRADO{RESET} '{nome_proj}' -> '{arquivo_pontos.relative_to(pasta_trabalho)}' ({len(pontos_parseados)} pontos)")

    if dry_run:
        print(f"           {CYAN}[SIMULAÇÃO]{RESET} {len(pontos_parseados)} pontos seriam processados usando a fuso UTM {zona}")
        return len(pontos_parseados)

    # 4. Processa conversões de coordenadas e monta o payload
    payload_batch = []
    erros = 0
    agora = datetime.now(timezone.utc).isoformat()
    
    for p in pontos_parseados:
        try:
            if p.get("ja_geo"):
                lon, lat = p["lon"], p["lat"]
            else:
                lon, lat = converter_utm_para_geo(p["este"], p["norte"], zona)

            payload_batch.append({
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
                "criado_em":   agora
            })
        except Exception as exc:
            erros += 1
            if erros == 1:
                print(f"  {RED}Erro de conversão no ponto {p['nome']}: {exc}{RESET}")

    # 5. Insere no banco de dados via Supabase (em lote de 500 registros)
    inseridos = 0
    BATCH_SIZE = 500
    try:
        for idx in range(0, len(payload_batch), BATCH_SIZE):
            lote = payload_batch[idx:idx + BATCH_SIZE]
            res_insert = sb.table("pontos").insert(lote).execute()
            if res_insert.data:
                inseridos += len(res_insert.data)
        
        print(f"  {BOLD}{GREEN}SUCESSO{RESET}   '{nome_proj}': {inseridos} pontos importados com êxito! (erros: {erros})")
    except Exception as exc:
        print(f"  {RED}Falha ao gravar no Supabase para projeto '{nome_proj}': {exc}{RESET}")
        return 0

    return inseridos

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    print_banner()
    
    parser = argparse.ArgumentParser(description="Agente Importador de Topografia do GeoAdmin Pro")
    parser.add_argument("--caminho", type=str, default=CAMINHO_TRABALHO_PADRAO,
                        help=f"Caminho absoluto da pasta de trabalho (padrão: {CAMINHO_TRABALHO_PADRAO})")
    parser.add_argument("--dry-run", action="store_true",
                        help="Executa apenas a simulação (dry run) sem modificar o banco de dados")
    parser.add_argument("--projeto", type=str, default=None,
                        help="Importa apenas este projeto específico (cruzando com nome local)")
    args = parser.parse_args()

    # Validações do Ambiente
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_ANON_KEY") or os.getenv("SUPABASE_KEY")

    if not supabase_url or not supabase_key:
        print(f"{RED}{BOLD}ERRO: SUPABASE_URL e SUPABASE_ANON_KEY/SERVICE_ROLE_KEY não configuradas em backend/.env!{RESET}")
        sys.exit(1)

    try:
        from pyproj import Transformer
    except ImportError:
        print(f"{YELLOW}AVISO: 'pyproj' não encontrado. As conversões de coordenadas UTM serão fictícias.{RESET}")
        print(f"Instale rodando: {BOLD}pip install pyproj ezdxf{RESET}\n")

    pasta_trabalho = Path(args.caminho)
    # Tenta resolver o caminho recursivo se '01_ATIVOS' estiver embutido
    if not pasta_trabalho.exists():
        print(f"{RED}{BOLD}Caminho de trabalho '{args.caminho}' não encontrado no computador!{RESET}")
        sys.exit(1)

    # Resolve os caminhos internos comuns (01_ATIVOS, 02_SUSPENSOS) se o usuário passou a raiz do TRABALHO
    subpastas_escanear = [pasta_trabalho]
    for sub in ("01_ATIVOS", "02_SUSPENSOS"):
        if (pasta_trabalho / sub).exists():
            subpastas_escanear.append(pasta_trabalho / sub)

    # Conecta ao Supabase
    try:
        from supabase import create_client
        sb = create_client(supabase_url, supabase_key)
    except Exception as exc:
        print(f"{RED}{BOLD}Erro ao conectar ao cliente Supabase: {exc}{RESET}")
        sys.exit(1)

    # Busca projetos ativos do banco de dados para casamento
    try:
        res_proj = sb.table("projetos").select("id, nome, zona_utm").is_("deleted_at", "null").execute()
        projetos_db = res_proj.data or []
    except Exception as exc:
        print(f"{RED}{BOLD}Erro ao listar projetos do Supabase: {exc}{RESET}")
        sys.exit(1)

    if not projetos_db:
        print(f"{YELLOW}Nenhum projeto encontrado cadastrado no banco de dados Supabase.{RESET}")
        sys.exit(0)

    # Filtra projeto se passado por argumento
    if args.projeto:
        nome_alvo = normalizar_nome(args.projeto)
        projetos_db = [p for p in projetos_db if normalizar_nome(p["nome"]) == nome_alvo]
        if not projetos_db:
            print(f"{RED}Projeto alvo '{args.projeto}' não foi encontrado no banco de dados.{RESET}")
            sys.exit(1)

    print(f"{BOLD}Configurações Ativas:{RESET}")
    print(f"  Diretório Principal: {CYAN}{pasta_trabalho}{RESET}")
    print(f"  Subpastas ativas:    {CYAN}{', '.join([str(p.name) for p in subpastas_escanear if p != pasta_trabalho]) or 'Nenhuma'}{RESET}")
    print(f"  Projetos no banco:   {CYAN}{len(projetos_db)}{RESET}")
    print(f"  Modo Operação:       {YELLOW}{'SIMULAÇÃO (DRY RUN)' if args.dry_run else 'EXECUÇÃO REAL'}{RESET}\n")

    # Inicia processamento
    total_sucesso = 0
    
    # Processa cada projetoDB buscando as correspondências nas subpastas
    for projeto in projetos_db:
        pontos_projeto = 0
        for subpasta in subpastas_escanear:
            pontos_projeto = processar_e_importar(sb, projeto, subpasta, args.dry_run)
            if pontos_projeto > 0:
                total_sucesso += pontos_projeto
                break # Para de procurar em outras subpastas se já achou e importou

    print(f"\n{BOLD}{GREEN}=== Concluído! ==={RESET}")
    print(f"Total de pontos processados/importados: {BOLD}{total_sucesso}{RESET}\n")

if __name__ == "__main__":
    main()
