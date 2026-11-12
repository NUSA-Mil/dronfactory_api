from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from api.deps import get_current_admin, get_current_user
from core.database import get_db
from core.exceptions import BadRequestException, NotFoundException
from core.permissions import check_owner_or_worker
from core.security import get_password_hash
from models.user import User
from schemas.user import UserCreate, UserResponse, UserUpdate

router = APIRouter(prefix="/users", tags=["Users"])


@router.get(
    "",
    response_model=List[UserResponse],
    summary="Получить список пользователей (только Admin)",
)
async def get_users(
    search: Optional[str] = Query(None, description="Поиск по Email, имени или телефону"),
    role_id: Optional[int] = Query(None, description="Фильтр по роли"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_admin),
):
    offset = (page - 1) * limit
    stmt = select(User).options(selectinload(User.role))

    if role_id:
        stmt = stmt.where(User.role_id == role_id)

    if search:
        search_pattern = f"%{search.strip()}%"
        stmt = stmt.where(
            or_(
                User.email.ilike(search_pattern),
                User.full_name.ilike(search_pattern),
                User.phone_number.ilike(search_pattern),
            )
        )

    stmt = stmt.order_by(User.user_id.asc()).offset(offset).limit(limit)
    res = await db.execute(stmt)
    return res.scalars().all()


@router.get(
    "/{user_id}",
    response_model=UserResponse,
    summary="Получить пользователя по ID",
)
async def get_user_by_id(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Доступен себе или сотрудникам/админам
    check_owner_or_worker(
        resource_user_id=user_id,
        current_user_id=int(getattr(current_user, "user_id")),
        current_user_role_id=int(getattr(current_user, "role_id")),
    )

    stmt = select(User).options(selectinload(User.role)).where(User.user_id == user_id)
    res = await db.execute(stmt)
    user = res.scalar_one_or_none()

    if not user:
        raise NotFoundException("Пользователь не найден")

    return user


@router.post(
    "",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Создать нового пользователя (только Admin)",
)
async def create_user(
    user_in: UserCreate,
    role_id: int = Query(1, description="ID роли пользователя"),
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_admin),
):
    email_str = str(user_in.email)
    existing_stmt = select(User).where(User.email == email_str)
    existing_res = await db.execute(existing_stmt)
    if existing_res.scalar_one_or_none():
        raise BadRequestException("Пользователь с таким email уже существует")

    db_user = User(
        email=email_str,
        password_hash=get_password_hash(user_in.password),
        phone_number=user_in.phone_number,
        full_name=user_in.full_name,
        role_id=target_role,
        is_active=True,
        is_verified=True,
        language="system",
        theme_mode="system",
    )
    db.add(db_user)
    await db.commit()

    user_id_int = int(getattr(db_user, "user_id"))

    stmt = select(User).options(selectinload(User.role)).where(User.user_id == user_id_int)
    res = await db.execute(stmt)
    return res.scalar_one()


@router.put(
    "/{user_id}",
    response_model=UserResponse,
    summary="Редактировать профиль пользователя (Свой ID или Admin)",
)
async def update_user(
    user_id: int,
    user_in: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    current_user_id = int(getattr(current_user, "user_id"))
    current_role_id = int(getattr(current_user, "role_id"))

    # Обычный пользователь (ID=7) может менять ТОЛЬКО свои данные (user_id=7)
    check_owner_or_worker(
        resource_user_id=user_id,
        current_user_id=current_user_id,
        current_user_role_id=current_role_id,
    )

    stmt = select(User).options(selectinload(User.role)).where(User.user_id == user_id)
    res = await db.execute(stmt)
    user = res.scalar_one_or_none()

    if not user:
        raise NotFoundException("Пользователь не найден")

    update_data = user_in.model_dump(exclude_unset=True)

    if "email" in update_data and update_data["email"] != getattr(user, "email"):
        email_stmt = select(User).where(User.email == update_data["email"])
        email_res = await db.execute(email_stmt)
        if email_res.scalar_one_or_none():
            raise BadRequestException("Email уже используется другим пользователем")

    for field, value in update_data.items():
        if value is not None:
            setattr(user, field, value)

    await db.commit()
    await db.refresh(user)
    return user


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить пользователя (только Admin)",
)
async def delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    current_admin_id = int(getattr(current_user, "user_id"))
    if user_id == current_admin_id:
        raise BadRequestException("Нельзя удалить собственного администратора")

    stmt = select(User).where(User.user_id == user_id)
    res = await db.execute(stmt)
    user = res.scalar_one_or_none()

    if not user:
        raise NotFoundException("Пользователь не найден")

    await db.delete(user)
    await db.commit()