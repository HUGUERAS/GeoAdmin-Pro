from __future__ import annotations

import routes.projetos as projetos_mod


def test_resumo_lotes_agrega_status_e_prontos():
    resumo = projetos_mod._resumo_lotes([
        {
            'cliente_id': 'cli-1',
            'participantes_area': [{'cliente_id': 'cli-1'}],
            'status_operacional': 'peca_pronta',
            'status_documental': 'peca_pronta',
            'status_geometria': 'geometria_final',
        },
        {
            'cliente_id': None,
            'participantes_area': [],
            'status_operacional': 'aguardando_cliente',
            'status_documental': 'pendente',
            'status_geometria': 'sem_geometria',
        },
    ])

    assert resumo['total'] == 2
    assert resumo['prontos'] == 1
    assert resumo['pendentes'] == 1
    assert resumo['sem_participante'] == 1
    assert resumo['com_geometria'] == 1
    assert resumo['por_status_operacional']['peca_pronta'] == 1
    assert resumo['por_status_documental']['pendente'] == 1


class FakeResponse:
    def __init__(self, data):
        self.data = data


class FakeQuery:
    def __init__(self, supabase, table: str):
        self.supabase = supabase
        self.table = table
        self.offset = 0
        self.limit = 0

    def select(self, *_args, **_kwargs):
        return self

    def order(self, *_args, **_kwargs):
        return self

    def range(self, inicio, fim):
        self.offset = inicio
        self.limit = fim
        return self

    def execute(self):
        return FakeResponse(self.supabase.resolver(self))


class FakeSupabase:
    def __init__(self, resolver):
        self.resolver = resolver

    def table(self, nome: str):
        return FakeQuery(self, nome)


def test_listar_projetos_injeta_resumo_lotes(monkeypatch):
    projetos = [
        {'id': 'proj-1', 'nome': 'Empreendimento A', 'status': 'medicao'},
        {'id': 'proj-2', 'nome': 'Projeto B', 'status': 'montagem'},
    ]

    monkeypatch.setattr(projetos_mod, '_get_supabase', lambda: FakeSupabase(lambda query: projetos if query.table == 'vw_projetos_completo' else []))
    monkeypatch.setattr(projetos_mod, '_resumo_lotes_lista', lambda _sb, ids: {
        'proj-1': {'total': 120, 'prontos': 20, 'pendentes': 100, 'sem_participante': 15, 'com_geometria': 48},
    })

    resposta = projetos_mod.listar_projetos()

    assert resposta['projetos'][0]['resumo_lotes']['total'] == 120
    assert resposta['projetos'][0]['areas_total'] == 120
    assert resposta['projetos'][0]['lotes_prontos'] == 20
    assert resposta['projetos'][0]['lotes_pendentes'] == 100
    assert 'resumo_lotes' not in resposta['projetos'][1]
