from __future__ import annotations

import io
import zipfile

from integracoes import areas_projeto as areas_mod


def test_salvar_area_e_listar_com_resumo(monkeypatch):
    store: dict[str, dict[str, object]] = {}
    monkeypatch.setattr(areas_mod, '_carregar_store', lambda: store)
    monkeypatch.setattr(areas_mod, '_salvar_store', lambda payload: store.update(payload))

    area = areas_mod.salvar_area_projeto(
        projeto_id='projeto-1',
        cliente_id='cliente-1',
        nome='Área A',
        proprietario_nome='João',
        municipio='Jaraguá',
        geometria_esboco=[
            {'lon': -49.0, 'lat': -14.0},
            {'lon': -49.0, 'lat': -14.001},
            {'lon': -48.999, 'lat': -14.001},
            {'lon': -48.999, 'lat': -14.0},
        ],
    )

    assert area['status_geometria'] == 'apenas_esboco'
    assert area['resumo_ativo']['vertices_total'] == 4
    assert areas_mod.listar_areas_projeto('projeto-1')[0]['nome'] == 'Área A'


def test_detectar_confrontacoes_identifica_sobreposicao(monkeypatch):
    area_a = {
        'id': 'a',
        'nome': 'Área A',
        'proprietario_nome': 'João',
        'geometria_final': [
            {'lon': -49.0, 'lat': -14.0},
            {'lon': -49.0, 'lat': -14.002},
            {'lon': -48.998, 'lat': -14.002},
            {'lon': -48.998, 'lat': -14.0},
        ],
        'geometria_esboco': [],
    }
    area_b = {
        'id': 'b',
        'nome': 'Área B',
        'proprietario_nome': 'Maria',
        'geometria_final': [
            {'lon': -48.9995, 'lat': -14.0005},
            {'lon': -48.9995, 'lat': -14.0025},
            {'lon': -48.9975, 'lat': -14.0025},
            {'lon': -48.9975, 'lat': -14.0005},
        ],
        'geometria_esboco': [],
    }

    confrontacoes = areas_mod.detectar_confrontacoes([area_a, area_b])

    assert len(confrontacoes) == 1
    assert confrontacoes[0]['tipo'] == 'sobreposicao'
    assert confrontacoes[0]['area_a']['nome'] == 'Área A'


def test_gerar_cartas_confrontacao_zip():
    areas = [
        {'id': 'a', 'nome': 'Área A', 'proprietario_nome': 'João', 'matricula': 'MAT-1'},
        {'id': 'b', 'nome': 'Área B', 'proprietario_nome': 'Maria', 'matricula': 'MAT-2'},
    ]
    confrontacoes = [
        {
            'id': 'a::b',
            'tipo': 'divisa',
            'contato_m': 128.4,
            'area_intersecao_ha': 0.0,
            'area_a': {'id': 'a', 'nome': 'Área A'},
            'area_b': {'id': 'b', 'nome': 'Área B'},
        }
    ]

    zip_bytes = areas_mod.gerar_cartas_confrontacao_zip(
        projeto={'id': 'projeto-1', 'projeto_nome': 'Projeto Teste'},
        areas=areas,
        confrontacoes=confrontacoes,
    )

    pacote = zipfile.ZipFile(io.BytesIO(zip_bytes))
    assert 'CARTA_CONFRONTACAO_01.txt' in pacote.namelist()
    assert 'manifesto_cartas.json' in pacote.namelist()
    assert 'Projeto Teste' in pacote.read('CARTA_CONFRONTACAO_01.txt').decode('utf-8')
