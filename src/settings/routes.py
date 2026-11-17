from fastapi import APIRouter, Depends
from sqlmodel.ext.asyncio.session import AsyncSession
from src.database import get_session
from src.auth.dependencies import require_admin
from src.auth.models import User
from src.common.response import StandardResponse
from src.settings.schemas import StoreSettingsResponse, StoreSettingsUpdate
from src.settings.services import StoreSettingsService

router = APIRouter()

@router.get("", response_model=StandardResponse[StoreSettingsResponse])
@router.get("/", response_model=StandardResponse[StoreSettingsResponse], include_in_schema=False)
async def get_settings(session: AsyncSession = Depends(get_session)) -> StandardResponse[StoreSettingsResponse]:
    """Get global store settings."""
    settings = await StoreSettingsService.get_settings(session)
    return StandardResponse(data=StoreSettingsResponse.model_validate(settings))

@router.put("", response_model=StandardResponse[StoreSettingsResponse])
@router.put("/", response_model=StandardResponse[StoreSettingsResponse], include_in_schema=False)
async def update_settings(
    data: StoreSettingsUpdate,
    session: AsyncSession = Depends(get_session),
    current_admin: User = Depends(require_admin),
) -> StandardResponse[StoreSettingsResponse]:
    """Update store settings. Requires admin role."""
    settings = await StoreSettingsService.update_settings(session, data)
    return StandardResponse(
        message="Store settings updated successfully",
        data=StoreSettingsResponse.model_validate(settings),
    )
