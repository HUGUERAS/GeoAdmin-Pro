from __future__ import annotations

from typing import Any

import routes.documentos as documentos_mod


class FakeResponse:
    def __init__(self, data):
        self.data = data


class FakeQuery:
    def __init__(self, supabase: 'FakeSupabase', table: str):
        self.supabase = supabase
        self.table = table
        self.action = 'select'
        self.filters: list[tuple[str, Any, Any]] = []

    def select(self, _campos: str):
        self.action = 'select'
        return self

    def eq(self, campo, valor):
        self.filters.append(('eq', campo, valor))
        return self

    def maybe_single(self):
        return self

    def execute(self):
        return FakeResponse(self.supabase.resolver(self))


class FakeTable:
    def __init__(self, supabase: 'FakeSupabase', table: str):
        self.supabase = supabase
        self.table = table

    def select(self, campos: str):
        return FakeQuery(self.supabase, self.table).select(campos)


class FakeSupabase:
    def __init__(self, resolver):
        self.resolver = resolver

    def table(self, nome: str):
        return FakeTable(self, nome)


def test_contexto_token_restringe_ao_participante(monkeypatch):
    monkeypatch.setattr(documentos_mod, 'obter_vinculo_por_token', lambda _sb, token: {
        'id': 'pc-1',
        'projeto_id': 'proj-1',
        'cliente_id': 'cli-1',
        'papel': 'coproprietario',
        'principal': False,
        'recebe_magic_link': True,
        'area_id': 'area-1',
        'magic_link_expira': '2099-01-01T00:00:00+00:00',
    })

    def resolver(query: FakeQuery):
        filtros = {(op, campo): valor for op, campo, valor in query.filters}
        if query.table == 'clientes':
            return {
                'id': 'cli-1',
                'nome': 'Hugo Henrique',
                'formulario_ok': False,
                'formulario_em': None,
                'magic_link_expira': None,
            }
        if query.table == 'vw_projetos_completo':
            return {
                'id': 'proj-1',
                'projeto_nome': 'Projeto Boa Vista',
                'municipio': 'Morrinhos',
                'estado': 'GO',
                'status': 'medicao',
            }
        if query.table == 'areas_projeto' and filtros.get(('eq', 'id')) == 'area-1':
            return {
                'id': 'area-1',
                'nome': 'Área 1',
                'municipio': 'Morrinhos',
                'estado': 'GO',
                'proprietario_nome': 'Hugo Henrique',
                'origem_tipo': 'formulario',
                'resumo_esboco': {'vertices_total': 4},
                'resumo_final': None,
            }
        raise AssertionError(f'Consulta inesperada: {query.table}')

    contexto = documentos_mod._contexto_token(FakeSupabase(resolver), 'token-1')

    assert contexto['cliente']['nome'] == 'Hugo Henrique'
    assert contexto['participante']['papel'] == 'coproprietario'
    assert contexto['participante']['area_id'] == 'area-1'
    assert contexto['area']['nome'] == 'Área 1'
    assert contexto['projeto']['projeto_nome'] == 'Projeto Boa Vista'
