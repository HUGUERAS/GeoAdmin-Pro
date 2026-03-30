from __future__ import annotations

import json
import tempfile
import zipfile
from pathlib import Path
from typing import Any

import pytest

from integracoes import referencia_cliente as ref


class FakeResponse:
    def __init__(self, data):
        self.data = data


class FakeQuery:
    def __init__(self, supabase: 'FakeSupabase', table: str):
        self.supabase = supabase
        self.table = table
        self.action = 'select'
        self.payload = None
        self.filters: list[tuple[str, Any, Any]] = []

    def select(self, *_args, **_kwargs):
        self.action = 'select'
        return self

    def eq(self, campo, valor):
        self.filters.append(('eq', campo, valor))
        return self

    def is_(self, campo, valor):
        self.filters.append(('is', campo, valor))
        return self

    def order(self, *_args, **_kwargs):
        self.filters.append(('order', _args, _kwargs))
        return self

    def limit(self, *_args, **_kwargs):
        self.filters.append(('limit', _args, _kwargs))
        return self

    def maybe_single(self):
        self.filters.append(('maybe_single', None, None))
        return self

    def update(self, payload):
        self.action = 'update'
        self.payload = payload
        return self

    def insert(self, payload):
        self.action = 'insert'
        self.payload = payload
        return self

    def execute(self):
        return FakeResponse(self.supabase.resolver(self))


class FakeSupabase:
    def __init__(self, resolver):
        self.resolver = resolver

    def table(self, nome: str):
        return FakeQuery(self, nome)


def _geojson_square() -> str:
    return json.dumps(
        {
            'type': 'FeatureCollection',
            'features': [
                {
                    'type': 'Feature',
                    'geometry': {
                        'type': 'Polygon',
                        'coordinates': [[
                            [-48.0, -14.0],
                            [-48.0, -14.001],
                            [-47.999, -14.001],
                            [-47.999, -14.0],
                            [-48.0, -14.0],
                        ]],
                    },
                }
            ],
        }
    )


def test_parse_geojson_feature_collection():
    vertices = ref.parse_geojson(_geojson_square())

    assert len(vertices) == 4
    assert vertices[0] == {'lon': -48.0, 'lat': -14.0}
    assert vertices[-1] == {'lon': -47.999, 'lat': -14.0}


def test_parse_kml_polygon():
    kml = """<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <Placemark>
      <Polygon>
        <outerBoundaryIs>
          <LinearRing>
            <coordinates>
              -48.0,-14.0,0 -48.0,-14.001,0 -47.999,-14.001,0 -47.999,-14.0,0 -48.0,-14.0,0
            </coordinates>
          </LinearRing>
        </outerBoundaryIs>
      </Polygon>
    </Placemark>
  </Document>
</kml>
"""

    vertices = ref.parse_kml(kml)

    assert len(vertices) == 4
    assert vertices[1] == {'lon': -48.0, 'lat': -14.001}


def test_parse_csv_ou_txt_com_cabecalho():
    conteudo = 'lon,lat\n-48.0,-14.0\n-48.0,-14.001\n-47.999,-14.001\n-47.999,-14.0\n'

    vertices = ref.parse_csv_ou_txt(conteudo)

    assert len(vertices) == 4
    assert vertices[2] == {'lon': -47.999, 'lat': -14.001}


def test_parse_shp_zip():
    shapefile = pytest.importorskip('shapefile')

    with tempfile.TemporaryDirectory() as temp_dir:
        base = Path(temp_dir) / 'poligono'
        writer = shapefile.Writer(str(base), shapeType=shapefile.POLYGON)
        writer.field('nome', 'C')
        writer.poly([[(-48.0, -14.0), (-48.0, -14.001), (-47.999, -14.001), (-47.999, -14.0), (-48.0, -14.0)]])
        writer.record('A')
        writer.close()

        zip_path = Path(temp_dir) / 'poligono.zip'
        with zipfile.ZipFile(zip_path, 'w') as zf:
            for ext in ('.shp', '.shx', '.dbf'):
                zf.write(str(base) + ext, arcname='poligono' + ext)

        vertices = ref.parse_shp_zip(zip_path.read_bytes())

    assert len(vertices) == 4
    assert vertices[0] == {'lon': -48.0, 'lat': -14.0}


def test_salvar_geometria_referencia_upsert_no_supabase():
    vertices = [
        {'lon': -48.0, 'lat': -14.0},
        {'lon': -48.0, 'lat': -14.001},
        {'lon': -47.999, 'lat': -14.001},
    ]
    tabela: dict[str, dict[str, Any]] = {}

    def resolver(query: FakeQuery):
        if query.table != 'geometrias_referencia_cliente':
            raise AssertionError(f'Tabela inesperada: {query.table}')

        if query.action == 'select':
            ativos = [item for item in tabela.values() if not item.get('deleted_at')]
            cliente_id = next((f[2] for f in query.filters if f[0] == 'eq' and f[1] == 'cliente_id'), None)
            ativos = [item for item in ativos if item.get('cliente_id') == cliente_id]
            ativos.sort(key=lambda item: item.get('atualizado_em') or '', reverse=True)
            return ativos[0] if ativos else None

        if query.action == 'insert':
            payload = dict(query.payload)
            payload['id'] = payload.get('id') or 'ref-1'
            payload['atualizado_em'] = payload.get('atualizado_em') or '2026-03-29T00:00:00+00:00'
            tabela[payload['id']] = payload
            return [payload]

        if query.action == 'update':
            area_id = next((f[2] for f in query.filters if f[0] == 'eq' and f[1] == 'id'), None)
            atual = tabela[area_id]
            atual.update(query.payload)
            atual['id'] = area_id
            atual['atualizado_em'] = atual.get('atualizado_em') or '2026-03-29T00:00:00+00:00'
            tabela[area_id] = atual
            return [atual]

        raise AssertionError(f'Acao inesperada: {query.action}')

    sb = FakeSupabase(resolver)

    resultado = ref.salvar_geometria_referencia(
        sb=sb,
        cliente_id='cliente-1',
        projeto_id='projeto-1',
        nome='Croqui 1',
        origem_tipo='manual',
        formato='manual',
        arquivo_nome=None,
        vertices=vertices,
        comparativo=None,
    )

    assert resultado['persistencia'] == 'supabase'
    assert resultado['nome'] == 'Croqui 1'
    assert resultado['resumo']['vertices_total'] == 3


def test_remover_geometria_referencia_soft_delete_no_supabase():
    tabela = {
        'ref-1': {
            'id': 'ref-1',
            'cliente_id': 'cliente-1',
            'projeto_id': 'projeto-1',
            'nome': 'Croqui 1',
            'deleted_at': None,
            'atualizado_em': '2026-03-29T00:00:00+00:00',
        }
    }

    def resolver(query: FakeQuery):
        if query.table != 'geometrias_referencia_cliente':
            raise AssertionError(f'Tabela inesperada: {query.table}')

        if query.action == 'select':
            ativos = [item for item in tabela.values() if not item.get('deleted_at')]
            cliente_id = next((f[2] for f in query.filters if f[0] == 'eq' and f[1] == 'cliente_id'), None)
            ativos = [item for item in ativos if item.get('cliente_id') == cliente_id]
            ativos.sort(key=lambda item: item.get('atualizado_em') or '', reverse=True)
            return ativos[0] if ativos else None

        if query.action == 'update':
            ref_id = next((f[2] for f in query.filters if f[0] == 'eq' and f[1] == 'id'), None)
            atual = tabela[ref_id]
            atual.update(query.payload)
            tabela[ref_id] = atual
            return [atual]

        raise AssertionError(f'Acao inesperada: {query.action}')

    sb = FakeSupabase(resolver)

    removido = ref.remover_geometria_referencia(sb, 'cliente-1')

    assert removido is True
    assert tabela['ref-1']['deleted_at'] is not None
