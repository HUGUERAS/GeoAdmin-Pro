from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import urllib.error
import urllib.request
import winreg
import zipfile


BACKEND_PADRAO = "https://geoadmin-pro-production.up.railway.app"
PASTA_TRABALHO_PADRAO = Path.home() / "GeoAdmin" / "Metrica"
CONFIG_DIR = Path(os.getenv("APPDATA", Path.home() / "AppData" / "Roaming")) / "GeoAdminBridge"
CONFIG_PATH = CONFIG_DIR / "config.json"
EXECUTAVEL_METRICA_PADRAO = Path(r"C:\Program Files (x86)\Métrica\Métrica TOPO\Metrica_TOPO_CAD.exe")
SUBPASTAS_WORKSPACE = {
    "entrada": "01_entrada",
    "cad": "02_cad",
    "documentos": "03_documentos",
    "exportacoes": "04_exportacoes",
    "bridge": "99_bridge",
}


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


def _garantir_workspace(pasta_projeto: Path) -> dict[str, Path]:
    pastas = {"raiz": pasta_projeto}
    for chave, nome in SUBPASTAS_WORKSPACE.items():
        destino = pasta_projeto / nome
        destino.mkdir(parents=True, exist_ok=True)
        pastas[chave] = destino
    (pastas["bridge"] / "logs").mkdir(parents=True, exist_ok=True)
    return pastas


def _registrar_log(pasta_projeto: Path, mensagem: str) -> None:
    logs_dir = pasta_projeto / SUBPASTAS_WORKSPACE["bridge"] / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    linha = f"[{agora_iso()}] {mensagem}\n"
    (logs_dir / "bridge.log").write_text(
        ((logs_dir / "bridge.log").read_text(encoding="utf-8") if (logs_dir / "bridge.log").exists() else "") + linha,
        encoding="utf-8",
    )


def _mover_se_existir(origem: Path, destino: Path) -> None:
    if not origem.exists():
        return
    destino.parent.mkdir(parents=True, exist_ok=True)
    if destino.exists():
        if destino.is_dir():
            shutil.rmtree(destino)
        else:
            destino.unlink()
    shutil.move(str(origem), str(destino))


def _criar_launcher_bat(pasta_projeto: Path, executavel: Path | None, manifesto: dict) -> Path:
    nome_dxf = (manifesto.get("arquivos") or {}).get("perimetro_dxf") or ""
    caminho_dxf = pasta_projeto / SUBPASTAS_WORKSPACE["cad"] / nome_dxf if nome_dxf else None
    linhas = [
        "@echo off",
        "setlocal",
        f"set METRICA_EXE={executavel}" if executavel else "set METRICA_EXE=",
        f"set DXF_ALVO={caminho_dxf}" if caminho_dxf else "set DXF_ALVO=",
        "if not \"%METRICA_EXE%\"==\"\" if exist \"%METRICA_EXE%\" (",
        "  if not \"%DXF_ALVO%\"==\"\" if exist \"%DXF_ALVO%\" (",
        "    start \"\" \"%METRICA_EXE%\" \"%DXF_ALVO%\"",
        "    goto :eof",
        "  )",
        "  start \"\" \"%METRICA_EXE%\"",
        "  goto :eof",
        ")",
        "echo Executavel do Metrica nao encontrado. Abra manualmente a pasta 02_cad.",
        f"start \"\" \"{pasta_projeto / SUBPASTAS_WORKSPACE['cad']}\"",
    ]
    launcher = pasta_projeto / "ABRIR_NO_METRICA.bat"
    launcher.write_text("\r\n".join(linhas) + "\r\n", encoding="utf-8")
    return launcher


def _organizar_workspace_extraido(pasta_temp: Path, pasta_projeto: Path, manifesto: dict, conteudo_zip: bytes) -> dict[str, Path]:
    pastas = _garantir_workspace(pasta_projeto)
    arquivos = manifesto.get("arquivos") or {}

    entrada = {
        arquivos.get("pontos_txt"),
        arquivos.get("pontos_csv"),
    }
    cad = {
        arquivos.get("perimetro_dxf"),
        arquivos.get("perimetro_kml"),
        Path(arquivos.get("perimetro_geojson") or "").name,
        Path(arquivos.get("referencia_cliente_geojson") or "").name,
    }

    raiz_readme = pasta_temp / (arquivos.get("readme") or "COMO_USAR_NO_METRICA.txt")
    if raiz_readme.exists():
        _mover_se_existir(raiz_readme, pasta_projeto / raiz_readme.name)

    raiz_manifesto = pasta_temp / (arquivos.get("manifesto") or "manifesto.json")
    if raiz_manifesto.exists():
        _mover_se_existir(raiz_manifesto, pastas["bridge"] / "manifesto.json")

    dados_dir = pasta_temp / "dados"
    if dados_dir.exists():
        for arquivo in dados_dir.iterdir():
            nome = arquivo.name
            if nome in {"perimetro_ativo.geojson", "referencia_cliente.geojson"}:
                _mover_se_existir(arquivo, pastas["cad"] / nome)
            elif nome == "documentos.json":
                _mover_se_existir(arquivo, pastas["documentos"] / nome)
            else:
                _mover_se_existir(arquivo, pastas["bridge"] / nome)
        shutil.rmtree(dados_dir, ignore_errors=True)

    for item in list(pasta_temp.iterdir()):
        if item.is_dir():
            continue
        if item.name in entrada:
            _mover_se_existir(item, pastas["entrada"] / item.name)
        elif item.name in cad:
            _mover_se_existir(item, pastas["cad"] / item.name)
        elif item.name.lower().endswith(".zip"):
            _mover_se_existir(item, pastas["exportacoes"] / item.name)
        elif item.name not in {"COMO_USAR_NO_METRICA.txt", "manifesto.json"}:
            _mover_se_existir(item, pastas["exportacoes"] / item.name)

    pacote_path = pastas["exportacoes"] / "pacote_geoadmin_metrica.zip"
    pacote_path.write_bytes(conteudo_zip)
    return pastas


def extrair_pacote(conteudo_zip: bytes, pasta_base: Path) -> tuple[Path, dict]:
    zip_memoria = zipfile.ZipFile(io.BytesIO(conteudo_zip))
    manifesto = json.loads(zip_memoria.read("manifesto.json").decode("utf-8"))
    pasta_sugerida = manifesto.get("pasta_trabalho_sugerida") or manifesto["projeto"].get("id") or "projeto"
    pasta_projeto = pasta_base / pasta_sugerida
    pasta_projeto.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as temp_dir:
        pasta_temp = Path(temp_dir)
        zip_memoria.extractall(pasta_temp)
        _organizar_workspace_extraido(pasta_temp, pasta_projeto, manifesto, conteudo_zip)
    return pasta_projeto, manifesto


def salvar_status_bridge(
    pasta_projeto: Path,
    projeto_id: str,
    backend_url: str,
    manifesto: dict,
    aviso_detalhes: str | None,
) -> None:
    executavel = detectar_executavel_metrica()
    launcher = _criar_launcher_bat(pasta_projeto, executavel, manifesto)
    status = {
        "schema": "geoadmin.bridge.status.v1",
        "atualizado_em": agora_iso(),
        "backend_url": backend_url,
        "projeto_id": projeto_id,
        "projeto_nome": manifesto.get("projeto", {}).get("nome"),
        "pasta_projeto": str(pasta_projeto),
        "launcher_bat": str(launcher),
        "executavel_metrica": str(executavel) if executavel else None,
        "aviso_detalhes": aviso_detalhes,
        "arquivos": manifesto.get("arquivos", {}),
        "workspace": {chave: str(pasta_projeto / nome) for chave, nome in SUBPASTAS_WORKSPACE.items()},
    }
    status_path = pasta_projeto / SUBPASTAS_WORKSPACE["bridge"] / "bridge_status.json"
    status_path.write_text(
        json.dumps(status, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    _registrar_log(pasta_projeto, f"Workspace preparado para o projeto {projeto_id}.")
    if executavel:
        _registrar_log(pasta_projeto, f"Executavel do Metrica detectado em {executavel}.")
    if aviso_detalhes:
        _registrar_log(pasta_projeto, f"Avisos do pacote: {aviso_detalhes}")


def abrir_pasta(pasta: Path) -> None:
    os.startfile(str(pasta))


def abrir_metrica(executavel: Path, pasta_projeto: Path, manifesto: dict, tentar_dxf: bool) -> None:
    arquivo_alvo = None
    if tentar_dxf:
        nome_dxf = (manifesto.get("arquivos") or {}).get("perimetro_dxf")
        if nome_dxf:
            candidato = pasta_projeto / SUBPASTAS_WORKSPACE["cad"] / nome_dxf
            if candidato.exists():
                arquivo_alvo = candidato

    if arquivo_alvo:
        subprocess.Popen([str(executavel), str(arquivo_alvo)])
        _registrar_log(pasta_projeto, f"Metrica aberto com DXF {arquivo_alvo.name}.")
        return

    subprocess.Popen([str(executavel)])
    _registrar_log(pasta_projeto, "Metrica aberto sem arquivo alvo.")


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
        _registrar_log(pasta_projeto, "Pasta do workspace aberta no Windows.")
    if abrir_cad and executavel:
        abrir_metrica(executavel, pasta_projeto, manifesto, tentar_dxf=tentar_dxf)
    elif abrir_cad and not executavel:
        _registrar_log(pasta_projeto, "Nao foi possivel abrir o Metrica: executavel nao encontrado.")

    return ResultadoPreparacao(
        projeto_id=projeto_id,
        pasta_projeto=pasta_projeto,
        manifesto=manifesto,
        aviso_detalhes=aviso_detalhes,
    )


def _print_resultado(resultado: ResultadoPreparacao) -> None:
    print(f"Projeto: {resultado.manifesto.get('projeto', {}).get('nome')}")
    print(f"Pasta:   {resultado.pasta_projeto}")
    print(f"Entrada: {resultado.pasta_projeto / SUBPASTAS_WORKSPACE['entrada']}")
    print(f"CAD:     {resultado.pasta_projeto / SUBPASTAS_WORKSPACE['cad']}")
    print(f"Bridge:  {resultado.pasta_projeto / SUBPASTAS_WORKSPACE['bridge'] / 'bridge_status.json'}")
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
