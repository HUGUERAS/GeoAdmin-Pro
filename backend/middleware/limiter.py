import time
import asyncio
import functools
from collections import defaultdict
from fastapi import Request, HTTPException


class CustomLimiter:
    def __init__(self):
        self.history: dict[str, list[float]] = defaultdict(list)

    def _check_limit(self, request: Request, max_reqs: int, window: int) -> None:
        if not (request and request.client):
            return
        ip = request.client.host
        now = time.time()
        self.history[ip] = [t for t in self.history[ip] if now - t < window]
        if len(self.history[ip]) >= max_reqs:
            raise HTTPException(status_code=429, detail="Too Many Requests")
        self.history[ip].append(now)

    def limit(self, limit_str: str):
        parts = limit_str.split("/")
        max_reqs = int(parts[0])
        window = 60 if "minute" in parts[1] else 1

        def decorator(func):
            if asyncio.iscoroutinefunction(func):
                @functools.wraps(func)
                async def async_wrapper(*args, **kwargs):
                    req = kwargs.get("request") or next(
                        (a for a in args if isinstance(a, Request)), None
                    )
                    self._check_limit(req, max_reqs, window)
                    return await func(*args, **kwargs)
                return async_wrapper
            else:
                @functools.wraps(func)
                def sync_wrapper(*args, **kwargs):
                    req = kwargs.get("request") or next(
                        (a for a in args if isinstance(a, Request)), None
                    )
                    self._check_limit(req, max_reqs, window)
                    return func(*args, **kwargs)
                return sync_wrapper

        return decorator


limiter = CustomLimiter()
