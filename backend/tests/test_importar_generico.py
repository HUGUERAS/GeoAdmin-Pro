import io
import asyncio
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from fastapi import UploadFile

from routes.importar_generico import importar_pontos_genericos


# ── Mocks para Supabase ────────────────────────────────────────────────────────
@pytest.fixture
def mock_supabase():
    with patch("main.get_supabase") as mock_get:
        mock_client = MagicMock()
        mock_get.return_value = mock_client
        yield mock_client


# ── Testes de Ingestão de Pontos Genéricos ─────────────────────────────────────
def test_importar_pontos_txt_sucesso(mock_supabase):
    async def run():
        # 1. Configura mock do projeto ativo no Supabase
        mock_projeto = MagicMock()
        mock_projeto.data = {"id": "proj-uuid-123", "nome": "santa maria", "zona_utm": "23S"}
        mock_supabase.table().select().eq().maybe_single().execute.return_value = mock_projeto

        # 2. Configura mock de pontos existentes (não duplicado)
        mock_existente = MagicMock()
        mock_existente.data = None
        mock_supabase.table().select().eq().eq().maybe_single().execute.return_value = mock_existente

        # 3. Configura mock de inserção com sucesso
        mock_insercao = MagicMock()
        mock_insercao.data = [{
            "id": "ponto-uuid-001",
            "nome": "PT01",
            "norte": 7859000.0,
            "este": 257000.0,
            "cota": 700.0,
            "lat": -15.7801,
            "lon": -47.9292
        }]
        mock_supabase.table().insert().execute.return_value = mock_insercao

        # 4. Cria arquivo UploadFile
        conteudo_arquivo = "PT01,7859000.0,257000.0,700.0\nPT02,7859100.0,257100.0,701.0\n"
        arquivo_upload = UploadFile(
            filename="santa_maria_pontos.txt",
            file=io.BytesIO(conteudo_arquivo.encode("latin-1"))
        )

        # 5. Executa a corrotina da rota diretamente
        resultado = await importar_pontos_genericos(
            projeto_id="proj-uuid-123",
            arquivo=arquivo_upload,
            aplicar_geoide=True,
            apenas_preview=False
        )

        # 6. Validações
        assert resultado.projeto_id == "proj-uuid-123"
        assert resultado.total_lidos == 2
        assert resultado.inseridos == 2
        assert resultado.duplicados == 0
        assert len(resultado.pontos) == 2

    asyncio.run(run())


def test_importar_pontos_kml_sucesso(mock_supabase):
    async def run():
        # 1. Configura mock do projeto ativo no Supabase
        mock_projeto = MagicMock()
        mock_projeto.data = {"id": "proj-uuid-123", "nome": "santa maria", "zona_utm": "23S"}
        mock_supabase.table().select().eq().maybe_single().execute.return_value = mock_projeto

        # 2. Configura mock de pontos existentes (não duplicado)
        mock_existente = MagicMock()
        mock_existente.data = None
        mock_supabase.table().select().eq().eq().maybe_single().execute.return_value = mock_existente

        # 3. Configura mock de inserção com sucesso
        mock_insercao = MagicMock()
        mock_insercao.data = [{"id": "ponto-uuid-kml", "nome": "PT_KML_001"}]
        mock_supabase.table().insert().execute.return_value = mock_insercao

        # 4. Cria conteúdo KML válido para o Brasil
        conteudo_kml = """<?xml version="1.0" encoding="UTF-8"?>
        <kml xmlns="http://www.opengis.net/kml/2.2">
          <Placemark>
            <name>PT_KML_001</name>
            <coordinates>-47.9292,-15.7801,700.0</coordinates>
          </Placemark>
        </kml>
        """
        arquivo_upload = UploadFile(
            filename="pontos.kml",
            file=io.BytesIO(conteudo_kml.encode("utf-8"))
        )

        resultado = await importar_pontos_genericos(
            projeto_id="proj-uuid-123",
            arquivo=arquivo_upload,
            aplicar_geoide=True,
            apenas_preview=False
        )

        assert resultado.total_lidos == 1
        assert resultado.inseridos == 1

    asyncio.run(run())
