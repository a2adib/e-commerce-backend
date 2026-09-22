from typing import Optional
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.orm import selectinload

from src.common.exceptions import http_400, http_404
from src.common.queries import create_instance
from src.products.models import Product
from src.cart.models import Cart, CartItem
from src.cart.schemas import CartItemAdd, CartItemUpdate, CartResponse, CartItemResponse


async def get_or_create_cart(session: AsyncSession, user_id: int) -> Cart:
    stmt = (
        select(Cart)
        .where(Cart.user_id == user_id)
        .options(selectinload(Cart.items).selectinload(CartItem.product))
    )
    result = await session.execute(stmt)
    cart = result.scalar_one_or_none()
    if not cart:
        cart = await create_instance(session, Cart, user_id=user_id, is_active=True)
        # Re-fetch with relationships loaded
        stmt = (
            select(Cart)
            .where(Cart.user_id == user_id)
            .options(selectinload(Cart.items).selectinload(CartItem.product))
        )
        cart = (await session.execute(stmt)).scalar_one()
    return cart


async def get_cart_response_for_user(session: AsyncSession, user_id: int) -> CartResponse:
    cart = await get_or_create_cart(session, user_id)

    # Query cart items directly with product joined to guarantee fresh state
    stmt = (
        select(CartItem)
        .where(CartItem.cart_id == cart.id)
        .options(selectinload(CartItem.product))
    )
    items = (await session.execute(stmt)).scalars().all()

    item_responses = []
    subtotal = 0.0
    total_items = 0

    for item in items:
        p = item.product
        is_available = bool(p and p.is_active and p.stock_qty >= item.quantity)
        price = p.price if p else 0.0
        line_total = round(price * item.quantity, 2)
        if is_available:
            subtotal += line_total
            total_items += item.quantity

        item_responses.append(
            CartItemResponse(
                public_id=item.public_id,
                product_public_id=p.public_id if p else "",
                product_name=p.name if p else "Unavailable Product",
                product_slug=p.slug if p else "",
                product_price=price,
                product_image=p.images[0] if (p and p.images) else None,
                quantity=item.quantity,
                line_total=line_total,
                is_available=is_available,
                stock_qty=p.stock_qty if p else 0,
            )
        )

    return CartResponse(
        public_id=cart.public_id,
        items=item_responses,
        subtotal=round(subtotal, 2),
        total_items=total_items,
    )


async def get_cart_service(session: AsyncSession, user_id: int) -> CartResponse:
    return await get_cart_response_for_user(session, user_id)


async def add_item_to_cart_service(
    session: AsyncSession, user_id: int, data: CartItemAdd
) -> CartResponse:
    # Verify product is active
    prod_stmt = select(Product).where(Product.public_id == data.product_public_id)
    p_res = await session.execute(prod_stmt)
    product = p_res.scalar_one_or_none()
    if not product or not product.is_active:
        raise http_400("Cannot add inactive or non-existent product to cart", code="PRODUCT_INACTIVE")

    if product.stock_qty < data.quantity:
        raise http_400(
            f"Not enough stock for '{product.name}'. Available: {product.stock_qty}",
            code="INSUFFICIENT_STOCK",
        )

    cart = await get_or_create_cart(session, user_id)

    # Check if item already exists in cart directly via query
    item_stmt = select(CartItem).where(CartItem.cart_id == cart.id, CartItem.product_id == product.id)
    existing_item = (await session.execute(item_stmt)).scalar_one_or_none()

    if existing_item:
        new_qty = existing_item.quantity + data.quantity
        if product.stock_qty < new_qty:
            raise http_400(
                f"Cannot add {data.quantity} more. Total in cart ({new_qty}) exceeds stock ({product.stock_qty}).",
                code="INSUFFICIENT_STOCK",
            )
        existing_item.quantity = new_qty
        session.add(existing_item)
    else:
        new_item = CartItem(cart_id=cart.id, product_id=product.id, quantity=data.quantity)
        session.add(new_item)

    await session.commit()
    return await get_cart_response_for_user(session, user_id)


async def update_cart_item_service(
    session: AsyncSession, user_id: int, item_public_id: str, data: CartItemUpdate
) -> CartResponse:
    cart = await get_or_create_cart(session, user_id)
    item_stmt = (
        select(CartItem)
        .where(CartItem.cart_id == cart.id, CartItem.public_id == item_public_id)
        .options(selectinload(CartItem.product))
    )
    item = (await session.execute(item_stmt)).scalar_one_or_none()
    if not item:
        raise http_404("Cart item not found", code="ITEM_NOT_FOUND")

    if item.product and item.product.stock_qty < data.quantity:
        raise http_400(
            f"Requested quantity ({data.quantity}) exceeds available stock ({item.product.stock_qty}).",
            code="INSUFFICIENT_STOCK",
        )

    item.quantity = data.quantity
    session.add(item)
    await session.commit()
    return await get_cart_response_for_user(session, user_id)


async def remove_cart_item_service(
    session: AsyncSession, user_id: int, item_public_id: str
) -> CartResponse:
    cart = await get_or_create_cart(session, user_id)
    item_stmt = select(CartItem).where(CartItem.cart_id == cart.id, CartItem.public_id == item_public_id)
    item = (await session.execute(item_stmt)).scalar_one_or_none()
    if not item:
        raise http_404("Cart item not found", code="ITEM_NOT_FOUND")

    await session.delete(item)
    await session.commit()
    return await get_cart_response_for_user(session, user_id)


async def clear_cart_service(session: AsyncSession, user_id: int) -> CartResponse:
    cart = await get_or_create_cart(session, user_id)
    item_stmt = select(CartItem).where(CartItem.cart_id == cart.id)
    items = (await session.execute(item_stmt)).scalars().all()
    for item in items:
        await session.delete(item)
    await session.commit()
    return await get_cart_response_for_user(session, user_id)
