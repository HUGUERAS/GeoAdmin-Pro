import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

def calcular_pendencias_documentais(sb, projeto_id: str) -> Dict[str, Any]:
    # Busca todos os documentos do projeto
    resp = sb.table('documentos_projeto').select('*').eq('projeto_id', projeto_id).execute()
    docs = getattr(resp, 'data', [])
    
    total = len(docs)
    pendentes = sum(1 for d in docs if d['status'] == 'pendente')
    enviados = sum(1 for d in docs if d['status'] == 'enviado')
    em_analise = sum(1 for d in docs if d['status'] == 'em_analise')
    aprovados = sum(1 for d in docs if d['status'] == 'aprovado')
    recusados = sum(1 for d in docs if d['status'] == 'recusado')
    vencidos = sum(1 for d in docs if d['status'] == 'vencido')
    
    lotes_com_pendencia = len(set(d['lote_id'] for d in docs if d['status'] == 'pendente' and d.get('lote_id')))
    participantes_com_pendencia = len(set(d['participante_id'] for d in docs if d['status'] == 'pendente' and d.get('participante_id')))

    return {
        'total': total,
        'pendentes': pendentes,
        'enviados': enviados,
        'em_analise': em_analise,
        'aprovados': aprovados,
        'recusados': recusados,
        'vencidos': vencidos,
        'lotes_com_pendencia': lotes_com_pendencia,
        'participantes_com_pendencia': participantes_com_pendencia
    }

def gerar_checklist_documental(sb, projeto_id: str, lote_id: str = None, participante_id: str = None):
    """Injeta documentos obrigatórios pendentes se não existirem."""
    obrigatorios = ['documento_pessoal', 'comprovante_endereco', 'termo_adesao']
    
    # Busca existentes
    query = sb.table('documentos_projeto').select('tipo_documento').eq('projeto_id', projeto_id)
    if lote_id: query = query.eq('lote_id', lote_id)
    if participante_id: query = query.eq('participante_id', participante_id)
    
    existentes_resp = query.execute()
    existentes = [d['tipo_documento'] for d in getattr(existentes_resp, 'data', [])]
    
    novos = []
    for tipo in obrigatorios:
        if tipo not in existentes:
            payload = {
                'projeto_id': projeto_id,
                'lote_id': lote_id,
                'participante_id': participante_id,
                'tipo_documento': tipo,
                'status': 'pendente'
            }
            # limpa nulos pro insert
            payload = {k: v for k, v in payload.items() if v is not None}
            res = sb.table('documentos_projeto').insert(payload).execute()
            if getattr(res, 'data', []):
                novos.append(res.data[0])
                
    return novos

def listar_documentos_pendentes_projeto(sb, projeto_id: str) -> List[Dict[str, Any]]:
    resp = sb.table('documentos_projeto').select('*').eq('projeto_id', projeto_id).eq('status', 'pendente').execute()
    return getattr(resp, 'data', [])

def registrar_upload_documento(sb, documento_id: str, nome_arquivo: str, storage_path: str):
    payload = {
        'status': 'enviado',
        'nome_arquivo': nome_arquivo,
        'storage_path': storage_path
    }
    resp = sb.table('documentos_projeto').update(payload).eq('id', documento_id).execute()
    doc = getattr(resp, 'data', [{}])[0]
    from services.realtime.manager import publish_event
    publish_event(doc.get('projeto_id'), "document_status_changed", {"documento_id": documento_id, "status": "enviado"})
    publish_event(doc.get('projeto_id'), "operational_summary_changed")
    return doc

def aprovar_documento(sb, documento_id: str):
    resp = sb.table('documentos_projeto').update({'status': 'aprovado'}).eq('id', documento_id).execute()
    doc = getattr(resp, 'data', [{}])[0]
    from services.realtime.manager import publish_event
    publish_event(doc.get('projeto_id'), "document_status_changed", {"documento_id": documento_id, "status": "aprovado"})
    publish_event(doc.get('projeto_id'), "operational_summary_changed")
    return doc

def recusar_documento(sb, documento_id: str, motivo: str):
    resp = sb.table('documentos_projeto').update({'status': 'recusado', 'motivo_recusa': motivo}).eq('id', documento_id).execute()
    doc = getattr(resp, 'data', [{}])[0]
    from services.realtime.manager import publish_event
    publish_event(doc.get('projeto_id'), "document_status_changed", {"documento_id": documento_id, "status": "recusado"})
    publish_event(doc.get('projeto_id'), "operational_summary_changed")
    return doc
