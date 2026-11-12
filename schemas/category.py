from datetime import datetime
from typing import Optional
from pydantic import Field
from schemas.common import BaseSchema, LocalizedText, LocalizedDescription


class CategoryCreate(BaseSchema):
    name: LocalizedText
    description: Optional[LocalizedDescription] = None


class CategoryUpdate(BaseSchema):
    name: Optional[LocalizedText] = None
    description: Optional[LocalizedDescription] = None


class CategoryResponse(BaseSchema):
    category_id: int
    name: LocalizedText
    description: Optional[LocalizedDescription] = None
    is_deleted: bool
    deleted_at: Optional[datetime] = None