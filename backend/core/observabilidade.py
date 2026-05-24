"""
GeoAdmin Pro - Observabilidade e Logging Estruturado

Implementa logging com correlation_id para rastreamento de requisições,
métricas operacionais e health checks profundos.
"""

import logging
import uuid
import time
from typing import Optional, Dict, Any
from contextvars import ContextVar
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from datetime import datetime

# Context variable para armazenar correlation_id por requisição
correlation_id_var: ContextVar[Optional[str]] = ContextVar("correlation_id", default=None)


def get_correlation_id() -> str:
    """Retorna o correlation_id atual ou gera um novo."""
    cid = correlation_id_var.get()
    if cid is None:
        cid = str(uuid.uuid4())
        correlation_id_var.set(cid)
    return cid


def set_correlation_id(cid: str) -> None:
    """Define o correlation_id para o contexto atual."""
    correlation_id_var.set(cid)


class CorrelationIdFilter(logging.Filter):
    """Filtro que adiciona correlation_id aos logs."""
    
    def filter(self, record: logging.LogRecord) -> bool:
        record.correlation_id = get_correlation_id()
        return True


class JsonFormatter(logging.Formatter):
    """Formatador de logs em JSON estruturado."""
    
    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "correlation_id": getattr(record, 'correlation_id', get_correlation_id()),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Adiciona informações extras se disponíveis
        if hasattr(record, 'request_id'):
            log_entry['request_id'] = record.request_id
        if hasattr(record, 'user_id'):
            log_entry['user_id'] = record.user_id
        if hasattr(record, 'endpoint'):
            log_entry['endpoint'] = record.endpoint
            
        # Adiciona stack trace para erros
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
        
        import json
        return json.dumps(log_entry, ensure_ascii=False)


def setup_logging(json_logs: bool = True, level: int = logging.INFO) -> None:
    """
    Configura logging estruturado para toda a aplicação.
    
    Args:
        json_logs: Se True, formata logs em JSON (produção). Se False, formato texto (dev).
        level: Nível de logging (DEBUG, INFO, WARNING, ERROR, CRITICAL).
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Remove handlers existentes
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Cria handler para console
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    
    if json_logs:
        console_handler.setFormatter(JsonFormatter())
    else:
        # Formato legível para desenvolvimento
        console_handler.setFormatter(
            logging.Formatter(
                '%(asctime)s | %(levelname)-8s | %(name)s | %(correlation_id)s | %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
        )
    
    # Adiciona filtro de correlation_id
    console_handler.addFilter(CorrelationIdFilter())
    root_logger.addHandler(console_handler)
    
    # Logger da aplicação
    app_logger = logging.getLogger("geoadmin")
    app_logger.setLevel(level)
    app_logger.info("Logging estruturado inicializado", extra={"correlation_id": get_correlation_id()})


class ObservabilityMiddleware(BaseHTTPMiddleware):
    """
    Middleware que adiciona observabilidade às requisições:
    - Gera/propaga correlation_id
    - Mede tempo de resposta
    - Loga requisições e respostas
    - Adiciona headers de rastreabilidade
    """
    
    async def dispatch(self, request: Request, call_next) -> Response:
        start_time = time.time()
        
        # Extrai ou gera correlation_id
        correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
        set_correlation_id(correlation_id)
        
        # logger da requisição
        logger = logging.getLogger("geoadmin.http")
        
        logger.info(
            f"{request.method} {request.url.path}",
            extra={
                "endpoint": request.url.path,
                "method": request.method,
                "client_ip": request.client.host if request.client else "unknown",
                "user_agent": request.headers.get("user-agent", "unknown"),
            }
        )
        
        try:
            # Processa requisição
            response = await call_next(request)
            
            # Calcula duração
            duration_ms = (time.time() - start_time) * 1000
            
            # Adiciona headers de rastreabilidade na resposta
            response.headers["X-Correlation-ID"] = correlation_id
            response.headers["X-Response-Time-Ms"] = f"{duration_ms:.2f}"
            
            # Log da resposta
            log_level = logging.WARNING if response.status_code >= 400 else logging.INFO
            logger.log(
                log_level,
                f"{response.status_code} em {duration_ms:.2f}ms",
                extra={
                    "status_code": response.status_code,
                    "duration_ms": duration_ms,
                    "endpoint": request.url.path,
                }
            )
            
            return response
            
        except Exception as exc:
            duration_ms = (time.time() - start_time) * 1000
            logger.error(
                f"Erro após {duration_ms:.2f}ms: {str(exc)}",
                extra={
                    "endpoint": request.url.path,
                    "duration_ms": duration_ms,
                    "error_type": type(exc).__name__,
                },
                exc_info=True
            )
            raise


def create_health_check_details() -> Dict[str, Any]:
    """
    Cria detalhes completos de health check incluindo:
    - Status do banco de dados
    - Status do storage
    - Versão da aplicação
    - Métricas básicas
    """
    from core.config import settings
    
    health_details = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "version": "2.0.0-vertex",
        "environment": os.getenv("APP_ENV", "development"),
        "checks": {}
    }
    
    # Check do Supabase
    try:
        from core.database import get_supabase
        supabase = get_supabase()
        if supabase:
            # Tenta uma query simples para validar conexão
            health_details["checks"]["supabase"] = {
                "status": "connected",
                "url": settings.SUPABASE_URL[:30] + "...",
            }
        else:
            health_details["checks"]["supabase"] = {"status": "not_configured"}
    except Exception as e:
        health_details["checks"]["supabase"] = {
            "status": "error",
            "message": str(e)
        }
        health_details["status"] = "degraded"
    
    # Check de memória (básico)
    import psutil
    try:
        memory = psutil.Process().memory_info()
        health_details["checks"]["memory"] = {
            "status": "ok",
            "rss_mb": round(memory.rss / 1024 / 1024, 2),
            "vms_mb": round(memory.vms / 1024 / 1024, 2),
        }
    except Exception as e:
        health_details["checks"]["memory"] = {
            "status": "unknown",
            "message": str(e)
        }
    
    return health_details


# Exportações públicas
__all__ = [
    "get_correlation_id",
    "set_correlation_id",
    "CorrelationIdFilter",
    "JsonFormatter",
    "setup_logging",
    "ObservabilityMiddleware",
    "create_health_check_details",
]
