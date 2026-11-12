import uuid
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from api.deps import get_current_user, get_current_manager
from core.database import get_db
from core.exceptions import BadRequestException, NotFoundException
from core.logger import log_audit
from models.drone import DroneVariant
from models.order import Order, OrderItem, OrderStatusEnum
from models.user import User
from core.permissions import ROLE_CLIENT, check_owner_or_worker
from schemas.order import (
    OrderCreate,
    OrderFeasibilityResponse,
    OrderResponse,
    OrderStatusUpdate,
)
from services.feasibility_service import feasibility_service

router = APIRouter(prefix="/orders", tags=["Orders & Cart"])


@router.get(
    "",
    response_model=List[OrderResponse],
    summary="Получить список заказов",
)
async def get_orders(
    order_status: Optional[OrderStatusEnum] = Query(None, alias="status", description="Фильтр по статусу"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    user_id_int = int(getattr(current_user, "user_id"))
    role_id_int = int(getattr(current_user, "role_id"))

    offset = (page - 1) * limit
    stmt = select(Order).options(selectinload(Order.items))

    if role_id_int == ROLE_CLIENT:
        stmt = stmt.where(Order.customer_id == user_id_int)

    if order_status:
        stmt = stmt.where(Order.status == order_status)

    stmt = stmt.order_by(Order.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get(
    "/{order_id}",
    response_model=OrderResponse,
    summary="Получить подробности заказа",
)
async def get_order_by_id(
    order_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = (
        select(Order)
        .options(selectinload(Order.items))
        .where(Order.order_id == order_id)
    )
    result = await db.execute(stmt)
    order = result.scalar_one_or_none()

    if not order:
        raise NotFoundException("Заказ не найден")

    check_owner_or_worker(
        resource_user_id=int(getattr(order, "customer_id")) if order.customer_id else 0,
        current_user_id=int(getattr(current_user, "user_id")),
        current_user_role_id=int(getattr(current_user, "role_id")),
    )

    return order


@router.get(
    "/{order_id}/feasibility",
    response_model=OrderFeasibilityResponse,
    summary="Проверить осуществимость заказа (наличие дронов и материалов BOM)",
)
async def check_order_feasibility(
    order_id: int,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_manager),
):
    """
    Проверяет возможность выполнения заказа:
    1. Проверяет наличие готовых дронов на складе.
    2. Если дронов не хватает, проверяет наличие материалов для их производства.
    """
    return await feasibility_service.check_order_feasibility(order_id, db)


@router.post(
    "",
    response_model=OrderResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Оформить новый заказ",
)
async def create_order(
    order_in: OrderCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    user_id_int = int(getattr(current_user, "user_id"))
    order_number = f"ORD-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"

    total_amount = 0.0
    order_items_to_add = []

    for item_in in order_in.items:
        variant_stmt = select(DroneVariant).where(
            and_(DroneVariant.variant_id == item_in.variant_id, DroneVariant.is_deleted == False)
        )
        variant_res = await db.execute(variant_stmt)
        variant = variant_res.scalar_one_or_none()

        if not variant:
            raise BadRequestException(f"Модификация дрона (ID: {item_in.variant_id}) не найдена")

        if not variant.is_active:
            raise BadRequestException(f"Модификация дрона '{variant.sku}' недоступна для заказа")

        unit_price = float(getattr(variant, "price"))
        item_total = unit_price * item_in.quantity
        total_amount += item_total

        order_items_to_add.append(
            {
                "variant_id": item_in.variant_id,
                "quantity": item_in.quantity,
                "unit_price": unit_price,
            }
        )

    order = Order(
        order_number=order_number,
        customer_id=user_id_int,
        customer_name=order_in.customer_name,
        customer_contact=order_in.customer_contact,
        created_by=user_id_int,
        status=OrderStatusEnum.new,
        delivery_type=order_in.delivery_type,
        delivery_address=order_in.delivery_address,
        payment_method=order_in.payment_method,
        payment_details=order_in.payment_details,
        total_amount=total_amount,
    )
    db.add(order)
    await db.flush()

    order_id_int = int(getattr(order, "order_id"))

    for item_data in order_items_to_add:
        order_item = OrderItem(
            order_id=order_id_int,
            variant_id=item_data["variant_id"],
            quantity=item_data["quantity"],
            unit_price=item_data["unit_price"],
        )
        db.add(order_item)

    await db.commit()

    log_audit(
        user_id=user_id_int,
        ip_address="127.0.0.1",
        category="ORDERS",
        action="CREATE_ORDER",
        details=f"Создан новый заказ {order_number} на сумму {total_amount}",
    )

    stmt = select(Order).options(selectinload(Order.items)).where(Order.order_id == order_id_int)
    res = await db.execute(stmt)
    return res.scalar_one()


@router.patch(
    "/{order_id}/status",
    response_model=OrderResponse,
    summary="Обновить статус заказа (Manager / Admin)",
)
async def update_order_status(
    order_id: int,
    status_in: OrderStatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_manager),
):
    stmt = select(Order).options(selectinload(Order.items)).where(Order.order_id == order_id)
    res = await db.execute(stmt)
    order = res.scalar_one_or_none()

    if not order:
        raise NotFoundException("Заказ не найден")

    user_id_int = int(getattr(current_user, "user_id"))
    old_status = order.status

    order.status = status_in.status
    if status_in.status == OrderStatusEnum.cancelled:
        order.cancelled_by = user_id_int
        order.cancel_reason = status_in.cancel_reason
    else:
        order.assigned_manager_id = user_id_int

    await db.commit()

    log_audit(
        user_id=user_id_int,
        ip_address="127.0.0.1",
        category="ORDERS",
        action="UPDATE_STATUS",
        details=f"Статус заказа {order.order_number} изменен с {old_status} на {status_in.status}",
    )

    return order