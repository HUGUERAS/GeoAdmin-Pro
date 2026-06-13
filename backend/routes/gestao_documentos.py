from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional

from middleware.auth import verificar_token
from main import get_supabase
from services.documentos import (
    calcular_pendencias_documentais,
    gerar_checklist_documental,
    listar_documentos_pendentes_projeto,
    registrar_upload_documento,
    aprovar_documento,
    recusar_documento
)

router = APIRouter(prefix="/projetos", tags=["Gestão Documental"])

@router.get("/{projeto_id}/gestao-documentos/resumo", dependencies=[Depends(verificar_token)])
def get_resumo_documental(projeto_id: str):
    sb = get_supabase()
    return calcular_pendencias_documentais(sb, projeto_id)

@router.get("/{projeto_id}/gestao-documentos/pendentes", dependencies=[Depends(verificar_token)])
def get_documentos_pendentes(projeto_id: str):
    sb = get_supabase()
    return listar_documentos_pendentes_projeto(sb, projeto_id)

class DocumentoUpload(BaseModel):
    documento_id: str
    nome_arquivo: str
    storage_path: str

@router.post("/{projeto_id}/gestao-documentos/upload", dependencies=[Depends(verificar_token)])
def upload_documento(projeto_id: str, payload: DocumentoUpload):
    sb = get_supabase()
    return registrar_upload_documento(sb, payload.documento_id, payload.nome_arquivo, payload.storage_path)

class RecusaPayload(BaseModel):
    motivo: str

@router.post("/{projeto_id}/gestao-documentos/{documento_id}/aprovar", dependencies=[Depends(verificar_token)])
def aprovar_doc(projeto_id: str, documento_id: str):
    sb = get_supabase()
    return aprovar_documento(sb, documento_id)

@router.post("/{projeto_id}/gestao-documentos/{documento_id}/recusar", dependencies=[Depends(verificar_token)])
def recusar_doc(projeto_id: str, documento_id: str, payload: RecusaPayload):
    sb = get_supabase()
    return recusar_documento(sb, documento_id, payload.motivo)

class ChecklistPayload(BaseModel):
    lote_id: Optional[str] = None
    participante_id: Optional[str] = None

@router.post("/{projeto_id}/gestao-documentos/checklist", dependencies=[Depends(verificar_token)])
def gerar_checklist(projeto_id: str, payload: ChecklistPayload):
    sb = get_supabase()
    return gerar_checklist_documental(sb, projeto_id, payload.lote_id, payload.participante_id)

# Relatorio de pendencias simples (JSON estruturado)
@router.get("/{projeto_id}/gestao-documentos/relatorio-pendencias", dependencies=[Depends(verificar_token)])
def relatorio_pendencias(projeto_id: str):
    sb = get_supabase()
    pendentes = listar_documentos_pendentes_projeto(sb, projeto_id)
    return {
        "projeto_id": projeto_id,
        "titulo": "Relatório de Pendências Documentais",
        "total_pendente": len(pendentes),
        "itens": pendentes
    }
