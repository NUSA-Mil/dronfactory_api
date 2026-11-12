from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select, and_, or_, String
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_manager
from core.database import get_db
from core.exceptions import NotFoundException
from models.category import Category
from models.user import User
from schemas.category import CategoryCreate, CategoryResponse, CategoryUpdate

router = APIRouter(prefix="/categories", tags=["Categories"])


@router.get(
    "",
    response_model=List[CategoryResponse],
    summary="Получить список всех активных категорий",
)
async def get_categories(
    search: Optional[str] = Query(None, description="Поиск по названию или описанию"),
    include_deleted: bool = Query(False, description="Включать удаленные категории (для менеджеров)"),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Category)

    if not include_deleted:
        stmt = stmt.where(Category.is_deleted == False)

    if search:
        search_pattern = f"%{search.strip()}%"
        stmt = stmt.where(
            or_(
                Category.name.cast(String).ilike(search_pattern),
                Category.description.cast(String).ilike(search_pattern),
            )
        )

    stmt = stmt.order_by(Category.category_id.asc())
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get(
    "/{category_id}",
    response_model=CategoryResponse,
    summary="Получить информацию о категории по ID",
)
async def get_category_by_id(
    category_id: int,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Category).where(
        and_(Category.category_id == category_id, Category.is_deleted == False)
    )
    result = await db.execute(stmt)
    category = result.scalar_one_or_none()

    if not category:
        raise NotFoundException("Категория не найдена")

    return category


@router.post(
    "",
    response_model=CategoryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Создать новую категорию (Manager / Admin)",
)
async def create_category(
    category_in: CategoryCreate,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_manager),
):
    category = Category(
        name=category_in.name.model_dump(),
        description=category_in.description.model_dump() if category_in.description else None,
    )
    db.add(category)
    await db.commit()
    await db.refresh(category)
    return category


@router.put(
    "/{category_id}",
    response_model=CategoryResponse,
    summary="Обновить категорию (Manager / Admin)",
)
async def update_category(
    category_id: int,
    category_in: CategoryUpdate,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_manager),
):
    stmt = select(Category).where(
        and_(Category.category_id == category_id, Category.is_deleted == False)
    )
    result = await db.execute(stmt)
    category = result.scalar_one_or_none()

    if not category:
        raise NotFoundException("Категория не найдена")

    update_data = category_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if value is not None:
            setattr(category, field, value)

    await db.commit()
    await db.refresh(category)
    return category


@router.delete(
    "/{category_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Мягкое удаление категории (Manager / Admin)",
)
async def delete_category(
    category_id: int,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_manager),
):
    stmt = select(Category).where(
        and_(Category.category_id == category_id, Category.is_deleted == False)
    )
    result = await db.execute(stmt)
    category = result.scalar_one_or_none()

    if not category:
        raise NotFoundException("Категория не найдена")

    category.is_deleted = True
    category.deleted_at = datetime.now(timezone.utc)
    await db.commit()