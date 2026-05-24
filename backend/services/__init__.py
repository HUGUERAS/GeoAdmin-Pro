"""
GeoAdmin Pro - Serviços de Negócio

Camada de serviços com regras de negócio e operações complexas.
"""

from .magic_link import MagicLinkService, PAPEIS_VALIDOS, EVENTOS_MAGIC_LINK_VALIDOS, CANAIS_MAGIC_LINK_VALIDOS

__all__ = [
    'MagicLinkService',
    'PAPEIS_VALIDOS',
    'EVENTOS_MAGIC_LINK_VALIDOS',
    'CANAIS_MAGIC_LINK_VALIDOS',
]
