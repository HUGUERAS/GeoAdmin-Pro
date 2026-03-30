from __future__ import annotations

import io
import json
import zipfile
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
        self.filters: list[tuple[str, str, object]] = []
        self.ordering = None

    def insert(self, payload):
        self.action = 'insert'
        self.payload = payload
        return self

    def select(self, _campos='*'):
        self.action = 'select'
        return self

    def eq(self, campo, valor):
        self.filters.append(('eq', campo, valor))
        return self

    def is_(self, campo, valor):
        self.filters.append(('is', campo, valor))
        return self

    def order(self, campo, desc=False):
        self.ordering = (campo, desc)
        return self

    def execute(self):
        return FakeResponse(self.supabase.resolver(self))


class FakeSupabase:
    def __init__(self):
        self.rows: list[dict] = []

    def resolver(self, query: FakeQuery):
        if query.table != 'arquivos_projeto':
            raise AssertionError(f'Tabela inesperada: {query.table}')
        if query.action == 'insert':
            self.rows.append(query.payload)
            return [query.payload]
        if query.action == 'select':
            resultado = [item for item in self.rows if item.get('deleted_at') is None]
            for op, campo, valor in query.filters:
                if op == 'eq':
                    resultado = [item for item in resultado if item.get(campo) == valor]
                elif op == 'is' and valor == 'null':
                    resultado = [item for item in resultado if item.get(campo) is None]
            return resultado
        raise AssertionError(f'Acao inesperada: {query.action}')

    def table(self, nome: str):
        return FakeQuery(self, nome)


def test_salvar_e_exportar_arquivos_projeto(monkeypatch, tmp_path: Path):
    sb = FakeSupabase()
    uploads_dir = tmp_path / 'uploads'
    monkeypatch.setattr(arquivos_mod, 'UPLOADS_DIR', uploads_dir)

    salvo = arquivos_mod.salvar_arquivo_projeto(
        sb,
        projeto_id='proj-1',
        nome_arquivo='base.kml',
        conteudo=b'<kml/>',
        origem='topografo',
        classificacao='referencia_visual',
    )

    caminho = Path(salvo['storage_path'])
    assert caminho.exists()
    assert salvo['classificacao'] == 'referencia_visual'
    assert salvo['origem'] == 'topografo'

    zip_bytes = arquivos_mod.exportar_arquivos_projeto_zip(sb, 'proj-1')
    with zipfile.ZipFile(io.BytesIO(zip_bytes), 'r') as zf:
        nomes = set(zf.namelist())
        assert 'referencia_visual/base.kml' in nomes
        manifesto = json.loads(zf.read('manifesto_arquivos_projeto.json').decode('utf-8'))
        assert manifesto[0]['nome_original'] == 'base.kml'
