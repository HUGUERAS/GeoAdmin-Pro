from __future__ import annotations

from typing import Any

import pytest
from fastapi import HTTPException

import routes.projetos as projetos_mod


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

    def insert(self, payload):
        self.action = 'insert'
        self.payload = payload
        return self

    def update(self, payload):
        self.action = 'update'
        self.payload = payload
        return self

    def eq(self, campo, valor):
        self.filters.append(('eq', campo, valor))
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


def test_validar_tipo_processo_normaliza():
    assert projetos_mod._validar_tipo_processo('seapa') == 'SEAPA'
    assert projetos_mod._validar_tipo_processo('ambos') == 'AMBOS'


def test_validar_tipo_processo_rejeita_valor_invalido():
    with pytest.raises(HTTPException) as excinfo:
        projetos_mod._validar_tipo_processo('XYZ')
    assert excinfo.value.status_code == 422


def test_atualizar_projeto_persiste_tipo_processo_validado(monkeypatch):
    def resolver(query: FakeQuery):
        if query.table == 'projetos' and query.action == 'update':
            return [{'id': 'projeto-1', **query.payload}]
        raise AssertionError(f'Consulta inesperada: {query.table}/{query.action}')

    sb = FakeSupabase(resolver)
    monkeypatch.setattr(projetos_mod, '_get_supabase', lambda: sb)
    monkeypatch.setattr(projetos_mod, '_projeto_ou_404', lambda _sb, _projeto_id: {'id': 'projeto-1'})
    monkeypatch.setattr(projetos_mod, '_enriquecer_projeto', lambda _sb, _projeto_id: {'id': _projeto_id, 'tipo_processo': 'SEAPA'})

    resultado = projetos_mod.atualizar_projeto(
        'projeto-1',
        projetos_mod.ProjetoUpdate(tipo_processo='seapa'),
    )

    assert resultado['tipo_processo'] == 'SEAPA'
    assert sb.calls[-1].payload['tipo_processo'] == 'SEAPA'
