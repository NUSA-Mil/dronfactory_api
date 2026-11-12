from datetime import datetime
from typing import Optional
from pydantic import Field, field_validator
from schemas.common import BaseSchema, sanitize_xss
from models.order import PaymentMethodEnum


class InvoiceCreate(BaseSchema):
    """Схема генерации чека/счета к заказу"""
    order_id: int
    amount: float = Field(..., gt=0)
    payment_method: PaymentMethodEnum
    payment_details: Optional[str] = Field(None, max_length=500)

    @field_validator("payment_details", mode="before")
    @classmethod
    def validate_xss(cls, v: Optional[str]) -> Optional[str]:
        return sanitize_xss(v)


class InvoiceResponse(BaseSchema):
    invoice_id: int
    invoice_number: str
    order_id: int
    user_id: Optional[int] = None
    amount: float
    payment_method: PaymentMethodEnum
    payment_details: Optional[str] = None
    is_paid: bool
    paid_at: Optional[datetime] = None
    receipt_url: Optional[str] = None
    created_at: datetime