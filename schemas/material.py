from datetime import datetime
from typing import Optional
from pydantic import Field, field_validator
from schemas.common import BaseSchema, LocalizedText, LocalizedDescription, sanitize_xss


class MaterialCreate(BaseSchema):
    sku: Optional[str] = Field(None, max_length=50)
    name: LocalizedText
    unit: str = Field("шт", max_length=20)
    description: Optional[LocalizedDescription] = None

    @field_validator("sku", "unit", mode="before")
    @classmethod
    def validate_xss(cls, v: Optional[str]) -> Optional[str]:
        return sanitize_xss(v)


class MaterialUpdate(BaseSchema):
    sku: Optional[str] = Field(None, max_length=50)
    name: Optional[LocalizedText] = None
    unit: Optional[str] = Field(None, max_length=20)
    description: Optional[LocalizedDescription] = None

    @field_validator("sku", "unit", mode="before")
    @classmethod
    def validate_xss(cls, v: Optional[str]) -> Optional[str]:
        return sanitize_xss(v)


class MaterialResponse(BaseSchema):
    material_id: int
    sku: Optional[str] = None
    name: LocalizedText
    unit: str
    description: Optional[LocalizedDescription] = None
    is_deleted: bool
    deleted_at: Optional[datetime] = None