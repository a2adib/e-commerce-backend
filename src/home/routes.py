from fastapi import APIRouter, Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from src.database import get_session
from src.common.response import StandardResponse
from src.auth.dependencies import require_admin
from src.home.schemas import HomePageUpdate, HomePageResponse
from src.home.services import (
    get_published_home_page_service,
    get_draft_home_page_service,
    save_draft_home_page_service,
    publish_home_page_service,
    discard_draft_home_page_service,
)

# Storefront Router
public_router = APIRouter(tags=["storefront"])

# Admin Router
admin_router = APIRouter(
    prefix="/admin/home",
    tags=["admin"],
    dependencies=[Depends(require_admin)],
)


def _to_hp_response(hp: HomePage) -> HomePageResponse:
    status_str = hp.status.value if hasattr(hp.status, "value") else str(hp.status)
    return HomePageResponse(
        public_id=hp.public_id,
        status=status_str,
        sections=hp.sections or [],
        updated_at=hp.updated_at,
        published_at=hp.published_at,
    )


# --- Public / Storefront Endpoint ---

@public_router.get("/home", response_model=StandardResponse[dict])
async def get_published_home(
    session: AsyncSession = Depends(get_session),
) -> StandardResponse[dict]:
    data = await get_published_home_page_service(session)
    return StandardResponse(data=data)


# --- Admin Endpoints ---

@admin_router.get("", response_model=StandardResponse[HomePageResponse])
async def get_draft_home(
    session: AsyncSession = Depends(get_session),
) -> StandardResponse[HomePageResponse]:
    draft = await get_draft_home_page_service(session)
    return StandardResponse(data=_to_hp_response(draft))


@admin_router.put("", response_model=StandardResponse[HomePageResponse])
async def save_draft_home(
    data: HomePageUpdate,
    session: AsyncSession = Depends(get_session),
) -> StandardResponse[HomePageResponse]:
    draft = await save_draft_home_page_service(session, data)
    return StandardResponse(
        message="Draft home page saved successfully",
        data=_to_hp_response(draft),
    )


@admin_router.post("/publish", response_model=StandardResponse[HomePageResponse])
async def publish_home(
    session: AsyncSession = Depends(get_session),
) -> StandardResponse[HomePageResponse]:
    published = await publish_home_page_service(session)
    return StandardResponse(
        message="Home page published successfully and cache invalidated",
        data=_to_hp_response(published),
    )


@admin_router.post("/discard", response_model=StandardResponse[HomePageResponse])
async def discard_draft_home(
    session: AsyncSession = Depends(get_session),
) -> StandardResponse[HomePageResponse]:
    draft = await discard_draft_home_page_service(session)
    return StandardResponse(
        message="Draft changes discarded",
        data=_to_hp_response(draft),
    )
