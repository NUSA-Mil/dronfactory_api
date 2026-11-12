from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional
from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from core.database import Base


if TYPE_CHECKING:
    from models.warehouse import WarehouseMaterialStock
    from models.drone import DroneVariantMaterial

class Material(Base):
    __tablename__ = "materials"

    material_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    sku: Mapped[Optional[str]] = mapped_column(String(50), unique=True, nullable=True, index=True)

    name: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)
    unit: Mapped[str] = mapped_column(String(20), default="шт", nullable=False)
    description: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)

    # Soft Delete
    is_deleted: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, index=True
    )
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    warehouse_stock: Mapped[List["WarehouseMaterialStock"]] = relationship(
        "WarehouseMaterialStock", back_populates="material", passive_deletes=True
    )
    variant_materials: Mapped[List["DroneVariantMaterial"]] = relationship(
        "DroneVariantMaterial", back_populates="material", passive_deletes=True
    )

    def __repr__(self) -> str:
        return f"<Material(id={self.material_id}, sku='{self.sku}')>"