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
        ValueError: Se SUPABASE_URL e as chaves Supabase não estiverem configuradas.
    """
    global _supabase_client

    if _supabase_client is not None:
        return _supabase_client

    settings.validate()

    # Backend deve preferir service role quando disponível. SUPABASE_KEY legado
    # continua aceito via Settings para não quebrar deployments existentes.
    supabase_key = settings.SUPABASE_SERVICE_ROLE_KEY or settings.SUPABASE_ANON_KEY
    _supabase_client = create_client(settings.SUPABASE_URL, supabase_key)
    return _supabase_client


def get_supabase_admin() -> Client:
    """
    Retorna um cliente Supabase com chave de serviço (admin).

    Use apenas para operações administrativas que exigem bypass de RLS.

    Returns:
        Client: Instância do cliente Supabase com service_role_key.

    Raises:
        ValueError: Se SUPABASE_SERVICE_ROLE_KEY não estiver configurado.
    """
    settings.validate()

    if not settings.SUPABASE_SERVICE_ROLE_KEY:
        raise ValueError(
            "SUPABASE_SERVICE_ROLE_KEY não configurado. "
            "Necessário para operações administrativas."
        )

    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)


def reset_supabase_client() -> None:
    """Reseta o cliente Supabase (útil para testes)."""
    global _supabase_client
    _supabase_client = None
