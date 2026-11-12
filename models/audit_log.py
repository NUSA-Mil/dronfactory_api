import enum
from datetime import datetime
from typing import Optional, Any, Dict
from sqlalchemy import BigInteger, String, DateTime, func
from sqlalchemy.dialects.postgresql import JSONB, INET, ENUM
from sqlalchemy.orm import Mapped, mapped_column
from core.database import Base


class AuditCategoryEnum(str, enum.Enum):
    AUTH = "AUTH"
    ORDERS = "ORDERS"
    WAREHOUSE = "WAREHOUSE"
    PRODUCTION = "PRODUCTION"
    SYSTEM = "SYSTEM"


class AuditLog(Base):
    __tablename__ = "audit_log"

    log_id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True
    )
    user_id: Mapped[Optional[int]] = mapped_column(
        nullable=True, index=True
    )
    category: Mapped[AuditCategoryEnum] = mapped_column(
        ENUM(AuditCategoryEnum, name="audit_category_enum", create_type=False),
        nullable=False,
        index=True
    )
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    table_name: Mapped[Optional[str]] = mapped_column(String(60), nullable=True)
    record_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)

    old_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    new_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(INET, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<AuditLog(id={self.log_id}, action='{self.action}', category='{self.category}')>"