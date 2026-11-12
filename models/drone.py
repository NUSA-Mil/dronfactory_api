from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional
from sqlalchemy import ARRAY, Boolean, DateTime, ForeignKey, Numeric, String, func, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from core.database import Base

if TYPE_CHECKING:
    from models.category import Category
    from models.material import Material
    from models.warehouse import WarehouseDroneStock


class Drone(Base):
    __tablename__ = "drones"

    drone_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)
    description: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    images: Mapped[Optional[List[str]]] = mapped_column(ARRAY(Text), nullable=True)
    video_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    categories: Mapped[List["DroneCategory"]] = relationship(
        "DroneCategory", back_populates="drone", cascade="all, delete-orphan"
    )
    variants: Mapped[List["DroneVariant"]] = relationship(
        "DroneVariant", back_populates="drone", cascade="all, delete-orphan"
    )


class DroneCategory(Base):
    __tablename__ = "drone_categories"

    drone_category_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    drone_id: Mapped[int] = mapped_column(
        ForeignKey("drones.drone_id", ondelete="CASCADE"), nullable=False, index=True
    )
    category_id: Mapped[int] = mapped_column(
        ForeignKey("categories.category_id", ondelete="CASCADE"), nullable=False, index=True
    )

    drone: Mapped["Drone"] = relationship("Drone", back_populates="categories")
    category: Mapped["Category"] = relationship("Category", back_populates="drone_associations")


class DroneVariant(Base):
    __tablename__ = "drone_variants"

    variant_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    drone_id: Mapped[int] = mapped_column(
        ForeignKey("drones.drone_id", ondelete="CASCADE"), nullable=False, index=True
    )
    sku: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    variant_name: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)
    description: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    price: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    drone: Mapped["Drone"] = relationship("Drone", back_populates="variants")
    bom_materials: Mapped[List["DroneVariantMaterial"]] = relationship(
        "DroneVariantMaterial", back_populates="variant", cascade="all, delete-orphan"
    )
    drone_stock: Mapped[List["WarehouseDroneStock"]] = relationship(
        "WarehouseDroneStock", back_populates="variant", passive_deletes=True
    )


class DroneVariantMaterial(Base):
    __tablename__ = "drone_variant_materials"

    bom_item_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    variant_id: Mapped[int] = mapped_column(
        ForeignKey("drone_variants.variant_id", ondelete="CASCADE"), nullable=False, index=True
    )
    material_id: Mapped[int] = mapped_column(
        ForeignKey("materials.material_id", ondelete="RESTRICT"), nullable=False, index=True
    )
    quantity: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    variant: Mapped["DroneVariant"] = relationship("DroneVariant", back_populates="bom_materials")
    material: Mapped["Material"] = relationship("Material", back_populates="variant_materials")