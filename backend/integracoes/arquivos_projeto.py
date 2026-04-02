from __future__ import annotations

import io
import json
import logging
import mimetypes
import os
import re
import uuid
import zipfile
from pathlib import Path
from typing import Any

logger = logging.getLogger("geoadmin.arquivos_projeto")

ROOT_DIR = Path(__file__).resolve().parents[1]
UPLOADS_DIR = ROOT_DIR / "uploads" / "arquivos_projeto"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

SUPABASE_STORAGE_PREFIX = "supabase://"
LOCAL_STORAGE_PREFIX = "local://"
DEFAULT_BUCKET = "arquivos-projeto"

ORIGENS_VALIDAS = {"topografo", "cliente", "escritorio", "sistema"}
CLASSIFICACOES_VALIDAS = {
    "referencia_visual",
    "esboco_area",
    "perimetro_tecnico",
    "camada_auxiliar",
    "documento_croqui",
    "exportacao",
}


def _dados(resposta: Any) -> list[dict[str, Any]]:
    return getattr(resposta, "data", None) or []


def _normalizar_origem(valor: str | None) -> str:
    origem = (valor or "topografo").strip().lower()
    return origem if origem in ORIGENS_VALIDAS else "topografo"


def _normalizar_classificacao(valor: str | None) -> str:
    classificacao = (valor or "referencia_visual").strip().lower()
    return classificacao if classificacao in CLASSIFICACOES_VALIDAS else "referencia_visual"


def _slug_nome(nome: str) -> str:
    nome_limpo = re.sub(r"[^A-Za-z0-9._-]+", "-", nome or "arquivo")
    return nome_limpo.strip("-") or "arquivo"


def _extensao(nome: str) -> str:
    return Path(nome or "").suffix.lower().lstrip(".") or "bin"


def _bucket_nome() -> str:
    return (os.getenv("SUPABASE_BUCKET_ARQUIVOS_PROJETO") or DEFAULT_BUCKET).strip() or DEFAULT_BUCKET


def _objeto_storage(projeto_id: str, arquivo_id: str, nome_original: str) -> str:
    return f"{projeto_id}/{arquivo_id}-{_slug_nome(nome_original)}"


def _storage_path_supabase(bucket: str, objeto: str) -> str:
    return f"{SUPABASE_STORAGE_PREFIX}{bucket}/{objeto}"


def _storage_path_local(caminho: Path) -> str:
    return f"{LOCAL_STORAGE_PREFIX}{caminho}"


def _parse_storage_path(storage_path: str) -> tuple[str, str] | None:
    bruto = str(storage_path or "")
    if not bruto.startswith(SUPABASE_STORAGE_PREFIX):
        return None
    bucket_e_objeto = bruto[len(SUPABASE_STORAGE_PREFIX):]
    bucket, separador, objeto = bucket_e_objeto.partition("/")
    if not separador or not bucket or not objeto:
        return None
    return bucket, objeto


def _garantir_bucket(sb, bucket: str) -> None:
    try:
        sb.storage.get_bucket(bucket)
        return
    except Exception:
        pass

    try:
        sb.storage.create_bucket(bucket, bucket, {"public": False})
    except Exception as exc:
        texto = str(exc).lower()
        if "already" in texto or "duplicate" in texto or "exists" in texto:
            return
        raise


def _salvar_local(projeto_id: str, arquivo_id: str, nome_original: str, conteudo: bytes) -> str:
    nome_salvo = f"{arquivo_id}-{_slug_nome(nome_original)}"
    pasta = UPLOADS_DIR / projeto_id
    pasta.mkdir(parents=True, exist_ok=True)
    caminho = pasta / nome_salvo
    caminho.write_bytes(conteudo)
    return _storage_path_local(caminho)


def _salvar_supabase(sb, projeto_id: str, arquivo_id: str, nome_original: str, conteudo: bytes, mime_type: str) -> str:
    bucket = _bucket_nome()
    objeto = _objeto_storage(projeto_id, arquivo_id, nome_original)
    _garantir_bucket(sb, bucket)
    sb.storage.from_(bucket).upload(objeto, conteudo, {"content-type": mime_type})
    return _storage_path_supabase(bucket, objeto)


def _ler_bytes_arquivo(sb, item: dict[str, Any]) -> bytes | None:
    storage_path = str(item.get("storage_path") or "")
    parsed = _parse_storage_path(storage_path)
    if parsed:
        bucket, objeto = parsed
        try:
            return sb.storage.from_(bucket).download(objeto)
        except Exception as exc:
            logger.warning("Falha ao baixar arquivo cartografico do Supabase Storage: %s", exc)
            return None

    caminho_str = storage_path[len(LOCAL_STORAGE_PREFIX):] if storage_path.startswith(LOCAL_STORAGE_PREFIX) else storage_path
    caminho = Path(caminho_str)
    if not caminho.exists() or not caminho.is_file():
        return None
    return caminho.read_bytes()


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
    nome_original = nome_arquivo or "arquivo"
    mime = mime_type or mimetypes.guess_type(nome_original)[0] or "application/octet-stream"

    storage_path: str
    provider = "supabase"
    try:
        storage_path = _salvar_supabase(sb, projeto_id, arquivo_id, nome_original, conteudo, mime)
    except Exception as exc:
        provider = "local"
        logger.warning("Falha ao enviar arquivo cartografico ao Supabase Storage; usando fallback local: %s", exc)
        storage_path = _salvar_local(projeto_id, arquivo_id, nome_original, conteudo)

    payload = {
        "id": arquivo_id,
        "projeto_id": projeto_id,
        "area_id": area_id,
        "cliente_id": cliente_id,
        "nome_arquivo": f"{arquivo_id}-{_slug_nome(nome_original)}",
        "nome_original": nome_original,
        "formato": _extensao(nome_original),
        "mime_type": mime,
        "tamanho_bytes": len(conteudo),
        "origem": _normalizar_origem(origem),
        "classificacao": _normalizar_classificacao(classificacao),
        "storage_path": storage_path,
        "hash_arquivo": None,
        "metadados_json": {"storage_provider": provider},
        "deleted_at": None,
    }
    resposta = sb.table("arquivos_projeto").insert(payload).execute()
    dados = _dados(resposta)
    return dados[0] if dados else payload


def listar_arquivos_projeto(sb, projeto_id: str) -> list[dict[str, Any]]:
    try:
        resposta = (
            sb.table("arquivos_projeto")
            .select("*")
            .eq("projeto_id", projeto_id)
            .is_("deleted_at", "null")
            .order("criado_em", desc=True)
            .execute()
        )
    except Exception as exc:
        if "arquivos_projeto" in str(exc).lower():
            return []
        raise
    return _dados(resposta)


def obter_arquivo_projeto(sb, projeto_id: str, arquivo_id: str) -> dict[str, Any] | None:
    try:
        resposta = (
            sb.table("arquivos_projeto")
            .select("*")
            .eq("projeto_id", projeto_id)
            .eq("id", arquivo_id)
            .is_("deleted_at", "null")
            .limit(1)
            .execute()
        )
    except Exception as exc:
        if "arquivos_projeto" in str(exc).lower():
            return None
        raise
    dados = _dados(resposta)
    return dados[0] if dados else None


def exportar_arquivos_projeto_zip(sb, projeto_id: str) -> bytes:
    arquivos = listar_arquivos_projeto(sb, projeto_id)
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        manifesto = []
        for item in arquivos:
            conteudo = _ler_bytes_arquivo(sb, item)
            if conteudo is None:
                continue
            pasta = item.get("classificacao") or "arquivos"
            nome = item.get("nome_original") or item.get("nome_arquivo") or "arquivo"
            zf.writestr(f"{pasta}/{nome}", conteudo)
            manifesto.append({
                "id": item.get("id"),
                "nome_original": nome,
                "origem": item.get("origem"),
                "classificacao": item.get("classificacao"),
                "cliente_id": item.get("cliente_id"),
                "area_id": item.get("area_id"),
                "storage_path": item.get("storage_path"),
            })
        zf.writestr(
            "manifesto_arquivos_projeto.json",
            json.dumps(manifesto, ensure_ascii=False, indent=2).encode("utf-8"),
        )
    return zip_buffer.getvalue()
