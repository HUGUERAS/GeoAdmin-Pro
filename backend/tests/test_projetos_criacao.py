from __future__ import annotations

import pytest
from fastapi import HTTPException

import routes.projetos as projetos_mod


class FakeResponse:
    def __init__(self, data):
        self.data = data


class FakeQuery:
    def __init__(self, supabase: "FakeSupabase", table: str):
        self.supabase = supabase
        self.table = table
        self.payload = None
        self.filters: list[tuple[str, str, object]] = []

    def update(self, payload):
        self.payload = payload
        return self

    def eq(self, campo, valor):
        self.filters.append(("eq", campo, valor))
        return self

    def is_(self, campo, valor):
        self.filters.append(("is", campo, valor))
        return self

    def execute(self):
        self.supabase.calls.append((self.table, self.payload, list(self.filters)))
        return FakeResponse([{"id": "proj-1"}])


class FakeSupabase:
    def __init__(self):
        self.calls = []

    def table(self, nome: str):
        return FakeQuery(self, nome)


def test_reverter_criacao_projeto_soft_delete_projeto_e_participantes():
    sb = FakeSupabase()

    projetos_mod._reverter_criacao_projeto(sb, "proj-1")

    assert sb.calls[0][0] == "projeto_clientes"
    assert sb.calls[0][2][0] == ("eq", "projeto_id", "proj-1")
    assert sb.calls[1][0] == "projetos"
    assert sb.calls[1][2][0] == ("eq", "id", "proj-1")


def test_criar_projeto_reverte_quando_etapa_posterior_falha(monkeypatch):
    chamadas_reversao = []

    monkeypatch.setattr(projetos_mod, "_get_supabase", lambda: object())
    monkeypatch.setattr(projetos_mod, "_participantes_payload", lambda payload: [])
    monkeypatch.setattr(projetos_mod, "_cliente_principal_do_payload", lambda sb, participantes, payload: "cli-1")
    monkeypatch.setattr(projetos_mod, "_inserir_projeto_compativel", lambda sb, dados: FakeResponse([{"id": "proj-1"}]))
    monkeypatch.setattr(projetos_mod, "_enriquecer_projeto", lambda sb, projeto_id: (_ for _ in ()).throw(RuntimeError("falha no enrich")))
    monkeypatch.setattr(projetos_mod, "_reverter_criacao_projeto", lambda sb, projeto_id: chamadas_reversao.append(projeto_id))

    payload = projetos_mod.ProjetoCreate(nome="Projeto Teste")

    with pytest.raises(HTTPException) as excinfo:
        projetos_mod.criar_projeto(payload)

    assert excinfo.value.status_code == 500
    assert chamadas_reversao == ["proj-1"]
