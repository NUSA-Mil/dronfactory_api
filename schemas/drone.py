from datetime import datetime
from typing import Optional, List
from pydantic import Field, field_validator
from schemas.common import BaseSchema, LocalizedText, LocalizedDescription, sanitize_xss
from schemas.material import MaterialResponse


# ===== BOM (СПЕЦИФИКАЦИЯ МАТЕРИАЛОВ) =====
class DroneVariantMaterialCreate(BaseSchema):
    material_id: int
    quantity: float = Field(..., gt=0)
    notes: Optional[str] = Field(None, max_length=255)

    @field_validator("notes", mode="before")
    @classmethod
    def validate_xss(cls, v: Optional[str]) -> Optional[str]:
        return sanitize_xss(v)


class DroneVariantMaterialUpdate(BaseSchema):
    quantity: Optional[float] = Field(None, gt=0)
    notes: Optional[str] = Field(None, max_length=255)

    @field_validator("notes", mode="before")
    @classmethod
    def validate_xss(cls, v: Optional[str]) -> Optional[str]:
        return sanitize_xss(v)


class DroneVariantMaterialResponse(BaseSchema):
    bom_item_id: int
    variant_id: int
    material_id: int
    material: Optional[MaterialResponse] = None
    quantity: float
    notes: Optional[str] = None


# ===== КОМПЛЕКТАЦИИ (VARIANTS) =====
class DroneVariantCreate(BaseSchema):
    sku: str = Field(..., min_length=3, max_length=50)
    variant_name: LocalizedText
    description: Optional[LocalizedDescription] = None
    price: float = Field(..., ge=0)
    is_active: bool = True
    bom_materials: Optional[List[DroneVariantMaterialCreate]] = None

    @field_validator("sku", mode="before")
    @classmethod
    def validate_xss(cls, v: Optional[str]) -> Optional[str]:
        return sanitize_xss(v)


class DroneVariantUpdate(BaseSchema):
    sku: Optional[str] = Field(None, min_length=3, max_length=50)
    variant_name: Optional[LocalizedText] = None
    description: Optional[LocalizedDescription] = None
    price: Optional[float] = Field(None, ge=0)
    is_active: Optional[bool] = None

    @field_validator("sku", mode="before")
    @classmethod
    def validate_xss(cls, v: Optional[str]) -> Optional[str]:
        return sanitize_xss(v)


class DroneVariantResponse(BaseSchema):
    variant_id: int
    drone_id: int
    sku: str
    variant_name: LocalizedText
    description: Optional[LocalizedDescription] = None
    price: float
    is_active: bool
    is_deleted: bool
    bom_materials: List[DroneVariantMaterialResponse] = []
    created_at: datetime


# ===== ДРОНЫ =====
class DroneCreate(BaseSchema):
    name: LocalizedText
    description: Optional[LocalizedDescription] = None
    category_ids: List[int] = Field(..., min_length=1)
    images: Optional[List[str]] = None
    video_url: Optional[str] = None  # Поддержка ссылок и Base64 без лимита длины
    is_active: bool = True

    @field_validator("video_url", mode="before")
    @classmethod
    def validate_xss(cls, v: Optional[str]) -> Optional[str]:
        return sanitize_xss(v)


class DroneUpdate(BaseSchema):
    name: Optional[LocalizedText] = None
    description: Optional[LocalizedDescription] = None
    category_ids: Optional[List[int]] = Field(None, min_length=1)
    images: Optional[List[str]] = None
    video_url: Optional[str] = None  # Поддержка ссылок и Base64 без лимита длины
    is_active: Optional[bool] = None

    @field_validator("video_url", mode="before")
    @classmethod
    def validate_xss(cls, v: Optional[str]) -> Optional[str]:
        return sanitize_xss(v)


class DroneResponse(BaseSchema):
    drone_id: int
    name: LocalizedText
    description: Optional[LocalizedDescription] = None
    images: Optional[List[str]] = None
    video_url: Optional[str] = None
    is_active: bool
    is_deleted: bool
    variants: List[DroneVariantResponse] = []
    created_at: datetime