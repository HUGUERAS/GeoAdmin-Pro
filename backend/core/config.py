"""
GeoAdmin Pro - Configurações do Sistema

Centraliza todas as configurações da aplicação via variáveis de ambiente.
"""

import os
from typing import List
from dotenv import load_dotenv

load_dotenv()


class Settings:
    """Configurações da aplicação."""

    # Ambiente e URLs oficiais (Contrato de Arquitetura Vertex)
    APP_ENV: str = os.getenv("APP_ENV", "development")
    ALLOWED_ORIGINS: List[str] = [
        origem.strip() for origem in
        os.getenv("ALLOWED_ORIGINS", ",".join([
            "http://localhost:8081",
            "http://127.0.0.1:8081",
            "http://localhost:8082",
            "http://127.0.0.1:8082",
            "http://localhost:19006",
            "http://127.0.0.1:19006",
            "http://localhost:8000",
            "http://127.0.0.1:8000",
        ])).split(",")
    ]
    PUBLIC_APP_URL: str = os.getenv("PUBLIC_APP_URL", "http://localhost:8000")

    # Supabase - nomes oficiais com compatibilidade para SUPABASE_KEY legado
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY_LEGACY: str = os.getenv("SUPABASE_KEY", "")
    SUPABASE_ANON_KEY: str = os.getenv("SUPABASE_ANON_KEY") or SUPABASE_KEY_LEGACY
    SUPABASE_SERVICE_ROLE_KEY: str = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or SUPABASE_KEY_LEGACY
    SUPABASE_JWT_SECRET: str = os.getenv("SUPABASE_JWT_SECRET", "")

    # Bucket de Storage
    SUPABASE_BUCKET_ARQUIVOS_PROJETO: str = os.getenv(
        "SUPABASE_BUCKET_ARQUIVOS_PROJETO", "arquivos-projeto"
    )

    @property
    def allowed_origins(self) -> List[str]:
        """Retorna lista de origens CORS permitidas."""
        return self.ALLOWED_ORIGINS

    @property
    def cors_origin_regex(self) -> str:
        """Retorna regex para validação de origens CORS."""
        return (
            r"^https?://("
            # Rede local (dev)
            r"localhost|"
            r"127\.0\.0\.1|"
            r"10(?:\.\d{1,3}){3}|"
            r"192\.168(?:\.\d{1,3}){2}|"
            r"172\.(?:1[6-9]|2\d|3[0-1])(?:\.\d{1,3}){2}|"
            # Vercel (preview + production)
            r"[a-z0-9\-]+\.vercel\.app"
            r")(:\d+)?$"
        )

    # PROJ
    PROJ_DATA_DIR: str = os.getenv("PROJ_DATA", "")

    # VERTEXROSEA
    VERTEXROSEA_API_URL: str = os.getenv("VERTEXROSEA_API_URL", "http://localhost:8001")
    VERTEXROSEA_API_KEY: str = os.getenv("VERTEXROSEA_API_KEY", "")

    def validate(self) -> None:
        """Valida configurações críticas."""
        if not self.SUPABASE_URL or not (self.SUPABASE_ANON_KEY or self.SUPABASE_SERVICE_ROLE_KEY):
            raise ValueError(
                "Supabase não configurado. Defina SUPABASE_URL e SUPABASE_ANON_KEY "
                "ou SUPABASE_SERVICE_ROLE_KEY "
                "no arquivo .env ou no ambiente do servidor."
            )

        # Validação de ambiente - impede uso de configuração local em produção
        if self.APP_ENV == "production":
            if not self.SUPABASE_SERVICE_ROLE_KEY:
                raise ValueError(
                    "SUPABASE_SERVICE_ROLE_KEY é obrigatório em produção."
                )


settings = Settings()
