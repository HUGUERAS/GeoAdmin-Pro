import os
import json
from unittest.mock import MagicMock, patch
from services.inbound_messages import processar_inbound

def test_processar_inbound_telefone_desconhecido():
    sb = MagicMock()
    # Mock idempotencia: não encontrou repetido
    sb.table().select().eq().execute.return_value.data = []
    
    # Mock clientes: vazio (unlinked)
    sb.table().select().eq().is_().execute.return_value.data = []
    
    # Mock insert de mensagem externa
    sb.table().insert().execute.return_value.data = [{'id': 'msg-1', 'status': 'unlinked'}]
    
    res = processar_inbound(sb, 'whatsapp', 'msg-ext-123', '999999999', 'Ola')
    
    assert res['ok'] is True
    assert res['status'] == 'unlinked'
    print("Test inbound telefone desconhecido: OK")

def test_processar_inbound_idempotencia():
    sb = MagicMock()
    # Mock idempotencia: já existe
    sb.table().select().eq().execute.return_value.data = [{'id': 'ja-existe'}]
    
    res = processar_inbound(sb, 'whatsapp', 'msg-ext-123', '999999999', 'Ola')
    
    assert res['status'] == 'duplicate_ignored'
    print("Test inbound idempotencia: OK")

@patch('services.agents.orchestrator.handle_orchestrator_query')
@patch('services.notifications.enfileirar_mensagem')
def test_processar_inbound_telefone_conhecido(mock_enfileirar, mock_orchestrator):
    sb = MagicMock()
    mock_orchestrator.return_value = "Resposta gerada pela IA"
    
    # Idempotencia: ok
    sb.table().select().eq().execute.return_value.data = []
    
    # Clientes: ok
    cliente_mock = MagicMock()
    cliente_mock.data = [{'id': 'cli-1', 'nome': 'Joao', 'telefone': '999999999'}]
    
    # Projeto_clientes: ok
    proj_mock = MagicMock()
    proj_mock.data = [{'id': 'pc-1', 'projeto_id': 'proj-1'}]
    
    # Sessões: nao achou, vai criar
    sess_mock = MagicMock()
    sess_mock.data = []
    
    # Mensagens_externas insert
    insert_ext_mock = MagicMock()
    insert_ext_mock.data = [{'id': 'msg-ext-novo', 'status': 'received'}]
    
    # Criar sessao mock
    insert_sess_mock = MagicMock()
    insert_sess_mock.data = [{'id': 'sess-nova-1'}]
    
    # Side effects ordenados para os calls no DB
    # 1. Idempotencia -> select.eq
    # 2. Clientes -> select.eq.is_
    # 3. ProjetoClientes -> select.eq.is_
    # 4. Sessoes -> select.eq.ilike.is_
    sb.table().select().eq().execute.return_value.data = []  # idempotencia
    sb.table().select().eq().is_().execute.side_effect = [cliente_mock, proj_mock]
    
    # Mock inserts
    sb.table().insert().execute.side_effect = [
        insert_ext_mock,    # cria msg externa
        insert_sess_mock,   # cria sessao
        MagicMock(),        # cria msg user no chat
        MagicMock()         # cria msg assistant no chat
    ]
    
    # Sessoes select (cuidado: o ilike vem depois)
    sb.table().select().eq().ilike().is_().execute.return_value = sess_mock
    
    res = processar_inbound(sb, 'whatsapp', 'msg-ext-123', '999999999', 'Ola, perdi meu link')
    
    assert res['status'] == 'linked'
    assert res['projeto_id'] == 'proj-1'
    mock_orchestrator.assert_called_once()
    mock_enfileirar.assert_called_once()
    print("Test inbound telefone conhecido: OK")

if __name__ == "__main__":
    test_processar_inbound_telefone_desconhecido()
    test_processar_inbound_idempotencia()
    test_processar_inbound_telefone_conhecido()
    print("ALL INBOUND TESTS PASSED")
