import json
import tempfile
from pathlib import Path
from typing import List, Optional, Union
from pydantic import EmailStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    PROJECT_NAME: str = "dronfactory_api"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "production"

    # Единый URL для облачной PostgreSQL (можно переопределить в Render через DATABASE_URL)
    DATABASE_URL: Optional[str] = (
        "postgresql://neondb_owner:npg_6rNOdWc5YQjZ@ep-polished-thunder-ba24i87b.c-8.eu-central-1.aws.neon.tech/neondb"
    )

    # Fallback-параметры PostgreSQL для локальной разработки
    POSTGRES_SERVER: str = "127.0.0.1"
    POSTGRES_PORT: int = 5433
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "54322"
    POSTGRES_DB: str = "dronfactory_2"

    @property
    def ASYNC_DATABASE_URL(self) -> str:
        if self.DATABASE_URL:
            url = self.DATABASE_URL.strip()
            if url.startswith("postgres://"):
                url = url.replace("postgres://", "postgresql+asyncpg://", 1)
            elif url.startswith("postgresql://"):
                url = url.replace("postgresql://", "postgresql+asyncpg://", 1)

            if "?" in url:
                base, query = url.split("?", 1)
                params = [p for p in query.split("&") if not p.startswith("sslmode=")]
                url = f"{base}?{'&'.join(params)}" if params else base
            return url

        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    # Захардкоженный рабочий Upstash Redis URL (при желании переопределяется через REDIS_URL_ENV)
    REDIS_URL_ENV: str = (
        "rediss://default:gQAAAAAAAwo_AAIgcDIwZGVlZTc2NTYwNzQ0NzliYjg5OWYxYzhhNjMyNjZmNQ@precise-turtle-199231.upstash.io:6379"
    )

    # Fallback-параметры Redis
    REDIS_HOST: str = "127.0.0.1"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: str = ""

    @property
    def REDIS_URL(self) -> str:
        if self.REDIS_URL_ENV and self.REDIS_URL_ENV.strip():
            return self.REDIS_URL_ENV.strip()
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    SECRET_KEY: str = "dronfactory_super_secret_jwt_key_2026_change_me"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # CORS Settings
    BACKEND_CORS_ORIGINS: List[str] = ["*"]

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            v = v.strip()
            if v in ("*", "[*]"):
                return ["*"]
            if v.startswith("[") and v.endswith("]"):
                return json.loads(v)
            return [i.strip() for i in v.split(",") if i.strip()]
        return v

    # SMTP / Email Configuration
    SMTP_HOST: str = "127.0.0.1"
    SMTP_PORT: int = 1025
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    EMAILS_FROM_EMAIL: EmailStr = "noreply@dronfactory.ru"
    EMAILS_FROM_NAME: str = "Dronfactory Support"

    # Временные директории (работают безопасно и на Windows, и в Linux-контейнере Render)
    @property
    def _BASE_STORAGE(self) -> Path:
        if self.ENVIRONMENT == "production":
            return Path(tempfile.gettempdir()) / "dronfactory"
        return BASE_DIR

    @property
    def STORAGE_DIR(self) -> Path:
        return self._BASE_STORAGE / "storage"

    @property
    def AVATARS_DIR(self) -> Path:
        return self.STORAGE_DIR / "avatars"

    @property
    def DRONES_DIR(self) -> Path:
        return self.STORAGE_DIR / "drones"

    @property
    def LOGS_DIR(self) -> Path:
        return self._BASE_STORAGE / "logs"

    @property
    def BACKUPS_DIR(self) -> Path:
        return self._BASE_STORAGE / "private" / "backups"

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()