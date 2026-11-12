from typing import Optional
from schemas.common import BaseSchema


class RoleResponse(BaseSchema):
    """[ReadOnly]: Доступно только для чтения (GET)"""
    role_id: int
    name: str
    description: Optional[str] = None