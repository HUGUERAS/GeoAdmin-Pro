"""
Módulo do serviço Magic Link.

Exporta o serviço centralizado para gerenciamento de Magic Links.
"""

from .service import MagicLinkService, PAPEIS_VALIDOS, EVENTOS_MAGIC_LINK_VALIDOS, CANAIS_MAGIC_LINK_VALIDOS

__all__ = [
    'MagicLinkService',
    'PAPEIS_VALIDOS',
    'EVENTOS_MAGIC_LINK_VALIDOS',
    'CANAIS_MAGIC_LINK_VALIDOS',
]
