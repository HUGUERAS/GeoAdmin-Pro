#!/usr/bin/env python3
"""
GeoAdmin Pro — Agente Organizador Físico de Projetos
=====================================================
backend/scripts/organizador_projetos.py

Este script executa localmente no computador do topógrafo para escanear
arquivos avulsos e desorganizados (na raiz de D:\\TRABALHO ou em pastas temporárias),
reconhecer a qual projeto eles pertencem por meio de cruzamento com o banco de dados Supabase,
e movê-los fisicamente para dentro da pasta raiz correspondente do projeto.

Ele prioriza a separação estrita por PROJETO em vez de tipo de arquivo,
conforme a preferência do usuário.
"""

import os
import sys
import re
import shutil
import argparse
import unicodedata
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple

# Garante que o diretório backend/ esteja no sys.path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

# Carrega dotenv local
try:
    from dotenv import load_dotenv
    load_dotenv(backend_dir / ".env")
except ImportError:
    pass

# Configurações Padrão
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
    print(f"{BOLD}{MAGENTA}")
    print(r"   ____              _       _           _        ___                            ")
    print(r"  / ___| ___  ___   / \   __| |_ __ ___ (_)_ __  / _ \ _ __ __ _  __ _ _ __ ___ ")
    print(r" | |  _ / _ \/ _ \ / _ \ / _` | '_ ` _ \| | '_ \| | | | '__/ _` |/ _` | '_ ` _ \ ")
    print(r" | |_| |  __/ (_) / ___ \ (_| | | | | | | | | | | |_| | | | (_| | (_| | | | | | |")
    print(r"  \____|\___|\___/_/   \_\__,_|_| |_| |_|_|_| |_|\___/|_|  \__, |\__,_|_| |_| |_|")
    print(f"                                                           |___/[ Organizador ]{RESET}\n")

# ── Normalização de Nomes ─────────────────────────────────────────────────────
def normalizar_nome(texto: str) -> str:
    """Normaliza strings para comparação simples: minúsculo, sem acentos, sem extensões."""
    if not texto:
        return ""
    texto = texto.lower().strip()
    texto = re.sub(r"\s+", " ", texto)
    # Remove acentos
    nfkd = unicodedata.normalize("NFKD", texto)
    texto = "".join([c for c in nfkd if not unicodedata.combining(c)])
    # Remove caracteres especiais comuns
    texto = re.sub(r"[^a-z0-9\s_-]", "", texto)
    return texto

# ── Algoritmo de Casamento de Projetos ─────────────────────────────────────────
def encontrar_projeto_correspondente(nome_arquivo: str, projetos: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    Tenta associar um nome de arquivo a um dos projetos ativos da base de dados.
    Usa casamento de substrings e palavras-chave exclusivas com pontuação de tamanho.
    """
    fl_norm = normalizar_nome(Path(nome_arquivo).stem)
    if not fl_norm:
        return None

    candidatos = []
    
    # ── Passo 1: Casamento de substring completa (ex: 'cemig' em 'levantamento_cemig_2026')
    for proj in projetos:
        proj_norm = normalizar_nome(proj["nome"])
        if not proj_norm:
            continue
        if proj_norm in fl_norm:
            candidatos.append((len(proj_norm), proj))

    if candidatos:
        # Retorna o projeto com o nome correspondente mais longo para evitar correspondências parciais curtas
        candidatos.sort(key=lambda x: x[0], reverse=True)
        return candidatos[0][1]

    # ── Passo 2: Casamento por palavra-chave significativa (ignora termos barulhentos)
    palavras_ignorar = {"projeto", "de", "e", "com", "versao", "final", "teste", "campo", "lote", "gleba"}
    
    for proj in projetos:
        proj_norm = normalizar_nome(proj["nome"])
        palavras_proj = [w for w in proj_norm.split(" ") if w not in palavras_ignorar and len(w) > 2]
        
        for pal in palavras_proj:
            if pal in fl_norm:
                return proj

    return None

# ── Descobrindo o Destino Físico do Projeto ──────────────────────────────────
def obter_pasta_destino_projeto(pasta_base: Path, nome_projeto: str) -> Path:
    """
    Busca se a pasta do projeto já existe em alguma subpasta de D:\\TRABALHO (ex: 01_ATIVOS, 02_SUSPENSOS).
    Se não existir, cria por padrão na pasta de projetos ativos: 01_ATIVOS/nome_projeto.
    """
    subpastas_escanear = ["01_ATIVOS", "02_SUSPENSOS", "03_ARQUIVO"]
    
    # Procura em subpastas conhecidas
    for sub in subpastas_escanear:
        caminho_sub = pasta_base / sub
        if caminho_sub.exists():
            for cp in caminho_sub.iterdir():
                if cp.is_dir() and normalizar_nome(cp.name) == normalizar_nome(nome_projeto):
                    return cp

    # Fallback: Se não existe em lugar nenhum, cria na pasta de projetos ativos (01_ATIVOS)
    pasta_ativos = pasta_base / "01_ATIVOS"
    if not pasta_ativos.exists():
        pasta_ativos = pasta_base # Se não houver 01_ATIVOS, usa a raiz
        
    return pasta_ativos / nome_projeto

# ── Evita Sobrescrever Arquivos Duplicados ────────────────────────────────────
def obter_caminho_sem_duplicata(caminho_arquivo: Path) -> Path:
    """Se o arquivo já existir na pasta de destino, adiciona um sufixo numerado (ex: _v1, _v2)."""
    if not caminho_arquivo.exists():
        return caminho_arquivo

    base = caminho_arquivo.parent
    stem = caminho_arquivo.stem
    ext = caminho_arquivo.suffix
    
    i = 1
    while True:
        novo_caminho = base / f"{stem}_v{i}{ext}"
        if not novo_caminho.exists():
            return novo_caminho
        i += 1

# ── Execução Principal da Organização ─────────────────────────────────────────
def organizar_arquivos_avulsos(sb, pasta_base: Path, pasta_origem: Path, projetos: List[Dict[str, Any]], dry_run: bool, recursivo: bool = False) -> List[Tuple[Path, Path]]:
    """Varre arquivos soltos no diretório de origem e move para as pastas de projetos correspondentes."""
    movimentacoes = []
    
    # Conjunto de nomes de projetos normalizados para evitar re-organizar arquivos que já estão dentro de pastas de projeto!
    nomes_projetos_normalizados = {normalizar_nome(p["nome"]) for p in projetos}
    
    if recursivo:
        arquivos_avulsos = []
        for root, _, files in os.walk(pasta_origem):
            root_path = Path(root)
            
            # Se o diretório atual ou qualquer pasta pai dele for de um projeto já cadastrado no banco, pula!
            partes_norm = [normalizar_nome(part) for part in root_path.parts]
            if any(part in nomes_projetos_normalizados for part in partes_norm):
                continue
                
            for f in files:
                arquivos_avulsos.append(root_path / f)
    else:
        # Lista arquivos diretamente na pasta de origem (não recursivo, para não bagunçar pastas já prontas!)
        arquivos_avulsos = [p for p in pasta_origem.iterdir() if p.is_file()]
    
    # Ignora arquivos de sistema comuns e arquivos de controle
    arquivos_ignorar = {".gitignore", "desktop.ini", "thumbs.db", "organizador.py", "importar_pontos.py", "importador_desktop.py"}
    
    for arq in arquivos_avulsos:
        if arq.name.lower() in arquivos_ignorar or arq.name.startswith(("_LOG", "_INVENTARIO", "_datas")):
            continue

        proj_compativel = encontrar_projeto_correspondente(arq.name, projetos)
        if not proj_compativel:
            continue

        # Descobre onde está a pasta do projeto (ou onde deve ser criada)
        pasta_dest = obter_pasta_destino_projeto(pasta_base, proj_compativel["nome"])
        caminho_final = pasta_dest / arq.name
        
        # Gera nome sem duplicidade caso o arquivo já exista lá
        caminho_final_seguro = obter_caminho_sem_duplicata(caminho_final)
        movimentacoes.append((arq, caminho_final_seguro))

    return list(set(movimentacoes))  # Remove duplicatas se houver e retorna

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    print_banner()

    parser = argparse.ArgumentParser(description="Agente Organizador Físico de Pastas do GeoAdmin Pro")
    parser.add_argument("--caminho", type=str, default=CAMINHO_TRABALHO_PADRAO,
                        help=f"Caminho absoluto do diretório principal (padrão: {CAMINHO_TRABALHO_PADRAO})")
    parser.add_argument("--origem", type=str, default=None,
                        help="Pasta desorganizada a escanear. (Padrão: raiz do diretório principal)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Apenas simula a reorganização dos arquivos locais sem movê-los física ou permanentemente")
    parser.add_argument("--recursivo", "-r", action="store_true",
                        help="Faz a busca de arquivos avulsos de forma recursiva em subpastas")
    args = parser.parse_args()

    # Credenciais do Supabase
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_ANON_KEY") or os.getenv("SUPABASE_KEY")

    if not supabase_url or not supabase_key:
        print(f"{RED}{BOLD}ERRO: SUPABASE_URL e chaves não configuradas em backend/.env!{RESET}")
        sys.exit(1)

    pasta_base = Path(args.caminho)
    if not pasta_base.exists():
        print(f"{RED}{BOLD}Erro: O caminho de trabalho '{args.caminho}' não existe no computador!{RESET}")
        sys.exit(1)

    # Pasta de origem padrão é a raiz do TRABALHO
    pasta_origem = Path(args.origem) if args.origem else pasta_base
    if not pasta_origem.exists():
        print(f"{RED}{BOLD}Erro: A pasta de origem desorganizada '{pasta_origem}' não existe!{RESET}")
        sys.exit(1)

    # Inicializa conexão Supabase
    try:
        from supabase import create_client
        sb = create_client(supabase_url, supabase_key)
    except Exception as exc:
        print(f"{RED}{BOLD}Erro ao conectar ao Supabase: {exc}{RESET}")
        sys.exit(1)

    # Busca projetos do Supabase
    try:
        res_proj = sb.table("projetos").select("id, nome").is_("deleted_at", "null").execute()
        projetos = res_proj.data or []
    except Exception as exc:
        print(f"{RED}{BOLD}Erro ao consultar lista de projetos: {exc}{RESET}")
        sys.exit(1)

    if not projetos:
        print(f"{YELLOW}Nenhum projeto ativo encontrado no banco de dados Supabase.{RESET}")
        sys.exit(0)

    print(f"{BOLD}Configurações do Organizador:{RESET}")
    print(f"  Diretório Principal: {CYAN}{pasta_base}{RESET}")
    print(f"  Pasta de Escaneamento: {CYAN}{pasta_origem}{RESET}")
    print(f"  Projetos Ativos:      {CYAN}{len(projetos)}{RESET}")
    print(f"  Escaneamento Recursivo: {CYAN}{'Sim' if args.recursivo else 'Não'}{RESET}")
    print(f"  Modo Operação:        {YELLOW}{'SIMULAÇÃO (DRY RUN)' if args.dry_run else 'ORGANIZAÇÃO REAL'}{RESET}\n")

    # Calcula movimentações potenciais
    movimentacoes = organizar_arquivos_avulsos(sb, pasta_base, pasta_origem, projetos, args.dry_run, recursivo=args.recursivo)

    if not movimentacoes:
        print(f"{GREEN}Excelente! Nenhum arquivo avulso ou desorganizado para separar na pasta '{pasta_origem}'.{RESET}\n")
        sys.exit(0)

    print(f"{BOLD}Arquivos Detectados para Organização:{RESET}")
    for orig, dest in movimentacoes:
        print(f"  [Arquivo] '{orig.name}'\n       --> {GREEN}Mover para:{RESET} '{dest.relative_to(pasta_base)}'")

    if args.dry_run:
        print(f"\n{CYAN}[SIMULAÇÃO] {len(movimentacoes)} arquivos seriam movidos para suas pastas de projeto correspondentes.{RESET}\n")
        sys.exit(0)

    # Prompt Interativo de Confirmação
    print(f"\n{BOLD}{YELLOW}Você confirma a movimentação física desses {len(movimentacoes)} arquivos no seu computador? [s/N]: {RESET}", end="")
    try:
        confirmacao = input().strip().lower()
    except (KeyboardInterrupt, EOFError):
        print(f"\n{RED}Cancelado pelo usuário.{RESET}")
        sys.exit(0)

    if confirmacao not in ("s", "sim"):
        print(f"{RED}Operação cancelada. Nenhum arquivo foi movido.{RESET}\n")
        sys.exit(0)

    # Executa a movimentação física dos arquivos
    sucessos = 0
    for orig, dest in movimentacoes:
        try:
            # Cria a pasta de destino se não existir
            dest.parent.mkdir(parents=True, exist_ok=True)
            # Move o arquivo de forma segura
            shutil.move(str(orig), str(dest))
            sucessos += 1
        except Exception as exc:
            print(f"  {RED}[ERRO] Falha ao mover '{orig.name}': {exc}{RESET}")

    print(f"\n{BOLD}{GREEN}=== Concluído! ==={RESET}")
    print(f"Total de {sucessos} de {len(movimentacoes)} arquivos organizados com absoluto êxito nas suas pastas de projeto!\n")

if __name__ == "__main__":
    main()
