import redis.asyncio as aioredis
from fastapi import Request, HTTPException, status
from core.config import settings
from core.logger import app_logger

if settings.REDIS_URL.startswith("rediss://"):
    redis_client = aioredis.from_url(
        settings.REDIS_URL,
        decode_responses=True,
        protocol=2,
        ssl_cert_reqs="none",
    )
else:
    redis_client = aioredis.from_url(
        settings.REDIS_URL,
        decode_responses=True,
        protocol=2,
    )


async def check_rate_limit(request: Request, max_requests: int = 5, window_seconds: int = 60):
    """Rate Limiter с отказоустойчивостью при сбое Redis"""
    client_ip = request.client.host if request.client else "127.0.0.1"
    key = f"rate_limit:{request.url.path}:{client_ip}"

    try:
        requests_count = await redis_client.incr(key)
        if requests_count == 1:
            await redis_client.expire(key, window_seconds)

        if requests_count > max_requests:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Слишком много попыток. Попробуйте снова через {window_seconds} секунд."
            )
    except HTTPException as e:
        raise e
    except Exception as e:
        app_logger.warning(f"Rate Limiter: Сбой подключения к Redis ({e}). Пропуск без ограничений.")