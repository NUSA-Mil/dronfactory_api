from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_admin
from core.database import get_db
from models.role import Role
from models.user import User
from schemas.role import RoleResponse

router = APIRouter(prefix="/roles", tags=["Roles & Security"])


@router.get(
    "",
    response_model=List[RoleResponse],
    summary="Получить список системных ролей (только Admin)",
)
async def get_roles(
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_admin),
):
    stmt = select(Role).order_by(Role.role_id.asc())
    result = await db.execute(stmt)
    return result.scalars().all()