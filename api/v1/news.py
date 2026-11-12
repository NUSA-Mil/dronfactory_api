from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select, or_, String
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_manager
from core.database import get_db
from core.exceptions import NotFoundException
from models.news import News
from models.user import User
from schemas.news import NewsCreate, NewsResponse, NewsUpdate

router = APIRouter(prefix="/news", tags=["News & Articles"])


@router.get(
    "",
    response_model=List[NewsResponse],
    summary="Получить список всех новостей",
)
async def get_news_list(
    search: Optional[str] = Query(None, description="Поиск по заголовку или содержимому"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    offset = (page - 1) * limit
    stmt = select(News)

    if search:
        search_pattern = f"%{search.strip()}%"
        stmt = stmt.where(
            or_(
                News.title.cast(String).ilike(search_pattern),
                News.content.cast(String).ilike(search_pattern),
            )
        )

    stmt = stmt.order_by(News.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get(
    "/{news_id}",
    response_model=NewsResponse,
    summary="Получить новость по ID",
)
async def get_news_by_id(
    news_id: int,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(News).where(News.news_id == news_id)
    result = await db.execute(stmt)
    news_item = result.scalar_one_or_none()

    if not news_item:
        raise NotFoundException("Новость не найдена")

    return news_item


@router.post(
    "",
    response_model=NewsResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Опубликовать новость (Manager / Admin)",
)
async def create_news(
    news_in: NewsCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_manager),
):
    user_id_int = int(getattr(current_user, "user_id"))

    news_item = News(
        title=news_in.title.model_dump(),
        content=news_in.content.model_dump(),
        author_id=user_id_int,
    )
    db.add(news_item)
    await db.commit()
    await db.refresh(news_item)
    return news_item


@router.put(
    "/{news_id}",
    response_model=NewsResponse,
    summary="Обновить новость (Manager / Admin)",
)
async def update_news(
    news_id: int,
    news_in: NewsUpdate,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_manager),
):
    stmt = select(News).where(News.news_id == news_id)
    result = await db.execute(stmt)
    news_item = result.scalar_one_or_none()

    if not news_item:
        raise NotFoundException("Новость не найдена")

    update_data = news_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if value is not None:
            setattr(news_item, field, value)

    await db.commit()
    await db.refresh(news_item)
    return news_item


@router.delete(
    "/{news_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить новость (Manager / Admin)",
)
async def delete_news(
    news_id: int,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_manager),
):
    stmt = select(News).where(News.news_id == news_id)
    result = await db.execute(stmt)
    news_item = result.scalar_one_or_none()

    if not news_item:
        raise NotFoundException("Новость не найдена")

    await db.delete(news_item)
    await db.commit()