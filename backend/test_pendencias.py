import os
import json
from unittest.mock import MagicMock
from services.agents.pendencias import (
    resumir_pendencias_projeto,
    listar_lotes_sem_participante,
    listar_pendencias_por_lote,
    calcular_indicadores_operacionais
)

def test_resumir_pendencias_projeto():
    sb = MagicMock()
    # Mock para areas_projeto count (Total Lotes = 10)
    sb.table().select().eq().is_().execute.return_value.count = 10
    
    # Executa a função
    resumo = resumir_pendencias_projeto(sb, "projeto-123")
    
    assert resumo['projeto_id'] == "projeto-123"
    assert resumo['total_lotes'] == 10
    # Como todos os mocks retornam count=10 por padrão nesse mock simples, lotes_com_participante = 10, logo lotes_sem_participante = 0
    assert resumo['lotes_sem_participante'] == 0
    print("Test resumir_pendencias_projeto: OK")

def test_listar_lotes_sem_participante():
    sb = MagicMock()
    sb.table().select().eq().eq().is_().execute.return_value.data = [
        {"id": "lote-1", "codigo_lote": "L01", "quadra": "Q1", "setor": "S1"}
    ]
    
    lotes = listar_lotes_sem_participante(sb, "projeto-123")
    
    assert len(lotes) == 1
    assert lotes[0]['codigo_lote'] == "L01"
    print("Test listar_lotes_sem_participante: OK")

def test_listar_pendencias_por_lote():
    sb = MagicMock()
    sb.table().select().eq().eq().is_().maybe_single().execute.return_value.data = {
        "status_operacional": "pendente",
        "status_documental": "aguardando"
    }
    # Mock para listagens (clientes e magic links)
    sb.table().select().eq().is_().execute.return_value.data = []
    
    resp = listar_pendencias_por_lote(sb, "projeto-123", "lote-1")
    
    assert resp['lote_id'] == "lote-1"
    assert resp['status_operacional'] == "pendente"
    assert resp['participantes_vinculados'] == 0
    assert "Não há tabela estruturada de documentos pendentes" in resp['observacao']
    print("Test listar_pendencias_por_lote: OK")

def test_calcular_indicadores():
    sb = MagicMock()
    # Para o resumo, o mock retorna 10 em tudo
    sb.table().select().eq().is_().execute.return_value.count = 10
    
    ind = calcular_indicadores_operacionais(sb, "projeto-123")
    
    # Lotes_com_participante = 10, Total_Lotes = 10 -> 100%
    assert ind['percentual_com_participante'] == 100.0
    assert ind['saude_geral'] == 'boa'
    print("Test calcular_indicadores: OK")

if __name__ == "__main__":
    test_resumir_pendencias_projeto()
    test_listar_lotes_sem_participante()
    test_listar_pendencias_por_lote()
    test_calcular_indicadores()
    print("ALL TESTS PASSED")
