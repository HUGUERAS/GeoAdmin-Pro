from __future__ import annotations

import io
from pathlib import Path
import zipfile

from integracoes import areas_projeto as areas_mod


class FakeResponse:
    def __init__(self, data):
        self.data = data


class FakeQuery:
    def __init__(self, supabase: 'FakeSupabase', table: str):
        self.supabase = supabase
        self.table = table
        self.action = 'select'
        self.payload = None
        self.filters: list[tuple[str, object, object]] = []

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
        self.supabase.calls.append(self)
        return FakeResponse(self.supabase.resolver(self))


class FakeSupabase:
    def __init__(self, resolver):
        self.resolver = resolver
        self.calls: list[FakeQuery] = []

    def table(self, nome: str):
        return FakeQuery(self, nome)


def test_salvar_area_e_listar_com_resumo():
    tabela: dict[str, dict[str, object]] = {}

    def resolver(query: FakeQuery):
        if query.table != 'areas_projeto':
            raise AssertionError(f'Tabela inesperada: {query.table}')

        if query.action == 'insert':
            payload = dict(query.payload)
            tabela[payload['id']] = payload
            return [payload]

        if query.action == 'update':
            area_id = next((f[2] for f in query.filters if f[0] == 'eq' and f[1] == 'id'), None)
            atual = tabela[area_id]
            atual.update(query.payload)
            tabela[area_id] = atual
            return [atual]

        if query.action == 'select':
            if any(f[0] == 'eq' and f[1] == 'id' for f in query.filters):
                area_id = next(f[2] for f in query.filters if f[0] == 'eq' and f[1] == 'id')
                item = tabela.get(area_id)
                if item and not item.get('deleted_at'):
                    return item
                return None
            projeto_id = next((f[2] for f in query.filters if f[0] == 'eq' and f[1] == 'projeto_id'), None)
            return [item for item in tabela.values() if item.get('projeto_id') == projeto_id and not item.get('deleted_at')]

        raise AssertionError(f'Acao inesperada: {query.action}')

    sb = FakeSupabase(resolver)

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
        sb=sb,
    )

    assert area['status_geometria'] == 'apenas_esboco'
    assert area['resumo_ativo']['vertices_total'] == 4
    assert areas_mod.listar_areas_projeto('projeto-1', sb=sb)[0]['nome'] == 'Área A'


def test_detectar_confrontacoes_identifica_sobreposicao():
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


def test_gerar_cartas_confrontacao_zip_com_template_docx():
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
        projeto={'id': 'projeto-1', 'projeto_nome': 'Projeto Teste', 'municipio': 'Jaraguá', 'comarca': 'Jaraguá'},
        areas=areas,
        confrontacoes=confrontacoes,
    )

    pacote = zipfile.ZipFile(io.BytesIO(zip_bytes))
    assert 'CARTA_CONFRONTACAO_01.docx' in pacote.namelist()
    assert 'manifesto_cartas.json' in pacote.namelist()


def test_gerar_cartas_confrontacao_zip_fallback_txt(monkeypatch):
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
    monkeypatch.setattr(areas_mod, 'TEMPLATE_CARTA_CONFRONTACAO', Path('C:/arquivo/inexistente/carta.docx'))

    zip_bytes = areas_mod.gerar_cartas_confrontacao_zip(
        projeto={'id': 'projeto-1', 'projeto_nome': 'Projeto Teste'},
        areas=areas,
        confrontacoes=confrontacoes,
    )

    pacote = zipfile.ZipFile(io.BytesIO(zip_bytes))
    assert 'CARTA_CONFRONTACAO_01.txt' in pacote.namelist()
    assert 'Projeto Teste' in pacote.read('CARTA_CONFRONTACAO_01.txt').decode('utf-8')
