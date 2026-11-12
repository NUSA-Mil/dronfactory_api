from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select, and_, or_, String, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from api.deps import get_current_manager
from core.database import get_db
from core.exceptions import BadRequestException, NotFoundException
from models.drone import Drone, DroneCategory, DroneVariant, DroneVariantMaterial
from models.user import User
from schemas.drone import (
    DroneCreate,
    DroneResponse,
    DroneUpdate,
    DroneVariantCreate,
    DroneVariantMaterialCreate,
    DroneVariantMaterialResponse,
    DroneVariantResponse,
    DroneVariantUpdate,
)

router = APIRouter(prefix="/drones", tags=["Drones & Catalog"])


# ===== КАТАЛОГ ДРОНОВ (DRONES) =====

@router.get(
    "",
    response_model=List[DroneResponse],
    summary="Get drone list from catalog",
)
async def get_drones(
        category_id: Optional[int] = Query(None, description="Category ID filter"),
        search: Optional[str] = Query(None, description="Search by name, description or SKU"),
        is_active_only: bool = Query(True, description="Filter active drones only"),
        page: int = Query(1, ge=1),
        limit: int = Query(20, ge=1, le=100),
        db: AsyncSession = Depends(get_db),
):
    offset = (page - 1) * limit
    stmt = (
        select(Drone)
        .options(
            selectinload(Drone.categories),
            selectinload(Drone.variants).selectinload(DroneVariant.bom_materials).selectinload(
                DroneVariantMaterial.material),
        )
        .where(Drone.is_deleted == False)
    )

    if is_active_only:
        stmt = stmt.where(Drone.is_active == True)

    if category_id:
        stmt = stmt.join(Drone.categories).where(DroneCategory.category_id == category_id)

    if search:
        search_pattern = f"%{search.strip()}%"
        stmt = stmt.outerjoin(Drone.variants).where(
            or_(
                Drone.name.cast(String).ilike(search_pattern),
                Drone.description.cast(String).ilike(search_pattern),
                DroneVariant.sku.ilike(search_pattern),
            )
        )

    stmt = stmt.offset(offset).limit(limit).order_by(Drone.created_at.desc())
    result = await db.execute(stmt)
    return result.scalars().unique().all()


@router.get(
    "/{drone_id}",
    response_model=DroneResponse,
    summary="Get drone details by ID",
)
async def get_drone_by_id(
        drone_id: int,
        db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(Drone)
        .options(
            selectinload(Drone.categories),
            selectinload(Drone.variants).selectinload(DroneVariant.bom_materials).selectinload(
                DroneVariantMaterial.material),
        )
        .where(and_(Drone.drone_id == drone_id, Drone.is_deleted == False))
    )
    result = await db.execute(stmt)
    drone = result.scalar_one_or_none()

    if not drone:
        raise NotFoundException("Drone not found")

    return drone


@router.post(
    "",
    response_model=DroneResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create new drone (Manager / Admin)",
)
async def create_drone(
        drone_in: DroneCreate,
        db: AsyncSession = Depends(get_db),
        _current_user: User = Depends(get_current_manager),
):
    drone = Drone(
        name=drone_in.name.model_dump(),
        description=drone_in.description.model_dump() if drone_in.description else None,
        images=drone_in.images,
        video_url=drone_in.video_url,
        is_active=drone_in.is_active,
    )
    db.add(drone)
    await db.flush()

    drone_id_int = int(getattr(drone, "drone_id"))

    for cat_id in drone_in.category_ids:
        drone_cat = DroneCategory(drone_id=drone_id_int, category_id=cat_id)
        db.add(drone_cat)

    await db.commit()

    stmt = (
        select(Drone)
        .options(
            selectinload(Drone.categories),
            selectinload(Drone.variants).selectinload(DroneVariant.bom_materials).selectinload(
                DroneVariantMaterial.material),
        )
        .where(Drone.drone_id == drone_id_int)
    )
    res = await db.execute(stmt)
    return res.scalar_one()


@router.put(
    "/{drone_id}",
    response_model=DroneResponse,
    summary="Update drone parameters (Manager / Admin)",
)
async def update_drone(
        drone_id: int,
        drone_in: DroneUpdate,
        db: AsyncSession = Depends(get_db),
        _current_user: User = Depends(get_current_manager),
):
    stmt = select(Drone).where(and_(Drone.drone_id == drone_id, Drone.is_deleted == False))
    result = await db.execute(stmt)
    drone = result.scalar_one_or_none()

    if not drone:
        raise NotFoundException("Drone not found")

    update_data = drone_in.model_dump(exclude_unset=True)

    # 1. Если переданы категории, атомарно очищаем старые записи через execute delete
    if "category_ids" in update_data:
        cat_ids = update_data.pop("category_ids")
        if cat_ids is not None:
            # Прямое удаление старых категорий в БД
            await db.execute(
                delete(DroneCategory).where(DroneCategory.drone_id == drone_id)
            )
            await db.flush()  # Гарантируем, что DELETE применился до добавления новых

            # Добавление новых связей
            for new_cat_id in cat_ids:
                db.add(DroneCategory(drone_id=drone_id, category_id=new_cat_id))

    # 2. Обновление остальных полей дрона
    for field, value in update_data.items():
        if value is not None:
            setattr(drone, field, value)

    await db.commit()

    # 3. Возвращаем обновленный объект с подгруженными связями
    res_stmt = (
        select(Drone)
        .options(
            selectinload(Drone.categories),
            selectinload(Drone.variants).selectinload(DroneVariant.bom_materials).selectinload(
                DroneVariantMaterial.material),
        )
        .where(Drone.drone_id == drone_id)
    )
    res = await db.execute(res_stmt)
    return res.scalar_one()


@router.delete(
    "/{drone_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft delete drone (Manager / Admin)",
)
async def delete_drone(
        drone_id: int,
        db: AsyncSession = Depends(get_db),
        _current_user: User = Depends(get_current_manager),
):
    stmt = select(Drone).where(and_(Drone.drone_id == drone_id, Drone.is_deleted == False))
    result = await db.execute(stmt)
    drone = result.scalar_one_or_none()

    if not drone:
        raise NotFoundException("Drone not found")

    drone.is_deleted = True
    drone.deleted_at = datetime.now(timezone.utc)
    await db.commit()


# ===== ВАРИАНТЫ / КОМПЛЕКТАЦИИ (DRONE VARIANTS) =====

@router.post(
    "/{drone_id}/variants",
    response_model=DroneVariantResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create drone variant (Manager / Admin)",
)
async def create_drone_variant(
    drone_id: int,
    variant_in: DroneVariantCreate,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_manager),
):
    drone_stmt = select(Drone).where(and_(Drone.drone_id == drone_id, Drone.is_deleted == False))
    drone_res = await db.execute(drone_stmt)
    if not drone_res.scalar_one_or_none():
        raise NotFoundException("Drone not found")

    sku_stmt = select(DroneVariant).where(DroneVariant.sku == variant_in.sku)
    sku_res = await db.execute(sku_stmt)
    if sku_res.scalar_one_or_none():
        raise BadRequestException("Variant with specified SKU already exists")

    variant = DroneVariant(
        drone_id=drone_id,
        sku=variant_in.sku,
        variant_name=variant_in.variant_name.model_dump(),
        description=variant_in.description.model_dump() if variant_in.description else None,
        price=variant_in.price,
        is_active=variant_in.is_active,
    )
    db.add(variant)
    await db.flush()

    variant_id_int = int(getattr(variant, "variant_id"))

    if variant_in.bom_materials:
        for bom_in in variant_in.bom_materials:
            bom_item = DroneVariantMaterial(
                variant_id=variant_id_int,
                material_id=bom_in.material_id,
                quantity=bom_in.quantity,
                notes=bom_in.notes,
            )
            db.add(bom_item)

    await db.commit()

    res_stmt = (
        select(DroneVariant)
        .options(selectinload(DroneVariant.bom_materials).selectinload(DroneVariantMaterial.material))
        .where(DroneVariant.variant_id == variant_id_int)
    )
    res = await db.execute(res_stmt)
    return res.scalar_one()


@router.put(
    "/variants/{variant_id}",
    response_model=DroneVariantResponse,
    summary="Update drone variant (Manager / Admin)",
)
async def update_drone_variant(
    variant_id: int,
    variant_in: DroneVariantUpdate,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_manager),
):
    stmt = select(DroneVariant).where(and_(DroneVariant.variant_id == variant_id, DroneVariant.is_deleted == False))
    result = await db.execute(stmt)
    variant = result.scalar_one_or_none()

    if not variant:
        raise NotFoundException("Drone variant not found")

    update_data = variant_in.model_dump(exclude_unset=True)

    if "sku" in update_data and update_data["sku"] != str(getattr(variant, "sku")):
        sku_stmt = select(DroneVariant).where(DroneVariant.sku == update_data["sku"])
        sku_res = await db.execute(sku_stmt)
        if sku_res.scalar_one_or_none():
            raise BadRequestException("SKU is already in use by another variant")

    for field, value in update_data.items():
        if value is not None:
            setattr(variant, field, value)

    await db.commit()

    res_stmt = (
        select(DroneVariant)
        .options(selectinload(DroneVariant.bom_materials).selectinload(DroneVariantMaterial.material))
        .where(DroneVariant.variant_id == variant_id)
    )
    res = await db.execute(res_stmt)
    return res.scalar_one()


@router.delete(
    "/variants/{variant_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft delete drone variant (Manager / Admin)",
)
async def delete_drone_variant(
        variant_id: int,
        db: AsyncSession = Depends(get_db),
        _current_user: User = Depends(get_current_manager),
):
    stmt = select(DroneVariant).where(and_(DroneVariant.variant_id == variant_id, DroneVariant.is_deleted == False))
    result = await db.execute(stmt)
    variant = result.scalar_one_or_none()

    if not variant:
        raise NotFoundException("Drone variant not found")

    variant.is_deleted = True
    variant.deleted_at = datetime.now(timezone.utc)
    await db.commit()


# ===== СПЕЦИФИКАЦИЯ МАТЕРИАЛОВ (BOM) =====

@router.post(
    "/variants/{variant_id}/bom",
    response_model=DroneVariantMaterialResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add material component to variant BOM (Manager / Admin)",
)
async def add_bom_material(
        variant_id: int,
        bom_in: DroneVariantMaterialCreate,
        db: AsyncSession = Depends(get_db),
        _current_user: User = Depends(get_current_manager),
):
    variant_stmt = select(DroneVariant).where(
        and_(DroneVariant.variant_id == variant_id, DroneVariant.is_deleted == False))
    variant_res = await db.execute(variant_stmt)
    if not variant_res.scalar_one_or_none():
        raise NotFoundException("Drone variant not found")

    bom_item = DroneVariantMaterial(
        variant_id=variant_id,
        material_id=bom_in.material_id,
        quantity=bom_in.quantity,
        notes=bom_in.notes,
    )
    db.add(bom_item)
    await db.commit()

    bom_item_id_int = int(getattr(bom_item, "bom_item_id"))

    stmt = select(DroneVariantMaterial).options(selectinload(DroneVariantMaterial.material)).where(
        DroneVariantMaterial.bom_item_id == bom_item_id_int)
    res = await db.execute(stmt)
    return res.scalar_one()


@router.delete(
    "/bom/{bom_item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove component from BOM (Manager / Admin)",
)
async def remove_bom_material(
        bom_item_id: int,
        db: AsyncSession = Depends(get_db),
        _current_user: User = Depends(get_current_manager),
):
    stmt = select(DroneVariantMaterial).where(DroneVariantMaterial.bom_item_id == bom_item_id)
    result = await db.execute(stmt)
    bom_item = result.scalar_one_or_none()

    if not bom_item:
        raise NotFoundException("BOM item not found")

    await db.delete(bom_item)
    await db.commit()