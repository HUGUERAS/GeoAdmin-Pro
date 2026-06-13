import os
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_websocket_sem_token_rejeitado():
    try:
        with client.websocket_connect("/ws/projetos/proj-123/operacional"):
            pass
        raise AssertionError("Devia ter falhado sem token")
    except Exception as e:
        assert "1008" in str(e) or "close" in str(e).lower() or "403" in str(e)
    print("Test WS sem token: OK")

def test_websocket_com_token_falso_mas_auth_desligado():
    os.environ["AUTH_OBRIGATORIO"] = "false"
    
    with client.websocket_connect("/ws/projetos/proj-123/operacional?token=dummy") as websocket:
        websocket.send_text("ping")
        data = websocket.receive_text()
        assert data == "pong"
    print("Test WS ping pong: OK")

def test_event_bus_publishing():
    from services.realtime.manager import publish_event
    publish_event("proj-123", "test_event", {"foo": "bar"})
    print("Test publish event: OK")

if __name__ == "__main__":
    test_websocket_sem_token_rejeitado()
    test_websocket_com_token_falso_mas_auth_desligado()
    test_event_bus_publishing()
    print("ALL REALTIME TESTS PASSED")
