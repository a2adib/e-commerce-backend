from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from src.settings.models import StoreSettings
from src.settings.schemas import StoreSettingsUpdate

class StoreSettingsService:
    @staticmethod
    async def get_settings(session: AsyncSession) -> StoreSettings:
        result = await session.execute(select(StoreSettings))
        settings = result.scalars().first()
        if not settings:
            settings = StoreSettings(brand_name="STOREFRONT")
            session.add(settings)
            await session.commit()
            await session.refresh(settings)
        return settings

    @staticmethod
    async def update_settings(session: AsyncSession, data: StoreSettingsUpdate) -> StoreSettings:
        settings = await StoreSettingsService.get_settings(session)
        settings.brand_name = data.brand_name
        settings.logo_url = data.logo_url
        
        session.add(settings)
        await session.commit()
        await session.refresh(settings)
        return settings
