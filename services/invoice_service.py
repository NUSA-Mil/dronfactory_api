import uuid
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from core.exceptions import NotFoundException, BadRequestException
from models.order import Order
from models.invoice import Invoice
from schemas.invoice import InvoiceCreate


class InvoiceService:
    @staticmethod
    async def create_invoice(data: InvoiceCreate, db: AsyncSession) -> Invoice:
        """Генерация счета/чека на основе существующего заказа"""
        order_res = await db.execute(select(Order).where(Order.order_id == data.order_id))
        order = order_res.scalar_one_or_none()

        if not order:
            raise NotFoundException("Заказ не найден")

        # Проверка существующих чеков
        existing_res = await db.execute(select(Invoice).where(Invoice.order_id == data.order_id))
        if existing_res.scalar_one_or_none():
            raise BadRequestException("К этому заказу уже выписан чек")

        # Формирование номера чека: INV-YYYY-XXXXXX
        year = datetime.now(timezone.utc).year
        unique_suffix = str(uuid.uuid4().hex[:6]).upper()
        invoice_number = f"INV-{year}-{unique_suffix}"

        invoice = Invoice(
            invoice_number=invoice_number,
            order_id=data.order_id,
            user_id=order.customer_id,
            amount=data.amount,
            payment_method=data.payment_method,
            payment_details=data.payment_details,
            is_paid=False,
            receipt_url=f"/storage/invoices/{invoice_number}.pdf"
        )

        db.add(invoice)
        await db.commit()
        await db.refresh(invoice)
        return invoice


invoice_service = InvoiceService()