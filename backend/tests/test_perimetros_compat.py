from routes import perimetros as perimetros_mod


class FakeResponse:
    def __init__(self, data):
        self.data = data


class FakeQuery:
    def __init__(self, supabase, table):
        self.supabase = supabase
        self.table = table
        self.action = "select"
        self.selection = None
        self.payload = None
        self.filters = []

    def select(self, selection):
        self.selection = selection
        return self

    def eq(self, field, value):
        self.filters.append(("eq", field, value))
        return self

    def is_(self, field, value):
        self.filters.append(("is", field, value))
        return self

    def order(self, *_args, **_kwargs):
        return self

    def limit(self, *_args, **_kwargs):
        return self

    def maybe_single(self):
        return self

    def insert(self, payload):
        self.action = "insert"
        self.payload = payload
        return self

    def update(self, payload):
        self.action = "update"
        self.payload = payload
        return self

    def execute(self):
        self.supabase.calls.append(self)
        return FakeResponse(self.supabase.resolver(self))


class FakeSupabase:
    def __init__(self, resolver):
        self.resolver = resolver
        self.calls = []

    def table(self, table):
        return FakeQuery(self, table)


def test_buscar_perimetro_ativo_aceita_schema_vertex_com_vertices():
    def resolver(query):
        assert query.table == "perimetros"
        if "vertices_json" in query.selection or any(f[1] == "deleted_at" for f in query.filters):
            raise Exception("column does not exist")
        tipo = next(f[2] for f in query.filters if f[:2] == ("eq", "tipo"))
        if tipo == "editado":
            return [{
                "id": "per-1",
                "projeto_id": "projeto-1",
                "tipo": "editado",
                "vertices": [{"lon": -56.1, "lat": -15.6}],
                "criado_em": "2026-05-01T00:00:00Z",
            }]
        return []

    perimetro = perimetros_mod.buscar_perimetro_ativo("projeto-1", supabase=FakeSupabase(resolver))

    assert perimetro == {
        "id": "per-1",
        "nome": "editado",
        "tipo": "editado",
        "criado_em": "2026-05-01T00:00:00Z",
        "vertices": [{"lon": -56.1, "lat": -15.6}],
    }


def test_salvar_perimetro_regrava_payload_no_schema_vertex_quando_legado_falha():
    inserted = []

    def resolver(query):
        assert query.table == "perimetros"
        if query.action == "select":
            return []
        if query.action == "update":
            raise Exception("column does not exist")
        if "vertices_json" in query.payload or "nome" in query.payload:
            raise Exception("column does not exist")
        inserted.append(query.payload)
        return [{
            **query.payload,
            "id": "per-2",
            "criado_em": "2026-05-02T00:00:00Z",
        }]

    payload = perimetros_mod.PerimetroCreate(
        projeto_id="projeto-1",
        nome="Perimetro editado",
        tipo="editado",
        vertices=[perimetros_mod.Vertice(lon=-56.1, lat=-15.6)],
    )

    perimetro = perimetros_mod.salvar_perimetro(payload, supabase=FakeSupabase(resolver))

    assert inserted == [{
        "projeto_id": "projeto-1",
        "tipo": "editado",
        "vertices": [{"lon": -56.1, "lat": -15.6, "nome": None}],
    }]
    assert perimetro["vertices"] == [{"lon": -56.1, "lat": -15.6, "nome": None}]


def test_salvar_original_existente_retorna_schema_vertex_sem_duplicar():
    def resolver(query):
        assert query.table == "perimetros"
        if query.action == "select":
            if any(f[:3] == ("eq", "tipo", "original") for f in query.filters):
                return [{"id": "per-original"}]
            if "vertices_json" in query.selection or "nome" in query.selection:
                raise Exception("column does not exist")
            return [{
                "id": "per-original",
                "projeto_id": "projeto-1",
                "tipo": "original",
                "vertices": [{"lon": -56.1, "lat": -15.6, "nome": "V1"}],
                "criado_em": "2026-05-02T00:00:00Z",
            }]
        raise AssertionError("Nao deveria inserir quando original ja existe")

    payload = perimetros_mod.PerimetroCreate(
        projeto_id="projeto-1",
        nome="Perimetro original",
        tipo="original",
        vertices=[perimetros_mod.Vertice(lon=-56.1, lat=-15.6, nome="V1")],
    )

    perimetro = perimetros_mod.salvar_perimetro(payload, supabase=FakeSupabase(resolver))

    assert perimetro["status"] == "ja_existe"
    assert perimetro["vertices"] == [{"lon": -56.1, "lat": -15.6, "nome": "V1"}]
