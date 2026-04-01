from __future__ import annotations

from pathlib import Path

import integracoes.arquivos_projeto as arquivos_mod


class FakeResponse:
    def __init__(self, data):
        self.data = data


class FakeQuery:
    def __init__(self, supabase: 'FakeSupabase', table: str):
        self.supabase = supabase
        self.table = table
        self.action = 'select'
        self.payload = None
        self.filters: list[tuple[str, object, object]] = []

    def select(self, *_args, **_kwargs):
        self.action = 'select'
        return self

    def eq(self, campo, valor):
        self.filters.append(('eq', campo, valor))
        return self

    def is_(self, campo, valor):
        self.filters.append(('is', campo, valor))
        return self

    def order(self, *_args, **_kwargs):
        return self

    def limit(self, *_args, **_kwargs):
        return self

    def update(self, payload):
        self.action = 'update'
        self.payload = payload
        return self

    def insert(self, payload):
        self.action = 'insert'
        self.payload = payload
        return self

    def execute(self):
        return FakeResponse(self.supabase.resolver(self))


class FakeStorageBucket:
    def __init__(self, storage: 'FakeStorage', bucket: str):
        self.storage = storage
        self.bucket = bucket

    def upload(self, objeto: str, conteudo: bytes, _opts=None):
        self.storage.buckets.setdefault(self.bucket, {})[objeto] = conteudo
        return {'path': objeto}

    def download(self, objeto: str):
        return self.storage.buckets[self.bucket][objeto]


class FakeStorage:
    def __init__(self):
        self.buckets: dict[str, dict[str, bytes]] = {}

    def get_bucket(self, bucket: str):
        if bucket not in self.buckets:
            raise RuntimeError('bucket inexistente')
        return {'name': bucket}

    def create_bucket(self, bucket: str, _name: str, _opts=None):
        self.buckets.setdefault(bucket, {})
        return {'name': bucket}

    def from_(self, bucket: str):
        self.buckets.setdefault(bucket, {})
        return FakeStorageBucket(self, bucket)


class FakeSupabase:
    def __init__(self, resolver):
        self.resolver = resolver
        self.storage = FakeStorage()

    def table(self, nome: str):
        return FakeQuery(self, nome)


def test_promover_arquivo_base_oficial_registra_evento():
    tabela_arquivos = {
        'arq-1': {
            'id': 'arq-1',
            'projeto_id': 'proj-1',
            'area_id': 'area-1',
            'cliente_id': 'cli-1',
            'origem': 'topografo',
            'classificacao': 'esboco_area',
            'storage_path': 'local://C:/tmp/arq-1.geojson',
            'deleted_at': None,
        }
    }
    eventos = []

    def resolver(query: FakeQuery):
        if query.table == 'arquivos_projeto':
            if query.action == 'select':
                arquivo_id = next((f[2] for f in query.filters if f[0] == 'eq' and f[1] == 'id'), None)
                return [tabela_arquivos[arquivo_id]] if arquivo_id else list(tabela_arquivos.values())
            if query.action == 'update':
                arquivo_id = next((f[2] for f in query.filters if f[0] == 'eq' and f[1] == 'id'), None)
                tabela_arquivos[arquivo_id].update(query.payload)
                return [tabela_arquivos[arquivo_id]]
        if query.table == 'eventos_cartograficos':
            if query.action == 'insert':
                eventos.append(query.payload)
                return [query.payload]
            if query.action == 'select':
                return eventos
        raise AssertionError(f'Tabela inesperada: {query.table} {query.action}')

    registro = arquivos_mod.promover_arquivo_base_oficial(
        FakeSupabase(resolver),
        projeto_id='proj-1',
        arquivo_id='arq-1',
        autor='Hugo',
        observacao='Validado em gabinete',
        classificacao_destino='perimetro_tecnico',
    )

    assert registro['base_oficial'] is True
    assert registro['classificacao'] == 'perimetro_tecnico'
    assert eventos[0]['tipo_evento'] == 'promocao_base_oficial'
    assert eventos[0]['autor'] == 'Hugo'


def test_migrar_arquivos_locais_para_storage_registra_evento(tmp_path):
    arquivo_local = tmp_path / 'lote.geojson'
    arquivo_local.write_bytes(b'{"type":"FeatureCollection","features":[]}')
    tabela_arquivos = {
        'arq-1': {
            'id': 'arq-1',
            'projeto_id': 'proj-1',
            'area_id': None,
            'cliente_id': None,
            'nome_original': 'lote.geojson',
            'nome_arquivo': 'arq-1-lote.geojson',
            'mime_type': 'application/geo+json',
            'origem': 'topografo',
            'classificacao': 'camada_auxiliar',
            'storage_path': f'local://{arquivo_local}',
            'metadados_json': {'storage_provider': 'local'},
            'deleted_at': None,
        }
    }
    eventos = []

    def resolver(query: FakeQuery):
        if query.table == 'arquivos_projeto':
            if query.action == 'select':
                return list(tabela_arquivos.values())
            if query.action == 'update':
                arquivo_id = next((f[2] for f in query.filters if f[0] == 'eq' and f[1] == 'id'), None)
                tabela_arquivos[arquivo_id].update(query.payload)
                return [tabela_arquivos[arquivo_id]]
        if query.table == 'eventos_cartograficos':
            if query.action == 'insert':
                eventos.append(query.payload)
                return [query.payload]
            if query.action == 'select':
                return eventos
        raise AssertionError(f'Tabela inesperada: {query.table} {query.action}')

    sb = FakeSupabase(resolver)
    resultado = arquivos_mod.migrar_arquivos_locais_para_storage(sb, projeto_id='proj-1', autor='Migração')

    assert resultado['migrados'] == 1
    assert tabela_arquivos['arq-1']['storage_path'].startswith('supabase://')
    assert eventos[0]['tipo_evento'] == 'migracao_storage'
    assert sb.storage.buckets
