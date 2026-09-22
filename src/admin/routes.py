from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlmodel.ext.asyncio.session import AsyncSession

from src.database import get_session
from src.common.response import StandardResponse
from src.common.filters import PaginationParams
from src.auth.dependencies import require_admin
from src.auth.schemas import UserResponse
from src.admin.schemas import (
    AdminUserUpdate,
    AdminUserDetailResponse,
    DashboardMetricsResponse,
)
from src.admin.services import (
    list_admin_users_service,
    get_admin_user_detail_service,
    update_admin_user_service,
    get_dashboard_metrics_service,
)

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(require_admin)],
)


@router.get("/users", response_model=StandardResponse[List[UserResponse]])
async def admin_list_users(
    search: Optional[str] = Query(None, description="Search by name, email, or phone"),
    role: Optional[str] = Query(None, description="Filter by role (admin/customer)"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    pagination: PaginationParams = Depends(),
    session: AsyncSession = Depends(get_session),
) -> StandardResponse[List[UserResponse]]:
    users, total = await list_admin_users_service(
        session,
        search=search,
        role=role,
        is_active=is_active,
        page=pagination.page,
        page_size=pagination.page_size,
    )
    return StandardResponse(
        data=[
            UserResponse(
                public_id=u.public_id,
                name=u.name,
                email=u.email,
                phone=u.phone,
                role=u.role.value if hasattr(u.role, "value") else str(u.role),
                avatar_url=u.avatar_url,
                is_active=u.is_active,
                created_at=u.created_at,
            )
            for u in users
        ]
    )


@router.get("/users/{public_id}", response_model=StandardResponse[AdminUserDetailResponse])
async def admin_get_user(
    public_id: str,
    session: AsyncSession = Depends(get_session),
) -> StandardResponse[AdminUserDetailResponse]:
    detail = await get_admin_user_detail_service(session, public_id)
    return StandardResponse(data=detail)


@router.patch("/users/{public_id}", response_model=StandardResponse[UserResponse])
async def admin_update_user(
    public_id: str,
    data: AdminUserUpdate,
    session: AsyncSession = Depends(get_session),
) -> StandardResponse[UserResponse]:
    user = await update_admin_user_service(session, public_id, data)
    return StandardResponse(
        message="User updated successfully",
        data=UserResponse(
            public_id=user.public_id,
            name=user.name,
            email=user.email,
            phone=user.phone,
            role=user.role.value if hasattr(user.role, "value") else str(user.role),
            avatar_url=user.avatar_url,
            is_active=user.is_active,
            created_at=user.created_at,
        ),
    )


@router.get("/dashboard", response_model=StandardResponse[DashboardMetricsResponse])
async def admin_dashboard(
    low_stock_threshold: int = Query(10, ge=0),
    session: AsyncSession = Depends(get_session),
) -> StandardResponse[DashboardMetricsResponse]:
    metrics = await get_dashboard_metrics_service(session, low_stock_threshold=low_stock_threshold)
    return StandardResponse(data=metrics)
