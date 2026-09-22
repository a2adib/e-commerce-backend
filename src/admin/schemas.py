from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, ConfigDict
from src.orders.schemas import OrderSummaryItem


class AdminUserUpdate(BaseModel):
    role: Optional[str] = None
    is_active: Optional[bool] = None


class AdminUserDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    public_id: str
    name: str
    email: str
    phone: Optional[str] = None
    role: str
    is_active: bool
    created_at: datetime
    orders_count: int = 0
    total_spent: float = 0.0
    recent_orders: List[OrderSummaryItem] = []


class LowStockProduct(BaseModel):
    public_id: str
    name: str
    sku: Optional[str] = None
    stock_qty: int
    price: float


class DashboardMetricsResponse(BaseModel):
    orders_by_status: dict[str, int]
    total_revenue: float
    total_orders: int
    new_users_last_30_days: int
    total_users: int
    low_stock_products: List[LowStockProduct]
