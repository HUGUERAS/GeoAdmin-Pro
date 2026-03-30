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
    def __init__(self, supabase: "FakeSupabase", table: str):
        self.supabase = supabase
        self.table = table
        self.action = "select"
        self.payload = None
        self.filters: list[tuple[str, str, object]] = []
        self.ordering = None

    def insert(self, payload):
        self.action = "insert"
        self.payload = payload
        return self

    def select(self, _campos="*"):
        self.action = "select"
        return self

    def eq(self, campo, valor):
        self.filters.append(("eq", campo, valor))
        return self

    def is_(self, campo, valor):
        self.filters.append(("is", campo, valor))
        return self

    def order(self, campo, desc=False):
        self.ordering = (campo, desc)
        return self

    def execute(self):
        return FakeResponse(self.supabase.resolver(self))


class FakeBucketProxy:
    def __init__(self, buckets: dict[str, dict[str, bytes]], bucket: str, quebrar_upload: bool = False):
        self.buckets = buckets
        self.bucket = bucket
        self.quebrar_upload = quebrar_upload

    def upload(self, path: str, file, file_options=None):
        if self.quebrar_upload:
            raise RuntimeError("storage indisponivel")
        if isinstance(file, bytes):
            conteudo = file
        else:
            conteudo = Path(file).read_bytes()
        self.buckets.setdefault(self.bucket, {})[path] = conteudo
        return {"path": path}

    def download(self, path: str):
        return self.buckets[self.bucket][path]


class FakeStorageClient:
    def __init__(self, quebrar_upload: bool = False):
        self.buckets: dict[str, dict[str, bytes]] = {}
        self.quebrar_upload = quebrar_upload

    def get_bucket(self, bucket: str):
        if bucket not in self.buckets:
            raise RuntimeError("bucket nao existe")
        return {"name": bucket}

    def create_bucket(self, bucket: str, name=None, options=None):
        self.buckets.setdefault(bucket, {})
        return {"name": name or bucket}

    def from_(self, bucket: str):
        self.buckets.setdefault(bucket, {})
        return FakeBucketProxy(self.buckets, bucket, quebrar_upload=self.quebrar_upload)


class FakeSupabase:
    def __init__(self, quebrar_upload: bool = False):
        self.rows: list[dict] = []
        self.storage = FakeStorageClient(quebrar_upload=quebrar_upload)

    def resolver(self, query: FakeQuery):
        if query.table != "arquivos_projeto":
            raise AssertionError(f"Tabela inesperada: {query.table}")
        if query.action == "insert":
            self.rows.append(query.payload)
            return [query.payload]
        if query.action == "select":
            resultado = [item for item in self.rows if item.get("deleted_at") is None]
            for op, campo, valor in query.filters:
                if op == "eq":
                    resultado = [item for item in resultado if item.get(campo) == valor]
                elif op == "is" and valor == "null":
                    resultado = [item for item in resultado if item.get(campo) is None]
            return resultado
        raise AssertionError(f"Acao inesperada: {query.action}")

    def table(self, nome: str):
        return FakeQuery(self, nome)


def test_salvar_e_exportar_arquivos_projeto_via_supabase_storage():
    sb = FakeSupabase()

    salvo = arquivos_mod.salvar_arquivo_projeto(
        sb,
        projeto_id="proj-1",
        nome_arquivo="base.kml",
        conteudo=b"<kml/>",
        origem="topografo",
        classificacao="referencia_visual",
    )

    assert salvo["storage_path"].startswith("supabase://arquivos-projeto/proj-1/")
    assert salvo["metadados_json"]["storage_provider"] == "supabase"

    zip_bytes = arquivos_mod.exportar_arquivos_projeto_zip(sb, "proj-1")
    with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as zf:
        nomes = set(zf.namelist())
        assert "referencia_visual/base.kml" in nomes
        manifesto = json.loads(zf.read("manifesto_arquivos_projeto.json").decode("utf-8"))
        assert manifesto[0]["nome_original"] == "base.kml"
        assert manifesto[0]["storage_path"].startswith("supabase://arquivos-projeto/")


def test_salvar_arquivo_projeto_faz_fallback_local_quando_storage_falha(monkeypatch, tmp_path: Path):
    sb = FakeSupabase(quebrar_upload=True)
    uploads_dir = tmp_path / "uploads"
    monkeypatch.setattr(arquivos_mod, "UPLOADS_DIR", uploads_dir)

    salvo = arquivos_mod.salvar_arquivo_projeto(
        sb,
        projeto_id="proj-2",
        nome_arquivo="croqui.pdf",
        conteudo=b"pdf",
        origem="cliente",
        classificacao="documento_croqui",
    )

    assert salvo["metadados_json"]["storage_provider"] == "local"
    assert salvo["storage_path"].startswith("local://")
    caminho = Path(salvo["storage_path"].replace("local://", "", 1))
    assert caminho.exists()
