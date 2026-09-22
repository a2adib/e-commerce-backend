from typing import List, Optional, Tuple
from datetime import datetime, timedelta, timezone
from sqlmodel import select, func, or_
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.orm import selectinload

from src.common.exceptions import http_400, http_404
from src.common.queries import paginate_query
from src.auth.models import User, UserRole
from src.orders.models import Order
from src.orders.enums import OrderStatus, PaymentStatus
from src.products.models import Product
from src.orders.schemas import OrderSummaryItem
from src.admin.schemas import (
    AdminUserUpdate,
    AdminUserDetailResponse,
    DashboardMetricsResponse,
    LowStockProduct,
)


async def list_admin_users_service(
    session: AsyncSession,
    search: Optional[str] = None,
    role: Optional[str] = None,
    is_active: Optional[bool] = None,
    page: int = 1,
    page_size: int = 20,
) -> Tuple[List[User], int]:
    stmt = select(User)

    if role:
        stmt = stmt.where(User.role == role)
    if is_active is not None:
        stmt = stmt.where(User.is_active == is_active)
    if search:
        term = f"%{search}%"
        stmt = stmt.where(
            or_(
                User.name.ilike(term),
                User.email.ilike(term),
                User.phone.ilike(term),
            )
        )

    stmt = stmt.order_by(User.created_at.desc())
    return await paginate_query(session, stmt, page=page, page_size=page_size)


async def get_admin_user_detail_service(
    session: AsyncSession, public_id: str
) -> AdminUserDetailResponse:
    user_stmt = select(User).where(User.public_id == public_id)
    user = (await session.execute(user_stmt)).scalar_one_or_none()
    if not user:
        raise http_404("User not found", code="USER_NOT_FOUND")

    # Fetch orders summary for this user
    orders_stmt = (
        select(Order)
        .where(Order.user_id == user.id, Order.is_active == True)
        .order_by(Order.created_at.desc())
    )
    orders = (await session.execute(orders_stmt)).scalars().all()

    orders_count = len(orders)
    total_spent = sum(
        o.total for o in orders if o.status not in (OrderStatus.CANCELLED, OrderStatus.RETURNED)
    )

    recent_orders = [
        OrderSummaryItem(
            public_id=o.public_id,
            order_number=o.order_number,
            status=o.status.value,
            total=o.total,
            created_at=o.created_at,
        )
        for o in orders[:5]
    ]

    return AdminUserDetailResponse(
        public_id=user.public_id,
        name=user.name,
        email=user.email,
        phone=user.phone,
        role=user.role.value if hasattr(user.role, "value") else str(user.role),
        is_active=user.is_active,
        created_at=user.created_at,
        orders_count=orders_count,
        total_spent=round(total_spent, 2),
        recent_orders=recent_orders,
    )


async def update_admin_user_service(
    session: AsyncSession, public_id: str, data: AdminUserUpdate
) -> User:
    user_stmt = select(User).where(User.public_id == public_id)
    user = (await session.execute(user_stmt)).scalar_one_or_none()
    if not user:
        raise http_404("User not found", code="USER_NOT_FOUND")

    if data.role is not None:
        try:
            user.role = UserRole(data.role)
        except ValueError:
            raise http_400(f"Invalid role: {data.role}", code="INVALID_ROLE")

    if data.is_active is not None:
        user.is_active = data.is_active

    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def get_dashboard_metrics_service(
    session: AsyncSession, low_stock_threshold: int = 10
) -> DashboardMetricsResponse:
    # 1. Orders by status
    orders_by_status = {s.value: 0 for s in OrderStatus}
    status_stmt = select(Order.status, func.count(Order.id)).where(Order.is_active == True).group_by(Order.status)
    status_results = (await session.execute(status_stmt)).all()
    total_orders = 0
    for st, count in status_results:
        val = st.value if hasattr(st, "value") else str(st)
        orders_by_status[val] = count
        total_orders += count

    # 2. Total revenue (completed / confirmed / processing / shipped / delivered non-cancelled orders)
    revenue_stmt = (
        select(func.sum(Order.total))
        .where(
            Order.is_active == True,
            Order.status.in_([OrderStatus.CONFIRMED, OrderStatus.PROCESSING, OrderStatus.SHIPPED, OrderStatus.DELIVERED]),
        )
    )
    revenue = (await session.execute(revenue_stmt)).scalar() or 0.0

    # 3. User metrics
    total_users = (await session.execute(select(func.count(User.id)))).scalar() or 0
    thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
    new_users = (
        await session.execute(
            select(func.count(User.id)).where(User.created_at >= thirty_days_ago)
        )
    ).scalar() or 0

    # 4. Low stock products
    low_stock_stmt = (
        select(Product)
        .where(Product.is_active == True, Product.stock_qty <= low_stock_threshold)
        .order_by(Product.stock_qty.asc())
        .limit(20)
    )
    low_stock = (await session.execute(low_stock_stmt)).scalars().all()
    low_stock_items = [
        LowStockProduct(
            public_id=p.public_id,
            name=p.name,
            sku=p.sku,
            stock_qty=p.stock_qty,
            price=p.price,
        )
        for p in low_stock
    ]

    return DashboardMetricsResponse(
        orders_by_status=orders_by_status,
        total_revenue=round(float(revenue), 2),
        total_orders=total_orders,
        new_users_last_30_days=new_users,
        total_users=total_users,
        low_stock_products=low_stock_items,
    )
