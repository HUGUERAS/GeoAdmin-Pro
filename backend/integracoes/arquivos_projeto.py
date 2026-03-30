from __future__ import annotations

import io
import logging
import mimetypes
import re
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger('geoadmin.arquivos_projeto')

ROOT_DIR = Path(__file__).resolve().parents[1]
UPLOADS_DIR = ROOT_DIR / 'uploads' / 'arquivos_projeto'
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

ORIGENS_VALIDAS = {'topografo', 'cliente', 'escritorio', 'sistema'}
CLASSIFICACOES_VALIDAS = {
    'referencia_visual',
    'esboco_area',
    'perimetro_tecnico',
    'camada_auxiliar',
    'documento_croqui',
    'exportacao',
}


def _dados(resposta: Any) -> list[dict[str, Any]]:
    return getattr(resposta, 'data', None) or []


def _normalizar_origem(valor: str | None) -> str:
    origem = (valor or 'topografo').strip().lower()
    return origem if origem in ORIGENS_VALIDAS else 'topografo'


def _normalizar_classificacao(valor: str | None) -> str:
    classificacao = (valor or 'referencia_visual').strip().lower()
    return classificacao if classificacao in CLASSIFICACOES_VALIDAS else 'referencia_visual'


def _slug_nome(nome: str) -> str:
    nome_limpo = re.sub(r'[^A-Za-z0-9._-]+', '-', nome or 'arquivo')
    return nome_limpo.strip('-') or 'arquivo'


def _extensao(nome: str) -> str:
    return Path(nome or '').suffix.lower().lstrip('.') or 'bin'


def salvar_arquivo_projeto(
    sb,
    *,
    projeto_id: str,
    nome_arquivo: str,
    conteudo: bytes,
    origem: str,
    classificacao: str,
    cliente_id: str | None = None,
    area_id: str | None = None,
    mime_type: str | None = None,
) -> dict[str, Any]:
    arquivo_id = str(uuid.uuid4())
    nome_original = nome_arquivo or 'arquivo'
    nome_salvo = f"{arquivo_id}-{_slug_nome(nome_original)}"
    pasta = UPLOADS_DIR / projeto_id
    pasta.mkdir(parents=True, exist_ok=True)
    caminho = pasta / nome_salvo
    caminho.write_bytes(conteudo)

    mime = mime_type or mimetypes.guess_type(nome_original)[0] or 'application/octet-stream'
    payload = {
        'id': arquivo_id,
        'projeto_id': projeto_id,
        'area_id': area_id,
        'cliente_id': cliente_id,
        'nome_arquivo': nome_salvo,
        'nome_original': nome_original,
        'formato': _extensao(nome_original),
        'mime_type': mime,
        'tamanho_bytes': len(conteudo),
        'origem': _normalizar_origem(origem),
        'classificacao': _normalizar_classificacao(classificacao),
        'storage_path': str(caminho),
        'metadados_json': {},
        'deleted_at': None,
    }
    resposta = sb.table('arquivos_projeto').insert(payload).execute()
    dados = _dados(resposta)
    return dados[0] if dados else payload


def listar_arquivos_projeto(sb, projeto_id: str) -> list[dict[str, Any]]:
    try:
        resposta = (
            sb.table('arquivos_projeto')
            .select('*')
            .eq('projeto_id', projeto_id)
            .is_('deleted_at', 'null')
            .order('criado_em', desc=True)
            .execute()
        )
    except Exception as exc:
        if 'arquivos_projeto' in str(exc).lower():
            return []
        raise
    return _dados(resposta)


def obter_arquivo_projeto(sb, projeto_id: str, arquivo_id: str) -> dict[str, Any] | None:
    try:
        resposta = (
            sb.table('arquivos_projeto')
            .select('*')
            .eq('projeto_id', projeto_id)
            .eq('id', arquivo_id)
            .is_('deleted_at', 'null')
            .limit(1)
            .execute()
        )
    except Exception as exc:
        if 'arquivos_projeto' in str(exc).lower():
            return None
        raise
    dados = _dados(resposta)
    return dados[0] if dados else None


def exportar_arquivos_projeto_zip(sb, projeto_id: str) -> bytes:
    arquivos = listar_arquivos_projeto(sb, projeto_id)
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        manifesto = []
        for item in arquivos:
            caminho = Path(item.get('storage_path') or '')
            if not caminho.exists() or not caminho.is_file():
                continue
            pasta = item.get('classificacao') or 'arquivos'
            nome = item.get('nome_original') or item.get('nome_arquivo') or caminho.name
            zf.write(caminho, arcname=f"{pasta}/{nome}")
            manifesto.append({
                'id': item.get('id'),
                'nome_original': nome,
                'origem': item.get('origem'),
                'classificacao': item.get('classificacao'),
                'cliente_id': item.get('cliente_id'),
                'area_id': item.get('area_id'),
            })
        zf.writestr('manifesto_arquivos_projeto.json', __import__('json').dumps(manifesto, ensure_ascii=False, indent=2).encode('utf-8'))
    return zip_buffer.getvalue()
