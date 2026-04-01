from __future__ import annotations

from typing import Any

import pytest
from fastapi import HTTPException

import routes.documentos as documentos_mod


class FakeResponse:
    def __init__(self, data):
        self.data = data


class FakeQuery:
    def __init__(self, supabase: "FakeSupabase", table: str):
        self.supabase = supabase
        self.table = table
        self.action = "select"
        self.filters: list[tuple[str, Any, Any]] = []

    def select(self, _campos: str):
        self.action = "select"
        return self

    def eq(self, campo, valor):
        self.filters.append(("eq", campo, valor))
        return self

    def is_(self, campo, valor):
        self.filters.append(("is", campo, valor))
        return self

    def order(self, *_args, **_kwargs):
        return self

    def limit(self, *_args, **_kwargs):
        return self

    def maybe_single(self):
        return self

    def single(self):
        return self

    def execute(self):
        return FakeResponse(self.supabase.resolver(self))


class FakeTable:
    def __init__(self, supabase: "FakeSupabase", table: str):
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
    monkeypatch.setattr(documentos_mod, "obter_vinculo_por_token", lambda _sb, token: {
        "id": "pc-1",
        "projeto_id": "proj-1",
        "cliente_id": "cli-1",
        "papel": "coproprietario",
        "principal": False,
        "recebe_magic_link": True,
        "area_id": "area-1",
        "magic_link_expira": "2099-01-01T00:00:00+00:00",
    })

    def resolver(query: FakeQuery):
        filtros = {(op, campo): valor for op, campo, valor in query.filters}
        if query.table == "clientes":
            return {
                "id": "cli-1",
                "nome": "Hugo Henrique",
                "formulario_ok": False,
                "formulario_em": None,
                "magic_link_expira": None,
            }
        if query.table == "vw_projetos_completo":
            return {
                "id": "proj-1",
                "projeto_nome": "Projeto Boa Vista",
                "municipio": "Morrinhos",
                "estado": "GO",
                "status": "medicao",
            }
        if query.table == "areas_projeto" and filtros.get(("eq", "id")) == "area-1":
            return {
                "id": "area-1",
                "nome": "Área 1",
                "municipio": "Morrinhos",
                "estado": "GO",
                "proprietario_nome": "Hugo Henrique",
                "origem_tipo": "formulario",
                "resumo_esboco": {"vertices_total": 4},
                "resumo_final": None,
            }
        raise AssertionError(f"Consulta inesperada: {query.table}")

    contexto = documentos_mod._contexto_token(FakeSupabase(resolver), "token-1")

    assert contexto["cliente"]["nome"] == "Hugo Henrique"
    assert contexto["participante"]["papel"] == "coproprietario"
    assert contexto["participante"]["area_id"] == "area-1"
    assert contexto["area"]["nome"] == "Área 1"
    assert contexto["projeto"]["projeto_nome"] == "Projeto Boa Vista"


def test_token_legado_ambiguo_pede_novo_link(monkeypatch):
    monkeypatch.setattr(documentos_mod, "obter_vinculo_por_token", lambda _sb, _token: None)

    def resolver(query: FakeQuery):
        filtros = {(op, campo): valor for op, campo, valor in query.filters}
        if query.table == "clientes":
            return {
                "id": "cli-1",
                "nome": "Cliente Antigo",
                "formulario_ok": False,
                "formulario_em": None,
                "magic_link_expira": "2099-01-01T00:00:00+00:00",
                "magic_link_token": "token-legado",
            }
        if query.table == "projeto_clientes" and filtros.get(("eq", "cliente_id")) == "cli-1":
            return [
                {"id": "pc-1", "projeto_id": "proj-1", "cliente_id": "cli-1"},
                {"id": "pc-2", "projeto_id": "proj-2", "cliente_id": "cli-1"},
            ]
        raise AssertionError(f"Consulta inesperada: {query.table}")

    with pytest.raises(HTTPException) as excinfo:
        documentos_mod._validar_token(FakeSupabase(resolver), "token-legado")

    assert excinfo.value.status_code == 409
    assert excinfo.value.detail["codigo"] == 603


def test_gerar_magic_link_participante_registra_evento(monkeypatch):
    eventos = []

    monkeypatch.setattr(documentos_mod, "listar_participantes_projeto", lambda _sb, _projeto_id: [{
        "id": "pc-1",
        "cliente_id": "cli-1",
        "nome": "Hugo Henrique",
        "papel": "principal",
        "principal": True,
        "recebe_magic_link": True,
        "area_id": "area-1",
        "magic_link_token": None,
    }])
    monkeypatch.setattr(documentos_mod, "gerar_magic_link_participante", lambda _sb, _projeto_id, **_kwargs: {
        "id": "pc-1",
        "cliente_id": "cli-1",
        "nome": "Hugo Henrique",
        "papel": "principal",
        "principal": True,
        "recebe_magic_link": True,
        "area_id": "area-1",
        "magic_link_token": "token-pc-1",
        "magic_link_expira": "2099-01-01T00:00:00+00:00",
    })
    monkeypatch.setattr(documentos_mod, "registrar_evento_magic_link", lambda _sb, **payload: eventos.append(payload) or payload)

    def resolver(query: FakeQuery):
        filtros = {(op, campo): valor for op, campo, valor in query.filters}
        if query.table == "vw_projetos_completo":
            return {"id": "proj-1", "projeto_nome": "Projeto Boa Vista", "cliente_id": "cli-1", "cliente_nome": "Hugo Henrique"}
        if query.table == "clientes" and filtros.get(("eq", "id")) == "cli-1":
            return {"id": "cli-1", "nome": "Hugo Henrique"}
        raise AssertionError(f"Consulta inesperada: {query.table} {query.filters}")

    resposta = documentos_mod.gerar_magic_link("proj-1", projeto_cliente_id="pc-1", supabase=FakeSupabase(resolver))

    assert resposta["projeto_cliente_id"] == "pc-1"
    assert resposta["area_id"] == "area-1"
    assert eventos
    assert eventos[0]["tipo_evento"] == "gerado"
    assert eventos[0]["projeto_cliente_id"] == "pc-1"
