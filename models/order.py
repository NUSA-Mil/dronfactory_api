import enum
from datetime import date, datetime
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import ENUM
from sqlalchemy.orm import Mapped, mapped_column, relationship
from core.database import Base

if TYPE_CHECKING:
    from models.drone import DroneVariant
    from models.invoice import Invoice
    from models.user import User


class OrderStatusEnum(str, enum.Enum):
    cart = "cart"
    new = "new"
    processing = "processing"
    production = "production"
    ready = "ready"
    completed = "completed"
    cancelled = "cancelled"


class DeliveryTypeEnum(str, enum.Enum):
    pickup = "pickup"
    delivery = "delivery"


class PaymentMethodEnum(str, enum.Enum):
    cash = "cash"
    card = "card"
    other = "other"


class PaymentStatusEnum(str, enum.Enum):
    pending = "pending"
    paid = "paid"
    refunded = "refunded"


class Order(Base):
    __tablename__ = "orders"

    order_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    order_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)

    customer_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True, index=True
    )
    customer_name: Mapped[str] = mapped_column(String(200), nullable=False)
    customer_contact: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    created_by: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True
    )

    assigned_manager_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True
    )
    cancelled_by: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True
    )
    cancel_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    status: Mapped[OrderStatusEnum] = mapped_column(
        ENUM(OrderStatusEnum, name="order_status_enum", create_type=False),
        default=OrderStatusEnum.cart,
        nullable=False,
        index=True
    )
    delivery_type: Mapped[DeliveryTypeEnum] = mapped_column(
        ENUM(DeliveryTypeEnum, name="delivery_type_enum", create_type=False),
        default=DeliveryTypeEnum.pickup,
        nullable=False
    )
    delivery_address: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    delivery_cost: Mapped[float] = mapped_column(Numeric(12, 2), default=0.0, nullable=False)

    payment_method: Mapped[PaymentMethodEnum] = mapped_column(
        ENUM(PaymentMethodEnum, name="payment_method_enum", create_type=False),
        default=PaymentMethodEnum.card,
        nullable=False
    )
    payment_details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    payment_status: Mapped[PaymentStatusEnum] = mapped_column(
        ENUM(PaymentStatusEnum, name="payment_status_enum", create_type=False),
        default=PaymentStatusEnum.pending,
        nullable=False
    )

    total_amount: Mapped[float] = mapped_column(Numeric(14, 2), default=0.0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    due_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    customer: Mapped[Optional["User"]] = relationship(
        "User", foreign_keys=[customer_id], back_populates="orders"
    )
    items: Mapped[List["OrderItem"]] = relationship(
        "OrderItem", back_populates="order", cascade="all, delete-orphan"
    )
    invoice: Mapped[Optional["Invoice"]] = relationship(
        "Invoice", back_populates="order", uselist=False, cascade="all, delete-orphan"
    )


class OrderItem(Base):
    __tablename__ = "order_items"

    item_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.order_id", ondelete="CASCADE"), nullable=False, index=True
    )
    variant_id: Mapped[int] = mapped_column(
        ForeignKey("drone_variants.variant_id", ondelete="RESTRICT"), nullable=False
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)

    order: Mapped["Order"] = relationship("Order", back_populates="items")
    variant: Mapped["DroneVariant"] = relationship("DroneVariant")