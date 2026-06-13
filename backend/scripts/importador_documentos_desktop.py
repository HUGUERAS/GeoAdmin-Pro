import os
import sys
import re
import unicodedata
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client

# Adiciona a pasta backend ao PATH para poder importar os modulos locais
backend_dir = Path(r"c:\Users\User\Documents\antigravity\GeoAdmin-Pro\backend")
sys.path.insert(0, str(backend_dir))

load_dotenv(backend_dir / ".env")

from main import get_supabase
from integracoes.arquivos_projeto import salvar_arquivo_projeto, listar_arquivos_projeto

# Configurações de caminhos
CAMINHO_TRABALHO = Path(r"D:\trabalho")
PASTAS_ATIVAS = ["01_ATIVOS", "02_SUSPENSOS"]

# Extensões que queremos importar como documentos/desenhos do projeto
EXTENSOES_DOCUMENTAIS = {".doc", ".docx", ".pdf", ".txt", ".dwg", ".dxf", ".kml", ".zip"}
PALAVRAS_IGNORAR = {"rinex", "relatorio_baseline", "log", "config", "install", "desktop.ini", "thumbs.db"}

def normalizar_nome(texto: str) -> str:
    if not texto:
        return ""
    texto = texto.lower().strip()
    texto = re.sub(r"\s+", " ", texto)
    nfkd = unicodedata.normalize("NFKD", texto)
    return "".join([c for c in nfkd if not unicodedata.combining(c)])

def obter_classificacao_e_origem(nome_arquivo: str) -> tuple[str, str]:
    ext = Path(nome_arquivo).suffix.lower()
    nome_norm = normalizar_nome(nome_arquivo)
    
    if ext in (".dwg", ".dxf", ".kml"):
        if "perimetro" in nome_norm or "final" in nome_norm or "oficial" in nome_norm:
            return "perimetro_tecnico", "topografo"
        return "camada_auxiliar", "topografo"
    
    if ext in (".doc", ".docx", ".pdf", ".txt"):
        if "memorial" in nome_norm or "anuencia" in nome_norm or "contrato" in nome_norm:
            return "referencia_visual", "escritorio"
        return "referencia_visual", "topografo"
        
    return "referencia_visual", "topografo"

def main():
    print("=" * 80)
    print("GEOADMIN PRO — IMPORTADOR DE DOCUMENTOS E ARQUIVOS FÍSICOS DO DISCO D:")
    print("=" * 80)
    
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_ANON_KEY")
    
    if not supabase_url or not supabase_key:
        print("[ERRO] Credenciais do Supabase não configuradas no backend/.env!")
        sys.exit(1)
        
    sb = get_supabase()
    
    # 1. Busca projetos ativos do banco
    try:
        res_proj = sb.table("projetos").select("id, nome").is_("deleted_at", "null").execute()
        projetos_db = res_proj.data or []
    except Exception as exc:
        print(f"[ERRO] Falha ao consultar projetos no Supabase: {exc}")
        sys.exit(1)
        
    if not projetos_db:
        print("[INFO] Nenhum projeto ativo encontrado no banco.")
        sys.exit(0)
        
    print(f"[INFO] Projetos ativos no banco: {len(projetos_db)}")
    
    # Mapeia as subpastas físicas ativas no disco D:
    subpastas_escanear = []
    for sub in PASTAS_ATIVAS:
        caminho_sub = CAMINHO_TRABALHO / sub
        if caminho_sub.exists():
            subpastas_escanear.append(caminho_sub)
            
    if not subpastas_escanear:
        print(f"[ERRO] Nenhum diretório de trabalho válido encontrado em {CAMINHO_TRABALHO}!")
        sys.exit(1)
        
    print(f"[INFO] Escaneando subpastas físicas: {', '.join([str(p.name) for p in subpastas_escanear])}\n")
    
    total_arquivos_importados = 0
    
    for projeto in projetos_db:
        nome_proj = projeto["nome"]
        projeto_id = projeto["id"]
        
        # Procura a pasta física do projeto correspondente
        caminho_projeto = None
        for subpasta in subpastas_escanear:
            pasta_potencial = subpasta / nome_proj
            if pasta_potencial.exists():
                caminho_projeto = pasta_potencial
                break
            # Tenta busca normalizada
            for cp in subpasta.iterdir():
                if cp.is_dir() and normalizar_nome(cp.name) == normalizar_nome(nome_proj):
                    caminho_projeto = cp
                    break
            if caminho_projeto:
                break
                
        if not caminho_projeto:
            continue
            
        print(f"\nProjeto: '{nome_proj}' (ID: {projeto_id})")
        print(f" -> Pasta Física: {caminho_projeto.relative_to(CAMINHO_TRABALHO)}")
        
        # Lista arquivos já cadastrados no banco para evitar duplicados
        arquivos_banco = listar_arquivos_projeto(sb, projeto_id)
        nomes_banco = {a["nome_original"].lower() for a in arquivos_banco}
        
        # Varre recursivamente os arquivos da pasta física do projeto
        arquivos_para_processar = []
        for root, _, files in os.walk(caminho_projeto):
            for f in files:
                path_arq = Path(root) / f
                ext = path_arq.suffix.lower()
                nome_low = f.lower()
                
                # Regras de filtros
                if ext not in EXTENSOES_DOCUMENTAIS:
                    continue
                if any(pi in nome_low for pi in PALAVRAS_IGNORAR):
                    continue
                if path_arq.name.startswith(("_LOG", "_INVENTARIO", "_datas")):
                    continue
                if f.lower() in nomes_banco:
                    continue
                if path_arq.stat().st_size > 15 * 1024 * 1024: # Limita a 15MB
                    continue
                    
                arquivos_para_processar.append(path_arq)
                
        if not arquivos_para_processar:
            print("   -> Nenhum novo arquivo de documento/desenho relevante pendente de importação.")
            continue
            
        print(f"   -> Encontrados {len(arquivos_para_processar)} arquivo(s) para importar:")
        
        for arq in arquivos_para_processar[:10]: # Limita a 10 arquivos por projeto para ser razoável
            try:
                nome_original = arq.name
                conteudo = arq.read_bytes()
                classificacao, origem = obter_classificacao_e_origem(nome_original)
                
                print(f"      [UPLOADING] '{nome_original}' ({len(conteudo)/1024:.1f} KB) | Classe: {classificacao}...")
                
                salvar_arquivo_projeto(
                    sb,
                    projeto_id=projeto_id,
                    nome_arquivo=nome_original,
                    conteudo=conteudo,
                    origem=origem,
                    classificacao=classificacao,
                    autor="script_importador_documentos"
                )
                total_arquivos_importados += 1
            except Exception as e:
                print(f"      [ERRO] Falha ao importar '{arq.name}': {e}")
                
    print("\n" + "=" * 80)
    print(f"IMPORTAÇÃO CONCLUÍDA COM EXCELENTE ÊXITO!")
    print(f"Total de documentos e desenhos cartográficos importados no Supabase: {total_arquivos_importados}")
    print("=" * 80)

if __name__ == "__main__":
    main()
