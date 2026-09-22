from typing import List, Optional
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.common.exceptions import http_404
from src.common.queries import create_instance
from src.addresses.models import Address
from src.addresses.schemas import AddressCreate, AddressUpdate


async def list_addresses_service(
    session: AsyncSession, user_id: int
) -> List[Address]:
    stmt = (
        select(Address)
        .where(Address.user_id == user_id, Address.is_active == True)
        .order_by(Address.is_default.desc(), Address.created_at.desc())
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_address_service(
    session: AsyncSession, user_id: int, public_id: str
) -> Address:
    stmt = select(Address).where(
        Address.user_id == user_id,
        Address.public_id == public_id,
        Address.is_active == True,
    )
    result = await session.execute(stmt)
    address = result.scalar_one_or_none()
    if not address:
        raise http_404("Address not found", code="ADDRESS_NOT_FOUND")
    return address


async def unset_defaults(session: AsyncSession, user_id: int):
    stmt = select(Address).where(Address.user_id == user_id, Address.is_default == True)
    defaults = (await session.execute(stmt)).scalars().all()
    for d in defaults:
        d.is_default = False
        session.add(d)


async def create_address_service(
    session: AsyncSession, user_id: int, data: AddressCreate
) -> Address:
    if data.is_default:
        await unset_defaults(session, user_id)

    # If first address for user, automatically mark as default
    existing_count = (
        await session.execute(select(Address).where(Address.user_id == user_id, Address.is_active == True))
    ).scalars().all()

    is_default = data.is_default or len(existing_count) == 0

    address = await create_instance(
        session,
        Address,
        user_id=user_id,
        full_name=data.full_name,
        phone=data.phone,
        address_line=data.address_line,
        city=data.city,
        district=data.district,
        postal_code=data.postal_code,
        is_default=is_default,
        is_active=True,
    )
    return address


async def update_address_service(
    session: AsyncSession, user_id: int, public_id: str, data: AddressUpdate
) -> Address:
    address = await get_address_service(session, user_id, public_id)
    update_dict = data.model_dump(exclude_unset=True)

    if update_dict.get("is_default") is True:
        await unset_defaults(session, user_id)

    for key, val in update_dict.items():
        setattr(address, key, val)

    session.add(address)
    await session.commit()
    await session.refresh(address)
    return address


async def delete_address_service(
    session: AsyncSession, user_id: int, public_id: str
):
    address = await get_address_service(session, user_id, public_id)
    address.is_active = False
    session.add(address)
    await session.commit()
