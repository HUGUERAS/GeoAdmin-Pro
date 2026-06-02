"""
GeoAdmin Pro - Testes do VertexClient

Valida a resiliência e as chamadas do cliente HTTP de integração do VERTEXROSEA.
"""

import pytest
from unittest.mock import AsyncMock, patch
import httpx
from integracoes.vertex_client import VertexClient

@pytest.mark.anyio
async def test_validar_dxf_sucesso():
    """Valida chamada com sucesso para validação de DXF."""
    client = VertexClient()
    
    # Mock do método interno _request
    mock_resposta = {"valido": True, "avisos": [], "versao": "AutoCAD 2013"}
    
    with patch.object(client, "_request", new_callable=AsyncMock) as mock_req:
        mock_req.return_value = mock_resposta
        
        resultado = await client.validar_dxf(b"conteudo dxf", "teste.dxf")
        
        assert resultado["valido"] is True
        assert resultado["versao"] == "AutoCAD 2013"
        mock_req.assert_called_once()

@pytest.mark.anyio
async def test_extrair_pontos_dxf_sucesso():
    """Valida extração de pontos com sucesso."""
    client = VertexClient()
    mock_resposta = {
        "pontos": [
            {"codigo": "V01", "norte": 7500000.1, "este": 450000.2}
        ]
    }
    
    with patch.object(client, "_request", new_callable=AsyncMock) as mock_req:
        mock_req.return_value = mock_resposta
        
        pontos = await client.extrair_pontos_dxf(b"conteudo dxf", "teste.dxf")
        
        assert len(pontos) == 1
        assert pontos[0]["codigo"] == "V01"
        assert pontos[0]["norte"] == 7500000.1

@pytest.mark.anyio
async def test_vertex_indisponivel():
    """Valida comportamento resiliente de erro de conexão."""
    client = VertexClient()
    
    with patch("httpx.AsyncClient.post", side_effect=httpx.ConnectError("Connection refused")):
        with pytest.raises(ConnectionError) as exc_info:
            await client.validar_dxf(b"conteudo dxf", "teste.dxf")
        
        assert "Não foi possível conectar ao VERTEXROSEA" in str(exc_info.value)

@pytest.mark.anyio
async def test_vertex_timeout():
    """Valida comportamento sob timeout da API externa."""
    client = VertexClient()
    
    with patch("httpx.AsyncClient.post", side_effect=httpx.TimeoutException("Timeout")):
        with pytest.raises(TimeoutError) as exc_info:
            await client.validar_dxf(b"conteudo dxf", "teste.dxf")
        
        assert "excedeu o tempo limite" in str(exc_info.value)
