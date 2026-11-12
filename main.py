import sys
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from api.v1 import api_router
from core.config import settings
from core.logger import app_logger
from core.rate_limit import redis_client
from core.security_headers import setup_security_middlewares

# Фикс сброса сокетов asyncpg в Windows
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


@asynccontextmanager
async def lifespan(app: FastAPI):
    app_logger.info("Запуск приложения DronFactory API...")
    settings.STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    settings.AVATARS_DIR.mkdir(parents=True, exist_ok=True)
    settings.DRONES_DIR.mkdir(parents=True, exist_ok=True)
    settings.LOGS_DIR.mkdir(parents=True, exist_ok=True)
    settings.BACKUPS_DIR.mkdir(parents=True, exist_ok=True)

    yield

    app_logger.info("Остановка приложения DronFactory API...")
    await redis_client.aclose()


app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan,
)

setup_security_middlewares(app)
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/", tags=["Health Check"])
async def root():
    return {
        "status": "ok",
        "project": settings.PROJECT_NAME,
        "docs": "/docs",
    }