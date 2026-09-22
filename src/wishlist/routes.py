from typing import List
from fastapi import APIRouter, Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from src.database import get_session
from src.common.response import StandardResponse
from src.auth.dependencies import require_customer
from src.auth.models import User
from src.wishlist.schemas import WishlistItemResponse
from src.wishlist.services import (
    get_wishlist_service,
    add_to_wishlist_service,
    remove_from_wishlist_service,
)

router = APIRouter(prefix="/wishlist", tags=["customer"])


@router.get("", response_model=StandardResponse[List[WishlistItemResponse]])
async def get_wishlist(
    current_user: User = Depends(require_customer),
    session: AsyncSession = Depends(get_session),
) -> StandardResponse[List[WishlistItemResponse]]:
    items = await get_wishlist_service(session, current_user.id)
    return StandardResponse(data=items)


@router.post("/{product_id}", response_model=StandardResponse[WishlistItemResponse])
async def add_to_wishlist(
    product_id: str,
    current_user: User = Depends(require_customer),
    session: AsyncSession = Depends(get_session),
) -> StandardResponse[WishlistItemResponse]:
    item = await add_to_wishlist_service(session, current_user.id, product_id)
    return StandardResponse(message="Added to wishlist", data=item)


@router.delete("/{product_id}", response_model=StandardResponse[None])
async def remove_from_wishlist(
    product_id: str,
    current_user: User = Depends(require_customer),
    session: AsyncSession = Depends(get_session),
) -> StandardResponse[None]:
    await remove_from_wishlist_service(session, current_user.id, product_id)
    return StandardResponse(message="Removed from wishlist")
