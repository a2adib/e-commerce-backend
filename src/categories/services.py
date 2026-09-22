from typing import Optional, List
import re
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.orm import selectinload

from src.common.exceptions import http_400, http_404
from src.common.queries import create_instance
from src.categories.models import Category
from src.categories.schemas import CategoryCreate, CategoryUpdate


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    return text.strip("-")


async def create_category_service(
    session: AsyncSession, data: CategoryCreate
) -> Category:
    slug = data.slug or slugify(data.name)
    existing = await session.execute(select(Category).where(Category.slug == slug))
    if existing.scalar_one_or_none():
        raise http_400(f"Category with slug '{slug}' already exists", code="SLUG_EXISTS")

    parent_id = None
    if data.parent_public_id:
        parent_result = await session.execute(
            select(Category).where(Category.public_id == data.parent_public_id)
        )
        parent = parent_result.scalar_one_or_none()
        if not parent:
            raise http_404("Parent category not found", code="PARENT_NOT_FOUND")
        parent_id = parent.id

    category = await create_instance(
        session,
        Category,
        name=data.name,
        slug=slug,
        description=data.description,
        image_url=data.image_url,
        parent_id=parent_id,
        is_active=True,
    )
    # Reload parent relation
    category_loaded = await get_category_service(session, category.public_id)
    return category_loaded


async def get_category_service(
    session: AsyncSession, public_id: str, active_only: bool = False
) -> Category:
    stmt = (
        select(Category)
        .where(Category.public_id == public_id)
        .options(selectinload(Category.parent))
    )
    if active_only:
        stmt = stmt.where(Category.is_active == True)
    result = await session.execute(stmt)
    category = result.scalar_one_or_none()
    if not category:
        raise http_404("Category not found", code="CATEGORY_NOT_FOUND")
    return category


async def list_categories_service(
    session: AsyncSession, active_only: bool = True
) -> List[Category]:
    stmt = select(Category).options(selectinload(Category.parent)).order_by(Category.name.asc())
    if active_only:
        stmt = stmt.where(Category.is_active == True)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def update_category_service(
    session: AsyncSession, public_id: str, data: CategoryUpdate
) -> Category:
    category = await get_category_service(session, public_id, active_only=False)

    update_dict = data.model_dump(exclude_unset=True)

    if "parent_public_id" in update_dict:
        parent_pid = update_dict.pop("parent_public_id")
        if parent_pid:
            p_res = await session.execute(select(Category).where(Category.public_id == parent_pid))
            parent = p_res.scalar_one_or_none()
            if not parent:
                raise http_404("Parent category not found", code="PARENT_NOT_FOUND")
            category.parent_id = parent.id
        else:
            category.parent_id = None

    if "slug" in update_dict and update_dict["slug"]:
        new_slug = update_dict["slug"]
        existing = await session.execute(
            select(Category).where(Category.slug == new_slug, Category.id != category.id)
        )
        if existing.scalar_one_or_none():
            raise http_400(f"Slug '{new_slug}' is already taken", code="SLUG_EXISTS")

    for key, val in update_dict.items():
        setattr(category, key, val)

    session.add(category)
    await session.commit()
    await session.refresh(category)
    return await get_category_service(session, public_id)


async def delete_category_service(
    session: AsyncSession, public_id: str
) -> Category:
    category = await get_category_service(session, public_id, active_only=False)
    category.is_active = False
    session.add(category)
    await session.commit()
    return category
