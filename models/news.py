from datetime import datetime
from typing import Any, Dict, Optional
from sqlalchemy import DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from core.database import Base

class News(Base):
    __tablename__ = "news"

    news_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)
    content: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)

    author_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )