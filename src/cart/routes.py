from fastapi import APIRouter, Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from src.database import get_session
from src.common.response import StandardResponse
from src.auth.dependencies import require_customer
from src.auth.models import User
from src.cart.schemas import CartItemAdd, CartItemUpdate, CartResponse
from src.cart.services import (
    get_cart_service,
    add_item_to_cart_service,
    update_cart_item_service,
    remove_cart_item_service,
    clear_cart_service,
)

router = APIRouter(prefix="/cart", tags=["customer"])


@router.get("", response_model=StandardResponse[CartResponse])
async def get_cart(
    current_user: User = Depends(require_customer),
    session: AsyncSession = Depends(get_session),
) -> StandardResponse[CartResponse]:
    cart = await get_cart_service(session, current_user.id)
    return StandardResponse(data=cart)


@router.post("/items", response_model=StandardResponse[CartResponse])
async def add_item_to_cart(
    data: CartItemAdd,
    current_user: User = Depends(require_customer),
    session: AsyncSession = Depends(get_session),
) -> StandardResponse[CartResponse]:
    cart = await add_item_to_cart_service(session, current_user.id, data)
    return StandardResponse(message="Item added to cart", data=cart)


@router.patch("/items/{item_public_id}", response_model=StandardResponse[CartResponse])
async def update_cart_item(
    item_public_id: str,
    data: CartItemUpdate,
    current_user: User = Depends(require_customer),
    session: AsyncSession = Depends(get_session),
) -> StandardResponse[CartResponse]:
    cart = await update_cart_item_service(session, current_user.id, item_public_id, data)
    return StandardResponse(message="Cart updated", data=cart)


@router.delete("/items/{item_public_id}", response_model=StandardResponse[CartResponse])
async def remove_cart_item(
    item_public_id: str,
    current_user: User = Depends(require_customer),
    session: AsyncSession = Depends(get_session),
) -> StandardResponse[CartResponse]:
    cart = await remove_cart_item_service(session, current_user.id, item_public_id)
    return StandardResponse(message="Item removed from cart", data=cart)


@router.delete("", response_model=StandardResponse[CartResponse])
async def clear_cart(
    current_user: User = Depends(require_customer),
    session: AsyncSession = Depends(get_session),
) -> StandardResponse[CartResponse]:
    cart = await clear_cart_service(session, current_user.id)
    return StandardResponse(message="Cart cleared", data=cart)
