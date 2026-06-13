"""Testes do parser de OCR (sem chamar a Vision real)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services import ocr_vision as ocr


def test_parseia_cpf_formatado():
    texto = "REPUBLICA FEDERATIVA DO BRASIL\nNOME\nMARIA ROSA ALMEIDA\nCPF 123.456.789-01"
    campos = ocr.parsear_campos(texto)
    assert campos.get("cpf") == "12345678901"
    assert campos.get("nome") == "Maria Rosa Almeida"


def test_parseia_cpf_sem_pontuacao():
    campos = ocr.parsear_campos("doc 98765432100 fim")
    assert campos.get("cpf") == "98765432100"


def test_parseia_rg():
    campos = ocr.parsear_campos("RG: 1.234.567 SSP-DF")
    assert "rg" in campos


def test_texto_vazio():
    assert ocr.parsear_campos("") == {}


def test_ocr_documentos_agrega(monkeypatch):
    # Mocka extrair_texto para nao chamar a Vision
    textos = iter(["NOME\nJOAO DA SILVA\nCPF 11122233344", "RG 9.999.999"])
    monkeypatch.setattr(ocr, "extrair_texto", lambda b: next(textos, ""))
    res = ocr.ocr_documentos([b"img1", b"img2"])
    assert res.get("cpf") == "11122233344"
    assert "rg" in res
    assert "_texto_ocr" in res


def test_extrair_texto_sem_lib_retorna_vazio(monkeypatch):
    # Simula ausencia da lib google.cloud.vision -> retorna ""
    import builtins
    real_import = builtins.__import__

    def fake_import(name, *a, **k):
        if name.startswith("google.cloud"):
            raise ImportError("no vision")
        return real_import(name, *a, **k)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    assert ocr.extrair_texto(b"qualquer") == ""
