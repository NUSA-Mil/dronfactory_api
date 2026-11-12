from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional
from sqlalchemy import Boolean, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from core.database import Base

if TYPE_CHECKING:
    from models.drone import DroneCategory


class Category(Base):
    __tablename__ = "categories"

    category_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    name: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)
    description: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)

    is_deleted: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, index=True
    )
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    drone_associations: Mapped[List["DroneCategory"]] = relationship(
        "DroneCategory", back_populates="category", passive_deletes=True
    )

    def __repr__(self) -> str:
        return f"<Category(id={self.category_id}, is_deleted={self.is_deleted})>"