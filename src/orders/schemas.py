from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field
from src.orders.enums import OrderStatus, PaymentMethod, PaymentStatus


class ShippingAddressSnapshot(BaseModel):
    full_name: str
    phone: str
    address_line: str
    city: str
    district: str
    postal_code: Optional[str] = None


class CheckoutRequest(BaseModel):
    address_id: Optional[str] = None
    address: Optional[ShippingAddressSnapshot] = None
    phone: Optional[str] = None
    note: Optional[str] = None
    payment_method: PaymentMethod = PaymentMethod.COD


class OrderItemInput(BaseModel):
    product_public_id: str
    quantity: int = Field(ge=1)


class AdminOrderCreate(BaseModel):
    user_public_id: Optional[str] = None
    items: List[OrderItemInput]
    shipping_address: ShippingAddressSnapshot
    delivery_charge: float = 0.0
    discount: float = 0.0
    note: Optional[str] = None
    payment_method: PaymentMethod = PaymentMethod.COD
    payment_status: PaymentStatus = PaymentStatus.PENDING


class AdminOrderUpdate(BaseModel):
    shipping_address: Optional[ShippingAddressSnapshot] = None
    items: Optional[List[OrderItemInput]] = None
    note: Optional[str] = None
    delivery_charge: Optional[float] = None
    discount: Optional[float] = None


class OrderStatusUpdate(BaseModel):
    status: OrderStatus
    note: Optional[str] = None


class BulkOrderStatusUpdate(BaseModel):
    order_public_ids: List[str]
    status: OrderStatus
    note: Optional[str] = None


class OrderItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    public_id: str
    product_public_id: Optional[str] = None
    product_name: str
    unit_price: float
    quantity: int
    line_total: float


class OrderStatusHistoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    public_id: str
    from_status: Optional[str] = None
    to_status: str
    changed_by: Optional[str] = None
    note: Optional[str] = None
    created_at: datetime


class OrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    public_id: str
    order_number: str
    user_public_id: Optional[str] = None
    customer_name: Optional[str] = None
    customer_email: Optional[str] = None
    status: str
    payment_method: str
    payment_status: str
    subtotal: float
    delivery_charge: float
    discount: float
    total: float
    shipping_snapshot: dict
    note: Optional[str] = None
    items: List[OrderItemResponse] = []
    status_history: List[OrderStatusHistoryResponse] = []
    created_at: datetime


class OrderSummaryItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    public_id: str
    order_number: str
    status: str
    total: float
    created_at: datetime
