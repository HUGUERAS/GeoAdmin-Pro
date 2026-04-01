"""
Rate limiter em memória (sem dependências externas).

Uso:
    limiter = RateLimiter(max_requests=5, janela_segundos=60)

    @router.post("/endpoint")
    def meu_endpoint(request: Request):
        limiter.verificar(request.client.host or "anon")
        ...
"""
from __future__ import annotations

import time
from collections import defaultdict, deque
from fastapi import HTTPException, Request


class RateLimiter:
    def __init__(self, max_requests: int, janela_segundos: int):
        self.max_requests = max_requests
        self.janela = janela_segundos
        self._janelas: dict[str, deque[float]] = defaultdict(deque)

    def verificar(self, chave: str) -> None:
        """Lança HTTP 429 se a chave excedeu o limite na janela."""
        agora = time.monotonic()
        fila = self._janelas[chave]
        corte = agora - self.janela
        while fila and fila[0] < corte:
            fila.popleft()
        if len(fila) >= self.max_requests:
            raise HTTPException(
                status_code=429,
                detail={
                    "erro": "Muitas requisições. Aguarde antes de tentar novamente.",
                    "retry_after_seconds": self.janela,
                },
                headers={"Retry-After": str(self.janela)},
            )
        fila.append(agora)

    def chave_da_request(self, request: Request) -> str:
        """Extrai IP da request como chave de rate limiting."""
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return (request.client.host if request.client else None) or "anon"


# Instâncias compartilhadas
# Magic link: máximo 10 envios por IP por minuto
magic_link_limiter = RateLimiter(max_requests=10, janela_segundos=60)

# Consulta de token (formulário): máximo 30 por IP por minuto
token_limiter = RateLimiter(max_requests=30, janela_segundos=60)
