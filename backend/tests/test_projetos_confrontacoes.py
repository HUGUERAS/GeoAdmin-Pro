from routes import projetos as projetos_mod


class FakeResponse:
    def __init__(self, data):
        self.data = data


class FakeQuery:
    def __init__(self, table):
        self.table = table
        self.filters = []

    def select(self, _campos):
        return self

    def eq(self, campo, valor):
        self.filters.append((campo, valor))
        return self

    def execute(self):
        if self.table == "vw_pontos_geo":
            raise Exception("relation public.vw_pontos_geo does not exist")
        return FakeResponse([
            {
                "id": "ponto-1",
                "codigo": "P01",
                "lon": -56.1,
                "lat": -15.6,
                "norte": 8270000.0,
                "este": 600000.0,
                "altitude_m": 0.0,
                "origem": "landiiiinnn",
            }
        ])


class FakeSupabase:
    def table(self, table):
        return FakeQuery(table)


def test_pontos_projeto_faz_fallback_para_tabela_pontos():
    pontos = projetos_mod._pontos_projeto(FakeSupabase(), "projeto-1")

    assert pontos == [
        {
            "id": "ponto-1",
            "codigo": "P01",
            "nome": "P01",
            "lon": -56.1,
            "lat": -15.6,
            "norte": 8270000.0,
            "este": 600000.0,
            "origem": "landiiiinnn",
            "altitude_m": 0.0,
            "descricao": None,
        }
    ]


def test_normalizar_pontos_projeto_aceita_cota_legada():
    pontos = projetos_mod._normalizar_pontos_projeto([{"codigo": "P02", "cota": 123.45}])

    assert pontos == [{"codigo": "P02", "cota": 123.45, "nome": "P02", "altitude_m": 123.45, "descricao": None}]


def test_resumo_confrontacoes_conta_status_e_areas():
    assert hasattr(projetos_mod, "_resumo_confrontacoes")

    confrontacoes = [
        {"area_id": "area-1", "status_revisao": "pendente"},
        {"area_id": "area-1", "status_revisao": "confirmada"},
        {"area_id": "area-2", "status": "descartada"},
        {"area_id": None},
    ]
    confrontantes = [{"id": "conf-1"}, {"id": "conf-2"}]

    resumo = projetos_mod._resumo_confrontacoes(confrontacoes, confrontantes)

    assert resumo == {
        "total": 4,
        "confrontantes_total": 2,
        "areas_com_confrontacao": 2,
        "pendentes": 2,
        "confirmadas": 1,
        "descartadas": 1,
        "por_status": {
            "confirmada": 1,
            "descartada": 1,
            "pendente": 2,
        },
    }


def test_prontidao_piloto_resume_requisitos_minimos():
    assert hasattr(projetos_mod, "_prontidao_piloto")

    projeto = {
        "id": "projeto-1",
        "cliente_id": "cliente-1",
        "clientes": [{"id": "cliente-1"}],
        "participantes": [{"cliente_id": "cliente-1"}],
        "perimetro_ativo": {"id": "perimetro-1"},
        "formulario": {"formulario_ok": True},
    }

    resumo = projetos_mod._prontidao_piloto(projeto)

    assert resumo == {
        "status": "pronto",
        "pronto": True,
        "pendencias": [],
        "requisitos": {
            "projeto_cadastrado": True,
            "cliente_vinculado": True,
            "participantes_mapeados": True,
            "perimetro_definido": True,
            "formulario_cliente": True,
        },
    }
