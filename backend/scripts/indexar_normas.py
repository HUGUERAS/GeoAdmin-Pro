"""
backend/scripts/indexar_normas.py

Indexa documentos das normas INCRA no Supabase (pgvector) usando
embeddings voyage-3 da Anthropic.

Uso:
  cd backend
  python scripts/indexar_normas.py

Coloque os arquivos PDF ou TXT em backend/normas/:
  normas/norma_tecnica_3ed.pdf
  normas/lei_13465_2017.pdf
  normas/manual_sigef.pdf

Requer:
  pip install anthropic PyMuPDF python-dotenv
  ANTHROPIC_API_KEY no .env
"""

import os
import sys
import re
import time
from pathlib import Path

from dotenv import load_dotenv

# Adiciona o diretório backend ao path
sys.path.insert(0, str(Path(__file__).parent.parent))
load_dotenv()


NORMAS_DIR = Path(__file__).parent.parent / "normas"
CHUNK_SIZE  = 500    # tokens aproximados (1 token ≈ 4 chars em PT)
CHUNK_CHARS = CHUNK_SIZE * 4
OVERLAP     = 50 * 4  # 50 tokens de overlap

DOCUMENTOS = {
    "norma_tecnica_3ed": "Norma Técnica de Georreferenciamento de Imóveis Rurais — 3ª Ed. INCRA",
    "lei_13465_2017":    "Lei 13.465/2017 — Regularização Fundiária Rural e Urbana",
    "manual_sigef":      "Manual Técnico do SIGEF — INCRA",
}


def extrair_texto_pdf(caminho: Path) -> str:
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(str(caminho))
        textos = []
        for pagina in doc:
            textos.append(pagina.get_text())
        return "\n".join(textos)
    except ImportError:
        print("  [AVISO] PyMuPDF não instalado. Instale com: pip install PyMuPDF")
        return ""


def extrair_texto(caminho: Path) -> str:
    if caminho.suffix.lower() == ".pdf":
        return extrair_texto_pdf(caminho)
    return caminho.read_text(encoding="utf-8", errors="replace")


def dividir_chunks(texto: str, documento: str, nome_arquivo: str) -> list[dict]:
    """Divide texto em chunks com overlap, preservando parágrafos."""
    # Divide em parágrafos
    paragrafos = re.split(r"\n{2,}", texto.strip())
    chunks = []
    buffer = ""
    pagina = 1

    for par in paragrafos:
        par = par.strip()
        if not par:
            continue

        # Detecta número de página aproximado (para PDFs)
        if re.match(r"^\d+$", par):
            pagina = int(par)
            continue

        buffer += par + "\n\n"

        if len(buffer) >= CHUNK_CHARS:
            trecho = buffer[:CHUNK_CHARS]
            # Tenta cortar no final de uma frase
            corte = trecho.rfind(". ")
            if corte > CHUNK_CHARS // 2:
                trecho = trecho[:corte + 1]

            fonte = f"{DOCUMENTOS.get(nome_arquivo, documento)}, p.{pagina}"
            chunks.append({
                "documento": nome_arquivo,
                "fonte": fonte,
                "pagina": pagina,
                "texto": trecho.strip(),
            })
            # Overlap: mantém os últimos OVERLAP chars no buffer
            buffer = buffer[len(trecho) - OVERLAP:]

    # Último chunk com o que sobrou
    if buffer.strip():
        fonte = f"{DOCUMENTOS.get(nome_arquivo, documento)}, p.{pagina}"
        chunks.append({
            "documento": nome_arquivo,
            "fonte": fonte,
            "pagina": pagina,
            "texto": buffer.strip(),
        })

    return chunks


def indexar():
    import anthropic
    from main import get_supabase

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERRO: ANTHROPIC_API_KEY não encontrada no .env")
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)
    sb = get_supabase()

    if not NORMAS_DIR.exists():
        NORMAS_DIR.mkdir(parents=True)
        print(f"Pasta criada: {NORMAS_DIR}")
        print("Coloque os PDFs/TXTs das normas INCRA nessa pasta e rode novamente.")
        return

    arquivos = list(NORMAS_DIR.glob("*.pdf")) + list(NORMAS_DIR.glob("*.txt"))
    if not arquivos:
        print(f"Nenhum arquivo encontrado em {NORMAS_DIR}")
        return

    total_chunks = 0

    for arq in arquivos:
        nome_arquivo = arq.stem
        print(f"\n📄 Processando: {arq.name}")

        texto = extrair_texto(arq)
        if not texto.strip():
            print(f"  [AVISO] Texto vazio em {arq.name}, pulando.")
            continue

        chunks = dividir_chunks(texto, arq.name, nome_arquivo)
        print(f"  {len(chunks)} chunks gerados")

        for i, chunk in enumerate(chunks, 1):
            print(f"  [{i}/{len(chunks)}] Gerando embedding...", end="\r")

            # Gera embedding via voyage-3
            resp = client.embeddings.create(
                model="voyage-3",
                input=[chunk["texto"]],
            )
            vetor = resp.embeddings[0].embedding

            # Upsert no Supabase
            sb.table("normas_chunks").upsert({
                "documento": chunk["documento"],
                "fonte": chunk["fonte"],
                "pagina": chunk["pagina"],
                "texto": chunk["texto"],
                "embedding": vetor,
            }).execute()

            total_chunks += 1

            # Rate limit: voyage-3 tem limite de requests/min
            if i % 10 == 0:
                time.sleep(1)

        print(f"  ✅ {len(chunks)} chunks indexados")

    print(f"\n✅ Total indexado: {total_chunks} chunks")
    print("Rode POST /rag/consultar para testar.")


if __name__ == "__main__":
    indexar()
