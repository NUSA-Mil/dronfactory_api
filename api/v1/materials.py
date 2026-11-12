from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select, and_, or_, String
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_worker
from core.database import get_db
from core.exceptions import BadRequestException, NotFoundException
from models.material import Material
from models.user import User
from schemas.material import MaterialCreate, MaterialResponse, MaterialUpdate

router = APIRouter(prefix="/materials", tags=["Materials & Inventory"])


@router.get(
    "",
    response_model=List[MaterialResponse],
    summary="Получить список всех материалов",
)
async def get_materials(
    search: Optional[str] = Query(None, description="Поиск по SKU, названию или описанию"),
    include_deleted: bool = Query(False, description="Включать удаленные материалы"),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_worker),
):
    offset = (page - 1) * limit
    stmt = select(Material)

    if not include_deleted:
        stmt = stmt.where(Material.is_deleted == False)

    if search:
        search_pattern = f"%{search.strip()}%"
        stmt = stmt.where(
            or_(
                Material.sku.ilike(search_pattern),
                Material.name.cast(String).ilike(search_pattern),
                Material.description.cast(String).ilike(search_pattern),
            )
        )

    stmt = stmt.order_by(Material.material_id.asc()).offset(offset).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get(
    "/{material_id}",
    response_model=MaterialResponse,
    summary="Получить материал по ID",
)
async def get_material_by_id(
    material_id: int,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_worker),
):
    stmt = select(Material).where(
        and_(Material.material_id == material_id, Material.is_deleted == False)
    )
    result = await db.execute(stmt)
    material = result.scalar_one_or_none()

    if not material:
        raise NotFoundException("Материал не найден")

    return material


@router.post(
    "",
    response_model=MaterialResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Создать новый материал (Manager / Storekeeper / Admin)",
)
async def create_material(
    material_in: MaterialCreate,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_worker),
):
    if material_in.sku:
        sku_stmt = select(Material).where(Material.sku == material_in.sku)
        sku_res = await db.execute(sku_stmt)
        if sku_res.scalar_one_or_none():
            raise BadRequestException("Материал с таким SKU уже существует")

    material = Material(
        sku=material_in.sku,
        name=material_in.name.model_dump(),
        unit=material_in.unit,
        description=material_in.description.model_dump() if material_in.description else None,
    )
    db.add(material)
    await db.commit()
    await db.refresh(material)
    return material


@router.put(
    "/{material_id}",
    response_model=MaterialResponse,
    summary="Обновить параметры материала (Manager / Storekeeper / Admin)",
)
async def update_material(
    material_id: int,
    material_in: MaterialUpdate,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_worker),
):
    stmt = select(Material).where(
        and_(Material.material_id == material_id, Material.is_deleted == False)
    )
    result = await db.execute(stmt)
    material = result.scalar_one_or_none()

    if not material:
        raise NotFoundException("Материал не найден")

    update_data = material_in.model_dump(exclude_unset=True)

    if "sku" in update_data and update_data["sku"] and update_data["sku"] != getattr(material, "sku"):
        sku_stmt = select(Material).where(Material.sku == update_data["sku"])
        sku_res = await db.execute(sku_stmt)
        if sku_res.scalar_one_or_none():
            raise BadRequestException("Артикул SKU уже используется другим материалом")

    for field, value in update_data.items():
        if value is not None:
            setattr(material, field, value)

    await db.commit()
    await db.refresh(material)
    return material


@router.delete(
    "/{material_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Мягкое удаление материала (Manager / Storekeeper / Admin)",
)
async def delete_material(
    material_id: int,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_worker),
):
    stmt = select(Material).where(
        and_(Material.material_id == material_id, Material.is_deleted == False)
    )
    result = await db.execute(stmt)
    material = result.scalar_one_or_none()

    if not material:
        raise NotFoundException("Материал не найден")

    material.is_deleted = True
    material.deleted_at = datetime.now(timezone.utc)
    await db.commit()