from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any

import pytest
from fastapi import HTTPException

import routes.clientes.routes as clientes_mod


class FakeResponse:
    def __init__(self, data):
        self.data = data


class FakeQuery:
    def __init__(self, supabase: "FakeSupabase", table: str):
        self.supabase = supabase
        self.table = table
        self.action = "select"
        self.payload = None
        self.filters: list[tuple[str, Any, Any]] = []

    def select(self, *_args, **_kwargs):
        self.action = "select"
        return self

    def eq(self, campo, valor):
        self.filters.append(("eq", campo, valor))
        return self

    def in_(self, campo, valores):
        self.filters.append(("in", campo, tuple(valores)))
        return self

    def is_(self, campo, valor):
        self.filters.append(("is", campo, valor))
        return self

    def order(self, *_args, **_kwargs):
        self.filters.append(("order", _args, _kwargs))
        return self

    def limit(self, *_args, **_kwargs):
        self.filters.append(("limit", _args, _kwargs))
        return self

    def maybe_single(self):
        self.filters.append(("maybe_single", None, None))
        return self

    def update(self, payload):
        self.action = "update"
        self.payload = payload
        return self

    def insert(self, payload):
        self.action = "insert"
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


class FakeUploadFile:
    def __init__(self, filename: str, content: bytes):
        self.filename = filename
        self._content = content

    async def read(self):
        return self._content


def test_montar_resumos_clientes_e_checklist():
    clientes = [
        {
            "id": "cliente-1",
            "nome": "Joao",
            "cpf": "123",
            "telefone": "999",
            "email": "joao@exemplo.com",
            "formulario_ok": True,
            "formulario_em": "2026-03-25T10:00:00+00:00",
            "criado_em": "2026-03-24T10:00:00+00:00",
        }
    ]
    projetos = [
        {
            "id": "projeto-1",
            "cliente_id": "cliente-1",
            "projeto_nome": "Fazenda A",
            "status": "medicao",
            "criado_em": "2026-03-24T11:00:00+00:00",
        }
    ]
    formularios = [
        {
            "cliente_id": "cliente-1",
            "projeto_id": "projeto-1",
            "formulario_ok": True,
            "formulario_em": "2026-03-25T10:00:00+00:00",
            "magic_link_expira": "2026-04-01T10:00:00+00:00",
        }
    ]
    documentos = []
    confrontantes = [
        {"projeto_id": "projeto-1", "nome": "Vizinho 1", "criado_em": "2026-03-25T11:00:00+00:00"}
    ]

    resumos = clientes_mod.montar_resumos_clientes(clientes, projetos, formularios, documentos, confrontantes)
    checklist = clientes_mod.montar_checklist_projeto(
        clientes[0],
        {
            **projetos[0],
            "documentos_total": 0,
            "confrontantes_total": 1,
            "formulario_ok": True,
            "formulario_em": "2026-03-25T10:00:00+00:00",
            "magic_link_expira": "2026-04-01T10:00:00+00:00",
        },
        {"vertices": [{"lon": -48.0, "lat": -14.0}, {"lon": -48.0, "lat": -14.001}, {"lon": -47.999, "lat": -14.001}]},
    )
    alertas = clientes_mod.montar_alertas(clientes[0], projetos, [checklist])
    timeline = clientes_mod.montar_timeline(clientes[0], projetos, documentos, confrontantes)

    assert resumos[0]["status_documentacao"] == "pronto_para_documentar"
    assert resumos[0]["projetos_total"] == 1
    assert checklist["status"] == "em_andamento"
    assert checklist["concluidos"] == 5
    assert alertas == []
    assert any(evento["tipo"] == "confrontante" for evento in timeline)


def test_detalhar_cliente_agrega_dados_documentais(monkeypatch):
    cliente = {
        "id": "cliente-1",
        "nome": "Joao",
        "cpf": "123",
        "telefone": "999",
        "email": "joao@exemplo.com",
        "criado_em": "2026-03-24T10:00:00+00:00",
        "formulario_ok": True,
        "formulario_em": "2026-03-25T10:00:00+00:00",
    }
    projetos = [
        {
            "id": "projeto-1",
            "cliente_id": "cliente-1",
            "projeto_nome": "Fazenda A",
            "status": "medicao",
            "criado_em": "2026-03-24T11:00:00+00:00",
            "total_pontos": 8,
        }
    ]
    formularios = [
        {
            "projeto_id": "projeto-1",
            "cliente_id": "cliente-1",
            "formulario_ok": True,
            "formulario_em": "2026-03-25T10:00:00+00:00",
            "magic_link_expira": "2026-04-01T10:00:00+00:00",
        }
    ]
    documentos = [
        {"id": "doc-1", "projeto_id": "projeto-1", "tipo": "gprf", "gerado_em": "2026-03-25T12:00:00+00:00"}
    ]
    confrontantes = [
        {
            "id": "conf-1",
            "projeto_id": "projeto-1",
            "lado": "Norte",
            "tipo": "particular",
            "nome": "Vizinho 1",
            "cpf": "111",
            "nome_imovel": "Sitio Vizinho",
            "matricula": "MAT-1",
            "origem": "fase2",
            "criado_em": "2026-03-25T13:00:00+00:00",
        }
    ]
    geometria = {
        "id": "ref-1",
        "cliente_id": "cliente-1",
        "projeto_id": "projeto-1",
        "nome": "Croqui A",
        "origem_tipo": "manual",
        "formato": "manual",
        "vertices": [{"lon": -48.0, "lat": -14.0}, {"lon": -48.0, "lat": -14.001}, {"lon": -47.999, "lat": -14.001}],
        "resumo": {"vertices_total": 3, "area_ha": 1.0, "perimetro_m": 10.0},
        "comparativo": {"status": "proxima", "sobreposicao_percentual": 100.0},
        "atualizado_em": "2026-03-25T14:00:00+00:00",
        "persistencia": "arquivo_local",
    }

    monkeypatch.setattr(clientes_mod, "cliente_ou_404", lambda _sb, _cliente_id: cliente)
    monkeypatch.setattr(clientes_mod, "carregar_projetos", lambda _sb, _cliente_ids: projetos)
    monkeypatch.setattr(clientes_mod, "carregar_formularios", lambda _sb, _cliente_ids: formularios)
    monkeypatch.setattr(clientes_mod, "carregar_documentos", lambda _sb, _projeto_ids: documentos)
    monkeypatch.setattr(clientes_mod, "carregar_confrontantes", lambda _sb, _projeto_ids: confrontantes)
    monkeypatch.setattr(clientes_mod, "carregar_perimetros_ativos_por_projeto", lambda _projetos: {"projeto-1": {"tipo": "editado", "vertices": [{"lon": -48.0, "lat": -14.0}, {"lon": -48.0, "lat": -14.001}, {"lon": -47.999, "lat": -14.001}]}})
    monkeypatch.setattr(clientes_mod, "obter_geometria_referencia", lambda _sb, _cliente_id: geometria)

    resultado = clientes_mod.detalhar_cliente("cliente-1")

    assert resultado["resumo"]["status_documentacao"] == "documentacao_em_andamento"
    assert resultado["projetos"][0]["documentos_total"] == 1
    assert resultado["confrontantes"][0]["nome"] == "Vizinho 1"
    assert resultado["geometria_referencia"]["comparativo"]["status"] == "proxima"
    assert len(resultado["checklist"][0]["itens"]) == 6


def test_criar_confrontante_valida_vinculo_e_insere():
    def resolver(query):
        if query.table == "clientes" and query.action == "select":
            return {"id": "cliente-1", "nome": "Joao", "cpf_cnpj": None, "telefone": "999", "email": "joao@exemplo.com", "criado_em": "2026-03-24T10:00:00+00:00"}
        if query.table == "projetos" and query.action == "select":
            return {"id": "projeto-1", "cliente_id": "cliente-1"}
        if query.table == "confrontantes" and query.action == "insert":
            return [{**query.payload, "id": "conf-1"}]
        raise AssertionError(f"Consulta inesperada: {query.table}/{query.action}")

    sb = FakeSupabase(resolver)
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(clientes_mod, "get_supabase", lambda: sb)

    try:
        payload = clientes_mod.ConfrontanteCreate(
            projeto_id="projeto-1",
            nome="Vizinho 1",
            lado="Norte",
            tipo="particular",
        )
        resultado = clientes_mod.criar_confrontante("cliente-1", payload)
    finally:
        monkeypatch.undo()

    assert resultado["id"] == "conf-1"
    assert resultado["origem"] == "fase2"
    assert sb.calls[-1].table == "confrontantes"
    assert sb.calls[-1].action == "insert"


def test_atualizar_confrontante_rejeita_projeto_de_outro_cliente():
    def resolver(query):
        if query.table == "confrontantes" and query.action == "select":
            return {
                "id": "conf-1",
                "projeto_id": "projeto-1",
                "lado": "Norte",
                "tipo": "particular",
                "nome": "Vizinho 1",
                "deleted_at": None,
            }
        if query.table == "projetos" and query.action == "select":
            eq_id = next((f[2] for f in query.filters if f[0] == "eq" and f[1] == "id"), None)
            if eq_id == "projeto-1":
                return {"id": "projeto-1", "cliente_id": "cliente-1"}
            if eq_id == "projeto-2":
                return {"id": "projeto-2", "cliente_id": "cliente-2"}
            return {"id": eq_id, "cliente_id": "cliente-1"}
        raise AssertionError(f"Consulta inesperada: {query.table}/{query.action}")

    sb = FakeSupabase(resolver)
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(clientes_mod, "get_supabase", lambda: sb)

    try:
        payload = clientes_mod.ConfrontanteUpdate(projeto_id="projeto-2", nome="Vizinho 1")
        with pytest.raises(HTTPException) as excinfo:
            clientes_mod.atualizar_confrontante("cliente-1", "conf-1", payload)
    finally:
        monkeypatch.undo()

    assert excinfo.value.status_code == 404


def test_remover_confrontante_soft_delete():
    updates: dict[str, Any] = {}

    def resolver(query):
        if query.table == "confrontantes" and query.action == "select":
            if any(f[0] == "eq" and f[1] == "id" and f[2] == "conf-1" for f in query.filters):
                return {
                    "id": "conf-1",
                    "projeto_id": "projeto-1",
                    "lado": "Norte",
                    "tipo": "particular",
                    "nome": "Vizinho 1",
                    "deleted_at": None,
                }
        if query.table == "projetos" and query.action == "select":
            return {"id": "projeto-1", "cliente_id": "cliente-1", "nome": "Fazenda A"}
        if query.table == "confrontantes" and query.action == "update":
            updates.update(query.payload)
            return [{"id": "conf-1", **query.payload}]
        raise AssertionError(f"Consulta inesperada: {query.table}/{query.action}")

    sb = FakeSupabase(resolver)
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(clientes_mod, "get_supabase", lambda: sb)

    try:
        resultado = clientes_mod.remover_confrontante("cliente-1", "conf-1")
    finally:
        monkeypatch.undo()

    assert resultado["status"] == "ok"
    assert resultado["id"] == "conf-1"
    assert "deleted_at" in updates


def test_atualizar_cliente_persiste_campos():
    def resolver(query):
        if query.table == "clientes" and query.action == "select":
            return {"id": "cliente-1", "nome": "Joao", "cpf_cnpj": None, "telefone": "999", "email": None, "criado_em": "2026-03-24T10:00:00+00:00"}
        if query.table == "clientes" and query.action == "update":
            return [{**query.payload, "id": "cliente-1"}]
        raise AssertionError(f"Consulta inesperada: {query.table}/{query.action}")

    sb = FakeSupabase(resolver)
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(clientes_mod, "get_supabase", lambda: sb)

    try:
        resultado = clientes_mod.atualizar_cliente(
            "cliente-1",
            clientes_mod.ClienteUpdate(nome="Joao Silva", telefone="888"),
        )
    finally:
        monkeypatch.undo()

    assert resultado["nome"] == "Joao Silva"
    assert resultado["telefone"] == "888"


def test_salvar_geometria_manual_rejeita_poucos_vertices():
    with pytest.raises(HTTPException) as excinfo:
        clientes_mod.salvar_geometria_manual(
            "cliente-1",
            clientes_mod.GeometriaManualPayload(
                projeto_id="projeto-1",
                nome="Croqui",
                vertices=[
                    clientes_mod.VerticePayload(lon=-48.0, lat=-14.0),
                    clientes_mod.VerticePayload(lon=-48.0, lat=-14.001),
                ],
            ),
        )

    assert excinfo.value.status_code == 422


def test_importar_geometria_texto_delega_para_parser_e_salva(monkeypatch):
    capturado = {}
    vertices = [
        {"lon": -48.0, "lat": -14.0},
        {"lon": -48.0, "lat": -14.001},
        {"lon": -47.999, "lat": -14.001},
    ]

    monkeypatch.setattr(clientes_mod, "importar_vertices_por_formato", lambda formato, conteudo: vertices)
    monkeypatch.setattr(clientes_mod, "_salvar_referencia", lambda **kwargs: capturado.update(kwargs) or {"ok": True})

    resultado = clientes_mod.importar_geometria_texto(
        "cliente-1",
        clientes_mod.GeometriaTextoPayload(
            projeto_id="projeto-1",
            nome="Importacao 1",
            formato="geojson",
            conteudo="{}",
        ),
    )

    assert resultado == {"ok": True}
    assert capturado["origem_tipo"] == "importacao_texto"
    assert capturado["formato"] == "geojson"
    assert capturado["vertices"] == vertices


def test_importar_geometria_arquivo_processa_upload(monkeypatch):
    capturado = {}

    monkeypatch.setattr(clientes_mod, "_salvar_referencia", lambda **kwargs: capturado.update(kwargs) or {"ok": True})

    async def run():
        return await clientes_mod.importar_geometria_arquivo(
            "cliente-1",
            FakeUploadFile("area.geojson", b'{"type":"Polygon","coordinates":[[[-48.0,-14.0],[-48.0,-14.001],[-47.999,-14.001],[-48.0,-14.0]]]}'),
            projeto_id="projeto-1",
            nome="Arquivo 1",
            formato=None,
        )

    resultado = asyncio.run(run())

    assert resultado == {"ok": True}
    assert capturado["origem_tipo"] == "arquivo"
    assert capturado["arquivo_nome"] == "area.geojson"
    assert len(capturado["vertices"]) == 3


def test_excluir_geometria_referencia_encaminha_remocao(monkeypatch):
    sb = FakeSupabase(
        lambda query: {
            "id": "cliente-1",
            "nome": "Joao",
            "cpf_cnpj": None,
            "telefone": None,
            "email": None,
            "criado_em": "2026-03-24T10:00:00+00:00",
        }
    )
    monkeypatch.setattr(clientes_mod, "get_supabase", lambda: sb)
    monkeypatch.setattr(clientes_mod, "remover_geometria_referencia", lambda _sb, _cliente_id: True)

    resultado = clientes_mod.excluir_geometria_referencia("cliente-1")

    assert resultado == {"status": "ok", "cliente_id": "cliente-1"}


