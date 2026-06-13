import os
import json
from unittest.mock import MagicMock
from services.documentos import (
    calcular_pendencias_documentais,
    gerar_checklist_documental,
    registrar_upload_documento,
    aprovar_documento,
    recusar_documento
)

def test_calcular_pendencias():
    sb = MagicMock()
    docs = [
        {'id': '1', 'status': 'pendente', 'lote_id': 'l-1', 'participante_id': 'p-1'},
        {'id': '2', 'status': 'pendente', 'lote_id': 'l-1', 'participante_id': 'p-2'},
        {'id': '3', 'status': 'aprovado', 'lote_id': 'l-2', 'participante_id': 'p-3'}
    ]
    sb.table().select().eq().execute.return_value.data = docs
    
    resumo = calcular_pendencias_documentais(sb, 'proj-1')
    
    assert resumo['total'] == 3
    assert resumo['pendentes'] == 2
    assert resumo['aprovados'] == 1
    assert resumo['lotes_com_pendencia'] == 1
    assert resumo['participantes_com_pendencia'] == 2
    print("Test calcular pendencias: OK")

def test_gerar_checklist():
    sb = MagicMock()
    # Ja tem documento_pessoal
    sb.table().select().eq().execute.return_value.data = [{'tipo_documento': 'documento_pessoal'}]
    
    # insert retorna o gerado
    sb.table().insert().execute.return_value.data = [{'id': 'mocked-id'}]
    
    novos = gerar_checklist_documental(sb, 'proj-1')
    # Obrigatorios: 'documento_pessoal', 'comprovante_endereco', 'termo_adesao'
    # Como doc pessoal ja tem, vai gerar 2 novos
    assert len(novos) == 2
    print("Test gerar checklist: OK")

def test_recusar_documento():
    sb = MagicMock()
    sb.table().update().eq().execute.return_value.data = [{'id': 'doc-1', 'status': 'recusado', 'motivo_recusa': 'Ilegível'}]
    
    res = recusar_documento(sb, 'doc-1', 'Ilegível')
    assert res['status'] == 'recusado'
    assert res['motivo_recusa'] == 'Ilegível'
    print("Test recusar documento: OK")

if __name__ == "__main__":
    test_calcular_pendencias()
    test_gerar_checklist()
    test_recusar_documento()
    print("ALL DOCUMENTS TESTS PASSED")
