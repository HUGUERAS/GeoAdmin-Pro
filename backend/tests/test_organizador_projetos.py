import pytest
from pathlib import Path
from unittest.mock import MagicMock

from scripts import organizador_projetos as org

# ── Teste de Normalização de Nome de Arquivo ─────────────────────────────────
def test_normalizar_nome_organizador():
    assert org.normalizar_nome("Levantamento_Cemig_2026") == "levantamento_cemig_2026"
    assert org.normalizar_nome("Cerca - Togim (Final)") == "cerca - togim final"
    assert org.normalizar_nome("santa maria") == "santa maria"
    assert org.normalizar_nome("") == ""

# ── Teste de Casamento de Projetos por Nome de Arquivo ───────────────────────
def test_encontrar_projeto_correspondente():
    projetos = [
        {"id": "id-1", "nome": "cemig"},
        {"id": "id-2", "nome": "completando togim"},
        {"id": "id-3", "nome": "santa maria"},
        {"id": "id-4", "nome": "Fernando Castor"}
    ]
    
    # Caso 1: Casamento exato por substring
    res1 = org.encontrar_projeto_correspondente("levantamento_cemig.txt", projetos)
    assert res1 is not None
    assert res1["nome"] == "cemig"
    
    # Caso 2: Casamento por palavra-chave exclusiva ('togim')
    res2 = org.encontrar_projeto_correspondente("desenho_togim_completo.dxf", projetos)
    assert res2 is not None
    assert res2["nome"] == "completando togim"
    
    # Caso 3: Casamento por palavra-chave exclusiva com acentos ('santa maria')
    res3 = org.encontrar_projeto_correspondente("pontos_santamaria.txt", projetos)
    assert res3 is not None
    assert res3["nome"] == "santa maria"
    
    # Caso 4: Sem casamento
    res4 = org.encontrar_projeto_correspondente("levantamento_qualquer.txt", projetos)
    assert res4 is None

# ── Teste de Descoberta de Subpasta de Destino ────────────────────────────────
def test_obter_pasta_destino_projeto(tmp_path):
    pasta_base = tmp_path / "TRABALHO"
    pasta_base.mkdir()
    
    # Cria pasta de ativos para o teste
    pasta_ativos = pasta_base / "01_ATIVOS"
    pasta_ativos.mkdir()
    
    # Caso 1: Pasta do projeto já existe em 02_SUSPENSOS
    pasta_suspensos = pasta_base / "02_SUSPENSOS"
    pasta_suspensos.mkdir()
    pasta_projeto_existente = pasta_suspensos / "cemig"
    pasta_projeto_existente.mkdir()
    
    dest1 = org.obter_pasta_destino_projeto(pasta_base, "cemig")
    assert dest1 == pasta_projeto_existente
    
    # Caso 2: Pasta não existe em lugar nenhum, deve criar em 01_ATIVOS
    dest2 = org.obter_pasta_destino_projeto(pasta_base, "santa maria")
    assert dest2 == pasta_base / "01_ATIVOS" / "santa maria"

# ── Teste de Sufixo de Duplicado de Arquivo ───────────────────────────────────
def test_obter_caminho_sem_duplicata(tmp_path):
    caminho = tmp_path / "levantamento.txt"
    
    # Caso 1: Arquivo não existe ainda
    caminho_seguro1 = org.obter_caminho_sem_duplicata(caminho)
    assert caminho_seguro1 == caminho
    
    # Caso 2: Arquivo já existe, gera _v1
    caminho.write_text("dados", encoding="utf-8")
    caminho_seguro2 = org.obter_caminho_sem_duplicata(caminho)
    assert caminho_seguro2.name == "levantamento_v1.txt"
    
    # Caso 3: Ambos existem, gera _v2
    caminho_seguro2.write_text("dados", encoding="utf-8")
    caminho_seguro3 = org.obter_caminho_sem_duplicata(caminho)
    assert caminho_seguro3.name == "levantamento_v2.txt"

# ── Teste do Fluxo de Organização Geral ───────────────────────────────────────
def test_organizar_arquivos_avulsos_fluxo(tmp_path):
    pasta_base = tmp_path / "TRABALHO"
    pasta_base.mkdir()
    
    # Cria arquivos avulsos na raiz de TRABALHO
    (pasta_base / "resplendor_cemig_2026.txt").write_text("pontos", encoding="utf-8")
    (pasta_base / "mapa_togim.dxf").write_text("cad", encoding="utf-8")
    (pasta_base / "planilha_desorganizada.txt").write_text("dados", encoding="utf-8")
    
    projetos = [
        {"id": "id-1", "nome": "cemig"},
        {"id": "id-2", "nome": "completando togim"}
    ]
    
    # Executa a simulação
    movimentacoes = org.organizar_arquivos_avulsos(
        sb=MagicMock(),
        pasta_base=pasta_base,
        pasta_origem=pasta_base,
        projetos=projetos,
        dry_run=True
    )
    
    # Deve encontrar movimentações apenas para os arquivos correspondentes aos projetos
    assert len(movimentacoes) == 2
    
    nomes_arquivos_movidos = [orig.name for orig, dest in movimentacoes]
    assert "resplendor_cemig_2026.txt" in nomes_arquivos_movidos
    assert "mapa_togim.dxf" in nomes_arquivos_movidos
    assert "planilha_desorganizada.txt" not in nomes_arquivos_movidos


def test_organizar_arquivos_avulsos_recursivo(tmp_path):
    pasta_base = tmp_path / "TRABALHO"
    pasta_base.mkdir()
    
    # Cria pasta de drop zone soltos
    pasta_drop = pasta_base / "99_REVISAR_DEPOIS" / "arquivos_soltos_raiz"
    pasta_drop.mkdir(parents=True)
    (pasta_drop / "pelicano.zip").write_text("dados", encoding="utf-8")
    
    # Cria pasta de um projeto já organizado
    pasta_projeto_organizado = pasta_base / "01_ATIVOS" / "cemig"
    pasta_projeto_organizado.mkdir(parents=True)
    # Este arquivo já está organizado, o script NÃO deve tentar movê-lo!
    (pasta_projeto_organizado / "levantamento_cemig.txt").write_text("dados", encoding="utf-8")
    
    projetos = [
        {"id": "id-1", "nome": "cemig"},
        {"id": "id-2", "nome": "pelicano"}
    ]
    
    # Executa a busca recursiva
    movimentacoes = org.organizar_arquivos_avulsos(
        sb=MagicMock(),
        pasta_base=pasta_base,
        pasta_origem=pasta_base,
        projetos=projetos,
        dry_run=True,
        recursivo=True
    )
    
    # Deve identificar apenas o arquivo 'pelicano.zip' que está desorganizado.
    # O arquivo 'levantamento_cemig.txt' deve ser ignorado porque já está na pasta do projeto 'cemig'.
    assert len(movimentacoes) == 1
    assert movimentacoes[0][0].name == "pelicano.zip"

