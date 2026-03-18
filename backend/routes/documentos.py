"""
GeoAdmin Pro — Endpoints Magic Link + Geração de Documentos
backend/routes/documentos.py

POST /projetos/{id}/magic-link      → gera link e envia para cliente
GET  /formulario/cliente            → serve o formulário HTML
POST /formulario/cliente            → recebe dados preenchidos pelo cliente
POST /projetos/{id}/gerar-documentos → gera ZIP com os 7 docs GPRF
GET  /projetos/{id}/documentos      → lista docs gerados
"""

import uuid
import os
import logging
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import HTMLResponse, Response
from pydantic import BaseModel
from typing import Optional

logger = logging.getLogger("geoadmin.documentos")

router = APIRouter(tags=["Documentos GPRF"])


# ---------------------------------------------------------------------------
# Schema de entrada do formulário
# ---------------------------------------------------------------------------

class DadosFormulario(BaseModel):
    # Dados pessoais
    nome:               str
    cpf:                str
    rg:                 str
    estado_civil:       str
    profissao:          Optional[str] = ""
    telefone:           str
    email:              Optional[str] = ""
    conjuge_nome:       Optional[str] = ""
    conjuge_cpf:        Optional[str] = ""

    # Endereço
    endereco:           str
    endereco_numero:    Optional[str] = ""
    municipio:          str
    cep:                Optional[str] = ""

    # Imóvel
    nome_imovel:        str
    municipio_imovel:   str
    comarca:            Optional[str] = ""
    matricula:          Optional[str] = ""
    tempo_posse_anos:   Optional[int] = None

    # Confrontantes
    confrontantes:      list = []


# ---------------------------------------------------------------------------
# 1. Gerar Magic Link
# ---------------------------------------------------------------------------

@router.post("/projetos/{projeto_id}/magic-link",
             summary="Gerar link do formulário para o cliente")
def gerar_magic_link(projeto_id: str, supabase=None):
    """
    Gera um token único e retorna o link para o cliente preencher o formulário.
    O link expira em 7 dias.

    Retorna o link para você copiar e mandar via WhatsApp.
    """
    from main import get_supabase as _get
    sb = supabase or _get()

    # Buscar projeto e cliente
    try:
        res = sb.table("vw_projetos_completo") \
            .select("id, projeto_nome, cliente_id, cliente_nome") \
            .eq("id", projeto_id) \
            .single() \
            .execute()
    except Exception:
        raise HTTPException(404, {"erro": f"[ERRO-401] Projeto não encontrado.", "codigo": 401})

    projeto = res.data
    cliente_id = projeto.get("cliente_id")
    if not cliente_id:
        raise HTTPException(422, {"erro": "[ERRO-102] Projeto sem cliente vinculado.", "codigo": 102})

    # Gerar token
    token = str(uuid.uuid4())
    expira = datetime.utcnow() + timedelta(days=7)

    # Salvar no banco
    sb.table("clientes").update({
        "magic_link_token":  token,
        "magic_link_expira": expira.isoformat(),
    }).eq("id", cliente_id).execute()

    base_url = os.environ.get("APP_URL", "http://localhost:8000")
    link = f"{base_url}/formulario/cliente?token={token}"

    logger.info(f"Magic Link gerado para projeto '{projeto['projeto_nome']}'")

    return {
        "link":         link,
        "expira_em":    expira.strftime("%d/%m/%Y às %H:%M"),
        "cliente_nome": projeto.get("cliente_nome"),
        "projeto_nome": projeto.get("projeto_nome"),
        "mensagem_whatsapp": (
            f"Olá {projeto.get('cliente_nome', '')}! 👋\n\n"
            f"Para darmos andamento ao processo de regularização do imóvel "
            f"*{projeto.get('projeto_nome', '')}*, preciso que você preencha "
            f"um formulário com seus dados.\n\n"
            f"É rápido e pode fazer pelo celular:\n{link}\n\n"
            f"⏰ O link expira em 7 dias.\n\n"
            f"Qualquer dúvida é só chamar!"
        )
    }


# ---------------------------------------------------------------------------
# 2. Formulário do cliente (HTML)
# ---------------------------------------------------------------------------

@router.get("/formulario/cliente",
            response_class=HTMLResponse,
            summary="Formulário HTML para o cliente preencher")
def formulario_cliente(token: str = Query(...)):
    """Serve o formulário HTML. Validar token antes de mostrar."""
    html_path = os.path.join(
        os.path.dirname(__file__), "..", "static", "formulario_cliente.html"
    )
    try:
        with open(html_path, encoding="utf-8") as f:
            return HTMLResponse(f.read())
    except FileNotFoundError:
        raise HTTPException(404, "Formulário não encontrado.")


@router.post("/formulario/cliente",
             summary="Receber dados preenchidos pelo cliente")
def receber_formulario(
    dados: DadosFormulario,
    token: str = Query(...),
    supabase=None
):
    """
    Valida o token, salva os dados no banco e cria os confrontantes.
    Chamado pelo JavaScript do formulário HTML.
    """
    from main import get_supabase as _get
    sb = supabase or _get()

    # Validar token
    try:
        res_cli = sb.table("clientes") \
            .select("id, magic_link_expira") \
            .eq("magic_link_token", token) \
            .single() \
            .execute()
    except Exception:
        raise HTTPException(401, {"erro": "[ERRO-601] Token inválido.", "codigo": 601})

    cliente = res_cli.data
    if not cliente:
        raise HTTPException(401, {"erro": "[ERRO-601] Token inválido.", "codigo": 601})

    expira = cliente.get("magic_link_expira")
    if expira and datetime.fromisoformat(expira) < datetime.utcnow():
        raise HTTPException(401, {"erro": "[ERRO-602] Link expirado. Solicite um novo link.", "codigo": 602})

    cliente_id = cliente["id"]

    # Buscar projeto vinculado ao cliente
    res_proj = sb.table("projetos") \
        .select("id") \
        .eq("cliente_id", cliente_id) \
        .is_("deleted_at", "null") \
        .limit(1) \
        .execute()

    projeto_id = res_proj.data[0]["id"] if res_proj.data else None

    # Atualizar dados do cliente
    sb.table("clientes").update({
        "nome":             dados.nome,
        "cpf":              dados.cpf,
        "rg":               dados.rg,
        "estado_civil":     dados.estado_civil,
        "profissao":        dados.profissao,
        "telefone":         dados.telefone,
        "email":            dados.email,
        "conjuge_nome":     dados.conjuge_nome,
        "conjuge_cpf":      dados.conjuge_cpf,
        "endereco":         dados.endereco,
        "endereco_numero":  dados.endereco_numero,
        "municipio":        dados.municipio,
        "cep":              dados.cep,
        "formulario_ok":    True,
        "formulario_em":    datetime.utcnow().isoformat(),
    }).eq("id", cliente_id).execute()

    # Atualizar dados do projeto/imóvel
    if projeto_id:
        sb.table("projetos").update({
            "nome_imovel":       dados.nome_imovel,
            "municipio":         dados.municipio_imovel,
            "comarca":           dados.comarca,
            "matricula":         dados.matricula,
            "tempo_posse_anos":  dados.tempo_posse_anos,
        }).eq("id", projeto_id).execute()

        # Salvar confrontantes
        for conf in dados.confrontantes:
            if not conf.get("nome"):
                continue
            sb.table("confrontantes").insert({
                "projeto_id":   projeto_id,
                "lado":         conf.get("lado", "Outros"),
                "nome":         conf.get("nome"),
                "cpf":          conf.get("cpf", ""),
                "nome_imovel":  conf.get("nome_imovel", ""),
                "matricula":    conf.get("matricula", ""),
            }).execute()

    logger.info(f"Formulário recebido do cliente {cliente_id} — {len(dados.confrontantes)} confrontantes")

    return {"ok": True, "mensagem": "Dados recebidos com sucesso. Obrigado!"}


# ---------------------------------------------------------------------------
# 3. Gerar documentos GPRF
# ---------------------------------------------------------------------------

@router.post("/projetos/{projeto_id}/gerar-documentos",
             summary="Gerar ZIP com os 7 documentos GPRF",
             response_class=Response)
def gerar_documentos(projeto_id: str, supabase=None):
    """
    Gera os 7 documentos automaticamente e retorna um ZIP.
    Requer que o cliente tenha preenchido o formulário (formulario_ok=True).
    """
    from main import get_supabase as _get
    from integracoes.gerador_documentos import gerar_todos_documentos

    sb = supabase or _get()

    # Verificar se o formulário foi preenchido
    try:
        res = sb.table("vw_formulario_cliente") \
            .select("formulario_ok, cliente_nome, projeto_nome") \
            .eq("projeto_id", projeto_id) \
            .single() \
            .execute()
    except Exception:
        raise HTTPException(404, {"erro": "[ERRO-401] Projeto não encontrado.", "codigo": 401})

    dados_check = res.data
    if not dados_check.get("formulario_ok"):
        raise HTTPException(422, {
            "erro": (
                "[ERRO-103] Cliente ainda não preencheu o formulário. "
                "Envie o Magic Link primeiro via POST /projetos/{id}/magic-link."
            ),
            "codigo": 103
        })

    # Gerar documentos
    try:
        zip_bytes = gerar_todos_documentos(sb, projeto_id)
    except ValueError as e:
        raise HTTPException(422, {"erro": str(e), "codigo": 104})
    except Exception as e:
        raise HTTPException(500, {"erro": f"[ERRO-501] Falha ao gerar documentos: {e}", "codigo": 501})

    nome = f"GPRF_{dados_check.get('projeto_nome','projeto').replace(' ','_')[:25]}.zip"

    logger.info(f"Documentos GPRF gerados: {nome} ({len(zip_bytes)} bytes)")

    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{nome}"'}
    )


# ---------------------------------------------------------------------------
# 4. Listar documentos gerados
# ---------------------------------------------------------------------------

@router.get("/projetos/{projeto_id}/documentos",
            summary="Listar documentos gerados do projeto")
def listar_documentos(projeto_id: str, supabase=None):
    from main import get_supabase as _get
    sb = supabase or _get()

    try:
        res = sb.table("documentos_gerados") \
            .select("*") \
            .eq("projeto_id", projeto_id) \
            .order("gerado_em", desc=True) \
            .execute()
    except Exception as e:
        raise HTTPException(500, {"erro": f"[ERRO-502] {e}", "codigo": 502})

    return {"total": len(res.data), "documentos": res.data}
