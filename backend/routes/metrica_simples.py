"""
GeoAdmin Pro — Endpoint Métrica TXT (sem Supabase)

POST /metrica/txt
  Body: JSON com projeto_nome, numero_job, zona_utm (opcional), pontos[]
  Response: arquivo .txt pronto para importar no Métrica TOPO

Sem dependências externas. Quando o Supabase estiver estável, um GET
/projetos/{id}/metrica/txt busca os pontos no banco e chama esta mesma lógica.
"""

from fastapi import APIRouter, Depends
from middleware.auth import verificar_token
from fastapi.responses import Response, PlainTextResponse
from pydantic import BaseModel

router = APIRouter(tags=["Métrica"], dependencies=[Depends(verificar_token)])


class PontoPayload(BaseModel):
    nome: str
    norte: float
    este: float
    cota: float = 0.0
    codigo: str = "TP"
    descricao: str = ""


class MetricaTxtPayload(BaseModel):
    projeto_nome: str
    numero_job: str
    zona_utm: str = "23S"
    pontos: list[PontoPayload]


def gerar_txt(projeto_nome: str, numero_job: str, zona_utm: str, pontos: list[PontoPayload]) -> str:
    """Gera o conteúdo TXT no formato do Métrica TOPO."""
    linhas = [
        f"* Projeto:    {projeto_nome}",
        f"* Job:        {numero_job}",
        f"* Cliente:    ",
        f"* Zona UTM:   {zona_utm}",
        f"* Total pts:  {len(pontos)}",
        "* Gerado por: GeoAdmin Pro",
        "*",
        "* NOME\t\tNORTE\t\t\tESTE\t\t\tCOTA\t\tCÓDIGO",
        "*" + "-" * 78,
    ]
    for p in pontos:
        linhas.append(
            f"{p.nome:<12}\t"
            f"{p.norte:>18.6f}\t"
            f"{p.este:>18.6f}\t"
            f"{p.cota:>12.4f}\t"
            f"{p.codigo}"
        )
    return "\n".join(linhas)


@router.post(
    "/metrica/txt",
    summary="Gerar TXT para Métrica TOPO (sem Supabase)",
    response_class=Response,
)
def metrica_txt(payload: MetricaTxtPayload):
    """
    Recebe projeto + lista de pontos em JSON e devolve o arquivo .txt
    no formato que o Métrica TOPO importa (Nome, Norte, Este, Cota, Código).
    """
    if not payload.pontos:
        return PlainTextResponse(
            "* Erro: informe ao menos um ponto no campo 'pontos'.",
            status_code=400,
        )

    conteudo = gerar_txt(
        payload.projeto_nome,
        payload.numero_job,
        payload.zona_utm,
        payload.pontos,
    )
    nome_arquivo = f"GeoAdmin_{payload.numero_job}_{payload.projeto_nome[:20].replace(' ', '_')}.txt"
    return Response(
        content=conteudo.encode("utf-8"),
        media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{nome_arquivo}"'},
    )
