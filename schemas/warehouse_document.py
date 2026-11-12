from datetime import datetime
from typing import Optional, List
from pydantic import Field, field_validator
from schemas.common import BaseSchema, sanitize_xss
from models.warehouse import DocTypeEnum, DocStatusEnum


class WarehouseDocMaterialItemCreate(BaseSchema):
    material_id: int
    quantity: float = Field(..., gt=0)


class WarehouseDocDroneItemCreate(BaseSchema):
    variant_id: int
    quantity: int = Field(..., gt=0)


class WarehouseDocumentCreate(BaseSchema):
    warehouse_id: int
    doc_type: DocTypeEnum
    reason: Optional[str] = Field(None, max_length=500)
    order_id: Optional[int] = None
    material_items: Optional[List[WarehouseDocMaterialItemCreate]] = None
    drone_items: Optional[List[WarehouseDocDroneItemCreate]] = None

    @field_validator("reason", mode="before")
    @classmethod
    def validate_xss(cls, v: Optional[str]) -> Optional[str]:
        return sanitize_xss(v)


class WarehouseDocumentStatusUpdate(BaseSchema):
    status: DocStatusEnum


class WarehouseDocumentResponse(BaseSchema):
    document_id: int
    document_number: str
    warehouse_id: int
    created_by: int
    doc_type: DocTypeEnum
    status: DocStatusEnum
    reason: Optional[str] = None
    order_id: Optional[int] = None
    created_at: datetime
    processed_at: Optional[datetime] = None