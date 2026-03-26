from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
import winreg
import zipfile


BACKEND_PADRAO = "https://geoadmin-pro-production.up.railway.app"
PASTA_TRABALHO_PADRAO = Path.home() / "GeoAdmin" / "Metrica"
CONFIG_DIR = Path(os.getenv("APPDATA", Path.home() / "AppData" / "Roaming")) / "GeoAdminBridge"
CONFIG_PATH = CONFIG_DIR / "config.json"
EXECUTAVEL_METRICA_PADRAO = Path(r"C:\Program Files (x86)\Métrica\Métrica TOPO\Metrica_TOPO_CAD.exe")


@dataclass
class ResultadoPreparacao:
    projeto_id: str
    pasta_projeto: Path
    manifesto: dict
    aviso_detalhes: str | None


def agora_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def carregar_config() -> dict:
    if not CONFIG_PATH.exists():
        return {}
    try:
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def salvar_config(payload: dict) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def detectar_executavel_metrica() -> Path | None:
    if EXECUTAVEL_METRICA_PADRAO.exists():
        return EXECUTAVEL_METRICA_PADRAO

    chaves = [
        r"MetricaTopo.Projeto\shell\open\command",
        r"MetricaTopo.Desenho.DWG\shell\open\command",
        r"MetricaTopo.Desenho.VDF\shell\open\command",
    ]
    for chave in chaves:
        try:
            with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, chave) as registro:
                valor, _ = winreg.QueryValueEx(registro, "")
        except OSError:
            continue
        caminho = valor.strip().split('"')[1] if '"' in valor else valor.split(" ")[0]
        exe = Path(caminho)
        if exe.exists():
            return exe
    return None


def baixar_pacote(backend_url: str, projeto_id: str) -> tuple[bytes, dict[str, str]]:
    rota = f"{backend_url.rstrip('/')}/projetos/{projeto_id}/metrica/preparar"
    requisicao = urllib.request.Request(rota, method="POST")
    try:
        with urllib.request.urlopen(requisicao, timeout=120) as resposta:
            headers = {k.lower(): v for k, v in resposta.headers.items()}
            return resposta.read(), headers
    except urllib.error.HTTPError as exc:
        detalhe = exc.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"Falha ao baixar pacote ({exc.code}): {detalhe or exc.reason}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Nao foi possivel conectar ao backend: {exc.reason}") from exc


def carregar_pacote_local(caminho_zip: Path) -> tuple[bytes, dict[str, str]]:
    if not caminho_zip.exists():
        raise RuntimeError(f"Pacote local nao encontrado: {caminho_zip}")
    return caminho_zip.read_bytes(), {}


def extrair_pacote(conteudo_zip: bytes, pasta_base: Path) -> tuple[Path, dict]:
    zip_memoria = zipfile.ZipFile(io.BytesIO(conteudo_zip))
    manifesto = json.loads(zip_memoria.read("manifesto.json").decode("utf-8"))
    pasta_sugerida = manifesto.get("pasta_trabalho_sugerida") or manifesto["projeto"].get("id") or "projeto"
    pasta_projeto = pasta_base / pasta_sugerida
    pasta_projeto.mkdir(parents=True, exist_ok=True)
    zip_memoria.extractall(pasta_projeto)
    return pasta_projeto, manifesto


def salvar_status_bridge(
    pasta_projeto: Path,
    projeto_id: str,
    backend_url: str,
    manifesto: dict,
    aviso_detalhes: str | None,
) -> None:
    status = {
        "schema": "geoadmin.bridge.status.v1",
        "atualizado_em": agora_iso(),
        "backend_url": backend_url,
        "projeto_id": projeto_id,
        "projeto_nome": manifesto.get("projeto", {}).get("nome"),
        "pasta_projeto": str(pasta_projeto),
        "aviso_detalhes": aviso_detalhes,
        "arquivos": manifesto.get("arquivos", {}),
    }
    (pasta_projeto / "bridge_status.json").write_text(
        json.dumps(status, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def abrir_pasta(pasta: Path) -> None:
    os.startfile(str(pasta))


def abrir_metrica(executavel: Path, pasta_projeto: Path, manifesto: dict, tentar_dxf: bool) -> None:
    arquivo_alvo = None
    if tentar_dxf:
        nome_dxf = (manifesto.get("arquivos") or {}).get("perimetro_dxf")
        if nome_dxf:
            candidato = pasta_projeto / nome_dxf
            if candidato.exists():
                arquivo_alvo = candidato

    if arquivo_alvo:
        subprocess.Popen([str(executavel), str(arquivo_alvo)])
        return

    subprocess.Popen([str(executavel)])


def preparar_para_metrica(
    backend_url: str,
    projeto_id: str,
    pasta_base: Path,
    abrir_workspace: bool,
    abrir_cad: bool,
    tentar_dxf: bool,
    pacote_local: Path | None = None,
) -> ResultadoPreparacao:
    if pacote_local:
        conteudo_zip, headers = carregar_pacote_local(pacote_local)
    else:
        conteudo_zip, headers = baixar_pacote(backend_url, projeto_id)
    pasta_projeto, manifesto = extrair_pacote(conteudo_zip, pasta_base)
    aviso_detalhes = headers.get("x-aviso-detalhes")

    salvar_status_bridge(pasta_projeto, projeto_id, backend_url, manifesto, aviso_detalhes)

    executavel = detectar_executavel_metrica()
    if abrir_workspace:
        abrir_pasta(pasta_projeto)
    if abrir_cad and executavel:
        abrir_metrica(executavel, pasta_projeto, manifesto, tentar_dxf=tentar_dxf)

    return ResultadoPreparacao(
        projeto_id=projeto_id,
        pasta_projeto=pasta_projeto,
        manifesto=manifesto,
        aviso_detalhes=aviso_detalhes,
    )


def _print_resultado(resultado: ResultadoPreparacao) -> None:
    print(f"Projeto: {resultado.manifesto.get('projeto', {}).get('nome')}")
    print(f"Pasta:   {resultado.pasta_projeto}")
    print(f"Bridge:  {resultado.pasta_projeto / 'bridge_status.json'}")
    if resultado.aviso_detalhes:
        print(f"Avisos:  {resultado.aviso_detalhes}")


def executar_cli() -> int:
    config = carregar_config()
    parser = argparse.ArgumentParser(description="GeoAdmin Bridge para preparar projetos do Métrica TOPO.")
    parser.add_argument("--backend-url", default=config.get("backend_url") or BACKEND_PADRAO)
    parser.add_argument("--projeto-id")
    parser.add_argument("--pacote-local")
    parser.add_argument("--pasta-base", default=config.get("pasta_base") or str(PASTA_TRABALHO_PADRAO))
    parser.add_argument("--nao-abrir-pasta", action="store_true")
    parser.add_argument("--abrir-metrica", action="store_true")
    parser.add_argument("--tentar-dxf", action="store_true")
    parser.add_argument("--salvar-config", action="store_true")

    args = parser.parse_args()
    if not args.projeto_id and not args.pacote_local:
        parser.error("Informe --projeto-id ou --pacote-local.")

    pasta_base = Path(args.pasta_base).expanduser()
    resultado = preparar_para_metrica(
        backend_url=args.backend_url,
        projeto_id=args.projeto_id or "pacote-local",
        pasta_base=pasta_base,
        abrir_workspace=not args.nao_abrir_pasta,
        abrir_cad=args.abrir_metrica,
        tentar_dxf=args.tentar_dxf,
        pacote_local=Path(args.pacote_local).expanduser() if args.pacote_local else None,
    )

    if args.salvar_config:
        salvar_config(
            {
                "backend_url": args.backend_url,
                "pasta_base": str(pasta_base),
            }
        )

    _print_resultado(resultado)
    return 0


if __name__ == "__main__":
    raise SystemExit(executar_cli())
