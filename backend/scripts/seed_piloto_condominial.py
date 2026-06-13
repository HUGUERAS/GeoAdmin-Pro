import argparse
import sys
import os
import uuid
import random

# Adiciona backend no path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from main import get_supabase

def parse_args():
    parser = argparse.ArgumentParser(description="Seed para Piloto Condominial (Beta Controlado)")
    parser.add_argument("--projeto", type=str, default="Piloto Condominial MVP", help="Nome do projeto")
    parser.add_argument("--lotes", type=int, default=50, help="Quantidade de lotes gerados")
    parser.add_argument("--percentual-sem-participante", type=int, default=20, help="%% de lotes sem dono")
    parser.add_argument("--percentual-documentos-pendentes", type=int, default=30, help="%% de docs não enviados")
    parser.add_argument("--percentual-magic-links", type=int, default=50, help="%% de participantes com magic link ativado")
    parser.add_argument("--percentual-confrontacoes-pendentes", type=int, default=10, help="%% de lotes com confrontacoes pendentes")
    parser.add_argument("--dry-run", action="store_true", default=True, help="Apenas simula a operação")
    parser.add_argument("--execute", action="store_true", help="Realiza a inserção no banco (desativa dry-run)")
    return parser.parse_args()

def main():
    args = parse_args()
    
    is_dry_run = not args.execute
    if args.dry_run and not args.execute:
        is_dry_run = True

    print(f"=== GERADOR DE MASSA PARA PROJETO PILOTO ===")
    print(f"Projeto: {args.projeto}")
    print(f"Lotes alvo: {args.lotes}")
    print(f"Modo: {'DRY-RUN' if is_dry_run else 'EXECUTE (REAL)'}")
    print("============================================")

    if not is_dry_run:
        print("[AVISO] Inserção de dados reais ativada.")

    sb = None
    if not is_dry_run:
        sb = get_supabase()

    # 0. Auth User creation for owner_id
    owner_id = "00000000-0000-0000-0000-000000000000"
    if not is_dry_run:
        from supabase import create_client
        sb_auth = create_client(os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_ANON_KEY"))
        try:
            res = sb_auth.auth.sign_in_with_password({"email": "admin@geoadmin.com", "password": "password123"})
            owner_id = res.user.id
        except Exception:
            try:
                res = sb_auth.auth.sign_up({"email": "admin@geoadmin.com", "password": "password123"})
                owner_id = res.user.id
            except Exception as e:
                print(f"Failed to create/login user: {e}")
                owner_id = str(uuid.uuid4())

    # 1. Criação do Projeto
    projeto_id = str(uuid.uuid4())
    print(f"\n[1] Criando Projeto: {args.projeto} (ID: {projeto_id})")
    
    if not is_dry_run:
        sb.table("projetos").insert({
            "id": projeto_id, 
            "nome": args.projeto, 
            "status": "medicao",
            "owner_id": owner_id,
            "municipio": "São Paulo",
            "uf": "SP"
        }).execute()

    # 2. Criação de Lotes (Áreas de Projeto)
    print(f"[2] Gerando {args.lotes} Lotes...")
    lotes_inserir = []
    for i in range(1, args.lotes + 1):
        lote_id = str(uuid.uuid4())
        nome_lote = f"Lote {i:03d}"
        lotes_inserir.append({
            "id": lote_id,
            "projeto_id": projeto_id,
            "nome": nome_lote,
            "tipo": "lote"
        })
    
    if not is_dry_run and lotes_inserir:
        sb.table("areas_projeto").insert(lotes_inserir).execute()

    # 3. Criação de Participantes
    num_participantes = int(args.lotes * (1 - (args.percentual_sem_participante / 100.0)))
    print(f"[3] Gerando {num_participantes} Participantes ({(100-args.percentual_sem_participante)}% de ocupação)...")
    
    participantes_inserir = []
    vinculos_inserir = []
    documentos_inserir = []
    magic_links_inserir = []
    confrontacoes_inserir = []
    
    for i in range(num_participantes):
        cliente_id = str(uuid.uuid4())
        participante_id = str(uuid.uuid4())
        lote_alvo = lotes_inserir[i]
        telefone = f"551199999{random.randint(1000, 9999)}"
        cpf = f"{random.randint(100, 999)}.{random.randint(100, 999)}.{random.randint(100, 999)}-{random.randint(10, 99)}"
        
        # Insere em clientes
        if not is_dry_run:
            sb.table("clientes").insert({
                "id": cliente_id,
                "owner_id": owner_id,
                "nome_razao": f"Morador Piloto {i+1}",
                "tipo_pessoa": "fisica",
                "cpf_cnpj": cpf,
                "contato": {"telefone": telefone}
            }).execute()

        # Insere no projeto_clientes
        participantes_inserir.append({
            "id": participante_id,
            "projeto_id": projeto_id,
            "cliente_id": cliente_id,
            "area_id": lote_alvo["id"],
            "papel": "coproprietario",
            "principal": False
        })

        # Vinculo lote-participante
        vinculos_inserir.append({
            "area_id": lote_alvo["id"],
            "cliente_id": cliente_id,
            "papel": "principal",
            "principal": True
        })

        # Documentos para este lote/participante
        has_pending_docs = random.randint(1, 100) <= args.percentual_documentos_pendentes
        documentos_inserir.append({
            "id": str(uuid.uuid4()),
            "projeto_id": projeto_id,
            "lote_id": lote_alvo["id"],
            "participante_id": participante_id,
            "cliente_id": cliente_id,
            "tipo_documento": "RG",
            "status": "pendente" if has_pending_docs else "aprovado"
        })

        # Magic Links pendentes
        is_magic_link_pending = random.randint(1, 100) <= args.percentual_magic_links
        if is_magic_link_pending:
            magic_links_inserir.append({
                "id": str(uuid.uuid4()),
                "projeto_id": projeto_id,
                "projeto_cliente_id": participante_id,
                "area_id": lote_alvo["id"],
                "cliente_id": cliente_id,
                "tipo_evento": "gerado",
                "token_hash": str(uuid.uuid4()),
                "expira_em": "2026-12-31T23:59:59Z"
            })

        # Confrontações pendentes
        is_confrontacao_pending = random.randint(1, 100) <= args.percentual_confrontacoes_pendentes
        if is_confrontacao_pending:
            confrontacoes_inserir.append({
                "id": str(uuid.uuid4()),
                "projeto_id": projeto_id,
                "area_id": lote_alvo["id"],
                "cliente_id": cliente_id,
                "tipo_evento": "reclassificacao",
                "observacao": "Pendente de assinatura de confrontante"
            })

    if not is_dry_run and participantes_inserir:
        sb.table("projeto_clientes").insert(participantes_inserir).execute()
        sb.table("area_clientes").insert(vinculos_inserir).execute()
        sb.table("documentos_projeto").insert(documentos_inserir).execute()
        if magic_links_inserir:
            sb.table("eventos_magic_link").insert(magic_links_inserir).execute()
        if confrontacoes_inserir:
            sb.table("eventos_cartograficos").insert(confrontacoes_inserir).execute()

    # 4. Geração de Inbound Simulado (Dry-Run)
    print(f"[4] Gerando Mensagens Operacionais...")
    msg_id = str(uuid.uuid4())
    if not is_dry_run and participantes_inserir:
        # Simulamos uma mensagem de boas vindas aprovada (draft -> approved -> sent)
        sb.table("mensagens_externas").insert({
            "id": msg_id,
            "projeto_id": projeto_id,
            "canal": "whatsapp",
            "direcao": "outbound",
            "conteudo": "Olá! Bem-vindo ao Piloto do Condomínio.",
            "status": "sent"
        }).execute()

    print("\n[SUCESSO] Seed concluído.")
    if is_dry_run:
        print("[INFO] Nenhuma alteração foi feita no banco (DRY-RUN ativo). Use --execute para rodar de verdade.")

if __name__ == "__main__":
    main()
