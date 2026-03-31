from __future__ import annotations

import integracoes.projeto_clientes as projeto_clientes_mod


def test_normalizar_participantes_respeita_magic_link_e_um_principal():
    participantes = projeto_clientes_mod.normalizar_participantes_entrada([
        {
            'nome': 'Cliente Principal',
            'cpf': '123.456.789-01',
            'papel': 'principal',
            'principal': True,
            'gerar_magic_link': False,
        },
        {
            'nome': 'Coproprietario',
            'cpf': '987.654.321-00',
            'papel': 'coproprietario',
            'principal': True,
            'gerar_magic_link': True,
        },
    ])

    assert len(participantes) == 2
    assert participantes[0]['principal'] is True
    assert participantes[1]['principal'] is False
    assert participantes[0]['papel'] == 'principal'
    assert participantes[0]['recebe_magic_link'] is False
    assert participantes[1]['recebe_magic_link'] is True
    assert participantes[0]['cpf'] == '12345678901'


class FakeResponse:
    def __init__(self, data):
        self.data = data


class FakeQuery:
    def __init__(self, supabase, table: str):
        self.supabase = supabase
        self.table = table
        self.action = 'select'
        self.payload = None
        self.filters: list[tuple[str, str, object]] = []

    def select(self, *_args, **_kwargs):
        self.action = 'select'
        return self

    def is_(self, campo, valor):
        self.filters.append(('is', campo, valor))
        return self

    def eq(self, campo, valor):
        self.filters.append(('eq', campo, valor))
        return self

    def in_(self, campo, valor):
        self.filters.append(('in', campo, valor))
        return self

    def order(self, *_args, **_kwargs):
        return self

    def execute(self):
        return FakeResponse(self.supabase.resolver(self))


class FakeSupabase:
    def __init__(self, resolver):
        self.resolver = resolver

    def table(self, nome: str):
        return FakeQuery(self, nome)


def test_listar_participantes_area_reaproveita_vinculo_do_projeto():
    def resolver(query: FakeQuery):
        if query.table == 'area_clientes':
            raise RuntimeError('area_clientes indisponivel no schema local')
        raise AssertionError(f'Tabela inesperada: {query.table}')

    areas = [{'id': 'area-1', 'cliente_id': 'cli-1', 'proprietario_nome': 'Maria'}]
    participantes_projeto = [{
        'id': 'pc-1',
        'cliente_id': 'cli-1',
        'area_id': 'area-1',
        'papel': 'coproprietario',
        'principal': False,
        'recebe_magic_link': True,
        'ordem': 0,
        'nome': 'Maria',
        'cpf': '123',
        'telefone': '62999999999',
        'email': 'maria@example.com',
    }]

    mapa = projeto_clientes_mod.listar_participantes_area(
        FakeSupabase(resolver),
        areas,
        participantes_projeto=participantes_projeto,
    )

    assert len(mapa['area-1']) == 1
    assert mapa['area-1'][0]['cliente_id'] == 'cli-1'
    assert mapa['area-1'][0]['papel'] == 'coproprietario'
