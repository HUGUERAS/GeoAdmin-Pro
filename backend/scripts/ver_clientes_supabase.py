import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client

# Adiciona o diretório backend ao path para carregar os módulos locais
backend_dir = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(backend_dir))

# Carrega as variáveis reais de produção do arquivo .env
load_dotenv(backend_dir / ".env")

supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_ANON_KEY")

if not supabase_url or not supabase_key:
    print("[ERRO] Credenciais do Supabase não encontradas no arquivo .env!")
    sys.exit(1)

print("=" * 80)
print(f"CONECTANDO DIRETAMENTE AO SUPABASE REAL: {supabase_url}")
print("=" * 80)

try:
    sb = create_client(supabase_url, supabase_key)
    
    # 1. Buscar os últimos clientes cadastrados
    print("\n[INFO] Consultando últimos clientes cadastrados...")
    res = sb.table("clientes").select("id, nome, cpf, telefone, criado_em").order("criado_em", desc=True).limit(10).execute()
    clientes = res.data
    
    if not clientes:
        print("   -> Nenhum cliente encontrado na tabela!")
    else:
        print("\nÚLTIMOS 10 CLIENTES NO BANCO DE DADOS REAL:")
        print("-" * 110)
        print(f"{'ID':<38} | {'NOME':<30} | {'CPF':<15} | {'TELEFONE':<15}")
        print("-" * 110)
        for cli in clientes:
            nome = cli.get("nome") or "Sem nome"
            cpf = cli.get("cpf") or "Sem CPF"
            tel = cli.get("telefone") or "Sem telefone"
            print(f"{cli['id']:<38} | {nome:<30} | {cpf:<15} | {tel:<15}")
        print("-" * 110)

    # 2. Buscar vínculos recentes de projetos
    print("\n[INFO] Consultando vínculos de projetos recentes...")
    res_proj = sb.table("projeto_clientes").select("id, projeto_id, cliente_id, criado_em").order("criado_em", desc=True).limit(5).execute()
    vinculos = res_proj.data
    if vinculos:
        print("\nÚLTIMOS VÍNCULOS PROJETO-CLIENTE:")
        print("-" * 110)
        print(f"{'VÍNCULO ID':<38} | {'PROJETO ID':<38} | {'CLIENTE ID':<38}")
        print("-" * 110)
        for v in vinculos:
            print(f"{v['id']:<38} | {v['projeto_id']:<38} | {v['cliente_id']:<38}")
        print("-" * 110)

except Exception as e:
    print(f"\n[ERRO] Ocorreu um erro ao consultar o Supabase: {e}")

print("=" * 80)
