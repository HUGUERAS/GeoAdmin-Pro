"""
GeoAdmin Pro - Testes de Integração de CAD (Contrato e Persistência)

Valida o empacotamento do contrato VERTEXROSEA e as rotas de contingência 
de persistência de status do Job.
"""

import pytest
from unittest.mock import MagicMock, patch
from integracoes.contrato_vertex import montar_contrato_vertex
from integracoes.freecad.generador_plantas import DadosPlantaTecnica
from integracoes.jobs_cad import registrar_job_cad, atualizar_status_job_cad

def test_montar_contrato_vertex_sucesso():
    """Valida montagem do contrato JSON com base nos dados reais do projeto."""
    dados_mock = DadosPlantaTecnica(
        projeto_id="projeto-uuid",
        projeto_nome="Fazenda Modelo",
        numero_job="JOB-100",
        nome_imovel="Fazenda Modelo",
        municipio="Goiânia",
        estado="GO",
        matricula="999",
        comarca="Goiânia",
        area_ha=10.0,
        area_m2=100000.0,
        perimetro_m=1200.0,
        vertices=[
            {"x": 100.0, "y": 200.0, "z": 10.0, "codigo": "M01"}
        ],
        centroide={"x": 100.0, "y": 200.0},
        bbox={"min_x": 90.0, "max_x": 110.0, "min_y": 190.0, "max_y": 210.0},
        cliente_nome="Pedro Silva",
        cliente_cpf="111.111.111-11",
        cliente_documento="RG-99",
        tecnico_nome="Hugo Topografo",
        tecnico_crt="CRT-12",
        tecnico_crea="CREA-99",
        tecnico_cpf="222.222.222-22",
        tecnico_codigo_incra="INCRA-333",
        confrontantes=[
            {"lado": "Norte", "nome": "Vizinho A", "cpf": "333.333.333-33"}
        ],
        pontos_ammarracao=[]
    )

    contrato = montar_contrato_vertex(dados_mock)
    
    assert contrato["project_ref"]["codigo"] == "Fazenda Modelo"
    assert contrato["property"]["municipio"] == "Goiânia"
    assert contrato["perimeter"]["vertices"][0]["codigo"] == "M01"
    assert contrato["abutters"][0]["nome"] == "Vizinho A"
    assert contrato["surveyor"]["nome"] == "Hugo Topografo"


def test_registrar_job_cad_fallback():
    """Valida contingência automática gravando em eventos_cartograficos caso jobs_cad falhe."""
    sb_mock = MagicMock()
    
    # Simula erro de tabela inexistente jobs_cad ao executar a query
    sb_mock.table.side_effect = Exception("Table 'jobs_cad' not found")
    
    with patch("integracoes.jobs_cad.registrar_evento_cartografico") as mock_evento:
        res = registrar_job_cad(sb_mock, "projeto-uuid", "vertex-job-abc")
        
        # O retorno deve ser o dict do job
        assert res["vertex_job_id"] == "vertex-job-abc"
        
        # Deve ter ativado o fallback e registrado o evento cartográfico de auditoria
        mock_evento.assert_called_once()
        args, kwargs = mock_evento.call_args
        assert kwargs["projeto_id"] == "projeto-uuid"
        assert kwargs["payload"]["vertex_job_id"] == "vertex-job-abc"
        assert kwargs["payload"]["jobs_cad_sucesso"] is False
