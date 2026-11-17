from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, Query, status
from sqlmodel.ext.asyncio.session import AsyncSession

from src.database import get_session
from src.common.response import StandardResponse
from src.common.filters import PaginationParams
from src.common.exceptions import http_403
from src.auth.dependencies import require_customer, require_admin, get_current_user
from src.auth.models import User
from src.orders.schemas import (
    CheckoutRequest,
    AdminOrderCreate,
    AdminOrderUpdate,
    OrderStatusUpdate,
    BulkOrderStatusUpdate,
    OrderResponse,
    OrderItemResponse,
    OrderStatusHistoryResponse,
)
from src.orders.services import (
    checkout_service,
    cancel_customer_order_service,
    admin_change_order_status_service,
    admin_create_order_service,
    admin_update_order_service,
    admin_list_orders_service,
    list_customer_orders_service,
    get_order_by_public_id,
    track_order_service,
)

# Storefront / Customer Router
customer_router = APIRouter(tags=["customer"])

# Admin Router
admin_router = APIRouter(
    prefix="/admin/orders",
    tags=["admin"],
    dependencies=[Depends(require_admin)],
)


def _val(enum_or_str):
    if enum_or_str is None:
        return None
    return enum_or_str.value if hasattr(enum_or_str, "value") else str(enum_or_str)


def _to_order_response(order) -> OrderResponse:
    return OrderResponse(
        public_id=order.public_id,
        order_number=order.order_number,
        user_public_id=order.user.public_id if order.user else None,
        customer_name=order.user.name if order.user else order.shipping_snapshot.get("full_name"),
        customer_email=order.user.email if order.user else None,
        status=_val(order.status),
        payment_method=_val(order.payment_method),
        payment_status=_val(order.payment_status),
        subtotal=order.subtotal,
        delivery_charge=order.delivery_charge,
        discount=order.discount,
        total=order.total,
        shipping_snapshot=order.shipping_snapshot,
        note=order.note,
        coupon_code=getattr(order, "coupon_code", None),
        items=[
            OrderItemResponse(
                public_id=item.public_id,
                product_public_id=item.product.public_id if item.product else None,
                product_name=item.product_name,
                unit_price=item.unit_price,
                quantity=item.quantity,
                line_total=item.line_total,
            )
            for item in (order.items or [])
        ],
        status_history=[
            OrderStatusHistoryResponse(
                public_id=h.public_id,
                from_status=_val(h.from_status),
                to_status=_val(h.to_status),
                changed_by=h.changed_by,
                note=h.note,
                created_at=h.created_at,
            )
            for h in (order.status_history or [])
        ],
        created_at=order.created_at,
    )


# --- Customer Endpoints ---

@customer_router.get("/orders/track", response_model=StandardResponse[OrderResponse])
async def track_order(
    order_number: str = Query(..., description="e.g. ORD-20261116-XXXX"),
    phone: str = Query(..., description="Phone number used at checkout"),
    session: AsyncSession = Depends(get_session),
) -> StandardResponse[OrderResponse]:
    order = await track_order_service(session, order_number, phone)
    return StandardResponse(data=_to_order_response(order))


@customer_router.post("/checkout", response_model=StandardResponse[OrderResponse], status_code=status.HTTP_201_CREATED)
async def checkout(
    data: CheckoutRequest,
    current_user: User = Depends(require_customer),
    session: AsyncSession = Depends(get_session),
) -> StandardResponse[OrderResponse]:
    order = await checkout_service(session, current_user, data)
    return StandardResponse(
        message="Order placed successfully",
        data=_to_order_response(order),
    )


@customer_router.get("/orders/me", response_model=StandardResponse[List[OrderResponse]])
async def get_my_orders(
    pagination: PaginationParams = Depends(),
    current_user: User = Depends(require_customer),
    session: AsyncSession = Depends(get_session),
) -> StandardResponse[List[OrderResponse]]:
    orders, total = await list_customer_orders_service(
        session, current_user.id, page=pagination.page, page_size=pagination.page_size
    )
    return StandardResponse(data=[_to_order_response(o) for o in orders])


@customer_router.get("/orders/me/{public_id}", response_model=StandardResponse[OrderResponse])
async def get_my_order_by_id(
    public_id: str,
    current_user: User = Depends(require_customer),
    session: AsyncSession = Depends(get_session),
) -> StandardResponse[OrderResponse]:
    order = await get_order_by_public_id(session, public_id)
    if order.user_id != current_user.id:
        raise http_403("Not authorized to view this order", code="FORBIDDEN")
    return StandardResponse(data=_to_order_response(order))


@customer_router.post("/orders/me/{public_id}/cancel", response_model=StandardResponse[OrderResponse])
async def cancel_my_order(
    public_id: str,
    note: Optional[str] = None,
    current_user: User = Depends(require_customer),
    session: AsyncSession = Depends(get_session),
) -> StandardResponse[OrderResponse]:
    order = await cancel_customer_order_service(session, current_user.id, public_id, note)
    return StandardResponse(
        message="Order cancelled successfully and stock restored",
        data=_to_order_response(order),
    )


# --- Admin Endpoints ---

@admin_router.get("", response_model=StandardResponse[List[OrderResponse]])
async def admin_list_orders(
    status: Optional[str] = Query(None),
    order_number: Optional[str] = Query(None),
    customer: Optional[str] = Query(None),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    pagination: PaginationParams = Depends(),
    session: AsyncSession = Depends(get_session),
) -> StandardResponse[List[OrderResponse]]:
    orders, total = await admin_list_orders_service(
        session,
        status=status,
        order_number=order_number,
        customer_search=customer,
        date_from=date_from,
        date_to=date_to,
        page=pagination.page,
        page_size=pagination.page_size,
    )
    return StandardResponse(data=[_to_order_response(o) for o in orders])


@admin_router.get("/{public_id}", response_model=StandardResponse[OrderResponse])
async def admin_get_order(
    public_id: str,
    session: AsyncSession = Depends(get_session),
) -> StandardResponse[OrderResponse]:
    order = await get_order_by_public_id(session, public_id)
    return StandardResponse(data=_to_order_response(order))


@admin_router.post("", response_model=StandardResponse[OrderResponse], status_code=status.HTTP_201_CREATED)
async def admin_create_order(
    data: AdminOrderCreate,
    current_admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> StandardResponse[OrderResponse]:
    order = await admin_create_order_service(session, current_admin, data)
    return StandardResponse(
        message="Order created successfully",
        data=_to_order_response(order),
    )


@admin_router.put("/{public_id}", response_model=StandardResponse[OrderResponse])
async def admin_update_order(
    public_id: str,
    data: AdminOrderUpdate,
    current_admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> StandardResponse[OrderResponse]:
    order = await admin_update_order_service(session, public_id, data, current_admin.public_id)
    return StandardResponse(
        message="Order updated successfully",
        data=_to_order_response(order),
    )


@admin_router.patch("/{public_id}/status", response_model=StandardResponse[OrderResponse])
async def admin_update_order_status(
    public_id: str,
    data: OrderStatusUpdate,
    current_admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> StandardResponse[OrderResponse]:
    order = await admin_change_order_status_service(
        session, public_id, data.status, current_admin.public_id, data.note
    )
    return StandardResponse(
        message=f"Order status updated to {data.status.value}",
        data=_to_order_response(order),
    )


@admin_router.delete("/{public_id}", response_model=StandardResponse[None])
async def admin_delete_order(
    public_id: str,
    session: AsyncSession = Depends(get_session),
) -> StandardResponse[None]:
    order = await get_order_by_public_id(session, public_id)
    order.is_active = False
    session.add(order)
    await session.commit()
    return StandardResponse(message="Order soft-deleted successfully")


@admin_router.patch("/bulk-status", response_model=StandardResponse[dict])
async def admin_bulk_update_status(
    data: BulkOrderStatusUpdate,
    current_admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> StandardResponse[dict]:
    updated_count = 0
    errors = []
    for pid in data.order_public_ids:
        try:
            await admin_change_order_status_service(
                session, pid, data.status, current_admin.public_id, data.note
            )
            updated_count += 1
        except Exception as e:
            errors.append({"public_id": pid, "error": str(e)})

    return StandardResponse(
        message=f"Bulk status update complete. Updated: {updated_count}, Failed: {len(errors)}",
        data={"updated_count": updated_count, "errors": errors},
    )
