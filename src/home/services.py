import json
from datetime import datetime, timezone
from typing import Optional, List
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.common.exceptions import http_400, http_404
from src.common.queries import create_instance
from src.common.redis import get_redis_client
from src.home.models import HomePage, HomePageStatus
from src.home.schemas import HomePageUpdate

REDIS_HOME_PAGE_CACHE_KEY = "cache:home_page:published"


async def get_or_create_home_page(session: AsyncSession, status: HomePageStatus) -> HomePage:
    stmt = select(HomePage).where(HomePage.status == status).order_by(HomePage.updated_at.desc())
    result = await session.execute(stmt)
    hp = result.scalar_one_or_none()
    if not hp:
        # Create default empty layout
        hp = HomePage(status=status, sections=[])
        session.add(hp)
        await session.commit()
        await session.refresh(hp)
    return hp


async def get_published_home_page_service(session: AsyncSession) -> dict:
    # 1. Try Redis cache first
    redis = await get_redis_client()
    if redis:
        try:
            cached = await redis.get(REDIS_HOME_PAGE_CACHE_KEY)
            if cached:
                return json.loads(cached)
        except Exception:
            pass

    # 2. Query published from DB
    stmt = select(HomePage).where(HomePage.status == HomePageStatus.PUBLISHED).order_by(HomePage.updated_at.desc())
    result = await session.execute(stmt)
    hp = result.scalar_one_or_none()

    if not hp:
        # Return fallback empty sections
        data = {
            "public_id": "default",
            "status": "published",
            "sections": [],
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "published_at": None,
        }
    else:
        # Filter only visible sections for storefront audience
        visible_sections = [s for s in (hp.sections or []) if s.get("is_visible", True)]
        data = {
            "public_id": hp.public_id,
            "status": hp.status.value,
            "sections": visible_sections,
            "updated_at": hp.updated_at.isoformat(),
            "published_at": hp.published_at.isoformat() if hp.published_at else None,
        }

    # 3. Store in Redis
    if redis:
        try:
            await redis.setex(REDIS_HOME_PAGE_CACHE_KEY, 3600, json.dumps(data))
        except Exception:
            pass

    return data


async def get_draft_home_page_service(session: AsyncSession) -> HomePage:
    return await get_or_create_home_page(session, HomePageStatus.DRAFT)


async def save_draft_home_page_service(session: AsyncSession, data: HomePageUpdate) -> HomePage:
    draft = await get_or_create_home_page(session, HomePageStatus.DRAFT)
    # Serialize validated Pydantic discriminated union objects
    draft.sections = [s.model_dump() for s in data.sections]
    draft.updated_at = datetime.now(timezone.utc)
    session.add(draft)
    await session.commit()
    await session.refresh(draft)
    return draft


async def publish_home_page_service(session: AsyncSession) -> HomePage:
    draft = await get_or_create_home_page(session, HomePageStatus.DRAFT)
    published = await get_or_create_home_page(session, HomePageStatus.PUBLISHED)

    # Copy sections from draft to published
    now = datetime.now(timezone.utc)
    published.sections = list(draft.sections)
    published.published_at = now
    published.updated_at = now
    session.add(published)
    await session.commit()
    await session.refresh(published)

    # Invalidate Redis cache
    redis = await get_redis_client()
    if redis:
        try:
            await redis.delete(REDIS_HOME_PAGE_CACHE_KEY)
        except Exception:
            pass

    return published


async def discard_draft_home_page_service(session: AsyncSession) -> HomePage:
    draft = await get_or_create_home_page(session, HomePageStatus.DRAFT)
    published = await get_or_create_home_page(session, HomePageStatus.PUBLISHED)

    # Revert draft sections to published version
    draft.sections = list(published.sections)
    draft.updated_at = datetime.now(timezone.utc)
    session.add(draft)
    await session.commit()
    await session.refresh(draft)
    return draft
