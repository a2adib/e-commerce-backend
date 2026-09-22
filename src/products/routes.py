from typing import List, Optional
from fastapi import APIRouter, Depends, Query, UploadFile, File, status
from sqlmodel.ext.asyncio.session import AsyncSession

from src.database import get_session
from src.common.response import StandardResponse
from src.common.filters import PaginationParams
from src.common.storage import get_storage_service, StorageService
from src.auth.dependencies import require_admin
from src.products.schemas import (
    ProductCreate,
    ProductUpdate,
    ProductResponse,
    ProductToggleActiveResponse,
)
from src.products.services import (
    create_product_service,
    get_product_service,
    get_product_by_slug_service,
    list_products_service,
    update_product_service,
    toggle_product_active_service,
    delete_product_service,
)

# Storefront router
public_router = APIRouter(prefix="/products", tags=["storefront"])

# Admin router
admin_router = APIRouter(
    prefix="/admin/products",
    tags=["admin"],
    dependencies=[Depends(require_admin)],
)


def _to_product_response(p) -> ProductResponse:
    return ProductResponse(
        public_id=p.public_id,
        name=p.name,
        slug=p.slug,
        description=p.description,
        price=p.price,
        compare_at_price=p.compare_at_price,
        sku=p.sku,
        stock_qty=p.stock_qty,
        images=p.images or [],
        is_featured=p.is_featured,
        category_public_id=p.category.public_id if p.category else "",
        category_name=p.category.name if p.category else None,
        is_active=p.is_active,
        created_at=p.created_at,
    )


# --- Storefront Endpoints ---

@public_router.get("", response_model=StandardResponse[List[ProductResponse]])
async def list_products(
    search: Optional[str] = Query(None, description="Search by name or description"),
    category: Optional[str] = Query(None, description="Category slug"),
    min_price: Optional[float] = Query(None, ge=0),
    max_price: Optional[float] = Query(None, ge=0),
    price_sort: Optional[str] = Query(None, pattern="^(asc|desc)$", description="Sort by price: asc or desc"),
    pagination: PaginationParams = Depends(),
    session: AsyncSession = Depends(get_session),
) -> StandardResponse[List[ProductResponse]]:
    products, total = await list_products_service(
        session,
        page=pagination.page,
        page_size=pagination.page_size,
        search=search,
        category_slug=category,
        min_price=min_price,
        max_price=max_price,
        price_sort=price_sort,
        active_only=True,
    )
    return StandardResponse(data=[_to_product_response(p) for p in products])


@public_router.get("/{slug}", response_model=StandardResponse[ProductResponse])
async def get_product_by_slug(
    slug: str,
    session: AsyncSession = Depends(get_session),
) -> StandardResponse[ProductResponse]:
    product = await get_product_by_slug_service(session, slug, active_only=True)
    return StandardResponse(data=_to_product_response(product))


# --- Admin Endpoints ---

@admin_router.get("", response_model=StandardResponse[List[ProductResponse]])
async def admin_list_products(
    search: Optional[str] = Query(None),
    category_id: Optional[str] = Query(None),
    active_only: bool = Query(False),
    pagination: PaginationParams = Depends(),
    session: AsyncSession = Depends(get_session),
) -> StandardResponse[List[ProductResponse]]:
    products, total = await list_products_service(
        session,
        page=pagination.page,
        page_size=pagination.page_size,
        search=search,
        category_public_id=category_id,
        active_only=active_only,
    )
    return StandardResponse(data=[_to_product_response(p) for p in products])


@admin_router.get("/{public_id}", response_model=StandardResponse[ProductResponse])
async def admin_get_product(
    public_id: str,
    session: AsyncSession = Depends(get_session),
) -> StandardResponse[ProductResponse]:
    product = await get_product_service(session, public_id, active_only=False)
    return StandardResponse(data=_to_product_response(product))


@admin_router.post("", response_model=StandardResponse[ProductResponse], status_code=status.HTTP_201_CREATED)
async def admin_create_product(
    data: ProductCreate,
    session: AsyncSession = Depends(get_session),
) -> StandardResponse[ProductResponse]:
    product = await create_product_service(session, data)
    return StandardResponse(
        message="Product created successfully",
        data=_to_product_response(product),
    )


@admin_router.put("/{public_id}", response_model=StandardResponse[ProductResponse])
async def admin_update_product(
    public_id: str,
    data: ProductUpdate,
    session: AsyncSession = Depends(get_session),
) -> StandardResponse[ProductResponse]:
    product = await update_product_service(session, public_id, data)
    return StandardResponse(
        message="Product updated successfully",
        data=_to_product_response(product),
    )


@admin_router.patch("/{public_id}/toggle-active", response_model=StandardResponse[ProductToggleActiveResponse])
async def admin_toggle_active(
    public_id: str,
    session: AsyncSession = Depends(get_session),
) -> StandardResponse[ProductToggleActiveResponse]:
    product = await toggle_product_active_service(session, public_id)
    return StandardResponse(
        message="Product active state toggled",
        data=ProductToggleActiveResponse(public_id=product.public_id, is_active=product.is_active),
    )


@admin_router.delete("/{public_id}", response_model=StandardResponse[None])
async def admin_delete_product(
    public_id: str,
    session: AsyncSession = Depends(get_session),
) -> StandardResponse[None]:
    await delete_product_service(session, public_id)
    return StandardResponse(message="Product deactivated successfully")


@admin_router.post("/upload-image", response_model=StandardResponse[dict])
async def upload_product_image(
    file: UploadFile = File(...),
    storage: StorageService = Depends(get_storage_service),
) -> StandardResponse[dict]:
    url = await storage.upload_file(file, folder="products")
    return StandardResponse(
        message="Image uploaded successfully",
        data={"url": url},
    )
