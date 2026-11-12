from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from core.config import settings


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Добавляет HTTP-заголовки безопасности с пропусками для CORS OPTIONS"""

    async def dispatch(self, request: Request, call_next):
        # Пропускаем OPTIONS-запросы без применения жестких CSP-заголовков, чтобы CORS не ломался
        if request.method == "OPTIONS":
            return await call_next(request)

        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"

        # Разрешаем Swagger UI и загрузку локальных ресурсов
        response.headers["Content-Security-Policy"] = (
            "default-src 'self' 'unsafe-inline' 'unsafe-eval' data: blob: http: https:; "
            "img-src 'self' data: blob: http: https:; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net;"
        )
        return response


def setup_security_middlewares(app: FastAPI):
    """Инициализация CORS и Security Headers"""
    origins = settings.BACKEND_CORS_ORIGINS
    allow_all = "*" in origins

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if allow_all else origins,
        allow_credentials=not allow_all,  # True только если НЕ wildcard '*'
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.add_middleware(SecurityHeadersMiddleware)