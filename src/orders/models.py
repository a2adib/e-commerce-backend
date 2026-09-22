from typing import Optional, TYPE_CHECKING, List
from datetime import datetime
from sqlmodel import Field, Relationship, JSON, Column
import sqlalchemy as sa
from sqlalchemy import DateTime, func

from src.common.mixins import CommonFieldMixin, IDMixin, TimestampMixin
from src.common.utils import generate_public_id
from src.orders.enums import OrderStatus, PaymentMethod, PaymentStatus

if TYPE_CHECKING:
    from src.auth.models import User
    from src.products.models import Product


class Order(CommonFieldMixin, table=True):
    __tablename__ = "orders"

    order_number: str = Field(unique=True, index=True, nullable=False, max_length=50)
    user_id: Optional[int] = Field(
        default=None, foreign_key="users.id", nullable=True, index=True
    )
    status: OrderStatus = Field(
        default=OrderStatus.PENDING,
        sa_column=Column(sa.Enum(OrderStatus, native_enum=False), nullable=False, default=OrderStatus.PENDING, index=True),
    )
    payment_method: PaymentMethod = Field(
        default=PaymentMethod.COD,
        sa_column=Column(sa.Enum(PaymentMethod, native_enum=False), nullable=False, default=PaymentMethod.COD),
    )
    payment_status: PaymentStatus = Field(
        default=PaymentStatus.PENDING,
        sa_column=Column(sa.Enum(PaymentStatus, native_enum=False), nullable=False, default=PaymentStatus.PENDING),
    )

    subtotal: float = Field(default=0.0, nullable=False, ge=0)
    delivery_charge: float = Field(default=0.0, nullable=False, ge=0)
    discount: float = Field(default=0.0, nullable=False, ge=0)
    total: float = Field(default=0.0, nullable=False, ge=0)

    # Shipping snapshot: full_name, phone, address_line, city, district, postal_code
    shipping_snapshot: dict = Field(
        default={}, sa_column=Column(JSON, nullable=False)
    )
    note: Optional[str] = Field(default=None, max_length=1000)

    user: Optional["User"] = Relationship(back_populates="orders")
    items: List["OrderItem"] = Relationship(
        back_populates="order",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    status_history: List["OrderStatusHistory"] = Relationship(
        back_populates="order",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )

    def __init__(self, **data):
        if "total_amount" in data and "total" not in data:
            data["total"] = data.pop("total_amount")
        if "shipping_address" in data and "shipping_snapshot" not in data:
            data["shipping_snapshot"] = data.pop("shipping_address")
        if "public_id" not in data:
            data["public_id"] = generate_public_id()
        super().__init__(**data)

    @property
    def shipping_address(self) -> dict:
        return self.shipping_snapshot

    @property
    def total_amount(self) -> float:
        return self.total


class OrderItem(CommonFieldMixin, table=True):
    __tablename__ = "order_items"

    order_id: int = Field(
        foreign_key="orders.id", index=True, nullable=False
    )
    product_id: Optional[int] = Field(
        default=None, foreign_key="products.id", nullable=True, index=True
    )
    product_name: str = Field(nullable=False, max_length=255)
    unit_price: float = Field(nullable=False, ge=0)
    quantity: int = Field(default=1, nullable=False, ge=1)
    line_total: float = Field(nullable=False, ge=0)

    order: Optional["Order"] = Relationship(back_populates="items")
    product: Optional["Product"] = Relationship(back_populates="order_items")

    def __init__(self, **data):
        if "public_id" not in data:
            data["public_id"] = generate_public_id()
        super().__init__(**data)


class OrderStatusHistory(IDMixin, table=True):
    __tablename__ = "order_status_history"

    order_id: int = Field(
        foreign_key="orders.id", index=True, nullable=False
    )
    from_status: Optional[OrderStatus] = Field(
        default=None,
        sa_column=Column(sa.Enum(OrderStatus, native_enum=False), nullable=True),
    )
    to_status: OrderStatus = Field(
        sa_column=Column(sa.Enum(OrderStatus, native_enum=False), nullable=False),
    )
    changed_by: Optional[str] = Field(default=None, max_length=100)  # e.g., 'customer:usr_xxx' or 'admin:usr_xxx' or 'system'
    note: Optional[str] = Field(default=None, max_length=1000)

    order: Optional["Order"] = Relationship(back_populates="status_history")

    def __init__(self, **data):
        if "public_id" not in data:
            data["public_id"] = generate_public_id()
        super().__init__(**data)
