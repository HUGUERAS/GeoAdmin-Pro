import sys
import os
import asyncio

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi.testclient import TestClient
from main import app
from unittest.mock import MagicMock

# Precisamos mockar a dependência de autenticação e o Supabase para o teste focado
from middleware.auth import verificar_token
app.dependency_overrides[verificar_token] = lambda: {"sub": "user_123"}

def fake_get_supabase():
    mock_sb = MagicMock()
    # mockando a resposta da sessoes
    mock_sb.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = [{"id": "12345678-1234-1234-1234-123456789abc"}]
    # mockando os inserimentos
    mock_sb.table.return_value.insert.return_value.execute.return_value.data = []
    # mockando a listagem de histórico
    mock_sb.table.return_value.select.return_value.eq.return_value.is_.return_value.order.return_value.limit.return_value.execute.return_value.data = []
    return mock_sb

import main
main.get_supabase = fake_get_supabase

def run_tests():
    print("Iniciando testes do endpoint /chat com Governança...")
    
    # Resolver o bug do TestClient instanciando as_asgi
    client = TestClient(app)

    print("--- Testando Rota de Historico ---")
    resp_hist = client.get("/chat/sessoes/recente/mensagens?projeto_id=proj-123")
    print(f"Status: {resp_hist.status_code}")
    print(f"Response: {resp_hist.json()}")

    print("\n--- Testando Criacao de Mensagem com payload completo ---")
    payload = {
        "projeto_id": "proj-123",
        "mensagem": "Qual o andamento?",
        "lote_id": "lote-999",
        "participante_id": "cli-777",
        "canal": "mobile"
    }
    
    # Esperamos erro interno na API porque ela chama a Anthropic real (não há API KEY no ambiente),
    # mas o payload deve passar pelo Pydantic com sucesso
    try:
        resp_post = client.post("/chat/", json=payload)
        print(f"Status: {resp_post.status_code}")
        print(f"Response: {resp_post.json()}")
    except Exception as e:
        print("Caiu na exception isolada (Provavelmente Anthropic_API_KEY).", str(e))

if __name__ == "__main__":
    run_tests()
