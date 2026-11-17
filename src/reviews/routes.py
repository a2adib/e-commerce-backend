from fastapi import APIRouter, Depends, status
from sqlmodel.ext.asyncio.session import AsyncSession
from src.database import get_session
from src.common.response import StandardResponse
from src.auth.dependencies import require_customer, require_admin
from src.auth.models import User
from src.reviews.schemas import ReviewCreate, ReviewResponse, ProductReviewsSummary
from src.reviews.services import (
    get_product_reviews_service,
    create_product_review_service,
    delete_review_service,
)

router = APIRouter(tags=["reviews"])
admin_router = APIRouter(
    prefix="/admin/reviews",
    tags=["admin"],
    dependencies=[Depends(require_admin)],
)


@router.get("/products/{slug_or_id}/reviews", response_model=StandardResponse[ProductReviewsSummary])
async def get_product_reviews(
    slug_or_id: str,
    session: AsyncSession = Depends(get_session),
) -> StandardResponse[ProductReviewsSummary]:
    summary = await get_product_reviews_service(session, slug_or_id)
    return StandardResponse(data=summary)


@router.post(
    "/products/{public_id}/reviews",
    response_model=StandardResponse[ReviewResponse],
    status_code=status.HTTP_201_CREATED,
)
async def submit_product_review(
    public_id: str,
    data: ReviewCreate,
    current_user: User = Depends(require_customer),
    session: AsyncSession = Depends(get_session),
) -> StandardResponse[ReviewResponse]:
    review = await create_product_review_service(session, public_id, current_user, data)
    return StandardResponse(
        message="Thank you for your review!",
        data=ReviewResponse(
            public_id=review.public_id,
            user_name=current_user.name,
            rating=review.rating,
            title=review.title,
            comment=review.comment,
            is_verified_purchase=review.is_verified_purchase,
            created_at=review.created_at,
        ),
    )


@admin_router.delete("/{public_id}", response_model=StandardResponse[None])
async def admin_delete_review(
    public_id: str,
    session: AsyncSession = Depends(get_session),
) -> StandardResponse[None]:
    await delete_review_service(session, public_id)
    return StandardResponse(message="Review removed successfully")
