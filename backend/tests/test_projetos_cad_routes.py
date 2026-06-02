"""
GeoAdmin Pro - Testes de Rotas da Bandeja Cartográfica (FastAPI projetos.py)

Valida as rotas do FastAPI mapeadas sob /projetos/{id}/arquivos/.../cad/...
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from routes.projetos import (
    api_validar_dxf,
    api_extrair_pontos,
    api_parse_txt,
    api_disparar_job_freecad,
    api_obter_status_job,
    ExtrairPontosPayload,
    ParseTxtPayload,
    JobFreeCadPayload,
)

@pytest.mark.anyio
@patch("routes.projetos._get_supabase")
@patch("integracoes.arquivos_projeto.obter_arquivo_projeto")
@patch("integracoes.arquivos_projeto._ler_bytes_arquivo")
@patch("integracoes.vertex_client.vertex_client.validar_dxf", new_callable=AsyncMock)
@patch("integracoes.jobs_cad.registrar_job_cad")
async def test_api_validar_dxf_sucesso(mock_reg_job, mock_validar, mock_read, mock_obter, mock_sb):
    """Valida rota de validação de DXF com sucesso."""
    mock_sb.return_value = MagicMock()
    mock_obter.return_value = {"id": "arq-123", "nome_original": "teste.dxf"}
    mock_read.return_value = b"dxf bytes"
    mock_validar.return_value = {"valido": True, "job_id": "job-dxf-xyz"}
    
    res = await api_validar_dxf("proj-123", "arq-123", layer="PERIMETRO")
    
    assert res["valido"] is True
    mock_validar.assert_called_once_with(b"dxf bytes", "teste.dxf", layer="PERIMETRO")
    mock_reg_job.assert_called_once()


@pytest.mark.anyio
@patch("routes.projetos._get_supabase")
@patch("integracoes.arquivos_projeto.obter_arquivo_projeto")
@patch("integracoes.arquivos_projeto._ler_bytes_arquivo")
@patch("integracoes.vertex_client.vertex_client.extrair_pontos_dxf", new_callable=AsyncMock)
@patch("integracoes.jobs_cad.registrar_job_cad")
async def test_api_extrair_pontos_sucesso(mock_reg_job, mock_extrair, mock_read, mock_obter, mock_sb):
    """Valida rota de extração de pontos com sucesso."""
    mock_sb.return_value = MagicMock()
    mock_obter.return_value = {"id": "arq-123", "nome_original": "teste.dxf"}
    mock_read.return_value = b"dxf bytes"
    mock_extrair.return_value = [{"codigo": "V01", "x": 100.0, "y": 200.0}]
    
    payload = ExtrairPontosPayload(fuso="23", hemisferio="S", layer="PERIMETRO")
    res = await api_extrair_pontos("proj-123", "arq-123", payload)
    
    assert res == {"pontos": [{"codigo": "V01", "x": 100.0, "y": 200.0}]}
    mock_extrair.assert_called_once_with(b"dxf bytes", "teste.dxf", "23", "S", layer="PERIMETRO")
    mock_reg_job.assert_called_once()


@pytest.mark.anyio
@patch("routes.projetos._get_supabase")
@patch("integracoes.arquivos_projeto.obter_arquivo_projeto")
@patch("integracoes.arquivos_projeto._ler_bytes_arquivo")
@patch("integracoes.vertex_client.vertex_client.parse_txt_coletora", new_callable=AsyncMock)
@patch("integracoes.jobs_cad.registrar_job_cad")
async def test_api_parse_txt_sucesso(mock_reg_job, mock_parse, mock_read, mock_obter, mock_sb):
    """Valida rota de parse de TXT com sucesso."""
    mock_sb.return_value = MagicMock()
    mock_obter.return_value = {"id": "arq-123", "nome_original": "teste.txt"}
    mock_read.return_value = b"txt bytes"
    mock_parse.return_value = {"pontos": [{"codigo": "V01", "x": 100.0}]}
    
    payload = ParseTxtPayload(fuso="23", hemisferio="S", formato="metrica_topo")
    res = await api_parse_txt("proj-123", "arq-123", payload)
    
    assert res == {"pontos": [{"codigo": "V01", "x": 100.0}]}
    mock_parse.assert_called_once_with(b"txt bytes", "teste.txt", fuso="23", hemisferio="S", formato="metrica_topo")
    mock_reg_job.assert_called_once()


@pytest.mark.anyio
@patch("routes.projetos._get_supabase")
@patch("routes.projetos._projeto_ou_404")
@patch("integracoes.freecad.generador_plantas._buscar_dados_planta")
@patch("integracoes.contrato_vertex.montar_contrato_vertex")
@patch("integracoes.vertex_client.vertex_client.disparar_job_freecad", new_callable=AsyncMock)
@patch("integracoes.jobs_cad.registrar_job_cad")
async def test_api_disparar_job_freecad_sucesso(
    mock_reg_job, mock_disparar, mock_montar, mock_buscar_dados, mock_ou_404, mock_sb
):
    """Valida rota de disparar Job FreeCAD com sucesso."""
    mock_sb.return_value = MagicMock()
    mock_ou_404.return_value = {"id": "proj-123"}
    mock_buscar_dados.return_value = MagicMock()
    mock_montar.return_value = {"contrato": "ok"}
    mock_disparar.return_value = {"job_id": "job-fc-abc", "status": "pending"}
    
    payload = JobFreeCadPayload(save_fcstd=True, output_dir=None)
    res = await api_disparar_job_freecad("proj-123", payload)
    
    assert res == {"job_id": "job-fc-abc", "status": "pending"}
    mock_disparar.assert_called_once_with(
        contrato_vertex={"contrato": "ok"},
        project_ref="proj-123",
        save_fcstd=True,
        output_dir=None
    )
    mock_reg_job.assert_called_once()


@pytest.mark.anyio
@patch("routes.projetos._get_supabase")
@patch("routes.projetos._projeto_ou_404")
@patch("integracoes.vertex_client.vertex_client.obter_status_job", new_callable=AsyncMock)
@patch("integracoes.jobs_cad.atualizar_status_job_cad")
async def test_api_obter_status_job_sucesso(mock_atualizar, mock_obter, mock_ou_404, mock_sb):
    """Valida rota de obter status do Job com sucesso."""
    mock_sb.return_value = MagicMock()
    mock_ou_404.return_value = {"id": "proj-123"}
    mock_obter.return_value = {
        "status": "done",
        "warnings": ["warn-1"],
        "erro": None,
        "artifacts": [{"name": "planta.dxf"}]
    }
    
    res = await api_obter_status_job("proj-123", "job-fc-abc")
    
    assert res["status"] == "done"
    mock_obter.assert_called_once_with("job-fc-abc")
    mock_atualizar.assert_called_once_with(
        mock_sb.return_value,
        vertex_job_id="job-fc-abc",
        status="done",
        erro=None,
        warnings=["warn-1"],
        artefatos_json={"artifacts": [{"name": "planta.dxf"}]}
    )
