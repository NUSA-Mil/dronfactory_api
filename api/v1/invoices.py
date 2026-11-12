import uuid
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_user
from core.database import get_db
from core.exceptions import BadRequestException, NotFoundException
from models.invoice import Invoice
from models.order import Order
from models.user import User
from core.permissions import ROLE_CLIENT, check_owner_or_worker
from schemas.invoice import InvoiceCreate, InvoiceResponse

router = APIRouter(prefix="/invoices", tags=["Invoices"])


@router.get(
    "",
    response_model=List[InvoiceResponse],
    summary="Получить список счетов / чеков",
)
async def get_invoices(
    order_id: Optional[int] = Query(None, description="Фильтр по ID заказа"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    user_id_int = int(getattr(current_user, "user_id"))
    role_id_int = int(getattr(current_user, "role_id"))

    offset = (page - 1) * limit
    stmt = select(Invoice)

    if role_id_int == ROLE_CLIENT:
        stmt = stmt.where(Invoice.user_id == user_id_int)

    if order_id:
        stmt = stmt.where(Invoice.order_id == order_id)

    stmt = stmt.order_by(Invoice.created_at.desc()).offset(offset).limit(limit)
    res = await db.execute(stmt)
    return res.scalars().all()


@router.get(
    "/{invoice_id}",
    response_model=InvoiceResponse,
    summary="Получить конкретный счет по ID",
)
async def get_invoice_by_id(
    invoice_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = select(Invoice).where(Invoice.invoice_id == invoice_id)
    res = await db.execute(stmt)
    invoice = res.scalar_one_or_none()

    if not invoice:
        raise NotFoundException("Счет не найден")

    check_owner_or_worker(
        resource_user_id=int(getattr(invoice, "user_id")) if invoice.user_id else 0,
        current_user_id=int(getattr(current_user, "user_id")),
        current_user_role_id=int(getattr(current_user, "role_id")),
    )

    return invoice


@router.post(
    "",
    response_model=InvoiceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Сформировать чек/счет к заказу",
)
async def create_invoice(
    inv_in: InvoiceCreate,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    order_stmt = select(Order).where(Order.order_id == inv_in.order_id)
    order_res = await db.execute(order_stmt)
    order = order_res.scalar_one_or_none()

    if not order:
        raise NotFoundException("Указанный заказ не найден")

    existing_inv_stmt = select(Invoice).where(Invoice.order_id == inv_in.order_id)
    existing_res = await db.execute(existing_inv_stmt)
    if existing_res.scalar_one_or_none():
        raise BadRequestException("Счет к этому заказу уже сформирован")

    inv_number = f"INV-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
    customer_id = getattr(order, "customer_id")

    invoice = Invoice(
        invoice_number=inv_number,
        order_id=inv_in.order_id,
        user_id=customer_id,
        amount=inv_in.amount,
        payment_method=inv_in.payment_method,
        payment_details=inv_in.payment_details,
        is_paid=True,
        paid_at=datetime.now(timezone.utc),
    )
    db.add(invoice)
    await db.commit()
    await db.refresh(invoice)
    return invoice