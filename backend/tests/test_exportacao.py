from __future__ import annotations

import io
import json
import zipfile

from integracoes import integracao_metrica as metrica_mod
from integracoes.integracao_metrica import PacoteMetrica
import routes.exportacao.pacote as exportacao_pacote_mod
import routes.exportacao.routes as exportacao_mod


def test_preparar_metrica_aceita_avisos_com_unicode(monkeypatch):
    def fake_gerar_pacote_metrica(_supabase, _projeto_id: str):
        return PacoteMetrica(
            projeto_nome="Projeto Teste",
            numero_job="JOB-123",
            total_pontos=3,
            txt="P01,TP,1.000,2.000,3.000",
            csv="Nome;Codigo;Norte;Este;Cota",
            dxf=b"DXF",
            kml="<kml></kml>",
            avisos=[
                "Projeto sem numero de job — o campo 'numero_job' esta vazio. Preencha no app antes de protocolar no INCRA."
            ],
        )

    monkeypatch.setattr(metrica_mod, "gerar_pacote_metrica", fake_gerar_pacote_metrica)
    monkeypatch.setattr(
        exportacao_pacote_mod,
        "coletar_contexto_pacote",
        lambda *_args, **_kwargs: {
            "projeto": {
                "id": "projeto-1",
                "projeto_nome": "Projeto Teste",
                "numero_job": "JOB-123",
                "cliente_id": "cliente-1",
                "cliente_nome": "Maria",
                "zona_utm": "23S",
                "status": "medicao",
            },
            "cliente": {"id": "cliente-1", "nome": "Maria"},
            "pontos": [{"nome": "P01", "norte": 1.0, "este": 2.0, "cota": 3.0}],
            "confrontantes": [{"id": "conf-1", "nome": "Vizinho"}],
            "documentos": [{"id": "doc-1", "tipo": "memorial"}],
            "perimetro_ativo": {
                "id": "per-1",
                "nome": "Oficial",
                "tipo": "definitivo",
                "vertices": [
                    {"lon": -49.0, "lat": -14.0},
                    {"lon": -49.0, "lat": -14.1},
                    {"lon": -49.1, "lat": -14.1},
                ],
            },
            "geometria_referencia": {
                "nome": "Croqui",
                "origem_tipo": "manual",
                "vertices": [
                    {"lon": -49.0, "lat": -14.0},
                    {"lon": -49.0, "lat": -14.05},
                    {"lon": -49.05, "lat": -14.05},
                ],
            },
            "resumo": {
                "pontos_total": 1,
                "confrontantes_total": 1,
                "documentos_total": 1,
                "perimetro_tipo": "definitivo",
                "referencia_cliente": True,
                "avisos_total": 1,
            },
        },
    )

    resposta = exportacao_mod.preparar_metrica("projeto-1", supabase=object())

    assert resposta.status_code == 200
    assert resposta.headers["x-avisos"] == "1"
    assert resposta.headers["x-aviso-detalhes"] == (
        "Projeto sem numero de job - o campo 'numero_job' esta vazio. "
        "Preencha no app antes de protocolar no INCRA."
    )

    pacote = zipfile.ZipFile(io.BytesIO(resposta.body))
    assert "GeoAdmin_JOB-123_Projeto_Teste.txt" in pacote.namelist()
    assert "GeoAdmin_JOB-123_Projeto_Teste.csv" in pacote.namelist()
    assert "GeoAdmin_JOB-123_Projeto_Teste.kml" in pacote.namelist()
    assert "GeoAdmin_JOB-123_Projeto_Teste.dxf" in pacote.namelist()
    assert "COMO_USAR_NO_METRICA.txt" in pacote.namelist()
    assert "manifesto.json" in pacote.namelist()
    assert "dados/projeto.json" in pacote.namelist()
    assert "dados/cliente.json" in pacote.namelist()
    assert "dados/confrontantes.json" in pacote.namelist()
    assert "dados/pontos.json" in pacote.namelist()
    assert "dados/perimetro_ativo.geojson" in pacote.namelist()
    assert "dados/referencia_cliente.geojson" in pacote.namelist()

    manifesto = json.loads(pacote.read("manifesto.json").decode("utf-8"))
    assert manifesto["schema"] == "geoadmin.metrica.bridge.v1"
    assert manifesto["projeto"]["id"] == "projeto-1"
    assert manifesto["cliente"]["nome"] == "Maria"
    assert manifesto["arquivos"]["perimetro_dxf"] == "GeoAdmin_JOB-123_Projeto_Teste.dxf"


def test_obter_manifesto_metrica_retorna_json_para_bridge(monkeypatch):
    monkeypatch.setattr(
        metrica_mod,
        "gerar_pacote_metrica",
        lambda *_args, **_kwargs: PacoteMetrica(
            projeto_nome="Projeto Teste",
            numero_job="JOB-123",
            total_pontos=3,
            txt="P01,TP,1.000,2.000,3.000",
            csv="Nome;Codigo;Norte;Este;Cota",
            dxf=b"DXF",
            kml="<kml></kml>",
            avisos=[],
        ),
    )
    monkeypatch.setattr(
        exportacao_pacote_mod,
        "coletar_contexto_pacote",
        lambda *_args, **_kwargs: {
            "projeto": {
                "id": "projeto-1",
                "projeto_nome": "Projeto Teste",
                "numero_job": "JOB-123",
                "cliente_id": "cliente-1",
                "cliente_nome": "Maria",
                "zona_utm": "23S",
                "status": "medicao",
            },
            "cliente": {"id": "cliente-1", "nome": "Maria"},
            "pontos": [],
            "confrontantes": [],
            "documentos": [],
            "perimetro_ativo": None,
            "geometria_referencia": None,
            "resumo": {
                "pontos_total": 0,
                "confrontantes_total": 0,
                "documentos_total": 0,
                "perimetro_tipo": None,
                "referencia_cliente": False,
                "avisos_total": 0,
            },
        },
    )

    manifesto = exportacao_mod.obter_manifesto_metrica("projeto-1", supabase=object())

    assert manifesto["schema"] == "geoadmin.metrica.bridge.v1"
    assert manifesto["projeto"]["id"] == "projeto-1"
    assert manifesto["cliente"]["nome"] == "Maria"
    assert manifesto["checklist"][0]["id"] == "importar_pontos"


