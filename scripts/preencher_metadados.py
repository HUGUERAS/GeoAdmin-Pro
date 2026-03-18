"""
scripts/preencher_metadados.py

Atualiza projetos no Supabase via PATCH /projetos/{id}.

Uso:
  python scripts/preencher_metadados.py [--dry-run]

  --dry-run: simula as chamadas sem alterar o banco

Edite PROJETOS abaixo antes de rodar.
"""

import argparse
import json
import sys
from datetime import datetime

import requests

BASE_URL = "http://127.0.0.1:8000"

# ── Lista de projetos a atualizar ──────────────────────────────────────────────
# Cada entrada: {"id": "<uuid>", "numero_job": "...", "municipio": "...", "estado": "..."}
# Campos opcionais: nome, status, zona_utm
PROJETOS = [
    # {
    #     "id": "00000000-0000-0000-0000-000000000001",
    #     "numero_job": "JOB-001",
    #     "municipio": "Campinas",
    #     "estado": "SP",
    # },
]
# ──────────────────────────────────────────────────────────────────────────────


def patch_projeto(projeto_id: str, dados: dict, dry_run: bool) -> dict:
    campos = {k: v for k, v in dados.items() if k != "id"}
    url = f"{BASE_URL}/projetos/{projeto_id}"

    if dry_run:
        return {"status": "dry-run", "id": projeto_id, "campos": campos}

    resp = requests.patch(url, json=campos, timeout=10)
    resp.raise_for_status()
    return {"status": "ok", "id": projeto_id, "retorno": resp.json()}


def main():
    parser = argparse.ArgumentParser(description="Preenche metadados de projetos via API")
    parser.add_argument("--dry-run", action="store_true", help="Simula sem alterar o banco")
    args = parser.parse_args()

    if not PROJETOS:
        print("⚠  Lista PROJETOS está vazia. Edite o script antes de rodar.", file=sys.stderr)
        sys.exit(1)

    log = []
    erros = 0

    for p in PROJETOS:
        projeto_id = p.get("id")
        if not projeto_id:
            print(f"  ERRO — entrada sem 'id': {p}", file=sys.stderr)
            erros += 1
            continue

        try:
            resultado = patch_projeto(projeto_id, p, dry_run=args.dry_run)
            log.append(resultado)
            prefixo = "[DRY-RUN]" if args.dry_run else "[OK]"
            print(f"  {prefixo} {projeto_id} → {resultado.get('campos', resultado.get('retorno'))}")
        except requests.HTTPError as exc:
            erros += 1
            entry = {"status": "erro_http", "id": projeto_id, "detalhe": str(exc)}
            log.append(entry)
            print(f"  [ERRO] {projeto_id} → HTTP {exc.response.status_code}: {exc.response.text}", file=sys.stderr)
        except Exception as exc:
            erros += 1
            entry = {"status": "erro", "id": projeto_id, "detalhe": str(exc)}
            log.append(entry)
            print(f"  [ERRO] {projeto_id} → {exc}", file=sys.stderr)

    # Output JSON do log
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = f"scripts/log_metadados_{ts}.json"
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(log, f, ensure_ascii=False, indent=2)

    print(f"\nTotal: {len(PROJETOS)} | Erros: {erros}")
    print(f"Log salvo em: {log_path}")

    if erros:
        sys.exit(1)


if __name__ == "__main__":
    main()
