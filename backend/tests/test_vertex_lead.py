"""Testes do endpoint /vertex/lead com um Supabase falso (sem rede)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from routes import vertex_lead as vl


class _Resp:
    def __init__(self, data):
        self.data = data


class _Query:
    def __init__(self, tabela, store, op="select"):
        self.tabela = tabela
        self.store = store
        self.op = op
        self._payload = None
        self._filtros = {}

    def insert(self, payload):
        self.op = "insert"
        self._payload = payload
        return self

    def update(self, payload):
        self.op = "update"
        self._payload = payload
        return self

    def select(self, *_a, **_k):
        self.op = "select"
        return self

    def eq(self, campo, valor):
        self._filtros[campo] = valor
        return self

    def is_(self, *_a, **_k):
        return self

    def limit(self, *_a, **_k):
        return self

    def execute(self):
        if self.op == "insert":
            # Simula schema do banco LIVE: rejeita cpf_cnpj e owner_id
            if "cpf_cnpj" in self._payload:
                raise Exception("Could not find the 'cpf_cnpj' column of 'clientes'")
            novo = dict(self._payload)
            novo["id"] = f"{self.tabela}-id-1"
            self.store.setdefault(self.tabela, []).append(novo)
            return _Resp([novo])
        if self.op == "update":
            self.store.setdefault("updates", []).append((self.tabela, self._payload, self._filtros))
            return _Resp([{}])
        # select
        linhas = self.store.get(self.tabela, [])
        out = [r for r in linhas if all(r.get(k) == v for k, v in self._filtros.items())]
        return _Resp(out)


class _FakeSB:
    def __init__(self):
        self.store = {}

    def table(self, nome):
        return _Query(nome, self.store)


class _FakeReq:
    headers = {}


def _setup(monkeypatch, secret=None):
    sb = _FakeSB()
    monkeypatch.setattr(vl, "_get_supabase", lambda: sb)
    monkeypatch.setenv("APP_URL", "https://geoadmin-api-800479022570.us-central1.run.app")
    if secret is not None:
        monkeypatch.setenv("VERTEX_LEAD_SECRET", secret)
    else:
        monkeypatch.delenv("VERTEX_LEAD_SECRET", raising=False)
    return sb


import asyncio


def test_lead_cria_cliente_e_retorna_link(monkeypatch):
    _setup(monkeypatch)
    payload = vl.LeadPayload(telefone="5561999990000", nome="Maria", cpf="")
    res = asyncio.run(vl.vertex_lead(payload, _FakeReq()))
    assert res["ok"] is True
    assert res["url"].startswith("https://geoadmin-api-800479022570.us-central1.run.app/formulario/cliente?token=")
    assert res["projeto_id"]  # projeto dedicado criado para o lead
    assert res["cliente_id"]
    assert res["projeto_cliente_id"]


def test_lead_tolerante_a_schema_sem_cpf_cnpj(monkeypatch):
    sb = _setup(monkeypatch)
    payload = vl.LeadPayload(telefone="5561888887777", nome="", cpf="12345678901")
    res = asyncio.run(vl.vertex_lead(payload, _FakeReq()))
    # caiu no fallback (cpf em vez de cpf_cnpj) e criou cliente mesmo assim
    assert res["cliente_id"]
    clientes = sb.store.get("clientes", [])
    assert clientes and "cpf_cnpj" not in clientes[0]


def test_lead_valida_segredo(monkeypatch):
    _setup(monkeypatch, secret="abc123")
    payload = vl.LeadPayload(telefone="5561777776666")
    req = _FakeReq()
    req.headers = {"x-vertex-secret": "errado"}
    try:
        asyncio.run(vl.vertex_lead(payload, req))
        assert False, "deveria ter barrado"
    except Exception as exc:
        assert "401" in str(exc) or "Segredo" in str(exc)
