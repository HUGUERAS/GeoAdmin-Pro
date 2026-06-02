import os
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from scripts import importador_desktop as imp

# ── Testes de Normalização de Nomes ───────────────────────────────────────────
def test_normalizar_nome_acentos_e_capitalizacao():
    assert imp.normalizar_nome("PROJETO TOGIM VERSÃO FINAL") == "projeto togim versao final"
    assert imp.normalizar_nome("cemig") == "cemig"
    assert imp.normalizar_nome("  Fazenda   Margarida  ") == "fazenda margarida"
    assert imp.normalizar_nome("assentamento") == "assentamento"
    assert imp.normalizar_nome(None) == ""

# ── Testes de Metadados de Linha GNSS ─────────────────────────────────────────
def test_extrair_metadados_linha_resplendor():
    linha = "RADIO CERTO DIA 19 CÓDIGV,,7859135.417,257133.596,772.385,HRMS:0.005,VRMS:0.007,STATUS:FIXED,SATS:26,AGE:2.0,PDOP:1.195"
    meta = imp.extrair_metadados_linha(linha)
    
    assert meta["status_gnss"] == "Fixo"
    assert meta["satelites"] == 26
    assert meta["pdop"] == 1.195
    assert meta["sigma_e"] == 0.005
    assert meta["sigma_n"] == 0.005
    assert meta["sigma_u"] == 0.007

def test_extrair_metadados_linha_com_sigma_direto():
    linha = "P01,,7859000.0,257000.0,700.0,STATUS:FLOAT,SATS:15,PDOP:2.5,SIGMA_E:0.12,SIGMA_U:0.25"
    meta = imp.extrair_metadados_linha(linha)
    
    assert meta["status_gnss"] == "Float"
    assert meta["satelites"] == 15
    assert meta["pdop"] == 2.5
    assert meta["sigma_e"] == 0.12
    assert meta["sigma_u"] == 0.25

def test_extrair_metadados_linha_padrao_se_ausente():
    linha = "PT01,,7859000.0,257000.0,700.0"
    meta = imp.extrair_metadados_linha(linha)
    
    assert meta["status_gnss"] == "Fixo"
    assert meta["satelites"] == 0
    assert meta["pdop"] == 0.0
    assert meta["sigma_e"] == 0.0
    assert meta["sigma_u"] == 0.0

# ── Testes de Conversão de Coordenadas ────────────────────────────────────────
def test_converter_utm_para_geo_precisao():
    # Simula a conversão usando pyproj
    try:
        from pyproj import Transformer
        # Executa conversão real se pyproj estiver instalado
        lon, lat = imp.converter_utm_para_geo(257133.596, 7859135.417, "23S")
        assert -48.0 < lon < -45.0
        assert -20.0 < lat < -18.0
    except ImportError:
        # Se pyproj não estiver instalado, confia no fallback estático
        lon, lat = imp.converter_utm_para_geo(257133.596, 7859135.417, "23S")
        assert lon == -46.0
        assert lat == -15.0

# ── Teste de Parser de Arquivo TXT / CSV Flexível ────────────────────────────
def test_parse_txt_topografia_estendido(tmp_path):
    conteudo = """
* Cabeçalho de teste
B_3711176,,7863511.473,251305.667,505.330
RADIO CERTO DIA 19 CÓDIGV,,7859135.417,257133.596,772.385,HRMS:0.005,VRMS:0.007,STATUS:FIXED,SATS:26,AGE:2.0,PDOP:1.195
RADIO DIA 15 - NUMERO 14,,7859138.165,257130.878,774.324,HRMS:0.314,VRMS:0.453,STATUS:FLOAT,SATS:25,AGE:1.0,PDOP:1.370
    """
    caminho = tmp_path / "teste_resplendor.txt"
    caminho.write_text(conteudo, encoding="latin-1")
    
    pontos = imp.parse_txt_topografia(caminho)
    
    assert len(pontos) == 3
    
    # Valida ponto 1 (clássico)
    assert pontos[0]["nome"] == "B_3711176"
    assert pontos[0]["codigo"] == "TP"
    assert pontos[0]["norte"] == 7863511.473
    assert pontos[0]["este"] == 251305.667
    assert pontos[0]["altitude_m"] == 505.330
    assert pontos[0]["status_gnss"] == "Fixo"
    
    # Valida ponto 2 (estendido FIXED)
    assert pontos[1]["nome"] == "RADIO CERTO DIA 19 CÓDIGV"
    assert pontos[1]["norte"] == 7859135.417
    assert pontos[1]["este"] == 257133.596
    assert pontos[1]["altitude_m"] == 772.385
    assert pontos[1]["status_gnss"] == "Fixo"
    assert pontos[1]["satelites"] == 26
    assert pontos[1]["pdop"] == 1.195
    assert pontos[1]["sigma_e"] == 0.005
    assert pontos[1]["sigma_u"] == 0.007
    
    # Valida ponto 3 (estendido FLOAT)
    assert pontos[2]["nome"] == "RADIO DIA 15 - NUMERO 14"
    assert pontos[2]["status_gnss"] == "Float"
    assert pontos[2]["satelites"] == 25
    assert pontos[2]["pdop"] == 1.370
    assert pontos[2]["sigma_e"] == 0.314
    assert pontos[2]["sigma_u"] == 0.453

def test_parse_txt_topografia_4_colunas(tmp_path):
    conteudo = """
PT01,7859000.0,257000.0,700.0
PT02,7859100.0,257100.0,701.0
    """
    caminho = tmp_path / "teste_4colunas.txt"
    caminho.write_text(conteudo, encoding="latin-1")
    
    pontos = imp.parse_txt_topografia(caminho)
    
    assert len(pontos) == 2
    assert pontos[0]["nome"] == "PT01"
    assert pontos[0]["norte"] == 7859000.0
    assert pontos[0]["este"] == 257000.0
    assert pontos[0]["altitude_m"] == 700.0

# ── Teste de Descoberta de Melhor Arquivo ────────────────────────────────────
def test_encontrar_melhor_arquivo(tmp_path):
    pasta_projeto = tmp_path / "cemig"
    pasta_projeto.mkdir()
    
    # Arquivo irrelevante ou penalizado
    (pasta_projeto / "relatorio.txt").write_text("código,norte,este,cota\n")
    # Arquivo bom genérico
    (pasta_projeto / "1.txt").write_text("PT01,,7859000.0,257000.0,700.0\n")
    # Arquivo excelente (com palavra-chave e muitos pontos)
    (pasta_projeto / "resplendor_cerca_pontos.txt").write_text(
        "PT01,,7859000.0,257000.0,700.0\nPT02,,7859100.0,257100.0,701.0\n"
    )
    
    arquivo, pontos = imp.encontrar_melhor_arquivo(pasta_projeto)
    
    assert arquivo is not None
    assert "resplendor_cerca_pontos.txt" in arquivo.name
    assert len(pontos) == 2

# ── Teste de Carga de Dados no Supabase ───────────────────────────────────────
def test_processar_e_importar_fluxo_completo(tmp_path):
    pasta_trabalho = tmp_path / "TRABALHO"
    pasta_trabalho.mkdir()
    
    pasta_projeto = pasta_trabalho / "cemig"
    pasta_projeto.mkdir()
    
    # Cria arquivo de pontos
    (pasta_projeto / "pontos.txt").write_text("PT01,,7859000.0,257000.0,700.0\n")
    
    # Mocks do Supabase
    mock_sb = MagicMock()
    
    # Mock do count (não tem pontos ainda)
    mock_count_res = MagicMock()
    mock_count_res.count = 0
    mock_count_res.data = []
    mock_sb.table().select().eq().limit().execute.return_value = mock_count_res
    
    # Mock do insert
    mock_insert_res = MagicMock()
    mock_insert_res.data = [{"id": "ponto-inserido-1"}]
    mock_sb.table().insert().execute.return_value = mock_insert_res
    
    projeto = {"id": "proj-uuid-123", "nome": "cemig", "zona_utm": "23S"}
    
    inseridos = imp.processar_e_importar(mock_sb, projeto, pasta_trabalho, dry_run=False)
    
    assert inseridos == 1
    mock_sb.table.assert_any_call("pontos")
