import logging
import re
from logging.handlers import RotatingFileHandler
from core.config import settings

settings.LOGS_DIR.mkdir(parents=True, exist_ok=True)

# [Пункт 8]: Фильтрация чувствительных данных (Пароли, Токены)
SENSITIVE_PATTERNS = [
    (r'(password["\']?\s*:\s*["\']?)([^"\'\s&]+)', r'\1***REDACTED***'),
    (r'(bearer\s+)([a-zA-Z0-9\._\-]+)', r'\1***TOKEN_REDACTED***'),
    (r'(secret["\']?\s*:\s*["\']?)([^"\'\s&]+)', r'\1***REDACTED***')
]


class MaskingFormatter(logging.Formatter):
    """Маскирует чувствительные данные перед записью в лог"""
    def format(self, record: logging.LogRecord) -> str:
        original = super().format(record)
        masked = original
        for pattern, replacement in SENSITIVE_PATTERNS:
            masked = re.sub(pattern, replacement, masked, flags=re.IGNORECASE)
        return masked


APP_FORMATTER = MaskingFormatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
AUDIT_FORMATTER = MaskingFormatter("%(asctime)s [%(levelname)s] dronfactory.audit: %(message)s", datefmt="%Y-%m-%d %H:%M:%S")

app_logger = logging.getLogger("dronfactory.app")
app_logger.setLevel(logging.INFO)
app_handler = RotatingFileHandler(settings.LOGS_DIR / "app.log", maxBytes=10*1024*1024, backupCount=5, encoding="utf-8")
app_handler.setFormatter(APP_FORMATTER)
app_logger.addHandler(app_handler)

audit_logger = logging.getLogger("dronfactory.audit")
audit_logger.setLevel(logging.INFO)
audit_handler = RotatingFileHandler(settings.LOGS_DIR / "audit.log", maxBytes=20*1024*1024, backupCount=10, encoding="utf-8")
audit_handler.setFormatter(AUDIT_FORMATTER)
audit_logger.addHandler(audit_handler)


def log_audit(user_id: int | None, ip_address: str, category: str, action: str, details: str):
    user_str = str(user_id) if user_id is not None else "ANONYMOUS"
    message = f"AUDIT | User: {user_str} | IP: {ip_address} | Category: {category} | Action: {action} | Details: {details}"
    audit_logger.info(message)