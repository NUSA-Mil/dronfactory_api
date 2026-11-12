import re
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_admin
from core.config import settings
from core.database import get_db
from models.audit_log import AuditLog, AuditCategoryEnum
from models.user import User
from schemas.audit_log import AuditLogResponse

router = APIRouter(prefix="/audit-logs", tags=["Audit Logs"])

LOG_PATTERN = re.compile(
    r"^(?P<timestamp>\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\s+\[\w+\]\s+[\w.]+:\s+AUDIT\s+\|\s+"
    r"User:\s+(?P<user_id>[^|]+)\|\s+"
    r"IP:\s+(?P<ip>[^|]+)\|\s+"
    r"Category:\s+(?P<category>[^|]+)\|\s+"
    r"Action:\s+(?P<action>[^|]+)\|\s+"
    r"Details:\s+(?P<details>.*)$"
)


def _read_audit_file_logs(
    category: Optional[AuditCategoryEnum] = None,
    user_id: Optional[int] = None,
    action: Optional[str] = None,
) -> List[AuditLogResponse]:
    log_path = settings.LOGS_DIR / "audit.log"
    if not log_path.exists():
        return []

    parsed_logs: List[AuditLogResponse] = []
    with log_path.open("r", encoding="utf-8", errors="replace") as f:
        lines = f.readlines()

    for idx, line in enumerate(reversed(lines), start=1):
        match = LOG_PATTERN.match(line.strip())
        if not match:
            continue

        raw_user = match.group("user_id").strip()
        uid = int(raw_user) if raw_user.isdigit() else None

        raw_cat = match.group("category").strip().upper()
        try:
            cat_enum = AuditCategoryEnum(raw_cat)
        except ValueError:
            cat_enum = AuditCategoryEnum.SYSTEM

        act_str = match.group("action").strip()
        raw_ip = match.group("ip").strip()
        # На случай X-Forwarded-For берем первый IP
        ip_str = raw_ip.split(",")[0].strip() if raw_ip else ""
        details_str = match.group("details").strip()
        dt = datetime.strptime(match.group("timestamp"), "%Y-%m-%d %H:%M:%S")

        if category and cat_enum != category:
            continue
        if user_id is not None and uid != user_id:
            continue
        if action and action.strip().lower() not in act_str.lower():
            continue

        parsed_logs.append(
            AuditLogResponse(
                log_id=idx,
                user_id=uid,
                category=cat_enum,
                action=act_str,
                table_name="audit.log",
                record_id=None,
                old_data=None,
                new_data={"details": details_str} if details_str else None,
                ip_address=None if ip_str in ("None", "-", "") else ip_str,
                created_at=dt,
            )
        )

    return parsed_logs


@router.get(
    "",
    response_model=List[AuditLogResponse],
    summary="Получить журнал аудита из БД и файла audit.log (только Admin)",
)
async def get_audit_logs(
    category: Optional[AuditCategoryEnum] = Query(None),
    user_id: Optional[int] = Query(None),
    action: Optional[str] = Query(None),
    table_name: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_admin),
):
    offset = (page - 1) * limit
    stmt = select(AuditLog)

    if category:
        stmt = stmt.where(AuditLog.category == category)
    if user_id is not None:
        stmt = stmt.where(AuditLog.user_id == user_id)
    if action:
        stmt = stmt.where(AuditLog.action.ilike(f"%{action.strip()}%"))
    if table_name:
        stmt = stmt.where(AuditLog.table_name == table_name)

    stmt = stmt.order_by(AuditLog.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(stmt)
    db_logs = list(result.scalars().all())

    # Объединяем записи из БД и текущего файла audit.log, если не задана конкретная таблица БД
    if not table_name or table_name == "audit.log":
        file_logs = _read_audit_file_logs(
            category=category,
            user_id=user_id,
            action=action,
        )
        if not db_logs:
            return file_logs[offset : offset + limit]

    return db_logs