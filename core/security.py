import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
import jwt
from passlib.context import CryptContext

from core.config import settings
from core.rate_limit import redis_client
from core.logger import app_logger

pwd_context = CryptContext(schemes=["argon2", "bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(subject: str | int, role_id: int, expires_delta: Optional[timedelta] = None) -> str:
    jti = str(uuid.uuid4())
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode: Dict[str, Any] = {
        "sub": str(subject),
        "role_id": role_id,
        "exp": expire,
        "type": "access",
        "jti": jti
    }
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(subject: str | int, expires_delta: Optional[timedelta] = None) -> tuple[str, str]:
    jti = str(uuid.uuid4())
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    )
    to_encode: Dict[str, Any] = {
        "sub": str(subject),
        "exp": expire,
        "type": "refresh",
        "jti": jti
    }
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt, jti


async def blacklist_token(jti: str, ttl_seconds: int):
    """Добавление jti токена в Redis Blacklist при Logout/блокировке"""
    try:
        await redis_client.setex(f"token_blacklist:{jti}", ttl_seconds, "revoked")
    except Exception as e:
        app_logger.warning(f"Ошибка сохранения jti в Redis Blacklist: {e}")


async def is_token_blacklisted(jti: str) -> bool:
    """Проверка отозван ли токен"""
    try:
        result = await redis_client.get(f"token_blacklist:{jti}")
        return result is not None
    except Exception as e:
        app_logger.warning(f"Ошибка проверки jti in Redis Blacklist: {e}")
        return False


async def decode_token(token: str, expected_type: str = "access") -> Dict[str, Any]:
    """Асинхронная проверка подписи, типа и наличия jti в черном списке Redis"""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if payload.get("type") != expected_type:
            return {}

        jti = payload.get("jti")
        if jti and await is_token_blacklisted(jti):
            return {}

        return payload
    except jwt.PyJWTError:
        return {}