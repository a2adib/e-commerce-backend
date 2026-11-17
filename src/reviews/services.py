from typing import Dict, List
from sqlmodel import select, or_
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.orm import selectinload
from src.common.exceptions import http_400, http_404
from src.products.models import Product
from src.auth.models import User
from src.orders.models import Order, OrderItem
from src.orders.enums import OrderStatus
from src.reviews.models import Review
from src.reviews.schemas import ReviewCreate, ReviewResponse, ProductReviewsSummary


async def get_product_reviews_service(
    session: AsyncSession, product_slug_or_id: str
) -> ProductReviewsSummary:
    prod_stmt = select(Product).where(
        or_(Product.slug == product_slug_or_id, Product.public_id == product_slug_or_id),
        Product.is_active == True,
    )
    prod_res = await session.execute(prod_stmt)
    product = prod_res.scalar_one_or_none()
    if not product:
        raise http_404("Product not found", code="PRODUCT_NOT_FOUND")

    stmt = (
        select(Review)
        .where(Review.product_id == product.id, Review.is_active == True)
        .options(selectinload(Review.user))
        .order_by(Review.created_at.desc())
    )
    result = await session.execute(stmt)
    reviews = list(result.scalars().all())

    total = len(reviews)
    dist: Dict[str, int] = {"1": 0, "2": 0, "3": 0, "4": 0, "5": 0}
    sum_rating = 0

    for r in reviews:
        str_rating = str(r.rating)
        dist[str_rating] = dist.get(str_rating, 0) + 1
        sum_rating += r.rating

    avg_rating = round(sum_rating / total, 1) if total > 0 else 0.0

    return ProductReviewsSummary(
        avg_rating=avg_rating,
        total_reviews=total,
        rating_distribution=dist,
        reviews=[
            ReviewResponse(
                public_id=r.public_id,
                user_name=r.user.name if r.user else "Anonymous",
                rating=r.rating,
                title=r.title,
                comment=r.comment,
                is_verified_purchase=r.is_verified_purchase,
                created_at=r.created_at,
            )
            for r in reviews
        ],
    )


async def create_product_review_service(
    session: AsyncSession, product_public_id: str, user: User, data: ReviewCreate
) -> Review:
    prod_stmt = select(Product).where(
        Product.public_id == product_public_id, Product.is_active == True
    )
    prod_res = await session.execute(prod_stmt)
    product = prod_res.scalar_one_or_none()
    if not product:
        raise http_404("Product not found", code="PRODUCT_NOT_FOUND")

    # Check if user already reviewed
    existing_stmt = select(Review).where(
        Review.product_id == product.id,
        Review.user_id == user.id,
        Review.is_active == True,
    )
    existing_res = await session.execute(existing_stmt)
    if existing_res.scalar_one_or_none():
        raise http_400("You have already reviewed this product", code="ALREADY_REVIEWED")

    # Check if verified purchaser
    order_stmt = (
        select(OrderItem)
        .join(Order, OrderItem.order_id == Order.id)
        .where(
            OrderItem.product_id == product.id,
            Order.user_id == user.id,
            Order.status.in_([
                OrderStatus.CONFIRMED,
                OrderStatus.PROCESSING,
                OrderStatus.SHIPPED,
                OrderStatus.DELIVERED,
            ]),
        )
    )
    order_res = await session.execute(order_stmt)
    is_verified = order_res.scalar_one_or_none() is not None

    review = Review(
        product_id=product.id,
        user_id=user.id,
        rating=data.rating,
        title=data.title,
        comment=data.comment,
        is_verified_purchase=is_verified,
    )
    session.add(review)
    await session.commit()
    await session.refresh(review)
    review.user = user
    return review


async def delete_review_service(session: AsyncSession, public_id: str) -> None:
    stmt = select(Review).where(Review.public_id == public_id)
    res = await session.execute(stmt)
    review = res.scalar_one_or_none()
    if not review:
        raise http_404("Review not found", code="REVIEW_NOT_FOUND")
    review.is_active = False
    session.add(review)
    await session.commit()
