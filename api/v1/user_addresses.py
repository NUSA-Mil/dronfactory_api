from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_user
from core.database import get_db
from core.exceptions import NotFoundException
from models.user import User, UserAddress
from schemas.user import UserAddressCreate, UserAddressResponse

router = APIRouter(prefix="/user-addresses", tags=["User Addresses"])


@router.get(
    "",
    response_model=List[UserAddressResponse],
    summary="Получить список адресов текущего пользователя",
)
async def get_my_addresses(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    user_id_int = int(getattr(current_user, "user_id"))
    stmt = select(UserAddress).where(UserAddress.user_id == user_id_int).order_by(UserAddress.address_id.asc())
    res = await db.execute(stmt)
    return res.scalars().all()


@router.post(
    "",
    response_model=UserAddressResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Добавить новый адрес доставки",
)
async def create_address(
    addr_in: UserAddressCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    user_id_int = int(getattr(current_user, "user_id"))

    if addr_in.is_default:
        existing_stmt = select(UserAddress).where(UserAddress.user_id == user_id_int)
        existing_res = await db.execute(existing_stmt)
        for old_addr in existing_res.scalars().all():
            old_addr.is_default = False

    addr = UserAddress(
        user_id=user_id_int,
        title=addr_in.title,
        city=addr_in.city,
        address_line=addr_in.address_line,
        comment=addr_in.comment,
        is_default=addr_in.is_default,
    )
    db.add(addr)
    await db.commit()
    await db.refresh(addr)
    return addr


@router.delete(
    "/{address_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить адрес доставки",
)
async def delete_address(
    address_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    user_id_int = int(getattr(current_user, "user_id"))
    stmt = select(UserAddress).where(
        and_(UserAddress.address_id == address_id, UserAddress.user_id == user_id_int)
    )
    res = await db.execute(stmt)
    addr = res.scalar_one_or_none()

    if not addr:
        raise NotFoundException("Адрес не найден")

    await db.delete(addr)
    await db.commit()