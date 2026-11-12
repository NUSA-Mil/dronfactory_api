from datetime import datetime, date
from typing import Optional, List
from pydantic import Field, field_validator
from schemas.common import BaseSchema, sanitize_xss
from models.order import OrderStatusEnum, DeliveryTypeEnum, PaymentMethodEnum, PaymentStatusEnum


class OrderItemCreate(BaseSchema):
    variant_id: int
    quantity: int = Field(..., gt=0)


class OrderItemResponse(BaseSchema):
    item_id: int
    order_id: int
    variant_id: int
    quantity: int
    unit_price: float


class OrderCreate(BaseSchema):
    customer_name: str = Field(..., min_length=2, max_length=200)
    customer_contact: Optional[str] = Field(None, max_length=200)
    delivery_type: DeliveryTypeEnum = DeliveryTypeEnum.pickup
    delivery_address: Optional[str] = Field(None, max_length=255)
    payment_method: PaymentMethodEnum = PaymentMethodEnum.card
    payment_details: Optional[str] = Field(None, max_length=500)
    items: List[OrderItemCreate] = Field(..., min_length=1)

    @field_validator("customer_name", "customer_contact", "delivery_address", "payment_details", mode="before")
    @classmethod
    def validate_xss(cls, v: Optional[str]) -> Optional[str]:
        return sanitize_xss(v)


class OrderStatusUpdate(BaseSchema):
    status: OrderStatusEnum
    cancel_reason: Optional[str] = Field(None, max_length=500)

    @field_validator("cancel_reason", mode="before")
    @classmethod
    def validate_xss(cls, v: Optional[str]) -> Optional[str]:
        return sanitize_xss(v)


class OrderResponse(BaseSchema):
    order_id: int
    order_number: str
    customer_id: Optional[int] = None
    customer_name: str
    customer_contact: Optional[str] = None
    status: OrderStatusEnum
    delivery_type: DeliveryTypeEnum
    delivery_address: Optional[str] = None
    delivery_cost: float
    payment_method: PaymentMethodEnum
    payment_status: PaymentStatusEnum
    total_amount: float
    items: List[OrderItemResponse] = []
    created_at: datetime
    due_date: Optional[date] = None

class MissingVariantItem(BaseSchema):
    variant_id: int
    needed: int


class MissingMaterialItem(BaseSchema):
    material_id: int
    needed: float
    available: float


class OrderFeasibilityResponse(BaseSchema):
    order_id: int
    is_feasible: bool
    drone_status_message: str
    material_status_message: str
    missing_variants: List[MissingVariantItem] = []
    missing_materials: List[MissingMaterialItem] = []