from typing import List, Optional, Tuple
from datetime import datetime, timezone
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from src.common.exceptions import http_400, http_404
from src.coupons.models import Coupon
from src.coupons.schemas import CouponCreate, CouponUpdate


def calculate_discount(coupon: Coupon, subtotal: float) -> float:
    if coupon.discount_type == "percentage":
        discount = (subtotal * coupon.discount_value) / 100.0
        if coupon.max_discount_amount and discount > coupon.max_discount_amount:
            discount = coupon.max_discount_amount
    else:  # fixed
        discount = min(coupon.discount_value, subtotal)
    return round(discount, 2)


async def validate_coupon_service(
    session: AsyncSession, code: str, subtotal: float
) -> Tuple[bool, float, str, Optional[Coupon]]:
    clean_code = code.strip().upper()
    stmt = select(Coupon).where(Coupon.code == clean_code, Coupon.is_active == True)
    result = await session.execute(stmt)
    coupon = result.scalar_one_or_none()

    if not coupon:
        return False, 0.0, "Invalid coupon code", None

    now = datetime.now(timezone.utc)
    if coupon.valid_until:
        valid_until_utc = coupon.valid_until if coupon.valid_until.tzinfo else coupon.valid_until.replace(tzinfo=timezone.utc)
        if valid_until_utc < now:
            return False, 0.0, "This coupon has expired", coupon

    if coupon.usage_limit is not None and coupon.used_count >= coupon.usage_limit:
        return False, 0.0, "Coupon usage limit has been reached", coupon

    if subtotal < coupon.min_order_amount:
        return (
            False,
            0.0,
            f"Minimum order amount of ${coupon.min_order_amount:.2f} required for this coupon",
            coupon,
        )

    discount_amount = calculate_discount(coupon, subtotal)
    return True, discount_amount, "Coupon applied successfully", coupon


async def create_coupon_service(session: AsyncSession, data: CouponCreate) -> Coupon:
    clean_code = data.code.strip().upper()
    existing = await session.execute(select(Coupon).where(Coupon.code == clean_code))
    if existing.scalar_one_or_none():
        raise http_400("A coupon with this code already exists", code="COUPON_EXISTS")

    coupon = Coupon(**data.model_dump())
    session.add(coupon)
    await session.commit()
    await session.refresh(coupon)
    return coupon


async def list_coupons_service(
    session: AsyncSession, active_only: bool = False
) -> List[Coupon]:
    stmt = select(Coupon).order_by(Coupon.created_at.desc())
    if active_only:
        stmt = stmt.where(Coupon.is_active == True)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_coupon_by_public_id(session: AsyncSession, public_id: str) -> Coupon:
    stmt = select(Coupon).where(Coupon.public_id == public_id)
    result = await session.execute(stmt)
    coupon = result.scalar_one_or_none()
    if not coupon:
        raise http_404("Coupon not found", code="COUPON_NOT_FOUND")
    return coupon


async def toggle_coupon_active_service(session: AsyncSession, public_id: str) -> Coupon:
    coupon = await get_coupon_by_public_id(session, public_id)
    coupon.is_active = not coupon.is_active
    session.add(coupon)
    await session.commit()
    await session.refresh(coupon)
    return coupon


async def delete_coupon_service(session: AsyncSession, public_id: str) -> None:
    coupon = await get_coupon_by_public_id(session, public_id)
    coupon.is_active = False
    session.add(coupon)
    await session.commit()
