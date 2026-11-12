# ===== schemas/audit_log.py =====
from datetime import datetime
from typing import Optional, Dict, Any
from schemas.common import BaseSchema
from models.audit_log import AuditCategoryEnum


class AuditLogResponse(BaseSchema):
    log_id: int
    user_id: Optional[int] = None
    category: AuditCategoryEnum
    action: str
    table_name: Optional[str] = None
    record_id: Optional[int] = None
    old_data: Optional[Dict[str, Any]] = None
    new_data: Optional[Dict[str, Any]] = None
    ip_address: Optional[str] = None
    created_at: datetime