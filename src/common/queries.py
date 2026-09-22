from typing import Type, TypeVar
from sqlmodel import SQLModel, select, func
from sqlmodel.ext.asyncio.session import AsyncSession

from .exceptions import http_404
from .utils import generate_public_id

ModelT = TypeVar("ModelT", bound=SQLModel)


async def get_instance_or_404(
    session: AsyncSession, model: Type[ModelT], public_id: str
) -> ModelT:
    stmt = select(model).where(model.public_id == public_id)  # type: ignore
    result = await session.execute(stmt)
    instance = result.scalar_one_or_none()
    if not instance:
        raise http_404(f"{model.__name__} not found")
    return instance


async def get_active_instance_or_404(
    session: AsyncSession, model: Type[ModelT], public_id: str
) -> ModelT:
    instance = await get_instance_or_404(session, model, public_id)
    if not instance.is_active:  # type: ignore
        raise http_404(f"{model.__name__} not found")
    return instance


async def soft_delete_instance(
    session: AsyncSession, instance: SQLModel
) -> SQLModel:
    instance.is_active = False  # type: ignore
    session.add(instance)
    await session.commit()
    await session.refresh(instance)
    return instance


async def create_instance(
    session: AsyncSession, model: Type[ModelT], **kwargs
) -> ModelT:
    if "public_id" not in kwargs:
        kwargs["public_id"] = generate_public_id()
    instance = model(**kwargs)
    session.add(instance)
    await session.commit()
    await session.refresh(instance)
    return instance


async def paginate_query(
    session: AsyncSession,
    stmt,
    page: int = 1,
    page_size: int = 20,
):
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await session.execute(count_stmt)).scalar() or 0

    offset = (page - 1) * page_size
    stmt = stmt.offset(offset).limit(page_size)
    result = await session.execute(stmt)
    items = result.scalars().all()

    return items, total
