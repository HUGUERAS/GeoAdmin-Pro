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


def test_salvar_participantes_projeto_em_lote_mescla_projeto_e_area():
    tabela_projeto_clientes = [
        {
            'id': 'pc-1',
            'projeto_id': 'proj-1',
            'cliente_id': 'cli-1',
            'papel': 'principal',
            'principal': True,
            'recebe_magic_link': True,
            'ordem': 0,
            'area_id': None,
            'magic_link_token': None,
            'magic_link_expira': None,
            'clientes': {'id': 'cli-1', 'nome': 'Titular', 'cpf_cnpj': '111', 'cpf': '111', 'telefone': '6299', 'email': None, 'formulario_ok': False, 'formulario_em': None, 'deleted_at': None},
        },
    ]
    tabela_area_clientes = []
    clientes = {
        'cli-1': {'id': 'cli-1', 'nome': 'Titular', 'cpf_cnpj': '111', 'cpf': '111', 'telefone': '6299', 'email': None, 'formulario_ok': False, 'formulario_em': None, 'deleted_at': None},
        'cli-2': {'id': 'cli-2', 'nome': 'Coproprietario', 'cpf_cnpj': '222', 'cpf': '222', 'telefone': '6288', 'email': None, 'formulario_ok': False, 'formulario_em': None, 'deleted_at': None},
    }

    class FakeResponse:
        def __init__(self, data):
            self.data = data

    class FakeQueryMut(FakeQuery):
        def update(self, payload):
            self.action = 'update'
            self.payload = payload
            return self

        def insert(self, payload):
            self.action = 'insert'
            self.payload = payload
            return self

    class FakeSupabaseMut(FakeSupabase):
        def table(self, nome: str):
            return FakeQueryMut(self, nome)

    def resolver(query: FakeQueryMut):
        if query.table == 'projeto_clientes':
            if query.action == 'select':
                return tabela_projeto_clientes
            if query.action == 'update':
                return []
            if query.action == 'insert':
                registros = query.payload if isinstance(query.payload, list) else [query.payload]
                tabela_projeto_clientes.clear()
                for indice, item in enumerate(registros):
                    tabela_projeto_clientes.append({
                        **item,
                        'id': f'pc-{indice + 1}',
                        'magic_link_token': None,
                        'magic_link_expira': None,
                        'clientes': clientes[item['cliente_id']],
                    })
                return tabela_projeto_clientes
        if query.table == 'area_clientes':
            if query.action == 'update':
                return []
            if query.action == 'insert':
                registros = query.payload if isinstance(query.payload, list) else [query.payload]
                tabela_area_clientes[:] = registros
                return registros
            if query.action == 'select':
                return []
        if query.table == 'clientes':
            if query.action == 'select':
                campo = next((f[1] for f in query.filters if f[0] == 'eq'), None)
                valor = next((f[2] for f in query.filters if f[0] == 'eq'), None)
                for cliente in clientes.values():
                    if cliente.get(campo) == valor:
                        return [cliente]
                return []
            if query.action == 'update':
                return []
            if query.action == 'insert':
                registros = query.payload if isinstance(query.payload, list) else [query.payload]
                return registros
        raise AssertionError(f'Tabela inesperada: {query.table} {query.action}')

    resultado = projeto_clientes_mod.salvar_participantes_projeto_em_lote(
        FakeSupabaseMut(resolver),
        'proj-1',
        [{
            'area_id': 'area-1',
            'participantes': [{
                'cliente_id': 'cli-2',
                'nome': 'Coproprietario',
                'cpf': '222',
                'telefone': '6288',
                'papel': 'coproprietario',
                'principal': False,
                'recebe_magic_link': True,
            }],
        }],
    )

    assert len(resultado['participantes_projeto']) == 2
    assert resultado['participantes_area']['area-1'][0]['cliente_id'] == 'cli-2'
