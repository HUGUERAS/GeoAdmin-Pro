import os
import sys
import logging
from dotenv import load_dotenv

# Configurar timezone e log
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Adiciona a pasta backend ao PATH para poder importar os modulos
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import get_supabase
from integracoes.arquivos_projeto import migrar_arquivos_locais_para_storage

def migrar_arquivos():
    """ Migra arquivos cartograficos que ainda estao salvos no disco (uploads folder) para o Supabase Storage """
    logger.info("Iniciando migracao de arquivos do disco local para o Supabase Storage...")
    sb = get_supabase()
    
    # A funcao verifica arquivos com storage prefix 'local://'
    resultado = migrar_arquivos_locais_para_storage(sb, autor="script_migracao")
    
    total = resultado.get("total", 0)
    migrados = resultado.get("migrados", 0)
    falhas = resultado.get("falhas", [])
    
    logger.info(f"Total de arquivos avaliados com pendencia local: {total}")
    logger.info(f"Sincronizados com sucesso no Supabase: {migrados}")
    
    if falhas:
        logger.error(f"Falhas durante migracao ({len(falhas)}):")
        for f in falhas:
            logger.error(f" - Arquivo ID: {f.get('arquivo_id')} | Erro: {f.get('erro')}")

def migrar_tokens_legados():
    """ 
    Migra qualquer token persistido no esquema legado `clientes.magic_link_token` 
    para o novo modelo transacional em `projeto_clientes.magic_link_token`.
    """
    logger.info("\n--- Verificando tokens legados na tabela de clientes ---")
    sb = get_supabase()
    
    try:
        # Busca clientes que ainda possuem algum magic_link_token
        res = getattr(sb.table("clientes").select("id, magic_link_token, magic_link_expira").not_.is_("magic_link_token", "null").execute(), "data", [])
        
        if not res:
            logger.info("Nenhum token legado encontrado. Tabela limpa e 100% atualizada!")
            return
            
        logger.info(f"Encontrados {len(res)} clientes com token legado. Copiando para projeto_clientes...")
        
        migrados = 0
        for cliente in res:
            c_id = cliente["id"]
            
            # Encontra o vínculo de projeto mais recente deste cliente
            pc_res = getattr(sb.table("projeto_clientes")
                             .select("id, magic_link_token")
                             .eq("cliente_id", c_id)
                             .order("criado_em", desc=True)
                             .limit(1).execute(), "data", [])
            
            if pc_res:
                pc_id = pc_res[0]["id"]
                # Se ainda nao tem token la, migra
                if not pc_res[0]["magic_link_token"]:
                    sb.table("projeto_clientes").update({
                        "magic_link_token": cliente["magic_link_token"],
                        "magic_link_expira": cliente["magic_link_expira"]
                    }).eq("id", pc_id).execute()
                    migrados += 1
                    
            # Esvazia os campos antigos para garantir que o BD fique no padrao novo
            sb.table("clientes").update({
                "magic_link_token": None,
                "magic_link_expira": None
            }).eq("id", c_id).execute()
            
        logger.info(f"Migracao concluida! {migrados} tokens migrados e removidos da tabela antiga.")
            
    except Exception as e:
        logger.error(f"Falha na limpeza dos tokens: {e}")

if __name__ == "__main__":
    # Carrega credenciais do ./backend/.env
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
    load_dotenv(env_path)
    
    logger.info("=== GEOADMIN PRO: SCRIPT DE MIGRACAO DA VERSAO ANTIGA ===")
    
    try:
        get_supabase() 
    except Exception as e:
        logger.error("Erro ao conectar no banco Supabase. Certifique-se de que backend/.env tem a SUPABASE_URL e SUPABASE_KEY válidas.")
        sys.exit(1)
        
    migrar_arquivos()
    migrar_tokens_legados()
    logger.info("\nMigracao da estrutura da 'versao antiga' finalizada. O app esta limpo!")
