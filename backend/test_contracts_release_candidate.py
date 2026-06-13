import os
import sys
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

# Importamos o app principal
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from main import app

client = TestClient(app)

# Um mock token e helper
FAKE_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.dummy.signature"

def test_chat_payload_invalido():
    response = client.post("/chat", headers={"Authorization": f"Bearer {FAKE_TOKEN}"}, json={})
    assert response.status_code == 422
    print("[OK] test_chat_payload_invalido - 422")

    response = client.post(
        "/chat", 
        headers={"Authorization": f"Bearer {FAKE_TOKEN}"}, 
        json={"mensagem": "", "projeto_id": "proj-1"}
    )
    assert response.status_code == 400
    assert "erro" in response.json()["detail"]
    print("[OK] test_chat_payload_invalido - 400")

def test_chat_oficial():
    with patch("routes.chat._get_supabase") as mock_supabase, \
         patch("routes.chat.handle_orchestrator_query") as mock_orchestrator, \
         patch("services.agents.memory.buscar_ou_criar_sessao") as mock_buscar_sessao, \
         patch("services.agents.memory.salvar_mensagem") as mock_salvar:
         
        mock_supabase.return_value = MagicMock()
        mock_buscar_sessao.return_value = "sess-123"
        mock_orchestrator.return_value = "Faltam os documentos X e Y"

        response = client.post(
            "/chat", 
            headers={"Authorization": f"Bearer {FAKE_TOKEN}"}, 
            json={
                "mensagem": "O que falta?",
                "projeto_id": "proj-1"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "sessao_id" in data
        assert "resposta" in data
        assert "agente_id" in data
        assert "metadados" in data
        assert data["sessao_id"] == "sess-123"
        assert data["resposta"] == "Faltam os documentos X e Y"
        assert data["agente_id"] == "orquestrador"
        print("[OK] test_chat_oficial")

def test_historico_oficial():
    with patch("routes.chat._get_supabase") as mock_supabase, \
         patch("services.agents.memory.carregar_historico_mensagens") as mock_carregar, \
         patch("services.agents.memory.buscar_ou_criar_sessao") as mock_buscar_sessao:
         
        mock_supabase.return_value = MagicMock()
        mock_buscar_sessao.return_value = "sess-123"
        mock_carregar.return_value = [
            {"id": "msg-1", "role": "user", "conteudo": "Ola"}
        ]

        response = client.get("/chat/sessoes/recente/mensagens?projeto_id=proj-1", headers={"Authorization": f"Bearer {FAKE_TOKEN}"})
        assert response.status_code == 200
        data = response.json()
        assert data["sessao_id"] == "sess-123"
        assert len(data["mensagens"]) == 1
        print("[OK] test_historico_oficial")

def test_documentos_pendentes():
    with patch("routes.gestao_documentos.calcular_pendencias_documentais") as mock_calcular:
        mock_calcular.return_value = {"total": 100, "pendentes": 10}
        response = client.get("/projetos/proj-1/gestao-documentos/resumo", headers={"Authorization": f"Bearer {FAKE_TOKEN}"})
        assert response.status_code == 200
        assert response.json()["pendentes"] == 10
        print("[OK] test_documentos_pendentes")

def test_webhooks_oficiais():
    with patch("os.getenv") as mock_getenv, \
         patch("routes.mensagens_externas.processar_inbound") as mock_processar:
         
        def env_side_effect(key, default=None):
            if key == 'WEBHOOKS_ENABLED': return 'true'
            if key == 'HERMES_WEBHOOK_SECRET': return 'secret123'
            if key == 'WHATSAPP_WEBHOOK_SECRET': return 'secret123'
            return default
        
        mock_getenv.side_effect = env_side_effect
        mock_processar.return_value = {"ok": True, "status": "linked"}

        response = client.post(
            "/webhooks/hermes",
            json={
                "provider_message_id": "msg-1",
                "from_telefone": "5511999",
                "texto": "teste",
                "secret": "secret123"
            }
        )
        assert response.status_code == 200
        assert response.json()["ok"] is True

        # Testando acesso negado no webhook
        response_negado = client.post(
            "/webhooks/whatsapp",
            json={
                "provider_message_id": "msg-1",
                "from_telefone": "5511999",
                "texto": "teste",
                "secret": "errado"
            }
        )
        assert response_negado.status_code == 401
        print("[OK] test_webhooks_oficiais")

def test_sem_stack_trace_para_frontend():
    with patch("routes.projetos.get_projetos") as mock_get_projetos:
        mock_get_projetos.side_effect = Exception("Erro critico interno na DB")
        response = client.get("/projetos", headers={"Authorization": f"Bearer {FAKE_TOKEN}"})
        assert response.status_code == 500
        assert response.json() == {"erro": "Erro interno", "codigo": 500}
        print("[OK] test_sem_stack_trace_para_frontend")

if __name__ == "__main__":
    test_chat_payload_invalido()
    test_chat_oficial()
    test_historico_oficial()
    test_documentos_pendentes()
    test_webhooks_oficiais()
    test_sem_stack_trace_para_frontend()
    print("ALL TESTS PASSED")
