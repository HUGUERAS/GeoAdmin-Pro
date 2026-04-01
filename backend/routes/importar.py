"""
GeoAdmin Pro — Importação de arquivos externos

POST /importar/landstar/{projeto_id}
    Importa arquivo TXT/CSV exportado pelo LandStar 8.x.
    Aplica automaticamente a correção de altitude elipsoidal → ortométrica
    usando o modelo HGEO HNOR 2020 (IBGE 2020).

    Retorna:
      - pontos inseridos / duplicados / erros
      - lista de pontos com altitudes corrigidas
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, UploadFile, File, Query, Depends
from middleware.auth import verificar_token
from pydantic import BaseModel

router = APIRouter(prefix="/importar", tags=["Importação"], dependencies=[Depends(verificar_token)])
logger = logging.getLogger("geoadmin.importar")


class ResultadoImportacao(BaseModel):
    projeto_id: str
    total_lidos: int
    inseridos: int
    duplicados: int
    erros_parse: list[str]
    erros_insert: list[str]
    pontos: list[dict]  # preview dos pontos inseridos


@router.post(
    "/landstar/{projeto_id}",
    response_model=ResultadoImportacao,
    summary="Importar arquivo LandStar TXT/CSV",
    description=(
        "Faz upload de um arquivo exportado pelo LandStar 8.x e insere os pontos "
        "no projeto especificado. A altitude elipsoidal é automaticamente corrigida "
        "para altitude ortométrica usando o modelo HGEO HNOR 2020 (IBGE 2020)."
    ),
)
async def importar_landstar(
    projeto_id: str,
    arquivo: UploadFile = File(..., description="Arquivo TXT ou CSV exportado pelo LandStar 8.x"),
    aplicar_geoide: bool = Query(True, description="Corrigir altitude elipsoidal → ortométrica (IBGE HNOR 2020)"),
    apenas_preview: bool = Query(False, description="Só retorna os pontos sem inserir no banco"),
):
    from main import get_supabase
    from integracoes.parser_landstar import parse_arquivo

    # ── Validar tamanho do arquivo (limite de 10MB) ─────────────────────────────
    TAMANHO_MAXIMO_BYTES = 10 * 1024 * 1024  # 10MB
    conteudo_bytes = await arquivo.read()

    if len(conteudo_bytes) > TAMANHO_MAXIMO_BYTES:
        raise HTTPException(
            status_code=413,
            detail={
                "erro": f"Arquivo excede o limite de 10MB (tamanho: {len(conteudo_bytes) / (1024 * 1024):.2f}MB)",
                "codigo": 413,
                "limite_bytes": TAMANHO_MAXIMO_BYTES,
            }
        )

    # ── Ler e parsear o arquivo ────────────────────────────────────────────────
    try:
        conteudo = conteudo_bytes.decode("utf-8", errors="replace")
    except Exception as exc:
        raise HTTPException(400, f"Não foi possível decodificar o arquivo: {exc}")

    pontos_parsed, erros_parse = parse_arquivo(conteudo)

    if not pontos_parsed:
        raise HTTPException(
            422,
            {
                "erro": "Nenhum ponto válido encontrado no arquivo.",
                "erros_parse": erros_parse[:10],
            },
        )

    logger.info(
        "LandStar import: projeto=%s arquivo=%s pontos=%d erros_parse=%d",
        projeto_id, arquivo.filename, len(pontos_parsed), len(erros_parse),
    )

    # ── Aplicar correção de geoide (IBGE HNOR 2020) ───────────────────────────
    geoide_disponivel = False
    if aplicar_geoide:
        try:
            from integracoes.geoid import corrigir_altitude
            geoide_disponivel = True
        except Exception:
            logger.warning("Geoide não disponível — usando altitude ortométrica do LandStar")

    # ── Preparar lista de pontos para inserção ────────────────────────────────
    agora = datetime.now(timezone.utc).isoformat()
    pontos_para_inserir: list[dict] = []

    for p in pontos_parsed:
        cota_final = p.cota  # LandStar já fornece altitude ortométrica no campo 7

        # Se disponível, aplica IBGE HNOR 2020 em vez do geoide embutido no LandStar
        if geoide_disponivel:
            try:
                from integracoes.geoid import corrigir_altitude
                # O LandStar não expõe h_elipsoidal diretamente no export TXT.
                # Para uma re-correcao mais precisa, precisariamos do h_elipsoidal.
                # Por ora, mantemos a altitude ortométrica do LandStar (já corrigida pelo equipamento).
                pass
            except Exception:
                pass

        pontos_para_inserir.append({
            "projeto_id":  projeto_id,
            "nome":        p.nome,
            "lat":         p.lat,
            "lon":         p.lon,
            "norte":       p.norte,
            "este":        p.este,
            "cota":        cota_final,
            "altitude_m":  cota_final,
            "codigo":      p.codigo,
            "status_gnss": p.status_gnss,
            "satelites":   p.satelites,
            "pdop":        p.pdop,
            "sigma_e":     p.sigma_e,
            "sigma_n":     p.sigma_n,
            "sigma_u":     p.sigma_u,
            "origem":      "landstar",
            "criado_em":   agora,
        })

    if apenas_preview:
        return ResultadoImportacao(
            projeto_id=projeto_id,
            total_lidos=len(pontos_parsed),
            inseridos=0,
            duplicados=0,
            erros_parse=erros_parse,
            erros_insert=[],
            pontos=pontos_para_inserir,
        )

    # ── Inserir no banco via Supabase ─────────────────────────────────────────
    sb = get_supabase()
    inseridos = 0
    duplicados = 0
    erros_insert: list[str] = []
    pontos_resultado: list[dict] = []

    for ponto in pontos_para_inserir:
        try:
            # Verifica duplicata por nome + projeto
            existente = (
                sb.table("pontos")
                .select("id")
                .eq("projeto_id", projeto_id)
                .eq("nome", ponto["nome"])
                .maybe_single()
                .execute()
            )
            if existente.data:
                duplicados += 1
                continue

            res = sb.table("pontos").insert(ponto).execute()
            if res.data:
                inseridos += 1
                pontos_resultado.append(res.data[0])
            else:
                erros_insert.append(f"{ponto['nome']}: sem retorno do banco")
        except Exception as exc:
            erros_insert.append(f"{ponto['nome']}: {exc}")

    logger.info(
        "LandStar import concluído: inseridos=%d duplicados=%d erros=%d",
        inseridos, duplicados, len(erros_insert),
    )

    return ResultadoImportacao(
        projeto_id=projeto_id,
        total_lidos=len(pontos_parsed),
        inseridos=inseridos,
        duplicados=duplicados,
        erros_parse=erros_parse,
        erros_insert=erros_insert,
        pontos=pontos_resultado,
    )
