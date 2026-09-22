from typing import List
from fastapi import APIRouter, Depends, status
from sqlmodel.ext.asyncio.session import AsyncSession

from src.database import get_session
from src.common.response import StandardResponse
from src.auth.dependencies import require_customer
from src.auth.models import User
from src.addresses.schemas import AddressCreate, AddressUpdate, AddressResponse
from src.addresses.services import (
    list_addresses_service,
    get_address_service,
    create_address_service,
    update_address_service,
    delete_address_service,
)

router = APIRouter(prefix="/addresses", tags=["customer"])


def _to_address_response(addr) -> AddressResponse:
    return AddressResponse(
        public_id=addr.public_id,
        full_name=addr.full_name,
        phone=addr.phone,
        address_line=addr.address_line,
        city=addr.city,
        district=addr.district,
        postal_code=addr.postal_code,
        is_default=addr.is_default,
        created_at=addr.created_at,
    )


@router.get("", response_model=StandardResponse[List[AddressResponse]])
async def list_addresses(
    current_user: User = Depends(require_customer),
    session: AsyncSession = Depends(get_session),
) -> StandardResponse[List[AddressResponse]]:
    addresses = await list_addresses_service(session, current_user.id)
    return StandardResponse(data=[_to_address_response(a) for a in addresses])


@router.post("", response_model=StandardResponse[AddressResponse], status_code=status.HTTP_201_CREATED)
async def create_address(
    data: AddressCreate,
    current_user: User = Depends(require_customer),
    session: AsyncSession = Depends(get_session),
) -> StandardResponse[AddressResponse]:
    address = await create_address_service(session, current_user.id, data)
    return StandardResponse(
        message="Address created successfully",
        data=_to_address_response(address),
    )


@router.get("/{public_id}", response_model=StandardResponse[AddressResponse])
async def get_address(
    public_id: str,
    current_user: User = Depends(require_customer),
    session: AsyncSession = Depends(get_session),
) -> StandardResponse[AddressResponse]:
    address = await get_address_service(session, current_user.id, public_id)
    return StandardResponse(data=_to_address_response(address))


@router.patch("/{public_id}", response_model=StandardResponse[AddressResponse])
async def update_address(
    public_id: str,
    data: AddressUpdate,
    current_user: User = Depends(require_customer),
    session: AsyncSession = Depends(get_session),
) -> StandardResponse[AddressResponse]:
    address = await update_address_service(session, current_user.id, public_id, data)
    return StandardResponse(
        message="Address updated successfully",
        data=_to_address_response(address),
    )


@router.delete("/{public_id}", response_model=StandardResponse[None])
async def delete_address(
    public_id: str,
    current_user: User = Depends(require_customer),
    session: AsyncSession = Depends(get_session),
) -> StandardResponse[None]:
    await delete_address_service(session, current_user.id, public_id)
    return StandardResponse(message="Address deleted successfully")
