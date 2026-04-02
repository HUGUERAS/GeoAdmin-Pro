from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

logger = logging.getLogger(__name__)

PAPEIS_VALIDOS = {
    'principal',
    'coproprietario',
    'possuidor',
    'herdeiro',
    'representante',
    'outro',
}

EVENTOS_MAGIC_LINK_VALIDOS = {'gerado', 'reenviado', 'revogado', 'consumido', 'legado'}
CANAIS_MAGIC_LINK_VALIDOS = {'whatsapp', 'email', 'sms', 'manual', 'interno'}


def _erro_schema(exc: Exception, trecho: str) -> bool:
    return trecho.lower() in str(exc).lower()


def _dados(resposta: Any) -> list[dict[str, Any]]:
    return getattr(resposta, 'data', None) or []


def _normalizar_documento(valor: str | None) -> str:
    return ''.join(ch for ch in str(valor or '') if ch.isdigit())


def _normalizar_papel(valor: str | None) -> str:
    papel = (valor or 'outro').strip().lower()
    if papel not in PAPEIS_VALIDOS:
        return 'outro'
    return papel


def _normalizar_tipo_evento(valor: str | None) -> str:
    chave = (valor or 'gerado').strip().lower()
    return chave if chave in EVENTOS_MAGIC_LINK_VALIDOS else 'gerado'


def _normalizar_canal(valor: str | None) -> str:
    chave = (valor or 'whatsapp').strip().lower()
    return chave if chave in CANAIS_MAGIC_LINK_VALIDOS else 'whatsapp'


def _buscar_cliente_por_documento(sb, cpf: str | None) -> dict[str, Any] | None:
    documento = _normalizar_documento(cpf)
    if not documento:
        return None
    for campo in ('cpf_cnpj', 'cpf'):
        try:
            resposta = (
                sb.table('clientes')
                .select('id, nome, cpf_cnpj, cpf, telefone, email, deleted_at, formulario_ok, formulario_em')
                .eq(campo, documento)
                .limit(1)
                .execute()
            )
        except Exception as exc:
            if _erro_schema(exc, f"'{campo}' column"):
                continue
            raise
        dados = _dados(resposta)
        if dados:
            return dados[0]
    return None


def _payload_cliente(nome: str, cpf: str | None, telefone: str | None, *, preferir_cpf_cnpj: bool = True) -> dict[str, Any]:
    payload: dict[str, Any] = {
        'nome': (nome or '').strip() or 'Cliente sem nome',
        'telefone': (telefone or '').strip() or None,
        'deleted_at': None,
    }
    documento = _normalizar_documento(cpf)
    if preferir_cpf_cnpj:
        payload['cpf_cnpj'] = documento or None
    else:
        payload['cpf'] = documento or None
    return payload


def resolver_cliente_participante(sb, participante: dict[str, Any]) -> str:
    cliente_id = participante.get('cliente_id')
    if cliente_id:
        return str(cliente_id)

    nome = (participante.get('nome') or '').strip()
    cpf = participante.get('cpf')
    telefone = participante.get('telefone')

    cliente_existente = _buscar_cliente_por_documento(sb, cpf)
    if cliente_existente:
        cliente_existente_id = str(cliente_existente['id'])
        try:
            (
                sb.table('clientes')
                .update(_payload_cliente(nome or cliente_existente.get('nome') or 'Cliente sem nome', cpf, telefone))
                .eq('id', cliente_existente_id)
                .execute()
            )
        except Exception:
            pass
        return cliente_existente_id

    ultimo_erro: Exception | None = None
    for preferir_cpf_cnpj in (True, False):
        try:
            resposta = sb.table('clientes').insert(
                _payload_cliente(nome, cpf, telefone, preferir_cpf_cnpj=preferir_cpf_cnpj)
            ).execute()
            dados = _dados(resposta)
            if dados:
                return str(dados[0]['id'])
        except Exception as exc:
            ultimo_erro = exc
            coluna = 'cpf_cnpj' if preferir_cpf_cnpj else 'cpf'
            if _erro_schema(exc, f"'{coluna}' column"):
                continue
            raise
    if ultimo_erro:
        raise ultimo_erro
    raise RuntimeError('Nao foi possivel resolver cliente participante')


def normalizar_participantes_entrada(payload_participantes: list[dict[str, Any]] | None, legado: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    participantes: list[dict[str, Any]] = []
    for indice, bruto in enumerate(payload_participantes or []):
        recebe_magic_link_bruto = bruto['recebe_magic_link'] if 'recebe_magic_link' in bruto else bruto.get('gerar_magic_link', indice == 0)
        participante = {
            'cliente_id': bruto.get('cliente_id'),
            'nome': (bruto.get('nome') or '').strip(),
            'cpf': _normalizar_documento(bruto.get('cpf')),
            'telefone': (bruto.get('telefone') or '').strip(),
            'papel': _normalizar_papel(bruto.get('papel')),
            'principal': bool(bruto.get('principal')),
            'recebe_magic_link': bool(recebe_magic_link_bruto),
            'ordem': int(bruto.get('ordem') or indice),
            'area_id': bruto.get('area_id'),
        }
        participantes.append(participante)

    if not participantes and legado:
        nome = (legado.get('cliente_nome') or '').strip()
        cpf = _normalizar_documento(legado.get('cliente_cpf'))
        telefone = (legado.get('cliente_telefone') or '').strip()
        cliente_id = legado.get('cliente_id')
        if nome or cpf or telefone or cliente_id:
            participantes.append({
                'cliente_id': cliente_id,
                'nome': nome,
                'cpf': cpf,
                'telefone': telefone,
                'papel': 'principal',
                'principal': True,
                'recebe_magic_link': bool(legado.get('gerar_magic_link', True)),
                'ordem': 0,
                'area_id': None,
            })

    if participantes:
        indice_principal = next((idx for idx, item in enumerate(participantes) if item.get('principal')), 0)
        for idx, item in enumerate(participantes):
            item['principal'] = idx == indice_principal
            if item['principal']:
                item['papel'] = 'principal'
    return participantes


def salvar_participantes_projeto(sb, projeto_id: str, participantes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not participantes:
        return []

    registros: list[dict[str, Any]] = []
    for ordem, participante in enumerate(participantes):
        cliente_id = resolver_cliente_participante(sb, participante)
        registros.append({
            'projeto_id': projeto_id,
            'cliente_id': cliente_id,
            'papel': _normalizar_papel(participante.get('papel')),
            'principal': bool(participante.get('principal')),
            'recebe_magic_link': bool(participante.get('recebe_magic_link')),
            'ordem': int(participante.get('ordem') or ordem),
            'area_id': participante.get('area_id'),
            'deleted_at': None,
        })

    try:
        sb.table('projeto_clientes').update({'deleted_at': datetime.now(timezone.utc).isoformat()}).eq('projeto_id', projeto_id).is_('deleted_at', 'null').execute()
        resposta = sb.table('projeto_clientes').insert(registros).execute()
        return _dados(resposta)
    except Exception as exc:
        if _erro_schema(exc, "'projeto_clientes' column") or 'projeto_clientes' in str(exc).lower():
            return []
        raise


def listar_participantes_projeto(sb, projeto_id: str, cliente_principal: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    try:
        resposta = (
            sb.table('projeto_clientes')
            .select('id, projeto_id, cliente_id, papel, principal, recebe_magic_link, ordem, area_id, magic_link_token, magic_link_expira, criado_em, clientes!inner(id, nome, cpf_cnpj, cpf, telefone, email, formulario_ok, formulario_em, deleted_at)')
            .eq('projeto_id', projeto_id)
            .is_('deleted_at', 'null')
            .order('ordem', desc=False)
            .execute()
        )
        itens = _dados(resposta)
        participantes: list[dict[str, Any]] = []
        for item in itens:
            cliente = item.get('clientes') or {}
            if cliente.get('deleted_at'):
                continue
            participantes.append({
                'id': item.get('id'),
                'projeto_id': item.get('projeto_id'),
                'cliente_id': item.get('cliente_id') or cliente.get('id'),
                'papel': item.get('papel') or 'outro',
                'principal': bool(item.get('principal')),
                'recebe_magic_link': bool(item.get('recebe_magic_link')),
                'ordem': item.get('ordem') or 0,
                'area_id': item.get('area_id'),
                'magic_link_token': item.get('magic_link_token'),
                'magic_link_expira': item.get('magic_link_expira'),
                'nome': cliente.get('nome'),
                'cpf': cliente.get('cpf') or cliente.get('cpf_cnpj'),
                'telefone': cliente.get('telefone'),
                'email': cliente.get('email'),
                'formulario_ok': bool(cliente.get('formulario_ok')),
                'formulario_em': cliente.get('formulario_em'),
            })
        if participantes:
            return participantes
    except Exception as exc:
        logger.warning("Falha ao listar participantes do projeto %s: %s", projeto_id, exc)

    if cliente_principal:
        return [{
            'id': None,
            'projeto_id': projeto_id,
            'cliente_id': cliente_principal.get('id'),
            'papel': 'principal',
            'principal': True,
            'recebe_magic_link': True,
            'ordem': 0,
            'area_id': None,
            'magic_link_token': cliente_principal.get('magic_link_token'),
            'magic_link_expira': cliente_principal.get('magic_link_expira'),
            'nome': cliente_principal.get('nome'),
            'cpf': cliente_principal.get('cpf') or cliente_principal.get('cpf_cnpj'),
            'telefone': cliente_principal.get('telefone'),
            'email': cliente_principal.get('email'),
            'formulario_ok': bool(cliente_principal.get('formulario_ok')),
            'formulario_em': cliente_principal.get('formulario_em'),
        }]
    return []


def _normalizar_saida_participante_area(item: dict[str, Any], cliente: dict[str, Any] | None = None) -> dict[str, Any]:
    cliente = cliente or item.get('clientes') or {}
    return {
        'id': item.get('id'),
        'area_id': item.get('area_id'),
        'cliente_id': item.get('cliente_id') or cliente.get('id'),
        'papel': item.get('papel') or 'outro',
        'principal': bool(item.get('principal')),
        'recebe_magic_link': bool(item.get('recebe_magic_link')),
        'ordem': item.get('ordem') or 0,
        'nome': cliente.get('nome') or item.get('nome'),
        'cpf': cliente.get('cpf') or cliente.get('cpf_cnpj') or item.get('cpf'),
        'telefone': cliente.get('telefone') or item.get('telefone'),
        'email': cliente.get('email') or item.get('email'),
        'formulario_ok': bool(cliente.get('formulario_ok')),
        'formulario_em': cliente.get('formulario_em'),
    }


def salvar_participantes_area(sb, area_id: str, participantes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    agora = datetime.now(timezone.utc).isoformat()
    try:
        (
            sb.table('area_clientes')
            .update({'deleted_at': agora})
            .eq('area_id', area_id)
            .is_('deleted_at', 'null')
            .execute()
        )
    except Exception as exc:
        if 'area_clientes' not in str(exc).lower():
            raise
        return []

    if not participantes:
        return []

    registros: list[dict[str, Any]] = []
    for ordem, participante in enumerate(participantes):
        cliente_id = resolver_cliente_participante(sb, participante)
        registros.append({
            'area_id': area_id,
            'cliente_id': cliente_id,
            'papel': _normalizar_papel(participante.get('papel')),
            'principal': bool(participante.get('principal')),
            'recebe_magic_link': bool(participante.get('recebe_magic_link')),
            'ordem': int(participante.get('ordem') or ordem),
            'deleted_at': None,
        })

    resposta = sb.table('area_clientes').insert(registros).execute()
    return [_normalizar_saida_participante_area(item) for item in _dados(resposta)]


def listar_participantes_area(
    sb,
    areas: list[dict[str, Any]],
    *,
    participantes_projeto: list[dict[str, Any]] | None = None,
) -> dict[str, list[dict[str, Any]]]:
    ids_area = [str(item.get('id')) for item in areas if item.get('id') and not str(item.get('id')).endswith(('-ref', '-tec'))]
    mapa: dict[str, list[dict[str, Any]]] = {str(item.get('id')): [] for item in areas if item.get('id')}
    if not ids_area:
        return mapa

    try:
        consulta = (
            sb.table('area_clientes')
            .select('id, area_id, cliente_id, papel, principal, recebe_magic_link, ordem, clientes!inner(id, nome, cpf_cnpj, cpf, telefone, email, formulario_ok, formulario_em, deleted_at)')
            .is_('deleted_at', 'null')
            .order('ordem', desc=False)
        )
        if len(ids_area) == 1:
            consulta = consulta.eq('area_id', ids_area[0])
        else:
            consulta = consulta.in_('area_id', ids_area)
        resposta = consulta.execute()
        for item in _dados(resposta):
            cliente = item.get('clientes') or {}
            if cliente.get('deleted_at'):
                continue
            area_id = str(item.get('area_id'))
            mapa.setdefault(area_id, []).append(_normalizar_saida_participante_area(item, cliente))
    except Exception as exc:
        if 'area_clientes' not in str(exc).lower():
            raise

    if participantes_projeto:
        for participante in participantes_projeto:
            area_id = participante.get('area_id')
            if not area_id:
                continue
            area_id = str(area_id)
            if area_id not in mapa:
                continue
            if any(str(item.get('cliente_id')) == str(participante.get('cliente_id')) for item in mapa[area_id]):
                continue
            mapa[area_id].append({
                'id': participante.get('id'),
                'area_id': area_id,
                'cliente_id': participante.get('cliente_id'),
                'papel': participante.get('papel') or 'outro',
                'principal': bool(participante.get('principal')),
                'recebe_magic_link': bool(participante.get('recebe_magic_link')),
                'ordem': participante.get('ordem') or 0,
                'nome': participante.get('nome'),
                'cpf': participante.get('cpf'),
                'telefone': participante.get('telefone'),
                'email': participante.get('email'),
                'formulario_ok': bool(participante.get('formulario_ok')),
                'formulario_em': participante.get('formulario_em'),
            })

    participantes_por_cliente = {str(item.get('cliente_id')): item for item in (participantes_projeto or []) if item.get('cliente_id')}
    for area in areas:
        area_id = str(area.get('id'))
        if mapa.get(area_id):
            continue
        cliente_id = area.get('cliente_id')
        if cliente_id and str(cliente_id) in participantes_por_cliente:
            participante = participantes_por_cliente[str(cliente_id)]
            mapa[area_id] = [{
                'id': participante.get('id'),
                'area_id': area_id,
                'cliente_id': participante.get('cliente_id'),
                'papel': participante.get('papel') or 'principal',
                'principal': True,
                'recebe_magic_link': bool(participante.get('recebe_magic_link', True)),
                'ordem': participante.get('ordem') or 0,
                'nome': participante.get('nome') or area.get('proprietario_nome'),
                'cpf': participante.get('cpf'),
                'telefone': participante.get('telefone'),
                'email': participante.get('email'),
                'formulario_ok': bool(participante.get('formulario_ok')),
                'formulario_em': participante.get('formulario_em'),
            }]
        elif cliente_id or area.get('proprietario_nome'):
            mapa[area_id] = [{
                'id': None,
                'area_id': area_id,
                'cliente_id': cliente_id,
                'papel': 'principal',
                'principal': True,
                'recebe_magic_link': False,
                'ordem': 0,
                'nome': area.get('proprietario_nome'),
                'cpf': None,
                'telefone': None,
                'email': None,
                'formulario_ok': False,
                'formulario_em': None,
            }]
    return mapa


def salvar_participantes_projeto_em_lote(sb, projeto_id: str, vinculos: list[dict[str, Any]]) -> dict[str, Any]:
    participantes_existentes = listar_participantes_projeto(sb, projeto_id)
    participantes_por_cliente = {
        str(item.get('cliente_id')): {
            'cliente_id': item.get('cliente_id'),
            'nome': item.get('nome'),
            'cpf': item.get('cpf'),
            'telefone': item.get('telefone'),
            'papel': item.get('papel') or 'outro',
            'principal': bool(item.get('principal')),
            'recebe_magic_link': bool(item.get('recebe_magic_link')),
            'ordem': item.get('ordem') or 0,
            'area_id': item.get('area_id'),
        }
        for item in participantes_existentes if item.get('cliente_id')
    }
    proxima_ordem = max([item.get('ordem') or 0 for item in participantes_existentes] + [-1]) + 1
    participantes_area_salvos: dict[str, list[dict[str, Any]]] = {}

    for vinculo in vinculos:
        area_id = str(vinculo.get('area_id') or '')
        participantes_area = normalizar_participantes_entrada(vinculo.get('participantes') or [])
        if not area_id or not participantes_area:
            continue

        area_payload: list[dict[str, Any]] = []
        for participante in participantes_area:
            cliente_id = resolver_cliente_participante(sb, participante)
            area_payload.append({
                **participante,
                'cliente_id': cliente_id,
            })
            if cliente_id in participantes_por_cliente:
                existente = participantes_por_cliente[cliente_id]
                existente.update({
                    'nome': participante.get('nome') or existente.get('nome'),
                    'cpf': participante.get('cpf') or existente.get('cpf'),
                    'telefone': participante.get('telefone') or existente.get('telefone'),
                    'papel': _normalizar_papel(participante.get('papel') or existente.get('papel')),
                    'principal': bool(participante.get('principal')),
                    'recebe_magic_link': bool(participante.get('recebe_magic_link')),
                    'area_id': area_id,
                })
            else:
                participantes_por_cliente[cliente_id] = {
                    'cliente_id': cliente_id,
                    'nome': participante.get('nome'),
                    'cpf': participante.get('cpf'),
                    'telefone': participante.get('telefone'),
                    'papel': _normalizar_papel(participante.get('papel')),
                    'principal': bool(participante.get('principal')),
                    'recebe_magic_link': bool(participante.get('recebe_magic_link')),
                    'ordem': proxima_ordem,
                    'area_id': area_id,
                }
                proxima_ordem += 1

        participantes_area_salvos[area_id] = salvar_participantes_area(sb, area_id, area_payload)

    participantes_projeto_salvos = salvar_participantes_projeto(sb, projeto_id, list(participantes_por_cliente.values()))
    return {
        'participantes_projeto': participantes_projeto_salvos,
        'participantes_area': participantes_area_salvos,
    }


def _obter_participante_base(sb, projeto_id: str, projeto_cliente_id: str | None = None, cliente_id: str | None = None) -> dict[str, Any] | None:
    participantes = listar_participantes_projeto(sb, projeto_id)
    if projeto_cliente_id:
        return next((item for item in participantes if str(item.get('id')) == str(projeto_cliente_id)), None)
    if cliente_id:
        return next((item for item in participantes if str(item.get('cliente_id')) == str(cliente_id)), None)
    return next((item for item in participantes if item.get('principal')), None) or next((item for item in participantes if item.get('recebe_magic_link')), None) or (participantes[0] if participantes else None)


def gerar_magic_link_participante(
    sb,
    projeto_id: str,
    *,
    projeto_cliente_id: str | None = None,
    cliente_id: str | None = None,
    dias: int = 7,
    espelhar_token_cliente_legacy: bool = False,
) -> dict[str, Any] | None:
    participante = _obter_participante_base(sb, projeto_id, projeto_cliente_id=projeto_cliente_id, cliente_id=cliente_id)
    if not participante:
        return None

    token = str(uuid.uuid4())
    expira = datetime.now(timezone.utc) + timedelta(days=dias)
    if participante.get('id'):
        try:
            (
                sb.table('projeto_clientes')
                .update({'magic_link_token': token, 'magic_link_expira': expira.isoformat()})
                .eq('id', participante['id'])
                .execute()
            )
        except Exception:
            pass

    if espelhar_token_cliente_legacy and participante.get('cliente_id'):
        try:
            (
                sb.table('clientes')
                .update({'magic_link_token': token, 'magic_link_expira': expira.isoformat()})
                .eq('id', participante['cliente_id'])
                .execute()
            )
        except Exception:
            pass

    participante['magic_link_token'] = token
    participante['magic_link_expira'] = expira.isoformat()
    return participante


def obter_vinculo_por_token(sb, token: str) -> dict[str, Any] | None:
    try:
        resposta = (
            sb.table('projeto_clientes')
            .select('id, projeto_id, cliente_id, papel, principal, recebe_magic_link, ordem, area_id, magic_link_token, magic_link_expira')
            .eq('magic_link_token', token)
            .is_('deleted_at', 'null')
            .limit(1)
            .execute()
        )
    except Exception as exc:
        if 'projeto_clientes' in str(exc).lower():
            return None
        raise
    dados = _dados(resposta)
    return dados[0] if dados else None


def registrar_evento_magic_link(
    sb,
    *,
    projeto_id: str,
    projeto_cliente_id: str | None,
    cliente_id: str | None,
    area_id: str | None,
    token: str | None,
    tipo_evento: str,
    canal: str = 'whatsapp',
    autor: str | None = None,
    expira_em: str | None = None,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    registro = {
        'projeto_id': projeto_id,
        'projeto_cliente_id': projeto_cliente_id,
        'cliente_id': cliente_id,
        'area_id': area_id,
        'token': token,
        'tipo_evento': _normalizar_tipo_evento(tipo_evento),
        'canal': _normalizar_canal(canal),
        'autor': autor,
        'expira_em': expira_em,
        'payload_json': payload or {},
        'deleted_at': None,
    }
    try:
        resposta = sb.table('eventos_magic_link').insert(registro).execute()
        dados = _dados(resposta)
        return dados[0] if dados else registro
    except Exception as exc:
        if 'eventos_magic_link' in str(exc).lower():
            return registro
        raise


def listar_eventos_magic_link(
    sb,
    projeto_id: str,
    *,
    projeto_cliente_id: str | None = None,
    area_id: str | None = None,
    limite: int = 50,
) -> list[dict[str, Any]]:
    try:
        consulta = (
            sb.table('eventos_magic_link')
            .select('*')
            .eq('projeto_id', projeto_id)
            .is_('deleted_at', 'null')
            .order('criado_em', desc=True)
            .limit(limite)
        )
        if projeto_cliente_id:
            consulta = consulta.eq('projeto_cliente_id', projeto_cliente_id)
        if area_id:
            consulta = consulta.eq('area_id', area_id)
        resposta = consulta.execute()
        return _dados(resposta)
    except Exception as exc:
        if 'eventos_magic_link' in str(exc).lower():
            return []
        raise
