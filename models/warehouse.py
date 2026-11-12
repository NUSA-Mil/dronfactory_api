import enum
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import ENUM, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from core.database import Base

if TYPE_CHECKING:
    from models.drone import DroneVariant
    from models.material import Material


class DocTypeEnum(str, enum.Enum):
    incoming = "incoming"
    write_off = "write_off"
    inventory = "inventory"


class DocStatusEnum(str, enum.Enum):
    draft = "draft"
    completed = "completed"
    cancelled = "cancelled"


class Warehouse(Base):
    __tablename__ = "warehouses"

    warehouse_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)
    address: Mapped[str] = mapped_column(String(255), nullable=False)
    is_assembly_site: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    material_stock: Mapped[List["WarehouseMaterialStock"]] = relationship(
        "WarehouseMaterialStock", back_populates="warehouse", cascade="all, delete-orphan"
    )
    drone_stock: Mapped[List["WarehouseDroneStock"]] = relationship(
        "WarehouseDroneStock", back_populates="warehouse", cascade="all, delete-orphan"
    )


class WarehouseMaterialStock(Base):
    __tablename__ = "warehouse_material_stock"

    stock_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    warehouse_id: Mapped[int] = mapped_column(
        ForeignKey("warehouses.warehouse_id", ondelete="RESTRICT"), nullable=False, index=True
    )
    material_id: Mapped[int] = mapped_column(
        ForeignKey("materials.material_id", ondelete="RESTRICT"), nullable=False, index=True
    )
    quantity: Mapped[float] = mapped_column(Numeric(12, 2), default=0.0, nullable=False)
    min_quantity: Mapped[float] = mapped_column(Numeric(12, 2), default=0.0, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    warehouse: Mapped["Warehouse"] = relationship("Warehouse", back_populates="material_stock")
    material: Mapped["Material"] = relationship("Material", back_populates="warehouse_stock")


class WarehouseDroneStock(Base):
    __tablename__ = "warehouse_drone_stock"

    drone_stock_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    warehouse_id: Mapped[int] = mapped_column(
        ForeignKey("warehouses.warehouse_id", ondelete="RESTRICT"), nullable=False, index=True
    )
    variant_id: Mapped[int] = mapped_column(
        ForeignKey("drone_variants.variant_id", ondelete="RESTRICT"), nullable=False, index=True
    )
    quantity: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    min_quantity: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    warehouse: Mapped["Warehouse"] = relationship("Warehouse", back_populates="drone_stock")
    variant: Mapped["DroneVariant"] = relationship("DroneVariant", back_populates="drone_stock")


class WarehouseDocument(Base):
    __tablename__ = "warehouse_documents"

    document_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    document_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    warehouse_id: Mapped[int] = mapped_column(
        ForeignKey("warehouses.warehouse_id", ondelete="RESTRICT"), nullable=False, index=True
    )
    created_by: Mapped[int] = mapped_column(
        ForeignKey("users.user_id", ondelete="RESTRICT"), nullable=False
    )
    doc_type: Mapped[DocTypeEnum] = mapped_column(
        ENUM(DocTypeEnum, name="doc_type_enum", create_type=False), nullable=False
    )
    status: Mapped[DocStatusEnum] = mapped_column(
        ENUM(DocStatusEnum, name="doc_status_enum", create_type=False), default=DocStatusEnum.draft, nullable=False, index=True
    )
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    order_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    material_items: Mapped[List["WarehouseDocMaterialItem"]] = relationship(
        "WarehouseDocMaterialItem", back_populates="document", cascade="all, delete-orphan"
    )
    drone_items: Mapped[List["WarehouseDocDroneItem"]] = relationship(
        "WarehouseDocDroneItem", back_populates="document", cascade="all, delete-orphan"
    )


class WarehouseDocMaterialItem(Base):
    __tablename__ = "warehouse_doc_material_items"

    item_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    document_id: Mapped[int] = mapped_column(
        ForeignKey("warehouse_documents.document_id", ondelete="CASCADE"), nullable=False
    )
    material_id: Mapped[int] = mapped_column(
        ForeignKey("materials.material_id", ondelete="RESTRICT"), nullable=False
    )
    quantity: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)

    document: Mapped["WarehouseDocument"] = relationship("WarehouseDocument", back_populates="material_items")


class WarehouseDocDroneItem(Base):
    __tablename__ = "warehouse_doc_drone_items"

    item_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    document_id: Mapped[int] = mapped_column(
        ForeignKey("warehouse_documents.document_id", ondelete="CASCADE"), nullable=False
    )
    variant_id: Mapped[int] = mapped_column(
        ForeignKey("drone_variants.variant_id", ondelete="RESTRICT"), nullable=False
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)

    document: Mapped["WarehouseDocument"] = relationship("WarehouseDocument", back_populates="drone_items")