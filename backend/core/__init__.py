"""
GeoAdmin Pro - Core Module

Módulo central com configurações, utilitários e dependências compartilhadas.
"""

from .config import settings
from .database import get_supabase

__all__ = ["settings", "get_supabase"]
