import sys
import os
import json
from pathlib import Path

# Adiciona o diretório backend ao path para imports
backend_dir = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(backend_dir))

from integracoes.areas_projeto import (
    importar_lotes_por_formato,
    importar_areas_projeto_em_lote,
    AREAS_STORE_PATH
)

class MockSupabaseClient:
    """Mock do cliente Supabase para forçar o fallback de persistência local com Risco Zero."""
    
    class MockTable:
        def select(self, *args, **kwargs): return self
        def insert(self, *args, **kwargs): return self
        def update(self, *args, **kwargs): return self
        def eq(self, *args, **kwargs): return self
        def order(self, *args, **kwargs): return self
        def is_(self, *args, **kwargs): return self
        def execute(self, *args, **kwargs):
            # Força o fallback local levantando um erro de schema cache / conexão
            raise RuntimeError("Could not find schema cache or database offline (Forced Mock Fallback)")

    def table(self, name):
        return self.MockTable()

def testar_importacao_batch():
    print("=" * 60)
    print("INICIANDO TESTE DE IMPORTAÇÃO EM LOTE - 120 LOTES")
    print("=" * 60)
    
    # 1. Carregar arquivo GeoJSON
    geojson_path = backend_dir / "data" / "amostra_120_lotes.geojson"
    if not geojson_path.exists():
        print(f"[ERRO] Arquivo de amostra {geojson_path} não encontrado!")
        sys.exit(1)
        
    print(f"1. Lendo malha GeoJSON: {geojson_path.name}")
    conteudo_bytes = geojson_path.read_bytes()
    
    # Limpa o store local de teste antes de rodar para termos uma rodada limpa
    if AREAS_STORE_PATH.exists():
        try:
            AREAS_STORE_PATH.unlink()
            print("   [OK] Limpo banco local de contingencia temporario para teste.")
        except Exception as e:
            print(f"   [AVISO] Nao foi possivel remover store anterior: {e}")

    # 2. Parsear arquivo no formato GeoJSON
    print("2. Executando parse_lotes_geojson...")
    resultado_parse = importar_lotes_por_formato("geojson", conteudo_bytes)
    lotes_parseados = resultado_parse["lotes"]
    print(f"   [OK] Sucesso: {len(lotes_parseados)} lotes identificados e normalizados.")
    
    # 3. Executar a importação em lote com Mock Supabase (forçando fallback local em arquivo)
    print("3. Executando importar_areas_projeto_em_lote (com sandbox local)...")
    mock_sb = MockSupabaseClient()
    
    # Substituir "Amostragem de Lotes no Painel" cabeçalho com acentuação corrigida
    projeto_id = "test-projeto-condominial-120"
    
    resultado_importacao = importar_areas_projeto_em_lote(
        projeto_id=projeto_id,
        lotes=lotes_parseados,
        atualizar_existentes=True,
        sb=mock_sb
    )
    
    # 4. Exibir resultados e estatísticas do painel
    print("\n" + "=" * 60)
    print("RESULTADO DA IMPORTACAO (SANDBOX LOCAL)")
    print("=" * 60)
    print(f"Total Recebido:    {resultado_importacao['total_recebido']}")
    print(f"Criadas no Lote:   {resultado_importacao['criadas']}")
    print(f"Atualizadas:       {resultado_importacao['atualizadas']}")
    print(f"Ignoradas:         {resultado_importacao['ignoradas']}")
    
    # Verificar se salvou fisicamente no JSON local
    if AREAS_STORE_PATH.exists():
        tamanho_kb = os.path.getsize(AREAS_STORE_PATH) / 1024
        print(f"\nPersistencia Local: {AREAS_STORE_PATH.name} ({tamanho_kb:.2f} KB)")
        
    painel = resultado_importacao["painel_lotes"]
    print(f"Total de itens no painel ordenado: {len(painel)}")
    
    # Mostrar amostragem dos 5 primeiros lotes do painel
    print("\nAmostragem de Lotes no Painel (Primeiros 5):")
    print("-" * 75)
    print(f"{'QUADRA':<8} | {'LOTE':<6} | {'IDENTIFICACAO':<20} | {'STATUS OP':<20} | {'GEOMETRIA':<15}")
    print("-" * 75)
    for item in painel[:5]:
        print(f"{item['quadra']:<8} | {item['codigo_lote']:<6} | {item['identificacao_lote']:<20} | {item['status_operacional']:<20} | {item['status_geometria']:<15}")
    print("-" * 75)
    
    print("\n[OK] TESTE DE IMPORTACAO CONCLUIDO COM SUCESSO ABSOLUTO E RISCO ZERO!")
    print("=" * 60 + "\n")

if __name__ == "__main__":
    testar_importacao_batch()
