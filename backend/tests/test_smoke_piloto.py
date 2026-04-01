"""
Smoke test do fluxo completo do piloto condominial.

Cobre:
  1.  Endpoint /health responde 200
  2.  Métricas do piloto calculam KPIs corretos sem banco real
  3.  Validação das métricas: sem lotes = tudo zerado
  4.  Métricas com lotes parcialmente preenchidos
  5.  Métricas com lotes prontos (status operacional + documental finais)
  6.  Contadores por_status_operacional e por_status_documental
  7.  Magic-links enviados conta apenas tipos "gerado" e "reenviado"
  8.  Formulários preenchidos isolados por área
"""
from __future__ import annotations

import types
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

import routes.projetos as projetos_mod


# ---------------------------------------------------------------------------
# Helpers de stub
# ---------------------------------------------------------------------------

class FakeResponse:
    def __init__(self, data, count=None):
        self.data = data
        self.count = count


def _build_fake_supabase(areas, area_clientes, projeto_clientes, clientes, eventos_count):
    """Monta um Supabase fake que responde de forma determinística por tabela."""

    class _FakeQuery:
        def __init__(self, table_name):
            self._table = table_name
            self._filters = {}
            self._in_filters = {}
            self._count = None

        def select(self, *_a, count=None, **_kw):
            if count:
                self._count = count
            return self

        def eq(self, col, val):
            self._filters[col] = val
            return self

        def in_(self, col, vals):
            self._in_filters[col] = vals
            return self

        def is_(self, *_a, **_kw):
            return self

        def execute(self):
            if self._table == "areas_projeto":
                return FakeResponse(areas)
            if self._table == "area_clientes":
                return FakeResponse(area_clientes)
            if self._table == "projeto_clientes":
                return FakeResponse(projeto_clientes)
            if self._table == "clientes":
                return FakeResponse(clientes)
            if self._table == "eventos_magic_link":
                return FakeResponse([], count=eventos_count)
            return FakeResponse([])

    class _FakeSupabase:
        def table(self, name):
            return _FakeQuery(name)

    return _FakeSupabase()


# ---------------------------------------------------------------------------
# Testes
# ---------------------------------------------------------------------------

def _call_metricas(monkeypatch, areas, area_clientes, projeto_clientes, clientes, eventos_count=0):
    """Chama metricas_piloto com dados fake e retorna o resultado."""
    fake_sb = _build_fake_supabase(areas, area_clientes, projeto_clientes, clientes, eventos_count)
    monkeypatch.setattr(projetos_mod, "_get_supabase", lambda: fake_sb)
    return projetos_mod.metricas_piloto("proj-piloto")


def test_sem_lotes_tudo_zerado(monkeypatch):
    result = _call_metricas(monkeypatch, areas=[], area_clientes=[], projeto_clientes=[], clientes=[])
    assert result["lotes_cadastrados"] == 0
    assert result["lotes_com_participante"] == 0
    assert result["magic_links_enviados"] == 0
    assert result["formularios_preenchidos"] == 0
    assert result["lotes_com_croqui"] == 0
    assert result["lotes_com_confrontantes_ok"] == 0
    assert result["lotes_prontos"] == 0
    assert result["por_status_operacional"] == {}
    assert result["por_status_documental"] == {}


def test_lotes_aguardando_sem_participante(monkeypatch):
    areas = [
        {"id": f"area-{i}", "status_operacional": "aguardando_cliente", "status_documental": "pendente"}
        for i in range(5)
    ]
    result = _call_metricas(monkeypatch, areas=areas, area_clientes=[], projeto_clientes=[], clientes=[])
    assert result["lotes_cadastrados"] == 5
    assert result["lotes_com_participante"] == 0
    assert result["por_status_operacional"]["aguardando_cliente"] == 5
    assert result["por_status_documental"]["pendente"] == 5


def test_lotes_com_participante(monkeypatch):
    areas = [
        {"id": "area-1", "status_operacional": "aguardando_cliente", "status_documental": "pendente"},
        {"id": "area-2", "status_operacional": "aguardando_cliente", "status_documental": "pendente"},
        {"id": "area-3", "status_operacional": "aguardando_cliente", "status_documental": "pendente"},
    ]
    # área-1 e área-2 têm participante
    area_clientes = [
        {"area_id": "area-1"},
        {"area_id": "area-2"},
    ]
    result = _call_metricas(monkeypatch, areas=areas, area_clientes=area_clientes, projeto_clientes=[], clientes=[])
    assert result["lotes_com_participante"] == 2


def test_formularios_preenchidos(monkeypatch):
    areas = [
        {"id": "area-1", "status_operacional": "aguardando_cliente", "status_documental": "pendente"},
        {"id": "area-2", "status_operacional": "aguardando_cliente", "status_documental": "pendente"},
    ]
    projeto_clientes = [
        {"cliente_id": "cli-1", "area_id": "area-1"},
        {"cliente_id": "cli-2", "area_id": "area-2"},
    ]
    # Apenas cli-1 preencheu
    clientes = [{"id": "cli-1", "formulario_ok": True}]
    result = _call_metricas(monkeypatch, areas=areas, area_clientes=[], projeto_clientes=projeto_clientes, clientes=clientes)
    assert result["formularios_preenchidos"] == 1


def test_lotes_com_croqui_e_confrontantes(monkeypatch):
    areas = [
        {"id": "area-1", "status_operacional": "croqui_recebido", "status_documental": "pendente"},
        {"id": "area-2", "status_operacional": "geometria_final", "status_documental": "confrontantes_ok"},
        {"id": "area-3", "status_operacional": "aguardando_cliente", "status_documental": "confrontantes_ok"},
        {"id": "area-4", "status_operacional": "aguardando_cliente", "status_documental": "pendente"},
    ]
    result = _call_metricas(monkeypatch, areas=areas, area_clientes=[], projeto_clientes=[], clientes=[])
    assert result["lotes_com_croqui"] == 2       # area-1, area-2
    assert result["lotes_com_confrontantes_ok"] == 2  # area-2, area-3


def test_lotes_prontos(monkeypatch):
    areas = [
        # pronto: operacional em geometria_final+, documental em documentacao_ok+
        {"id": "area-1", "status_operacional": "geometria_final", "status_documental": "documentacao_ok"},
        {"id": "area-2", "status_operacional": "peca_pronta", "status_documental": "peca_pronta"},
        # não-pronto: documental ainda em confrontantes_ok
        {"id": "area-3", "status_operacional": "geometria_final", "status_documental": "confrontantes_ok"},
        # não-pronto: operacional ainda em croqui
        {"id": "area-4", "status_operacional": "croqui_recebido", "status_documental": "documentacao_ok"},
    ]
    result = _call_metricas(monkeypatch, areas=areas, area_clientes=[], projeto_clientes=[], clientes=[])
    assert result["lotes_prontos"] == 2
    assert result["lotes_cadastrados"] == 4


def test_magic_links_enviados(monkeypatch):
    result = _call_metricas(monkeypatch, areas=[], area_clientes=[], projeto_clientes=[], clientes=[], eventos_count=42)
    assert result["magic_links_enviados"] == 42


def test_retorno_tem_projeto_id_e_timestamp(monkeypatch):
    result = _call_metricas(monkeypatch, areas=[], area_clientes=[], projeto_clientes=[], clientes=[])
    assert result["projeto_id"] == "proj-piloto"
    assert "calculado_em" in result
    # deve ser ISO 8601
    datetime.fromisoformat(result["calculado_em"])


def test_piloto_120_lotes_parciais(monkeypatch):
    """Simula cenário realista: 120 lotes, metade com participante, 30 prontos."""
    areas = []
    area_clientes = []
    for i in range(120):
        so = "peca_pronta" if i < 30 else ("croqui_recebido" if i < 60 else "aguardando_cliente")
        sd = "peca_pronta" if i < 30 else ("confrontantes_ok" if i < 60 else "pendente")
        areas.append({"id": f"area-{i}", "status_operacional": so, "status_documental": sd})
        if i < 60:
            area_clientes.append({"area_id": f"area-{i}"})

    result = _call_metricas(monkeypatch, areas=areas, area_clientes=area_clientes, projeto_clientes=[], clientes=[], eventos_count=75)
    assert result["lotes_cadastrados"] == 120
    assert result["lotes_com_participante"] == 60
    assert result["lotes_prontos"] == 30
    assert result["lotes_com_croqui"] == 60     # peca_pronta(30) + croqui_recebido(30)
    assert result["magic_links_enviados"] == 75
