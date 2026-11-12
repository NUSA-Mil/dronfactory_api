from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from api.deps import get_current_storekeeper
from core.database import get_db
from core.exceptions import BadRequestException, NotFoundException
from models.user import User
from models.warehouse import (
    Warehouse,
    WarehouseDroneStock,
    WarehouseMaterialStock,
)
from schemas.warehouse import (
    WarehouseCreate,
    WarehouseDroneStockCreate,
    WarehouseDroneStockResponse,
    WarehouseDroneStockUpdate,
    WarehouseMaterialStockCreate,
    WarehouseMaterialStockResponse,
    WarehouseMaterialStockUpdate,
    WarehouseResponse,
    WarehouseUpdate,
)

router = APIRouter(prefix="/warehouses", tags=["Warehouses & Stocks"])


# ===== УПРАВЛЕНИЕ СКЛАДАМИ (WAREHOUSES) =====

@router.get(
    "",
    response_model=List[WarehouseResponse],
    summary="Получить список всех складов",
)
async def get_warehouses(
    is_assembly_site: Optional[bool] = Query(None, description="Фильтр по площадуаде сборки"),
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_storekeeper),
):
    stmt = select(Warehouse)
    if is_assembly_site is not None:
        stmt = stmt.where(Warehouse.is_assembly_site == is_assembly_site)

    stmt = stmt.order_by(Warehouse.warehouse_id.asc())
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get(
    "/{warehouse_id}",
    response_model=WarehouseResponse,
    summary="Получить склад по ID",
)
async def get_warehouse_by_id(
    warehouse_id: int,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_storekeeper),
):
    stmt = select(Warehouse).where(Warehouse.warehouse_id == warehouse_id)
    res = await db.execute(stmt)
    wh = res.scalar_one_or_none()
    if not wh:
        raise NotFoundException("Склад не найден")
    return wh


@router.post(
    "",
    response_model=WarehouseResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Создать новый склад (Storekeeper / Manager / Admin)",
)
async def create_warehouse(
    wh_in: WarehouseCreate,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_storekeeper),
):
    wh = Warehouse(
        name=wh_in.name.model_dump(),
        address=wh_in.address,
        is_assembly_site=wh_in.is_assembly_site,
    )
    db.add(wh)
    await db.commit()
    await db.refresh(wh)
    return wh


@router.put(
    "/{warehouse_id}",
    response_model=WarehouseResponse,
    summary="Обновить параметры склада",
)
async def update_warehouse(
    warehouse_id: int,
    wh_in: WarehouseUpdate,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_storekeeper),
):
    stmt = select(Warehouse).where(Warehouse.warehouse_id == warehouse_id)
    res = await db.execute(stmt)
    wh = res.scalar_one_or_none()
    if not wh:
        raise NotFoundException("Склад не найден")

    update_data = wh_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if value is not None:
            setattr(wh, field, value)

    await db.commit()
    await db.refresh(wh)
    return wh


# ===== СКЛАДСКИЕ ОСТАТКИ: МАТЕРИАЛЫ =====

@router.get(
    "/{warehouse_id}/materials-stock",
    response_model=List[WarehouseMaterialStockResponse],
    summary="Получить остатки материалов на конкретном складе",
)
async def get_warehouse_material_stock(
    warehouse_id: int,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_storekeeper),
):
    stmt = (
        select(WarehouseMaterialStock)
        .options(selectinload(WarehouseMaterialStock.material))
        .where(WarehouseMaterialStock.warehouse_id == warehouse_id)
    )
    res = await db.execute(stmt)
    return res.scalars().all()


@router.post(
    "/materials-stock",
    response_model=WarehouseMaterialStockResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Инициализировать / настроить порог остатка материала на складе",
)
async def set_material_stock(
    stock_in: WarehouseMaterialStockCreate,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_storekeeper),
):
    stmt = select(WarehouseMaterialStock).where(
        and_(
            WarehouseMaterialStock.warehouse_id == stock_in.warehouse_id,
            WarehouseMaterialStock.material_id == stock_in.material_id,
        )
    )
    res = await db.execute(stmt)
    existing = res.scalar_one_or_none()

    if existing:
        raise BadRequestException("Запись остатка для данного материала на складе уже существует")

    stock = WarehouseMaterialStock(
        warehouse_id=stock_in.warehouse_id,
        material_id=stock_in.material_id,
        quantity=stock_in.quantity,
        min_quantity=stock_in.min_quantity,
    )
    db.add(stock)
    await db.commit()
    await db.refresh(stock)
    return stock


@router.put(
    "/materials-stock/{stock_id}",
    response_model=WarehouseMaterialStockResponse,
    summary="Обновить текущий остаток или мин. порог материала",
)
async def update_material_stock(
    stock_id: int,
    stock_in: WarehouseMaterialStockUpdate,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_storekeeper),
):
    stmt = select(WarehouseMaterialStock).where(WarehouseMaterialStock.stock_id == stock_id)
    res = await db.execute(stmt)
    stock = res.scalar_one_or_none()
    if not stock:
        raise NotFoundException("Запись остатка не найдена")

    update_data = stock_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if value is not None:
            setattr(stock, field, value)

    await db.commit()
    await db.refresh(stock)
    return stock


# ===== СКЛАДСКИЕ ОСТАТКИ: ДРОНЫ =====

@router.get(
    "/{warehouse_id}/drones-stock",
    response_model=List[WarehouseDroneStockResponse],
    summary="Получить остатки готовых дронов на конкретном складе",
)
async def get_warehouse_drone_stock(
    warehouse_id: int,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_storekeeper),
):
    stmt = (
        select(WarehouseDroneStock)
        .options(selectinload(WarehouseDroneStock.variant))
        .where(WarehouseDroneStock.warehouse_id == warehouse_id)
    )
    res = await db.execute(stmt)
    return res.scalars().all()


@router.post(
    "/drones-stock",
    response_model=WarehouseDroneStockResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Инициализировать / настроить остаток дронов на складе",
)
async def set_drone_stock(
    stock_in: WarehouseDroneStockCreate,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_storekeeper),
):
    stmt = select(WarehouseDroneStock).where(
        and_(
            WarehouseDroneStock.warehouse_id == stock_in.warehouse_id,
            WarehouseDroneStock.variant_id == stock_in.variant_id,
        )
    )
    res = await db.execute(stmt)
    existing = res.scalar_one_or_none()

    if existing:
        raise BadRequestException("Запись остатка для этой модификации на складе уже существует")

    stock = WarehouseDroneStock(
        warehouse_id=stock_in.warehouse_id,
        variant_id=stock_in.variant_id,
        quantity=stock_in.quantity,
        min_quantity=stock_in.min_quantity,
    )
    db.add(stock)
    await db.commit()
    await db.refresh(stock)
    return stock


@router.put(
    "/drones-stock/{drone_stock_id}",
    response_model=WarehouseDroneStockResponse,
    summary="Обновить текущий остаток или мин. порог дронов",
)
async def update_drone_stock(
    drone_stock_id: int,
    stock_in: WarehouseDroneStockUpdate,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_storekeeper),
):
    stmt = select(WarehouseDroneStock).where(WarehouseDroneStock.drone_stock_id == drone_stock_id)
    res = await db.execute(stmt)
    stock = res.scalar_one_or_none()
    if not stock:
        raise NotFoundException("Запись остатка дронов не найдена")

    update_data = stock_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if value is not None:
            setattr(stock, field, value)

    await db.commit()
    await db.refresh(stock)
    return stock