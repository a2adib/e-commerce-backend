from typing import List
from fastapi import APIRouter, Depends, status
from sqlmodel.ext.asyncio.session import AsyncSession
from src.database import get_session
from src.common.response import StandardResponse
from src.auth.dependencies import require_admin
from src.coupons.schemas import (
    CouponValidateRequest,
    CouponValidateResponse,
    CouponCreate,
    CouponResponse,
)
from src.coupons.services import (
    validate_coupon_service,
    create_coupon_service,
    list_coupons_service,
    get_coupon_by_public_id,
    toggle_coupon_active_service,
    delete_coupon_service,
)

public_router = APIRouter(prefix="/coupons", tags=["storefront"])
admin_router = APIRouter(
    prefix="/admin/coupons",
    tags=["admin"],
    dependencies=[Depends(require_admin)],
)


@public_router.post("/validate", response_model=StandardResponse[CouponValidateResponse])
async def validate_coupon(
    data: CouponValidateRequest,
    session: AsyncSession = Depends(get_session),
) -> StandardResponse[CouponValidateResponse]:
    is_valid, discount_amount, message, coupon = await validate_coupon_service(
        session, data.code, data.subtotal
    )

    new_subtotal = max(0.0, round(data.subtotal - discount_amount, 2))
    result = CouponValidateResponse(
        valid=is_valid,
        code=data.code.upper(),
        discount_type=coupon.discount_type if coupon else "none",
        discount_value=coupon.discount_value if coupon else 0.0,
        discount_amount=discount_amount,
        new_subtotal=new_subtotal,
        message=message,
    )
    return StandardResponse(data=result, message=message)


@admin_router.get("", response_model=StandardResponse[List[CouponResponse]])
async def admin_list_coupons(
    session: AsyncSession = Depends(get_session),
) -> StandardResponse[List[CouponResponse]]:
    coupons = await list_coupons_service(session, active_only=False)
    return StandardResponse(data=[CouponResponse.model_validate(c) for c in coupons])


@admin_router.post("", response_model=StandardResponse[CouponResponse], status_code=status.HTTP_201_CREATED)
async def admin_create_coupon(
    data: CouponCreate,
    session: AsyncSession = Depends(get_session),
) -> StandardResponse[CouponResponse]:
    coupon = await create_coupon_service(session, data)
    return StandardResponse(
        message=f"Coupon {coupon.code} created successfully",
        data=CouponResponse.model_validate(coupon),
    )


@admin_router.patch("/{public_id}/toggle-active", response_model=StandardResponse[CouponResponse])
async def admin_toggle_coupon(
    public_id: str,
    session: AsyncSession = Depends(get_session),
) -> StandardResponse[CouponResponse]:
    coupon = await toggle_coupon_active_service(session, public_id)
    return StandardResponse(
        message=f"Coupon status changed to {'active' if coupon.is_active else 'inactive'}",
        data=CouponResponse.model_validate(coupon),
    )


@admin_router.delete("/{public_id}", response_model=StandardResponse[None])
async def admin_delete_coupon(
    public_id: str,
    session: AsyncSession = Depends(get_session),
) -> StandardResponse[None]:
    await delete_coupon_service(session, public_id)
    return StandardResponse(message="Coupon deleted successfully")
