from routes import pontos as pontos_mod


def _ponto_payload(**overrides):
    base = {
        "projeto_id": "projeto-1",
        "area_id": "area-1",
        "nome": "P01",
        "lat": -16.397,
        "lon": -42.970,
        "norte": 8186000.0,
        "este": 512000.0,
        "cota": 980.5,
    }
    base.update(overrides)
    return pontos_mod.PontoCreate(**base)


def test_normalizar_ponto_preserva_area_id_para_operacao_por_lote():
    ponto = _ponto_payload()

    dados = pontos_mod._normalizar_ponto(ponto)

    assert dados["area_id"] == "area-1"
