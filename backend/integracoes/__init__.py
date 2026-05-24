"""
GeoAdmin Pro - Integrações Externas

Módulo de integração com sistemas externos (Métrica TOPO, SIGEF, etc.)
e funcionalidades auxiliares.
"""

from .areas_projeto import anexar_arquivos_area, salvar_area_projeto
from .arquivos_projeto import (
    buscar_arquivo_por_id,
    listar_arquivos_projeto,
    remover_arquivo_projeto,
    salvar_arquivo_projeto,
)
from .geoid import calcular_geoid
from .gerador_documentos import gerar_documentos_gprf
from .integracao_metrica import ExportadorMetrica
from .parser_landstar import ParserLandstar
from .projeto_clientes import (
    gerar_magic_link_participante,
    listar_eventos_magic_link,
    listar_participantes_projeto,
    obter_vinculo_por_token,
    registrar_evento_magic_link,
    salvar_participantes_projeto,
)
from .referencia_cliente import (
    comparar_com_perimetro_referencia,
    importar_vertices_por_formato,
    salvar_geometria_referencia,
)

__all__ = [
    "anexar_arquivos_area",
    "salvar_area_projeto",
    "buscar_arquivo_por_id",
    "listar_arquivos_projeto",
    "remover_arquivo_projeto",
    "salvar_arquivo_projeto",
    "calcular_geoid",
    "gerar_documentos_gprf",
    "ExportadorMetrica",
    "ParserLandstar",
    "gerar_magic_link_participante",
    "listar_eventos_magic_link",
    "listar_participantes_projeto",
    "obter_vinculo_por_token",
    "registrar_evento_magic_link",
    "salvar_participantes_projeto",
    "comparar_com_perimetro_referencia",
    "importar_vertices_por_formato",
    "salvar_geometria_referencia",
]
