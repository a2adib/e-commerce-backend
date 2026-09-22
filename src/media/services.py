import mimetypes
from typing import Optional

import httpx
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.config import settings
from src.common.exceptions import http_400
from src.common.queries import create_instance, paginate_query
from src.media.models import MediaAsset


async def upload_to_vercel_blob(
    filename: str, data: bytes, content_type: Optional[str] = None
) -> str:
    if not content_type:
        content_type, _ = mimetypes.guess_type(filename) or "application/octet-stream"

    headers = {
        "Authorization": f"Bearer {settings.VERCEL_BLOB_TOKEN}",
        "Content-Type": content_type,
    }
    params = {"filename": filename}

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://blob.vercel-storage.com/upload",
            headers=headers,
            params=params,
            content=data,
        )
    if resp.status_code not in (200, 201):
        raise http_400(f"Vercel Blob upload failed: {resp.text}")

    body = resp.json()
    return body.get("url") or body.get("blobUrl") or ""


async def upload_media_service(
    session: AsyncSession,
    filename: str,
    file_bytes: bytes,
    mime_type: str,
    user_id: Optional[int] = None,
) -> MediaAsset:
    url = await upload_to_vercel_blob(filename, file_bytes, mime_type)

    asset = await create_instance(
        session,
        MediaAsset,
        filename=filename,
        url=url,
        mime_type=mime_type,
        size_bytes=len(file_bytes),
        uploaded_by=user_id,
    )
    return asset


async def reuse_media_service(
    session: AsyncSession, media_public_id: str
) -> MediaAsset:
    stmt = select(MediaAsset).where(MediaAsset.public_id == media_public_id)
    result = await session.execute(stmt)
    asset = result.scalar_one_or_none()
    if not asset or not asset.is_active:
        raise http_400("Media asset not found")
    return asset


async def list_media_gallery_service(
    session: AsyncSession,
    page: int,
    page_size: int,
    mime_filter: Optional[str] = None,
) -> tuple[list[MediaAsset], int]:
    stmt = select(MediaAsset).where(MediaAsset.is_active == True)
    if mime_filter:
        stmt = stmt.where(MediaAsset.mime_type.startswith(mime_filter))
    stmt = stmt.order_by(MediaAsset.created_at.desc())
    return await paginate_query(session, stmt, page=page, page_size=page_size)
