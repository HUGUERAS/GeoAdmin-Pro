"""
VERTEX — Complemento interno de leitura de documentos (Google Cloud Vision).

Usado pelo POST /formulario/foto para tentar preencher CPF/RG/nome a partir das
fotos enviadas. Nao e um fluxo separado: se a Vision falhar, o cadastro segue
normalmente com as fotos salvas para revisao manual.
"""
from __future__ import annotations

import logging
import re

logger = logging.getLogger("vertex.ocr")


def extrair_texto(imagem_bytes: bytes) -> str:
    if not imagem_bytes:
        return ""
    try:
        from google.cloud import vision
    except Exception as exc:  # lib nao instalada
        logger.warning("google-cloud-vision indisponivel: %s", exc)
        return ""
    try:
        client = vision.ImageAnnotatorClient()
        image = vision.Image(content=imagem_bytes)
        resp = client.document_text_detection(image=image)
        if getattr(resp, "error", None) and resp.error.message:
            logger.warning("Vision retornou erro: %s", resp.error.message)
            return ""
        return (resp.full_text_annotation.text or "").strip()
    except Exception as exc:
        logger.warning("Falha no OCR Vision: %s", exc)
        return ""


def _so_digitos(valor: str) -> str:
    return "".join(ch for ch in valor if ch.isdigit())


def parsear_campos(texto: str) -> dict:
    """Extrai campos de documento brasileiro a partir do texto do OCR.
    Heuristico: CPF e o mais confiavel (regex). RG e nome sao best-effort."""
    out: dict = {}
    if not texto:
        return out

    # CPF: 000.000.000-00 ou 11 digitos isolados
    m = re.search(r"\b(\d{3}\.?\d{3}\.?\d{3}-?\d{2})\b", texto)
    if m:
        cpf = _so_digitos(m.group(1))
        if len(cpf) == 11:
            out["cpf"] = cpf

    # RG: numero proximo do rotulo RG
    m = re.search(r"RG[:\s\-]*([\d][\d.\-\sXx]{4,16})", texto, re.IGNORECASE)
    if m:
        rg = m.group(1).strip().rstrip(".- ")
        if rg:
            out["rg"] = rg

    # Nome: linha apos rotulo NOME (documentos costumam ter "NOME")
    m = re.search(r"NOME[:\s]*\n?([A-Z\u00c0-\u00da][A-Z\u00c0-\u00da \.]{4,})", texto)
    if m:
        nome = m.group(1).strip()
        # evita pegar rotulos como "NOME DO PAI" etc.
        if nome and " DO " not in f" {nome} " and " DA " not in f" {nome} ":
            out["nome"] = " ".join(p.capitalize() for p in nome.split())

    return out


def ocr_documentos(imagens: list[bytes]) -> dict:
    """Roda OCR em varias imagens e agrega os campos encontrados + texto bruto."""
    textos = []
    campos: dict = {}
    for img in imagens:
        texto = extrair_texto(img)
        if texto:
            textos.append(texto)
            for k, v in parsear_campos(texto).items():
                campos.setdefault(k, v)  # primeira ocorrencia vence
    campos["_texto_ocr"] = "\n---\n".join(textos)[:5000]
    return campos
