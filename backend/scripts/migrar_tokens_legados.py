"""
GeoAdmin Pro — Script de migração de tokens legados
====================================================
Copia magic_link_token de clientes.magic_link_token para
projeto_clientes.magic_link_token, eliminando o campo legado
como fonte primária de lookup.

Uso:
    cd backend
    python scripts/migrar_tokens_legados.py [--dry-run] [--limpar-legado]

Flags:
    --dry-run       Mostra o que seria migrado sem alterar nada
    --limpar-legado Após migrar, zera magic_link_token nos clientes
                    (só faz isso se todos os tokens foram migrados com sucesso)
"""

import argparse
import logging
import os
import sys
from datetime import datetime, timezone

# Garante que o diretório pai (backend/) está no path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger("geoadmin.migracao_tokens")


def _get_supabase():
    from supabase import create_client
    url = os.getenv("SUPABASE_URL", "")
    key = os.getenv("SUPABASE_KEY", "")
    if not url or not key:
        raise RuntimeError("SUPABASE_URL e SUPABASE_KEY precisam estar definidos no .env")
    return create_client(url, key)


def migrar(*, dry_run: bool = True, limpar_legado: bool = False) -> dict:
    sb = _get_supabase()

    logger.info("=== Migração de tokens legados %s===", "(DRY RUN) " if dry_run else "")

    # 1. Buscar todos os clientes com magic_link_token preenchido
    try:
        res_clientes = (
            sb.table("clientes")
            .select("id, nome, magic_link_token, magic_link_expira")
            .not_.is_("magic_link_token", "null")
            .is_("deleted_at", "null")
            .execute()
        )
    except Exception as exc:
        if "magic_link_token" in str(exc).lower():
            logger.info("Coluna clientes.magic_link_token não existe — migração não necessária.")
            return {"status": "ja_migrado", "total": 0, "migrados": 0, "erros": 0}
        raise

    clientes_com_token = getattr(res_clientes, "data", None) or []
    logger.info("Clientes com token legado: %d", len(clientes_com_token))

    if not clientes_com_token:
        logger.info("Nenhum token legado encontrado. Migração concluída.")
        return {"status": "vazio", "total": 0, "migrados": 0, "erros": 0}

    migrados = 0
    erros: list[str] = []

    for cliente in clientes_com_token:
        cliente_id = cliente["id"]
        token = cliente.get("magic_link_token")
        expira = cliente.get("magic_link_expira")

        # 2. Verificar se já existe vínculo em projeto_clientes para este cliente
        try:
            res_vinculos = (
                sb.table("projeto_clientes")
                .select("id, magic_link_token")
                .eq("cliente_id", cliente_id)
                .is_("deleted_at", "null")
                .execute()
            )
            vinculos = getattr(res_vinculos, "data", None) or []
        except Exception as exc:
            msg = f"[{cliente_id}] Erro ao buscar vínculos: {exc}"
            logger.error(msg)
            erros.append(msg)
            continue

        if not vinculos:
            msg = f"[{cliente_id}] {cliente.get('nome', '?')} — nenhum vínculo em projeto_clientes; pulando."
            logger.warning(msg)
            continue

        # 3. Copiar token para cada vínculo sem token próprio
        for vinculo in vinculos:
            if vinculo.get("magic_link_token"):
                logger.info(
                    "[%s] vínculo %s já tem token — pulando.",
                    cliente_id, vinculo["id"]
                )
                continue

            logger.info(
                "[%s] %s → copiando token para vínculo %s",
                cliente_id, cliente.get("nome", "?"), vinculo["id"]
            )

            if not dry_run:
                try:
                    (
                        sb.table("projeto_clientes")
                        .update({
                            "magic_link_token": token,
                            "magic_link_expira": expira,
                        })
                        .eq("id", vinculo["id"])
                        .execute()
                    )
                    migrados += 1
                except Exception as exc:
                    msg = f"[{cliente_id}] Erro ao atualizar vínculo {vinculo['id']}: {exc}"
                    logger.error(msg)
                    erros.append(msg)
            else:
                migrados += 1  # dry-run conta intenção

    # 4. Limpar tokens legados (opcional, só se todos OK)
    if limpar_legado and not dry_run and not erros:
        logger.info("Limpando magic_link_token dos clientes migrados...")
        ids_migrados = [c["id"] for c in clientes_com_token]
        try:
            (
                sb.table("clientes")
                .update({"magic_link_token": None, "magic_link_expira": None})
                .in_("id", ids_migrados)
                .execute()
            )
            logger.info("Tokens legados limpos em %d clientes.", len(ids_migrados))
        except Exception as exc:
            logger.error("Erro ao limpar tokens legados: %s", exc)
            erros.append(f"Erro na limpeza final: {exc}")
    elif limpar_legado and erros:
        logger.warning("Limpeza cancelada por causa de %d erros acima.", len(erros))

    logger.info(
        "=== Concluído: %d migrados, %d erros %s===",
        migrados, len(erros), "(DRY RUN) " if dry_run else ""
    )
    return {
        "status": "ok" if not erros else "parcial",
        "total": len(clientes_com_token),
        "migrados": migrados,
        "erros": len(erros),
        "detalhes_erros": erros,
    }


def main():
    parser = argparse.ArgumentParser(description="Migra tokens legados de clientes para projeto_clientes")
    parser.add_argument("--dry-run", action="store_true", default=True,
                        help="Simula sem alterar nada (padrão: ativo)")
    parser.add_argument("--executar", action="store_true",
                        help="Executa a migração de verdade (sobrepõe --dry-run)")
    parser.add_argument("--limpar-legado", action="store_true",
                        help="Zera magic_link_token nos clientes após migração bem-sucedida")
    args = parser.parse_args()

    dry_run = not args.executar
    if dry_run:
        logger.info("Modo DRY RUN ativo. Use --executar para aplicar as mudanças.")

    resultado = migrar(dry_run=dry_run, limpar_legado=args.limpar_legado)
    print("\nResultado:", resultado)
    sys.exit(0 if resultado["erros"] == 0 else 1)


if __name__ == "__main__":
    main()
