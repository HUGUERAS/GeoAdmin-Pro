"""
GeoAdmin Pro — Integração com FreeCAD
=====================================
backend/integracoes/freecad/__init__.py

Módulo de integração com FreeCAD para geração de peças técnicas
conforme NBR 13.133 (Levantamentos Topográficos) e NBR 14.166 
(Cadastro Técnico Multifinalitário).

Exporta plantas em DWG, DXF, PDF e DWF com:
- Perímetro do imóvel georreferenciado
- Carimbo padrão NBR 10.582 preenchido automaticamente
- Tabela de coordenadas dos vértices
- Seta de norte verdadeiro
- Legenda com confrontantes
- Dados do cliente e técnico via Magic Link
"""

from .generador_plantas import (
    gerar_planta_tecnica,
    gerar_script_freecad,
    executar_script_freecad,
    ConfiguracaoFreeCAD,
    DadosPlantaTecnica,
    _testar_geracao_mock,
)

__all__ = [
    "gerar_planta_tecnica",
    "gerar_script_freecad",
    "executar_script_freecad",
    "ConfiguracaoFreeCAD",
    "DadosPlantaTecnica",
    "_testar_geracao_mock",
]

__version__ = "1.0.0"
