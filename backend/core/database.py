"""
GeoAdmin Pro - Cliente Supabase

Gerencia a conexão com o banco de dados Supabase.
"""

from supabase import create_client, Client
from .config import settings


_supabase_client: Client | None = None


def get_supabase() -> Client:
    """
    Retorna um cliente Supabase configurado via variáveis de ambiente.
    
    Utiliza singleton para reutilizar a conexão.
    
    Returns:
        Client: Instância do cliente Supabase.
        
    Raises:
        ValueError: Se SUPABASE_URL ou SUPABASE_KEY não estiverem configurados.
    """
    global _supabase_client
    
    if _supabase_client is not None:
        return _supabase_client
    
    settings.validate()
    
    _supabase_client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
    return _supabase_client


def reset_supabase_client() -> None:
    """Reseta o cliente Supabase (útil para testes)."""
    global _supabase_client
    _supabase_client = None
