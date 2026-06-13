import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

def resumir_pendencias_projeto(sb, projeto_id: str) -> Dict[str, Any]:
    """Retorna um resumo agregado das pendÃªncias operacionais de um projeto."""
    try:
        # 1. Total Lotes
        resp_lotes = sb.table('areas_projeto').select('id', count='exact').eq('projeto_id', projeto_id).is_('deleted_at', 'null').execute()
        total_lotes = getattr(resp_lotes, 'count', 0) or 0

        # 2. Lotes com Participante
        # Precisamos buscar areas_projeto e ver quais estÃ£o em area_clientes
        resp_area_clientes = sb.table('area_clientes').select('area_id', count='exact').is_('deleted_at', 'null').execute()
        # Nota: O supabase python client filter in() nÃ£o Ã© simples, entÃ£o podemos buscar agrupado ou fazer a conta lÃ³gica:
        # Como Ã© um dashboard, a query direta pelo Supabase client Ã© limitante. 
        # Vamos contar areas cujo status_operacional != 'aguardando_cliente'
        resp_lotes_com = sb.table('areas_projeto').select('id', count='exact').eq('projeto_id', projeto_id).neq('status_operacional', 'aguardando_cliente').is_('deleted_at', 'null').execute()
        lotes_com_participante = getattr(resp_lotes_com, 'count', 0) or 0
        lotes_sem_participante = total_lotes - lotes_com_participante

        # 3. Magic Links
        resp_ml_enviados = sb.table('eventos_magic_link').select('id', count='exact').eq('projeto_id', projeto_id).in_('tipo_evento', ['gerado', 'reenviado']).is_('deleted_at', 'null').execute()
        magic_links_enviados = getattr(resp_ml_enviados, 'count', 0) or 0

        resp_ml_pendentes = sb.table('eventos_magic_link').select('id', count='exact').eq('projeto_id', projeto_id).eq('tipo_evento', 'gerado').is_('deleted_at', 'null').execute()
        magic_links_pendentes = getattr(resp_ml_pendentes, 'count', 0) or 0

        # 4. ConfrontaÃ§Ãµes pendentes
        resp_conf_pend = sb.table('confrontacoes_revisadas').select('id', count='exact').eq('projeto_id', projeto_id).eq('status_revisao', 'detectada').is_('deleted_at', 'null').execute()
        confrontacoes_pendentes = getattr(resp_conf_pend, 'count', 0) or 0

        return {
            "projeto_id": projeto_id,
            "total_lotes": total_lotes,
            "lotes_com_participante": lotes_com_participante,
            "lotes_sem_participante": lotes_sem_participante,
            "magic_links_enviados": magic_links_enviados,
            "magic_links_pendentes": magic_links_pendentes,
            "confrontacoes_pendentes": confrontacoes_pendentes,
            "documentos_pendentes": 0, # Fonte futura
            "ultima_atualizacao": "agora"
        }
    except Exception as e:
        logger.error(f"Erro ao resumir pendencias: {e}")
        return {
            "projeto_id": projeto_id,
            "total_lotes": 0,
            "lotes_com_participante": 0,
            "lotes_sem_participante": 0,
            "magic_links_enviados": 0,
            "magic_links_pendentes": 0,
            "confrontacoes_pendentes": 0,
            "documentos_pendentes": 0,
            "ultima_atualizacao": "erro"
        }

def listar_lotes_sem_participante(sb, projeto_id: str) -> List[Dict[str, Any]]:
    try:
        resp = sb.table('areas_projeto').select('id, codigo_lote, quadra, setor').eq('projeto_id', projeto_id).eq('status_operacional', 'aguardando_cliente').is_('deleted_at', 'null').execute()
        return getattr(resp, 'data', []) or []
    except Exception as e:
        logger.error(f"Erro ao listar lotes sem participante: {e}")
        return []

def listar_magic_links_pendentes(sb, projeto_id: str) -> List[Dict[str, Any]]:
    try:
        resp = sb.table('eventos_magic_link').select('id, canal, criado_em, projeto_cliente_id, area_id').eq('projeto_id', projeto_id).in_('tipo_evento', ['gerado', 'reenviado']).is_('deleted_at', 'null').execute()
        return getattr(resp, 'data', []) or []
    except Exception as e:
        logger.error(f"Erro ao listar magic links pendentes: {e}")
        return []

def listar_pendencias_por_lote(sb, projeto_id: str, lote_id: str) -> Dict[str, Any]:
    try:
        resp_area = sb.table('areas_projeto').select('*').eq('id', lote_id).eq('projeto_id', projeto_id).is_('deleted_at', 'null').maybe_single().execute()
        if not getattr(resp_area, 'data', None): return {'erro': 'Lote nao encontrado'}
        
        resp_cli = sb.table('area_clientes').select('*').eq('area_id', lote_id).is_('deleted_at', 'null').execute()
        clientes = getattr(resp_cli, 'data', []) or []
        
        resp_ml = sb.table('eventos_magic_link').select('*').eq('area_id', lote_id).is_('deleted_at', 'null').execute()
        ml = getattr(resp_ml, 'data', []) or []
        
        return {
            'lote_id': lote_id,
            'status_operacional': resp_area.data.get('status_operacional'),
            'status_documental': resp_area.data.get('status_documental'),
            'participantes_vinculados': len(clientes),
            'magic_links': len(ml),
            'documentos_pendentes': None,
            'observacao': 'Nao ha tabela estruturada de documentos pendentes encontrada no banco atual.'
        }
    except Exception as e:
        logger.error(f'Erro ao listar pendencias por lote: {e}')
        return {}

def calcular_indicadores_operacionais(sb, projeto_id: str) -> Dict[str, Any]:
    resumo = resumir_pendencias_projeto(sb, projeto_id)
    if resumo['total_lotes'] == 0: return {}
    pct_participantes = round((resumo['lotes_com_participante'] / resumo['total_lotes']) * 100, 2)
    return {
        'saude_geral': 'boa' if pct_participantes > 80 else 'critica',
        'percentual_com_participante': pct_participantes,
        'gargalo_principal': 'magic_links' if resumo['magic_links_pendentes'] > resumo['lotes_sem_participante'] else 'cadastro_clientes'
    }

