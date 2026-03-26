from __future__ import annotations

import io
import zipfile

from integracoes import integracao_metrica as metrica_mod
from integracoes.integracao_metrica import PacoteMetrica
import routes.exportacao as exportacao_mod


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
