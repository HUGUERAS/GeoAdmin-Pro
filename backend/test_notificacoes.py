import os
import json
from unittest.mock import MagicMock, patch
from services.notifications import enfileirar_mensagem, enviar_mensagem_aprovada

def test_enfileirar_com_require_approval():
    sb = MagicMock()
    # Simula insert com status = draft pq REQUIRE_HUMAN_APPROVAL eh default = true
    sb.table().insert().execute.return_value.data = [{'id': 'msg-1', 'status': 'draft'}]
    
    os.environ['REQUIRE_HUMAN_APPROVAL'] = 'true'
    
    res = enfileirar_mensagem(sb, 'proj-1', 'whatsapp', 'Teste conteudo', telefone='123')
    
    assert res['status'] == 'draft'
    print("Test enfileirar com require_approval: OK")

def test_enviar_mensagem_desabilitada_global():
    sb = MagicMock()
    # Simula mensagem já aprovada
    sb.table().select().eq().is_().execute.return_value.data = [
        {'id': 'msg-1', 'status': 'approved', 'telefone': '1234', 'canal': 'whatsapp', 'conteudo': 'oi'}
    ]
    # Retorno mock pro update
    sb.table().update().eq().execute.return_value.data = [{'id': 'msg-1', 'status': 'failed'}]
    
    os.environ['EXTERNAL_MESSAGES_ENABLED'] = 'false'
    
    res = enviar_mensagem_aprovada(sb, 'msg-1')
    
    assert res['sucesso'] is False
    assert res['erro'] == 'EXTERNAL_MESSAGES_ENABLED = false'
    print("Test enviar_mensagem_desabilitada_global: OK")

def test_enviar_mensagem_dry_run_whatsapp():
    sb = MagicMock()
    sb.table().select().eq().is_().execute.return_value.data = [
        {'id': 'msg-1', 'status': 'approved', 'telefone': '1234', 'canal': 'whatsapp', 'conteudo': 'oi'}
    ]
    sb.table().update().eq().execute.return_value.data = [{'id': 'msg-1', 'status': 'dry_run'}]
    
    os.environ['EXTERNAL_MESSAGES_ENABLED'] = 'true'
    os.environ['WHATSAPP_DRY_RUN'] = 'true'
    
    res = enviar_mensagem_aprovada(sb, 'msg-1')
    
    assert res['status'] == 'dry_run'
    print("Test enviar_mensagem_dry_run_whatsapp: OK")

if __name__ == "__main__":
    test_enfileirar_com_require_approval()
    test_enviar_mensagem_desabilitada_global()
    test_enviar_mensagem_dry_run_whatsapp()
    print("ALL NOTIFICATION TESTS PASSED")
