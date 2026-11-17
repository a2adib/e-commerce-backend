from typing import List, Optional, Tuple
from datetime import datetime, timezone
import random
import string
from sqlmodel import select, or_, and_
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.orm import selectinload

from src.common.exceptions import http_400, http_404, http_422
from src.common.queries import create_instance, paginate_query
from src.auth.models import User
from src.products.models import Product
from src.cart.models import Cart, CartItem
from src.addresses.models import Address
from src.orders.models import Order, OrderItem, OrderStatusHistory
from src.orders.enums import OrderStatus, PaymentMethod, PaymentStatus, VALID_TRANSITIONS
from src.orders.schemas import (
    CheckoutRequest,
    AdminOrderCreate,
    AdminOrderUpdate,
    OrderStatusUpdate,
    BulkOrderStatusUpdate,
    OrderItemInput,
)
from src.orders.tasks import send_order_confirmation_email


def generate_order_number() -> str:
    """Generates human-readable unique order number like ORD-20260921-7X9K."""
    date_part = datetime.now(timezone.utc).strftime("%Y%m%d")
    rand_part = "".join(random.choices(string.ascii_uppercase + string.digits, k=4))
    return f"ORD-{date_part}-{rand_part}"


async def get_order_by_public_id(
    session: AsyncSession, public_id: str, active_only: bool = True
) -> Order:
    stmt = (
        select(Order)
        .where(Order.public_id == public_id)
        .options(
            selectinload(Order.items).selectinload(OrderItem.product),
            selectinload(Order.user),
            selectinload(Order.status_history),
        )
    )
    if active_only:
        stmt = stmt.where(Order.is_active == True)
    result = await session.execute(stmt)
    order = result.scalar_one_or_none()
    if not order:
        raise http_404("Order not found", code="ORDER_NOT_FOUND")

    # Explicit query for status history to ensure fresh list
    history_stmt = (
        select(OrderStatusHistory)
        .where(OrderStatusHistory.order_id == order.id)
        .order_by(OrderStatusHistory.created_at.desc())
    )
    histories = (await session.execute(history_stmt)).scalars().all()
    order.status_history = list(histories)

    return order


async def record_status_history(
    session: AsyncSession,
    order_id: int,
    from_status: Optional[OrderStatus],
    to_status: OrderStatus,
    changed_by: Optional[str],
    note: Optional[str] = None,
):
    history = OrderStatusHistory(
        order_id=order_id,
        from_status=from_status,
        to_status=to_status,
        changed_by=changed_by,
        note=note,
    )
    session.add(history)


async def checkout_service(
    session: AsyncSession, user: User, data: CheckoutRequest
) -> Order:
    # 1. Address AND phone are REQUIRED, otherwise 422
    shipping_dict: dict = {}
    if data.address_id:
        addr_stmt = select(Address).where(
            Address.public_id == data.address_id,
            Address.user_id == user.id,
            Address.is_active == True,
        )
        address_obj = (await session.execute(addr_stmt)).scalar_one_or_none()
        if not address_obj:
            raise http_422("Invalid address_id provided", code="INVALID_ADDRESS")
        shipping_dict = {
            "full_name": address_obj.full_name,
            "phone": data.phone or address_obj.phone,
            "address_line": address_obj.address_line,
            "city": address_obj.city,
            "district": address_obj.district,
            "postal_code": address_obj.postal_code,
        }
    elif data.address:
        shipping_dict = data.address.model_dump()
        if data.phone:
            shipping_dict["phone"] = data.phone
    else:
        raise http_422("Shipping address is required", code="ADDRESS_REQUIRED")

    if not shipping_dict.get("phone"):
        raise http_422("Phone number is required for checkout", code="PHONE_REQUIRED")
    if not shipping_dict.get("address_line"):
        raise http_422("Address line is required", code="ADDRESS_REQUIRED")

    # 2. Retrieve Cart
    cart_stmt = (
        select(Cart)
        .where(Cart.user_id == user.id)
        .options(selectinload(Cart.items).selectinload(CartItem.product))
    )
    cart = (await session.execute(cart_stmt)).scalar_one_or_none()
    if not cart or not cart.items:
        raise http_400("Your cart is empty", code="EMPTY_CART")

    # In one DB transaction: validate stock and active status, create order with price snapshots, decrement stock, clear cart
    subtotal = 0.0
    items_to_create = []

    for item in cart.items:
        prod_stmt = select(Product).where(Product.id == item.product_id).with_for_update()
        product = (await session.execute(prod_stmt)).scalar_one_or_none()

        if not product or not product.is_active:
            raise http_400(
                f"Product '{item.product.name if item.product else 'Unknown'}' is no longer available",
                code="PRODUCT_UNAVAILABLE",
            )
        if product.stock_qty < item.quantity:
            raise http_400(
                f"Insufficient stock for '{product.name}'. Requested: {item.quantity}, Available: {product.stock_qty}",
                code="INSUFFICIENT_STOCK",
            )

        line_total = round(product.price * item.quantity, 2)
        subtotal += line_total

        # Decrement stock
        product.stock_qty -= item.quantity
        session.add(product)

        items_to_create.append(
            {
                "product_id": product.id,
                "product_name": product.name,
                "unit_price": product.price,
                "quantity": item.quantity,
                "line_total": line_total,
            }
        )

    delivery_charge = 50.0  # standard shipping
    discount = 0.0
    applied_coupon_code = None

    if getattr(data, "coupon_code", None):
        from src.coupons.services import validate_coupon_service
        is_valid, discount_amount, _, coupon_obj = await validate_coupon_service(
            session, data.coupon_code, subtotal
        )
        if is_valid and coupon_obj:
            discount = discount_amount
            applied_coupon_code = coupon_obj.code
            coupon_obj.used_count += 1
            session.add(coupon_obj)

    total = max(0.0, round(subtotal + delivery_charge - discount, 2))

    order = Order(
        order_number=generate_order_number(),
        user_id=user.id,
        status=OrderStatus.PENDING,
        payment_method=data.payment_method,
        payment_status=PaymentStatus.PENDING,
        subtotal=round(subtotal, 2),
        delivery_charge=delivery_charge,
        discount=discount,
        total=total,
        shipping_snapshot=shipping_dict,
        note=data.note,
        coupon_code=applied_coupon_code,
        is_active=True,
    )
    session.add(order)
    await session.flush()

    for item_dict in items_to_create:
        order_item = OrderItem(order_id=order.id, **item_dict)
        session.add(order_item)

    # Initial status history
    await record_status_history(
        session,
        order_id=order.id,
        from_status=None,
        to_status=OrderStatus.PENDING,
        changed_by=f"customer:{user.public_id}",
        note="Order placed via checkout",
    )

    # Clear cart items directly from DB
    cart_items_stmt = select(CartItem).where(CartItem.cart_id == cart.id)
    items_to_del = (await session.execute(cart_items_stmt)).scalars().all()
    for item in items_to_del:
        await session.delete(item)

    await session.commit()

    # Queue confirmation email task in background without blocking
    try:
        send_order_confirmation_email.apply_async(
            args=[order.order_number, user.email, order.total],
            retry=False,
        )
    except Exception:
        pass

    return await get_order_by_public_id(session, order.public_id)


async def cancel_customer_order_service(
    session: AsyncSession, user_id: int, public_id: str, note: Optional[str] = None
) -> Order:
    order = await get_order_by_public_id(session, public_id)
    if order.user_id != user_id:
        raise http_404("Order not found", code="ORDER_NOT_FOUND")

    # Only while pending
    if order.status != OrderStatus.PENDING:
        raise http_400(
            f"Orders in '{order.status.value}' status cannot be cancelled by customer. Only 'pending' orders can be cancelled.",
            code="INVALID_STATUS_TRANSITION",
        )

    # Restore stock
    for item in order.items:
        if item.product_id:
            p_stmt = select(Product).where(Product.id == item.product_id).with_for_update()
            p = (await session.execute(p_stmt)).scalar_one_or_none()
            if p:
                p.stock_qty += item.quantity
                session.add(p)

    prev_status = order.status
    order.status = OrderStatus.CANCELLED
    session.add(order)

    await record_status_history(
        session,
        order_id=order.id,
        from_status=prev_status,
        to_status=OrderStatus.CANCELLED,
        changed_by=f"customer:user_{user_id}",
        note=note or "Order cancelled by customer",
    )

    await session.commit()
    return await get_order_by_public_id(session, public_id)


async def admin_change_order_status_service(
    session: AsyncSession,
    public_id: str,
    new_status: OrderStatus,
    admin_public_id: str,
    note: Optional[str] = None,
) -> Order:
    order = await get_order_by_public_id(session, public_id)

    if new_status not in VALID_TRANSITIONS.get(order.status, set()):
        raise http_400(
            f"Cannot transition order from '{order.status.value}' to '{new_status.value}'.",
            code="INVALID_STATUS_TRANSITION",
        )

    # If transitioning to CANCELLED, restore stock
    if new_status == OrderStatus.CANCELLED and order.status != OrderStatus.CANCELLED:
        for item in order.items:
            if item.product_id:
                p_stmt = select(Product).where(Product.id == item.product_id).with_for_update()
                p = (await session.execute(p_stmt)).scalar_one_or_none()
                if p:
                    p.stock_qty += item.quantity
                    session.add(p)

    prev_status = order.status
    order.status = new_status
    if new_status == OrderStatus.DELIVERED and order.payment_method == PaymentMethod.COD:
        order.payment_status = PaymentStatus.PAID

    session.add(order)

    await record_status_history(
        session,
        order_id=order.id,
        from_status=prev_status,
        to_status=new_status,
        changed_by=f"admin:{admin_public_id}",
        note=note,
    )

    await session.commit()
    return await get_order_by_public_id(session, public_id)


async def admin_create_order_service(
    session: AsyncSession, admin_user: User, data: AdminOrderCreate
) -> Order:
    user_id = None
    if data.user_public_id:
        user_res = await session.execute(
            select(User).where(User.public_id == data.user_public_id)
        )
        user = user_res.scalar_one_or_none()
        if not user:
            raise http_404("Customer user not found", code="USER_NOT_FOUND")
        user_id = user.id

    subtotal = 0.0
    items_to_create = []

    for item_in in data.items:
        prod_stmt = select(Product).where(Product.public_id == item_in.product_public_id).with_for_update()
        product = (await session.execute(prod_stmt)).scalar_one_or_none()
        if not product or not product.is_active:
            raise http_400(
                f"Product '{item_in.product_public_id}' is inactive or non-existent",
                code="PRODUCT_UNAVAILABLE",
            )
        if product.stock_qty < item_in.quantity:
            raise http_400(
                f"Insufficient stock for '{product.name}'. Available: {product.stock_qty}",
                code="INSUFFICIENT_STOCK",
            )

        line_total = round(product.price * item_in.quantity, 2)
        subtotal += line_total
        product.stock_qty -= item_in.quantity
        session.add(product)

        items_to_create.append(
            {
                "product_id": product.id,
                "product_name": product.name,
                "unit_price": product.price,
                "quantity": item_in.quantity,
                "line_total": line_total,
            }
        )

    total = round(subtotal + data.delivery_charge - data.discount, 2)

    order = Order(
        order_number=generate_order_number(),
        user_id=user_id,
        status=OrderStatus.CONFIRMED,
        payment_method=data.payment_method,
        payment_status=data.payment_status,
        subtotal=round(subtotal, 2),
        delivery_charge=data.delivery_charge,
        discount=data.discount,
        total=total,
        shipping_snapshot=data.shipping_address.model_dump(),
        note=data.note,
        is_active=True,
    )
    session.add(order)
    await session.flush()

    for item_dict in items_to_create:
        order_item = OrderItem(order_id=order.id, **item_dict)
        session.add(order_item)

    await record_status_history(
        session,
        order_id=order.id,
        from_status=None,
        to_status=OrderStatus.CONFIRMED,
        changed_by=f"admin:{admin_user.public_id}",
        note=f"Manual order created by admin: {data.note or ''}",
    )

    await session.commit()
    return await get_order_by_public_id(session, order.public_id)


async def admin_update_order_service(
    session: AsyncSession,
    public_id: str,
    data: AdminOrderUpdate,
    admin_public_id: str,
) -> Order:
    order = await get_order_by_public_id(session, public_id)
    if order.status not in (OrderStatus.PENDING, OrderStatus.CONFIRMED):
        raise http_400(
            f"Cannot edit order in status '{order.status.value}'. Editing is only allowed while pending or confirmed.",
            code="ORDER_NOT_EDITABLE",
        )

    if data.shipping_address:
        order.shipping_snapshot = data.shipping_address.model_dump()
    if data.note is not None:
        order.note = data.note
    if data.delivery_charge is not None:
        order.delivery_charge = data.delivery_charge
    if data.discount is not None:
        order.discount = data.discount

    if data.items is not None:
        for old_item in order.items:
            if old_item.product_id:
                p_stmt = select(Product).where(Product.id == old_item.product_id).with_for_update()
                p = (await session.execute(p_stmt)).scalar_one_or_none()
                if p:
                    p.stock_qty += old_item.quantity
                    session.add(p)
            await session.delete(old_item)

        await session.flush()

        subtotal = 0.0
        for item_in in data.items:
            prod_stmt = select(Product).where(Product.public_id == item_in.product_public_id).with_for_update()
            p = (await session.execute(prod_stmt)).scalar_one_or_none()
            if not p or not p.is_active:
                raise http_400(f"Product '{item_in.product_public_id}' is unavailable", code="PRODUCT_UNAVAILABLE")
            if p.stock_qty < item_in.quantity:
                raise http_400(f"Insufficient stock for '{p.name}'", code="INSUFFICIENT_STOCK")
            line_total = round(p.price * item_in.quantity, 2)
            subtotal += line_total
            p.stock_qty -= item_in.quantity
            session.add(p)

            new_item = OrderItem(
                order_id=order.id,
                product_id=p.id,
                product_name=p.name,
                unit_price=p.price,
                quantity=item_in.quantity,
                line_total=line_total,
            )
            session.add(new_item)

        order.subtotal = round(subtotal, 2)

    order.total = round(order.subtotal + order.delivery_charge - order.discount, 2)
    session.add(order)

    await record_status_history(
        session,
        order_id=order.id,
        from_status=order.status,
        to_status=order.status,
        changed_by=f"admin:{admin_public_id}",
        note="Order details updated by admin",
    )

    await session.commit()
    return await get_order_by_public_id(session, public_id)


async def admin_list_orders_service(
    session: AsyncSession,
    status: Optional[str] = None,
    order_number: Optional[str] = None,
    phone: Optional[str] = None,
    customer_search: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    page: int = 1,
    page_size: int = 20,
) -> Tuple[List[Order], int]:
    stmt = (
        select(Order)
        .where(Order.is_active == True)
        .options(
            selectinload(Order.items).selectinload(OrderItem.product),
            selectinload(Order.user),
            selectinload(Order.status_history),
        )
    )

    if status:
        stmt = stmt.where(Order.status == status)
    if order_number:
        stmt = stmt.where(Order.order_number.ilike(f"%{order_number}%"))
    if date_from:
        stmt = stmt.where(Order.created_at >= date_from)
    if date_to:
        stmt = stmt.where(Order.created_at <= date_to)

    if customer_search:
        stmt = stmt.outerjoin(Order.user).where(
            or_(
                User.name.ilike(f"%{customer_search}%"),
                User.email.ilike(f"%{customer_search}%"),
            )
        )

    stmt = stmt.order_by(Order.created_at.desc())
    return await paginate_query(session, stmt, page=page, page_size=page_size)


async def list_customer_orders_service(
    session: AsyncSession, user_id: int, page: int = 1, page_size: int = 20
) -> Tuple[List[Order], int]:
    stmt = (
        select(Order)
        .where(Order.user_id == user_id, Order.is_active == True)
        .options(
            selectinload(Order.items).selectinload(OrderItem.product),
            selectinload(Order.user),
            selectinload(Order.status_history),
        )
        .order_by(Order.created_at.desc())
    )
    return await paginate_query(session, stmt, page=page, page_size=page_size)


async def track_order_service(
    session: AsyncSession, order_number: str, phone: str
) -> Order:
    clean_num = order_number.strip().upper()
    clean_phone = "".join(filter(str.isdigit, phone))
    if not clean_phone or len(clean_phone) < 4:
        raise http_400("Please provide a valid phone number", code="INVALID_PHONE")

    stmt = (
        select(Order)
        .where(Order.order_number == clean_num, Order.is_active == True)
        .options(
            selectinload(Order.items).selectinload(OrderItem.product),
            selectinload(Order.user),
            selectinload(Order.status_history),
        )
    )
    result = await session.execute(stmt)
    order = result.scalar_one_or_none()
    if not order:
        raise http_404("Order not found with provided order number and phone", code="ORDER_NOT_FOUND")

    order_phone = "".join(filter(str.isdigit, str(order.shipping_snapshot.get("phone", ""))))
    if not order_phone or (clean_phone not in order_phone and order_phone not in clean_phone):
        raise http_404("Order not found with provided order number and phone", code="ORDER_NOT_FOUND")

    history_stmt = (
        select(OrderStatusHistory)
        .where(OrderStatusHistory.order_id == order.id)
        .order_by(OrderStatusHistory.created_at.desc())
    )
    histories = (await session.execute(history_stmt)).scalars().all()
    order.status_history = list(histories)

    return order

