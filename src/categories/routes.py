from typing import List
from fastapi import APIRouter, Depends, status
from sqlmodel.ext.asyncio.session import AsyncSession

from src.database import get_session
from src.common.response import StandardResponse
from src.auth.dependencies import require_admin
from src.categories.schemas import (
    CategoryCreate,
    CategoryUpdate,
    CategoryResponse,
)
from src.categories.services import (
    create_category_service,
    get_category_service,
    list_categories_service,
    update_category_service,
    delete_category_service,
)

# Storefront router
public_router = APIRouter(prefix="/categories", tags=["storefront"])

# Admin router
admin_router = APIRouter(
    prefix="/admin/categories",
    tags=["admin"],
    dependencies=[Depends(require_admin)],
)


def _to_category_response(c) -> CategoryResponse:
    return CategoryResponse(
        public_id=c.public_id,
        name=c.name,
        slug=c.slug,
        description=c.description,
        image_url=c.image_url,
        parent_public_id=c.parent.public_id if c.parent else None,
        is_active=c.is_active,
        created_at=c.created_at,
    )


# --- Storefront Endpoints ---

@public_router.get("", response_model=StandardResponse[List[CategoryResponse]])
async def list_categories(
    session: AsyncSession = Depends(get_session),
) -> StandardResponse[List[CategoryResponse]]:
    categories = await list_categories_service(session, active_only=True)
    return StandardResponse(data=[_to_category_response(c) for c in categories])


# --- Admin Endpoints ---

@admin_router.get("", response_model=StandardResponse[List[CategoryResponse]])
async def admin_list_categories(
    session: AsyncSession = Depends(get_session),
) -> StandardResponse[List[CategoryResponse]]:
    categories = await list_categories_service(session, active_only=False)
    return StandardResponse(data=[_to_category_response(c) for c in categories])


@admin_router.get("/{public_id}", response_model=StandardResponse[CategoryResponse])
async def admin_get_category(
    public_id: str,
    session: AsyncSession = Depends(get_session),
) -> StandardResponse[CategoryResponse]:
    category = await get_category_service(session, public_id, active_only=False)
    return StandardResponse(data=_to_category_response(category))


@admin_router.post("", response_model=StandardResponse[CategoryResponse], status_code=status.HTTP_201_CREATED)
async def admin_create_category(
    data: CategoryCreate,
    session: AsyncSession = Depends(get_session),
) -> StandardResponse[CategoryResponse]:
    category = await create_category_service(session, data)
    return StandardResponse(
        message="Category created successfully",
        data=_to_category_response(category),
    )


@admin_router.put("/{public_id}", response_model=StandardResponse[CategoryResponse])
async def admin_update_category(
    public_id: str,
    data: CategoryUpdate,
    session: AsyncSession = Depends(get_session),
) -> StandardResponse[CategoryResponse]:
    category = await update_category_service(session, public_id, data)
    return StandardResponse(
        message="Category updated successfully",
        data=_to_category_response(category),
    )


@admin_router.delete("/{public_id}", response_model=StandardResponse[None])
async def admin_delete_category(
    public_id: str,
    session: AsyncSession = Depends(get_session),
) -> StandardResponse[None]:
    await delete_category_service(session, public_id)
    return StandardResponse(message="Category deactivated successfully")
