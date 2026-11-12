from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import field_validator
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

    @field_validator("ip_address", mode="before")
    @classmethod
    def coerce_ip_to_str(cls, v: Any) -> Optional[str]:
        if v is None:
            return None
        return str(v)