from __future__ import annotations

from typing import Any

from postgrest.exceptions import APIError

import routes.documentos as documentos_mod


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
        self.limit_value: int | None = None

    def select(self, _campos: str):
        self.action = 'select'
        return self

    def update(self, payload):
        self.action = 'update'
        self.payload = payload
        return self

    def eq(self, campo, valor):
        self.filters.append(('eq', campo, valor))
        return self

    def limit(self, valor: int):
        self.limit_value = valor
        return self

    def execute(self):
        return FakeResponse(self.supabase.resolver(self))


class FakeTable:
    def __init__(self, supabase: 'FakeSupabase', table: str):
        self.supabase = supabase
        self.table = table

    def select(self, campos: str):
        return FakeQuery(self.supabase, self.table).select(campos)

    def update(self, payload):
        return FakeQuery(self.supabase, self.table).update(payload)


class FakeSupabase:
    def __init__(self, resolver):
        self.resolver = resolver

    def table(self, nome: str):
        return FakeTable(self, nome)


def test_payload_cliente_formulario_normaliza_documentos():
    dados = documentos_mod.DadosFormulario(
        nome='Hugo',
        cpf='123.456.789-01',
        rg='123',
        estado_civil='solteiro',
        telefone='62999999999',
        endereco='Rua Teste',
        municipio='Goiania',
        nome_imovel='Fazenda Boa Vista',
        municipio_imovel='Goiania',
        conjuge_cpf='987.654.321-00',
    )

    payload = documentos_mod._payload_cliente_formulario(dados)

    assert payload['cpf_cnpj'] == '12345678901'
    assert payload['conjuge_cpf'] == '98765432100'


def test_busca_cliente_por_documento_encontra_soft_delete_com_cpf_mascarado():
    def resolver(query: FakeQuery):
        if query.table != 'clientes' or query.action != 'select':
            raise AssertionError('Consulta inesperada')
        filtros = {(op, campo): valor for op, campo, valor in query.filters}
        if filtros.get(('eq', 'cpf_cnpj')) == '12345678901':
            return [{'id': 'cliente-existente', 'deleted_at': '2026-03-30T00:00:00+00:00'}]
        return []

    sb = FakeSupabase(resolver)
    cliente = documentos_mod._buscar_cliente_por_documento_formulario(sb, '123.456.789-01')
    assert cliente == {'id': 'cliente-existente', 'deleted_at': '2026-03-30T00:00:00+00:00'}


def test_atualizar_cliente_reaproveita_existente_quando_cpf_duplicado(monkeypatch):
    dados = documentos_mod.DadosFormulario(
        nome='Hugo',
        cpf='123.456.789-01',
        rg='123',
        estado_civil='solteiro',
        telefone='62999999999',
        endereco='Rua Teste',
        municipio='Goiania',
        nome_imovel='Fazenda Boa Vista',
        municipio_imovel='Goiania',
    )

    class SupabaseQueDuplica:
        def table(self, _nome: str):
            class Query:
                def update(self, _payload):
                    return self

                def eq(self, _campo, _valor):
                    return self

                def execute(self):
                    raise APIError({
                        'message': 'duplicate key value violates unique constraint "clientes_cpf_cnpj_key"',
                        'code': '23505',
                        'hint': None,
                        'details': 'Key (cpf_cnpj)=(12345678901) already exists.',
                    })

            return Query()

    monkeypatch.setattr(documentos_mod, '_buscar_cliente_por_documento_formulario', lambda _sb, _cpf: {'id': 'cliente-existente', 'deleted_at': '2026-03-30T00:00:00+00:00'})
    monkeypatch.setattr(documentos_mod, '_reaproveitar_cliente_existente_formulario', lambda _sb, cliente_atual_id, cliente_existente_id, _dados: cliente_existente_id)

    resultado = documentos_mod._atualizar_cliente_formulario(SupabaseQueDuplica(), 'cliente-atual', dados)

    assert resultado == 'cliente-existente'


def test_atualizar_projeto_formulario_reduz_payload_quando_schema_ainda_nao_tem_colunas_novas():
    chamadas = []

    def resolver(query: FakeQuery):
        chamadas.append(query.payload.copy())
        if query.table == 'projetos' and query.action == 'update':
            if 'endereco_imovel' in query.payload:
                raise Exception("Could not find the 'endereco_imovel' column of 'projetos' in the schema cache")
            return [{'id': 'projeto-1'}]
        raise AssertionError('Consulta inesperada')

    sb = FakeSupabase(resolver)
    dados = documentos_mod.DadosFormulario(
        nome='Hugo',
        cpf='123.456.789-01',
        rg='123',
        estado_civil='solteiro',
        telefone='62999999999',
        endereco='Rua Teste',
        municipio='Goiania',
        nome_imovel='Fazenda Boa Vista',
        municipio_imovel='Goiania',
        endereco_imovel='Estrada do Córrego Fundo',
        endereco_imovel_numero='Km 12',
        cep_imovel='76380-000',
    )

    documentos_mod._atualizar_projeto_formulario(sb, 'projeto-1', dados)

    assert len(chamadas) == 2
    assert 'endereco_imovel' in chamadas[0]
    assert 'endereco_imovel' not in chamadas[1]
    assert chamadas[1]['nome_imovel'] == 'Fazenda Boa Vista'
