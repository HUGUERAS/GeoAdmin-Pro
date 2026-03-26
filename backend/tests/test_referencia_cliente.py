from __future__ import annotations

import asyncio
import io
import json
import tempfile
import zipfile
from pathlib import Path

import pytest

from integracoes import referencia_cliente as ref


def _geojson_square() -> str:
    return json.dumps(
        {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [[
                            [-48.0, -14.0],
                            [-48.0, -14.001],
                            [-47.999, -14.001],
                            [-47.999, -14.0],
                            [-48.0, -14.0],
                        ]],
                    },
                }
            ],
        }
    )


def test_parse_geojson_feature_collection():
    vertices = ref.parse_geojson(_geojson_square())

    assert len(vertices) == 4
    assert vertices[0] == {"lon": -48.0, "lat": -14.0}
    assert vertices[-1] == {"lon": -47.999, "lat": -14.0}


def test_parse_kml_polygon():
    kml = """<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <Placemark>
      <Polygon>
        <outerBoundaryIs>
          <LinearRing>
            <coordinates>
              -48.0,-14.0,0 -48.0,-14.001,0 -47.999,-14.001,0 -47.999,-14.0,0 -48.0,-14.0,0
            </coordinates>
          </LinearRing>
        </outerBoundaryIs>
      </Polygon>
    </Placemark>
  </Document>
</kml>
"""

    vertices = ref.parse_kml(kml)

    assert len(vertices) == 4
    assert vertices[1] == {"lon": -48.0, "lat": -14.001}


def test_parse_csv_ou_txt_com_cabecalho():
    conteudo = "lon,lat\n-48.0,-14.0\n-48.0,-14.001\n-47.999,-14.001\n-47.999,-14.0\n"

    vertices = ref.parse_csv_ou_txt(conteudo)

    assert len(vertices) == 4
    assert vertices[2] == {"lon": -47.999, "lat": -14.001}


def test_parse_shp_zip():
    shapefile = pytest.importorskip("shapefile")

    with tempfile.TemporaryDirectory() as temp_dir:
        base = Path(temp_dir) / "poligono"
        writer = shapefile.Writer(str(base), shapeType=shapefile.POLYGON)
        writer.field("nome", "C")
        writer.poly([[
            (-48.0, -14.0),
            (-48.0, -14.001),
            (-47.999, -14.001),
            (-47.999, -14.0),
            (-48.0, -14.0),
        ]])
        writer.record("A")
        writer.close()

        zip_path = Path(temp_dir) / "poligono.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            for ext in (".shp", ".shx", ".dbf"):
                zf.write(str(base) + ext, arcname="poligono" + ext)

        vertices = ref.parse_shp_zip(zip_path.read_bytes())

    assert len(vertices) == 4
    assert vertices[0] == {"lon": -48.0, "lat": -14.0}


def test_salvar_geometria_referencia_faz_fallback_local_quando_supabase_falha(monkeypatch):
    vertices = [
        {"lon": -48.0, "lat": -14.0},
        {"lon": -48.0, "lat": -14.001},
        {"lon": -47.999, "lat": -14.001},
    ]
    store: dict[str, dict[str, object]] = {}

    class FakeTabela:
        def select(self, *_args, **_kwargs):
            return self

        def eq(self, *_args, **_kwargs):
            return self

        def is_(self, *_args, **_kwargs):
            return self

        def order(self, *_args, **_kwargs):
            return self

        def limit(self, *_args, **_kwargs):
            return self

        def maybe_single(self):
            return self

        def execute(self):
            raise RuntimeError("supabase indisponivel")

    class FakeSb:
        def table(self, *_args, **_kwargs):
            return FakeTabela()

    monkeypatch.setattr(ref, "_carregar_store", lambda: store)
    monkeypatch.setattr(ref, "_salvar_store", lambda payload: store.update(payload))

    resultado = ref.salvar_geometria_referencia(
        sb=FakeSb(),
        cliente_id="cliente-1",
        projeto_id="projeto-1",
        nome="Croqui 1",
        origem_tipo="manual",
        formato="manual",
        arquivo_nome=None,
        vertices=vertices,
        comparativo=None,
    )

    assert resultado["persistencia"] == "arquivo_local"
    assert store["cliente-1"]["nome"] == "Croqui 1"
    assert store["cliente-1"]["resumo"]["vertices_total"] == 3


def test_remover_geometria_referencia_limpa_store_local(monkeypatch):
    store = {
        "cliente-1": {
            "id": "ref-1",
            "cliente_id": "cliente-1",
            "projeto_id": "projeto-1",
            "nome": "Croqui 1",
        }
    }

    class FakeTabela:
        def select(self, *_args, **_kwargs):
            return self

        def eq(self, *_args, **_kwargs):
            return self

        def is_(self, *_args, **_kwargs):
            return self

        def order(self, *_args, **_kwargs):
            return self

        def limit(self, *_args, **_kwargs):
            return self

        def maybe_single(self):
            return self

        def execute(self):
            class Resp:
                data = None

            return Resp()

    class FakeSb:
        def table(self, *_args, **_kwargs):
            return FakeTabela()

    monkeypatch.setattr(ref, "_carregar_store", lambda: store)
    monkeypatch.setattr(ref, "_salvar_store", lambda payload: store.update(payload))

    removido = ref.remover_geometria_referencia(FakeSb(), "cliente-1")

    assert removido is True
    assert "cliente-1" in store
    assert store["cliente-1"]["cliente_id"] == "cliente-1"
    assert store["cliente-1"]["deleted_at"] is not None
    assert store["cliente-1"]["persistencia"] == "arquivo_local"
