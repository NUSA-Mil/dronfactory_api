from datetime import datetime
from typing import Optional
from pydantic import Field, field_validator
from schemas.common import BaseSchema, LocalizedText, sanitize_xss


# ===== СКЛАДЫ (WAREHOUSES) =====
class WarehouseCreate(BaseSchema):
    name: LocalizedText
    address: str = Field(..., min_length=5, max_length=255)
    is_assembly_site: bool = False

    @field_validator("address", mode="before")
    @classmethod
    def validate_xss(cls, v: Optional[str]) -> Optional[str]:
        return sanitize_xss(v)


class WarehouseUpdate(BaseSchema):
    name: Optional[LocalizedText] = None
    address: Optional[str] = Field(None, min_length=5, max_length=255)
    is_assembly_site: Optional[bool] = None

    @field_validator("address", mode="before")
    @classmethod
    def validate_xss(cls, v: Optional[str]) -> Optional[str]:
        return sanitize_xss(v)


class WarehouseResponse(BaseSchema):
    warehouse_id: int
    name: LocalizedText
    address: str
    is_assembly_site: bool


# ===== НАПОЛНЕНИЕ СКЛАДА: МАТЕРИАЛЫ =====
class WarehouseMaterialStockCreate(BaseSchema):
    warehouse_id: int
    material_id: int
    quantity: float = Field(0.0, ge=0)
    min_quantity: float = Field(0.0, ge=0)


class WarehouseMaterialStockUpdate(BaseSchema):
    quantity: Optional[float] = Field(None, ge=0)
    min_quantity: Optional[float] = Field(None, ge=0)


class WarehouseMaterialStockResponse(BaseSchema):
    stock_id: int
    warehouse_id: int
    material_id: int
    quantity: float
    min_quantity: float
    updated_at: datetime


# ===== НАПОЛНЕНИЕ СКЛАДА: ДРОНЫ =====
class WarehouseDroneStockCreate(BaseSchema):
    warehouse_id: int
    variant_id: int
    quantity: int = Field(0, ge=0)
    min_quantity: int = Field(0, ge=0)


class WarehouseDroneStockUpdate(BaseSchema):
    quantity: Optional[int] = Field(None, ge=0)
    min_quantity: Optional[int] = Field(None, ge=0)


class WarehouseDroneStockResponse(BaseSchema):
    drone_stock_id: int
    warehouse_id: int
    variant_id: int
    quantity: int
    min_quantity: int
    updated_at: datetime