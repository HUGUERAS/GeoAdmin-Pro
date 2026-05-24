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
    
    # Supabase
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "")
    
    # CORS
    ALLOWED_ORIGINS_DEFAULT: List[str] = [
        "http://localhost:8081",
        "http://127.0.0.1:8081",
        "http://localhost:8082",
        "http://127.0.0.1:8082",
        "http://localhost:19006",
        "http://127.0.0.1:19006",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ]
    
    @property
    def allowed_origins(self) -> List[str]:
        """Retorna lista de origens CORS permitidas."""
        origins = os.getenv("ALLOWED_ORIGINS", ",".join(self.ALLOWED_ORIGINS_DEFAULT))
        return [origem.strip() for origem in origins.split(",")]
    
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
    
    def validate(self) -> None:
        """Valida configurações críticas."""
        if not self.SUPABASE_URL or not self.SUPABASE_KEY:
            raise ValueError(
                "Supabase não configurado. Defina SUPABASE_URL e SUPABASE_KEY "
                "no arquivo .env ou no ambiente do servidor."
            )


settings = Settings()
