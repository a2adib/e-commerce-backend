from typing import Optional, List, Tuple
from sqlmodel import select, func, or_
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.orm import selectinload

from src.common.exceptions import http_400, http_404
from src.common.queries import create_instance, paginate_query
from src.categories.services import slugify
from src.categories.models import Category
from src.products.models import Product
from src.products.schemas import ProductCreate, ProductUpdate


async def create_product_service(
    session: AsyncSession, data: ProductCreate
) -> Product:
    # Resolve category
    cat_res = await session.execute(
        select(Category).where(Category.public_id == data.category_public_id)
    )
    category = cat_res.scalar_one_or_none()
    if not category:
        raise http_404("Category not found", code="CATEGORY_NOT_FOUND")

    slug = data.slug or slugify(data.name)
    existing = await session.execute(select(Product).where(Product.slug == slug))
    if existing.scalar_one_or_none():
        raise http_400(f"Product with slug '{slug}' already exists", code="SLUG_EXISTS")

    product = await create_instance(
        session,
        Product,
        name=data.name,
        slug=slug,
        description=data.description,
        price=data.price,
        compare_at_price=data.compare_at_price,
        sku=data.sku,
        stock_qty=data.stock_qty,
        images=data.images,
        is_featured=data.is_featured,
        category_id=category.id,
        is_active=True,
    )
    return await get_product_service(session, product.public_id, active_only=False)


async def get_product_service(
    session: AsyncSession, public_id: str, active_only: bool = False
) -> Product:
    stmt = (
        select(Product)
        .where(Product.public_id == public_id)
        .options(selectinload(Product.category))
    )
    if active_only:
        stmt = stmt.where(Product.is_active == True)
    result = await session.execute(stmt)
    product = result.scalar_one_or_none()
    if not product:
        raise http_404("Product not found", code="PRODUCT_NOT_FOUND")
    return product


async def get_product_by_slug_service(
    session: AsyncSession, slug: str, active_only: bool = True
) -> Product:
    stmt = (
        select(Product)
        .where(Product.slug == slug)
        .options(selectinload(Product.category))
    )
    if active_only:
        stmt = stmt.where(Product.is_active == True)
    result = await session.execute(stmt)
    product = result.scalar_one_or_none()
    if not product:
        raise http_404("Product not found", code="PRODUCT_NOT_FOUND")
    return product


async def list_products_service(
    session: AsyncSession,
    page: int = 1,
    page_size: int = 20,
    search: Optional[str] = None,
    category_slug: Optional[str] = None,
    category_public_id: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    price_sort: Optional[str] = None,  # "asc" or "desc"
    active_only: bool = True,
) -> Tuple[List[Product], int]:
    stmt = select(Product).options(selectinload(Product.category))

    if active_only:
        stmt = stmt.where(Product.is_active == True)

    if search:
        term = f"%{search}%"
        stmt = stmt.where(
            or_(Product.name.ilike(term), Product.description.ilike(term))
        )

    if category_slug or category_public_id:
        stmt = stmt.join(Product.category)
        if category_slug:
            stmt = stmt.where(Category.slug == category_slug)
        if category_public_id:
            stmt = stmt.where(Category.public_id == category_public_id)

    if min_price is not None:
        stmt = stmt.where(Product.price >= min_price)
    if max_price is not None:
        stmt = stmt.where(Product.price <= max_price)

    if price_sort:
        if price_sort.lower() == "asc":
            stmt = stmt.order_by(Product.price.asc())
        elif price_sort.lower() == "desc":
            stmt = stmt.order_by(Product.price.desc())
    else:
        stmt = stmt.order_by(Product.created_at.desc())

    return await paginate_query(session, stmt, page=page, page_size=page_size)


async def update_product_service(
    session: AsyncSession, public_id: str, data: ProductUpdate
) -> Product:
    product = await get_product_service(session, public_id, active_only=False)
    update_dict = data.model_dump(exclude_unset=True)

    if "category_public_id" in update_dict:
        cat_pid = update_dict.pop("category_public_id")
        if cat_pid:
            cat_res = await session.execute(
                select(Category).where(Category.public_id == cat_pid)
            )
            category = cat_res.scalar_one_or_none()
            if not category:
                raise http_404("Category not found", code="CATEGORY_NOT_FOUND")
            product.category_id = category.id

    if "slug" in update_dict and update_dict["slug"]:
        new_slug = update_dict["slug"]
        existing = await session.execute(
            select(Product).where(Product.slug == new_slug, Product.id != product.id)
        )
        if existing.scalar_one_or_none():
            raise http_400(f"Slug '{new_slug}' is already taken", code="SLUG_EXISTS")

    for key, val in update_dict.items():
        setattr(product, key, val)

    session.add(product)
    await session.commit()
    await session.refresh(product)
    return await get_product_service(session, public_id, active_only=False)


async def toggle_product_active_service(
    session: AsyncSession, public_id: str
) -> Product:
    product = await get_product_service(session, public_id, active_only=False)
    product.is_active = not product.is_active
    session.add(product)
    await session.commit()
    await session.refresh(product)
    return product


async def delete_product_service(
    session: AsyncSession, public_id: str
) -> Product:
    product = await get_product_service(session, public_id, active_only=False)
    product.is_active = False
    session.add(product)
    await session.commit()
    return product
