from typing import List
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.orm import selectinload

from src.common.exceptions import http_400, http_404
from src.common.queries import create_instance
from src.products.models import Product
from src.wishlist.models import WishlistItem
from src.wishlist.schemas import WishlistItemResponse


async def get_wishlist_service(
    session: AsyncSession, user_id: int
) -> List[WishlistItemResponse]:
    stmt = (
        select(WishlistItem)
        .where(WishlistItem.user_id == user_id)
        .options(selectinload(WishlistItem.product))
        .order_by(WishlistItem.created_at.desc())
    )
    result = await session.execute(stmt)
    items = result.scalars().all()

    return [
        WishlistItemResponse(
            public_id=it.public_id,
            product_public_id=it.product.public_id if it.product else "",
            product_name=it.product.name if it.product else "Unavailable",
            product_slug=it.product.slug if it.product else "",
            product_price=it.product.price if it.product else 0.0,
            product_image=it.product.images[0] if (it.product and it.product.images) else None,
            is_active=it.product.is_active if it.product else False,
            created_at=it.created_at,
        )
        for it in items
    ]


async def add_to_wishlist_service(
    session: AsyncSession, user_id: int, product_public_id: str
) -> WishlistItemResponse:
    # Validate product is active
    prod_stmt = select(Product).where(Product.public_id == product_public_id)
    prod_res = await session.execute(prod_stmt)
    product = prod_res.scalar_one_or_none()
    if not product or not product.is_active:
        raise http_400("Cannot add inactive product to wishlist", code="PRODUCT_INACTIVE")

    # Check if already in wishlist
    stmt = select(WishlistItem).where(
        WishlistItem.user_id == user_id, WishlistItem.product_id == product.id
    )
    existing = (await session.execute(stmt)).scalar_one_or_none()
    if existing:
        return WishlistItemResponse(
            public_id=existing.public_id,
            product_public_id=product.public_id,
            product_name=product.name,
            product_slug=product.slug,
            product_price=product.price,
            product_image=product.images[0] if product.images else None,
            is_active=product.is_active,
            created_at=existing.created_at,
        )

    item = await create_instance(
        session, WishlistItem, user_id=user_id, product_id=product.id
    )
    return WishlistItemResponse(
        public_id=item.public_id,
        product_public_id=product.public_id,
        product_name=product.name,
        product_slug=product.slug,
        product_price=product.price,
        product_image=product.images[0] if product.images else None,
        is_active=product.is_active,
        created_at=item.created_at,
    )


async def remove_from_wishlist_service(
    session: AsyncSession, user_id: int, product_public_id: str
):
    prod_stmt = select(Product).where(Product.public_id == product_public_id)
    product = (await session.execute(prod_stmt)).scalar_one_or_none()
    if not product:
        raise http_404("Product not found", code="PRODUCT_NOT_FOUND")

    stmt = select(WishlistItem).where(
        WishlistItem.user_id == user_id, WishlistItem.product_id == product.id
    )
    item = (await session.execute(stmt)).scalar_one_or_none()
    if item:
        await session.delete(item)
        await session.commit()
